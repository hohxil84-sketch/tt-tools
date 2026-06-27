import React, { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { apiRequest } from '../api/client';
import { Card, Tbl, Badge, ActBtn, Pager, Sheet, Modal, Fld, DetailRows, priBtn, secBtn, inpS, selS, finpS, showToast } from '../components/shared';

interface User { id: string; account: string; display_name: string | null; role: string; status: string; plan_id?: string | null; plan_name?: string | null; created_at: string; updated_at?: string | null; last_login_at?: string | null; device_count?: number; credit_balance?: number | null; role_names?: string | null; monthly_usage?: number; audit_count?: number; period_end?: string | null; }
interface PlanOption { id: string; name: string; }
interface RoleOption { id: string; name: string; code: string; is_system: boolean; }
interface CreditAccount { id: string; balance: number; plan_name?: string | null; status: string; }
interface List { items: User[]; total: number; limit: number; offset: number; }
const SL: Record<string, string> = { active: '正常', blocked: '已封禁', deleted: '已删除' };
const SC: Record<string, string> = { active: '#34c759', blocked: '#ff9500', deleted: '#ff3b30' };

/** 根据 roleFilter 决定页面标题 */
function getTitle(roleFilter?: string): string {
  if (roleFilter === 'admin') return '系统用户';
  if (roleFilter === 'user') return '客户端用户';
  return '用户管理';
}

export default function Users({ roleFilter }: { roleFilter?: string }) {
  const [searchParams] = useSearchParams();
  const [d, setD] = useState<List | null>(null);
  const [q, setQ] = useState(''); const [sf, setSf] = useState(''); const [pg, setPg] = useState(0);
  const [err, setErr] = useState(''); const [detail, setDetail] = useState<User | null>(null);
  const [ca, setCa] = useState<{ id: string; s: string } | null>(null);
  const [cd, setCd] = useState<User | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [edit, setEdit] = useState<User | null>(null);
  const [resetPwUser, setResetPwUser] = useState<User | null>(null);
  const [newPw, setNewPw] = useState('');
  const [roleUser, setRoleUser] = useState<User | null>(null);
  const [creditUser, setCreditUser] = useState<User | null>(null);

  // === 批量操作 ===
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [batchTarget, setBatchTarget] = useState<{ action: string; label: string } | null>(null);
  const [batching, setBatching] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [limit, setLimit] = useState(10);

  const toggleSelect = (id: string) => {
    setSelected(prev => { const next = new Set(prev); if (next.has(id)) next.delete(id); else next.add(id); return next; });
  };
  const selectAll = () => {
    if (!d) return;
    const all = new Set(d.items.map(u => u.id));
    if (selected.size === d.items.length) setSelected(new Set()); else setSelected(all);
  };
  const clearSelection = () => setSelected(new Set());

  const doBatch = async () => {
    if (!batchTarget || selected.size === 0) return;
    setBatching(true);
    try {
      if (batchTarget.action === 'delete') {
        // 逐个删除
        let ok = 0, fail = 0;
        for (const uid of selected) {
          try { await apiRequest(`/admin/users/${uid}`, { method: 'DELETE' }); ok++; } catch { fail++; }
        }
        showToast(`删除成功 ${ok} 个` + (fail > 0 ? `，失败 ${fail} 个` : ''), fail > 0 ? 'error' : 'success');
      } else {
        // 批量改状态
        await apiRequest('/admin/users/batch/status', { method: 'POST', body: { ids: [...selected], status: batchTarget.action } });
        showToast(`批量${batchTarget.label}成功`, 'success');
      }
      clearSelection(); setBatchTarget(null); setRefreshKey(k => k + 1); load();
    } catch (e: unknown) { showToast(e instanceof Error ? e.message : '批量操作失败', 'error'); }
    finally { setBatching(false); }
  };

  // URL 参数 ?action=create 自动打开创建表单
  useEffect(() => {
    if (searchParams.get('action') === 'create') {
      setShowCreate(true);
    }
  }, [searchParams]);

  const load = useCallback(async () => {
    setErr('');
    try {
      const params: Record<string, string | number | undefined> = { limit, offset: pg * limit, search: q || undefined, status: sf || undefined };
      // 根据 roleFilter 附加角色筛选参数
      if (roleFilter) params.role = roleFilter;
      setD(await apiRequest<List>('/admin/users', { params }));
    }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '加载失败'); }
  }, [pg, q, sf, roleFilter, limit, refreshKey]);
  useEffect(() => { load(); }, [load]);

  const updStatus = async (id: string, ns: string) => {
    try {
      await apiRequest(`/admin/users/${id}/status`, { method: 'PATCH', body: { status: ns } });
      showToast('操作成功', 'success');
      setCa(null); setRefreshKey(k => k + 1); load();
    } catch (e: unknown) { showToast(e instanceof Error ? e.message : '操作失败', 'error'); }
  };
  const del = async () => {
    if (!cd) return;
    try {
      await apiRequest(`/admin/users/${cd.id}`, { method: 'DELETE' });
      showToast('删除成功', 'success');
      setCd(null); setRefreshKey(k => k + 1); load();
    } catch (e: unknown) { showToast(e instanceof Error ? e.message : '删除失败', 'error'); }
  };
  const resetPw = async () => { if (!resetPwUser || !newPw) { showToast('请输入新密码', 'error'); return; } try { await apiRequest(`/admin/users/${resetPwUser.id}/reset-password`, { method: 'POST', body: { new_password: newPw } }); showToast('密码重置成功', 'success'); setResetPwUser(null); setNewPw(''); setRefreshKey(k => k + 1); load(); } catch (e: unknown) { showToast(e instanceof Error ? e.message : '重置失败', 'error'); } };
  const isSystem = roleFilter === 'admin';
  const isClient = roleFilter === 'user';

  // 根据角色筛选条件动态构建表头
  const selectAllCheckbox = <input type="checkbox" checked={d ? selected.size === d.items.length && d.items.length > 0 : false} onChange={selectAll} style={{ width: 16, height: 16, cursor: 'pointer' }} />;
  const heads = isSystem
    ? [selectAllCheckbox, '账号', '名称', 'RBAC 角色', '状态', '设备', '最后登录', '审计', '更新时间', '']
    : isClient
      ? [selectAllCheckbox, '账号', '名称', '额度余额', '本月消费', '套餐', '到期时间', '状态', '设备', '最后登录', '更新时间', '']
      : [selectAllCheckbox, '账号', '名称', '角色', '额度余额', '套餐', '状态', '设备', '最后登录', '更新时间', ''];
  const colAligns: ('l'|'r'|'c')[] = isSystem
    ? ['c','c','c','c','c','c','c','c','c','r']
    : isClient
      ? ['c','c','c','c','c','c','c','c','c','c','c','r']
      : ['c','c','c','c','c','c','c','c','c','c','r'];
  const TP = d ? Math.ceil(d.total / limit) : 0;
  const title = getTitle(roleFilter);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.02em' }}>{title}</h2>
        <button onClick={() => setShowCreate(true)} style={priBtn}>+ 创建{roleFilter === 'admin' ? '管理员' : roleFilter === 'user' ? '用户' : ''}</button>
      </div>
      <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
        <input placeholder="搜索账号或名称…" value={q} onChange={e => { setQ(e.target.value); setPg(0); }} style={inpS} />
        <select value={sf} onChange={e => { setSf(e.target.value); setPg(0); }} style={selS}>
          <option value="">全部状态</option><option value="active">正常</option><option value="blocked">已封禁</option><option value="deleted">已删除</option>
        </select>
        <button onClick={load} style={secBtn}>刷新</button>
      </div>
      {err && <div style={{ color: 'var(--red)', fontSize: 12, marginBottom: 12 }}>{err}</div>}

      {/* 批量操作栏 */}
      {selected.size > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12, padding: '10px 16px', background: 'var(--blue-50)', borderRadius: 8, border: '1px solid var(--blue)' }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--blue)' }}>已选 {selected.size} 项</span>
          <ActBtn kind="block" onClick={() => setBatchTarget({ action: 'blocked', label: '封禁' })}>批量封禁</ActBtn>
          <ActBtn kind="unblock" onClick={() => setBatchTarget({ action: 'active', label: '解封' })}>批量解封</ActBtn>
          <ActBtn kind="delete" onClick={() => setBatchTarget({ action: 'delete', label: '删除' })}>批量删除</ActBtn>
          <button onClick={clearSelection} style={{ ...secBtn, fontSize: 11, marginLeft: 'auto' }}>取消选择</button>
        </div>
      )}

      <Card>
        <Tbl heads={heads} colAligns={colAligns}>
          {d?.items.map(u => {
            const lastLoginStr = u.last_login_at ? new Date(u.last_login_at).toLocaleString('zh-CN') : '—';
            const updatedStr = u.updated_at ? new Date(u.updated_at).toLocaleString('zh-CN') : '—';
            const balanceStr = u.credit_balance != null ? u.credit_balance.toLocaleString() : '—';
            const balanceColor = balanceStr === '—' ? 'var(--gray-400)' : (u.credit_balance ?? 0) > 0 ? '#34c759' : '#ff9500';
            const usageStr = (u.monthly_usage || 0).toLocaleString();
            // 操作按钮（三个视图共用）
            const actions = (
              <td style={{ textAlign: 'right', width: '22%', whiteSpace: 'nowrap' }}>
                <ActBtn kind="detail" onClick={() => setDetail(u)}>详情</ActBtn>
                <ActBtn kind="edit" onClick={() => setEdit(u)}>编辑</ActBtn>
                {u.role === 'admin' && <ActBtn kind="role" onClick={() => setRoleUser(u)}>角色</ActBtn>}
                {u.role === 'user' && <ActBtn kind="credit" onClick={() => setCreditUser(u)}>额度</ActBtn>}
                <ActBtn kind="password" onClick={() => { setResetPwUser(u); setNewPw(''); }}>密码</ActBtn>
                {u.status === 'active' && <ActBtn kind="block" onClick={() => setCa({ id: u.id, s: 'blocked' })}>封禁</ActBtn>}
                {u.status === 'blocked' && <ActBtn kind="unblock" onClick={() => setCa({ id: u.id, s: 'active' })}>解封</ActBtn>}
                <ActBtn kind="delete" onClick={() => setCd(u)}>删除</ActBtn>
              </td>
            );
            // 通用信息单元格
            const commonCells = (
              <>
                <td style={{ width: 30, padding: '8px 4px', textAlign: 'center' }}><input type="checkbox" checked={selected.has(u.id)} onChange={() => toggleSelect(u.id)} style={{ width: 16, height: 16, cursor: 'pointer' }} /></td>
                <td style={{ fontWeight: 500, fontSize: 13, width: '11%', textAlign: 'center' }}>{u.account}</td>
                <td style={{ color: 'var(--gray-500)', fontSize: 13, width: '8%', textAlign: 'center' }}>{u.display_name || '—'}</td>
              </>
            );
            // 根据视图类型渲染不同的列布局
            if (isSystem) {
              return (
                <tr key={u.id} style={{ background: selected.has(u.id) ? 'var(--blue-50)' : undefined }}>
                  {commonCells}
                  <td style={{ fontSize: 13, width: '10%', textAlign: 'center' }}><span style={{ fontSize: 12, fontWeight: 500, color: '#af52de' }}>{u.role_names || '—'}</span></td>
                  <td style={{ fontSize: 13, width: '7%', textAlign: 'center' }}><span style={{ fontSize: 12, fontWeight: 500, color: SC[u.status] }}>{SL[u.status]}</span></td>
                  <td style={{ fontSize: 13, width: '5%', textAlign: 'center', paddingRight: 24 }}><span style={{ fontSize: 12, fontWeight: 500, color: (u.device_count || 0) > 1 ? '#ff9500' : 'var(--gray-500)' }}>{u.device_count ?? 0}</span></td>
                  <td style={{ color: 'var(--gray-500)', fontSize: 12, width: '14%', textAlign: 'center' }}>{lastLoginStr}</td>
                  <td style={{ fontSize: 13, width: '5%', textAlign: 'center', paddingRight: 24 }}><span style={{ fontSize: 12, fontWeight: 500, color: (u.audit_count || 0) > 0 ? 'var(--gray-700)' : 'var(--gray-400)' }}>{u.audit_count ?? 0}</span></td>
                  <td style={{ color: 'var(--gray-400)', fontSize: 12, width: '13%', textAlign: 'center' }}>{updatedStr}</td>
                  {actions}
                </tr>
              );
            }
            if (isClient) {
              const periodEndStr = u.period_end ? new Date(u.period_end).toLocaleDateString('zh-CN') : '—';
              return (
                <tr key={u.id} style={{ background: selected.has(u.id) ? 'var(--blue-50)' : undefined }}>
                  {commonCells}
                  <td style={{ fontSize: 13, width: '7%', textAlign: 'center', paddingRight: 24 }}><span style={{ fontSize: 13, fontWeight: 600, color: balanceColor }}>{balanceStr}</span></td>
                  <td style={{ fontSize: 13, width: '5%', textAlign: 'center', paddingRight: 24 }}><span style={{ fontSize: 12, fontWeight: 500, color: (u.monthly_usage || 0) > 0 ? 'var(--gray-700)' : 'var(--gray-400)' }}>{usageStr}</span></td>
                  <td style={{ fontSize: 13, width: '5%', textAlign: 'center' }}><span style={{ fontSize: 12, fontWeight: 500 }}>{u.plan_name || '—'}</span></td>
                  <td style={{ color: 'var(--gray-500)', fontSize: 12, width: '7%', textAlign: 'center' }}>{periodEndStr}</td>
                  <td style={{ fontSize: 13, width: '5%', textAlign: 'center' }}><span style={{ fontSize: 12, fontWeight: 500, color: SC[u.status] }}>{SL[u.status]}</span></td>
                  <td style={{ fontSize: 13, width: '5%', textAlign: 'center', paddingRight: 24 }}><span style={{ fontSize: 12, fontWeight: 500, color: (u.device_count || 0) > 1 ? '#ff9500' : 'var(--gray-500)' }}>{u.device_count ?? 0}</span></td>
                  <td style={{ color: 'var(--gray-500)', fontSize: 12, width: '11%', textAlign: 'center' }}>{lastLoginStr}</td>
                  <td style={{ color: 'var(--gray-400)', fontSize: 12, width: '11%', textAlign: 'center' }}>{updatedStr}</td>
                  {actions}
                </tr>
              );
            }
            // 全部用户视图
            return (
              <tr key={u.id} style={{ background: selected.has(u.id) ? 'var(--blue-50)' : undefined }}>
                {commonCells}
                <td style={{ fontSize: 13, width: '6%', textAlign: 'center' }}><Badge t={u.role === 'admin' ? '管理员' : '用户'} c={u.role === 'admin' ? 'var(--blue)' : 'var(--gray-500)'} /></td>
                <td style={{ fontSize: 13, width: '7%', textAlign: 'center', paddingRight: 24 }}><span style={{ fontSize: 13, fontWeight: 600, color: balanceColor }}>{balanceStr}</span></td>
                <td style={{ fontSize: 13, width: '5%', textAlign: 'center' }}><span style={{ fontSize: 12, fontWeight: 500 }}>{u.plan_name || '—'}</span></td>
                <td style={{ fontSize: 13, width: '5%', textAlign: 'center' }}><span style={{ fontSize: 12, fontWeight: 500, color: SC[u.status] }}>{SL[u.status]}</span></td>
                <td style={{ fontSize: 13, width: '5%', textAlign: 'center', paddingRight: 24 }}><span style={{ fontSize: 12, fontWeight: 500, color: (u.device_count || 0) > 1 ? '#ff9500' : 'var(--gray-500)' }}>{u.device_count ?? 0}</span></td>
                <td style={{ color: 'var(--gray-500)', fontSize: 12, width: '12%', textAlign: 'center' }}>{lastLoginStr}</td>
                <td style={{ color: 'var(--gray-400)', fontSize: 12, width: '12%', textAlign: 'center' }}>{updatedStr}</td>
                {actions}
              </tr>
            );
          })}
        </Tbl>
      </Card>
      <Pager pg={pg} tp={TP} total={d?.total || 0} limit={limit} onLimitChange={(n) => { setLimit(n); setPg(0); }} onPrev={() => setPg(pg - 1)} onNext={() => setPg(pg + 1)} />
      {detail && <Sheet title="用户详情" close={() => setDetail(null)}>
        <DetailRows rows={[
          ['ID', detail.id],
          ['账号', detail.account],
          ['名称', detail.display_name],
          ['角色', detail.role === 'admin' ? '管理员 (admin)' : '用户 (user)'],
          ['状态', SL[detail.status] || detail.status],
          ['套餐', detail.plan_name || '—'],
          ['套餐到期', detail.period_end ? new Date(detail.period_end).toLocaleDateString('zh-CN') : '—'],
          ['额度余额', detail.credit_balance != null ? detail.credit_balance.toLocaleString() : '—'],
          ['RBAC 角色', detail.role_names || '—'],
          ['本月消费', (detail.monthly_usage || 0).toLocaleString()],
          ['绑定设备', detail.device_count ?? 0],
          ['最后登录', detail.last_login_at ? new Date(detail.last_login_at).toLocaleString('zh-CN') : '—'],
          ['操作审计', detail.audit_count ?? 0],
          ['注册时间', new Date(detail.created_at).toLocaleString('zh-CN')],
          ['更新时间', detail.updated_at ? new Date(detail.updated_at).toLocaleString('zh-CN') : '—'],
        ]} />
      </Sheet>}
      {ca && <Modal title="确认操作" close={() => setCa(null)} action={() => updStatus(ca.id, ca.s)} danger>
        <p>将用户状态改为 <b>{SL[ca.s]}</b>？</p>
      </Modal>}
      {cd && <Modal title="删除用户" close={() => setCd(null)} action={del} danger>
        <p>永久删除 <b>{cd.account}</b>？此操作不可撤销。</p>
      </Modal>}
      {showCreate && <UserForm roleFilter={roleFilter} close={() => setShowCreate(false)} done={() => { setShowCreate(false); setRefreshKey(k => k + 1); load(); }} />}
      {edit && <UserForm roleFilter={roleFilter} user={edit} close={() => setEdit(null)} done={() => { setEdit(null); setRefreshKey(k => k + 1); load(); }} />}
      {resetPwUser && <Modal title="重置密码" close={() => { setResetPwUser(null); setNewPw(''); }} action={resetPw}><p>为用户 <b>{resetPwUser.account}</b> 重置密码：</p><input type="password" value={newPw} onChange={e => setNewPw(e.target.value)} placeholder="输入新密码" style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--gray-300)', borderRadius: 'var(--radius-sm)', fontSize: 13 }} /></Modal>}
      {roleUser && <RoleAssignmentModal user={roleUser} close={() => setRoleUser(null)} done={() => { setRoleUser(null); setRefreshKey(k => k + 1); load(); }} />}
      {creditUser && <CreditAdjustModal user={creditUser} close={() => setCreditUser(null)} done={() => { setCreditUser(null); setRefreshKey(k => k + 1); load(); }} />}

      {batchTarget && <Modal title={`批量${batchTarget.label}`} close={() => setBatchTarget(null)} action={doBatch} danger={batchTarget.action === 'delete'}>
        <p>确认批量{batchTarget.label} <b>{selected.size}</b> 个用户？{batchTarget.action === 'delete' ? '此操作不可撤销。' : ''}</p>
      </Modal>}
    </div>
  );
}

function UserForm({ user, roleFilter, close, done }: { user?: User; roleFilter?: string; close: () => void; done: () => void }) {
  const [acc, setAcc] = useState(user?.account || '');
  const [pw, setPw] = useState('');
  const [dn, setDn] = useState(user?.display_name || '');
  const defaultRole = roleFilter || user?.role || 'user';
  const [role, setRole] = useState(defaultRole);
  const [planId, setPlanId] = useState(user?.plan_id || '');
  const [planOptions, setPlanOptions] = useState<PlanOption[]>([]);
  const [planLoading, setPlanLoading] = useState(true);
  const [planError, setPlanError] = useState('');
  const [saving, setSaving] = useState(false);
  const isEdit = !!user;
  const roleLocked = !!roleFilter;
  const isCreatingAdmin = !isEdit && role === 'admin';
  const isCreatingUser = !isEdit && role === 'user';
  const isEditingAdmin = isEdit && user?.role === 'admin';
  const isEditingUser = isEdit && user?.role === 'user';

  // 管理员创建/编辑时需要分配 RBAC 角色
  const [allRoles, setAllRoles] = useState<RoleOption[]>([]);
  const [selectedRoleIds, setSelectedRoleIds] = useState<Set<string>>(new Set());
  const [rolesLoading, setRolesLoading] = useState(false);
  // 编辑用户时显示的额度余额
  const [editCreditBalance, setEditCreditBalance] = useState<number | null>(null);

  // 加载套餐选项
  useEffect(() => {
    (async () => {
      setPlanError('');
      try {
        const data = await apiRequest<{ items: PlanOption[] }>('/admin/plans/options');
        setPlanOptions(data.items || []);
      } catch (err: unknown) {
        setPlanError(err instanceof Error ? err.message : '加载失败');
      }
      finally { setPlanLoading(false); }
    })();
  }, [user]);

  // 创建/编辑管理员时加载可用角色列表
  useEffect(() => {
    if (!isCreatingAdmin && !isEditingAdmin) return;
    (async () => {
      setRolesLoading(true);
      try {
        const [rolesRes, userRolesRes] = await Promise.all([
          apiRequest<{ items: RoleOption[] }>('/admin/roles'),
          isEdit ? apiRequest<RoleOption[]>(`/admin/users/${user!.id}/roles`) : Promise.resolve([]),
        ]);
        setAllRoles(rolesRes.items || []);
        if (isEdit) setSelectedRoleIds(new Set((userRolesRes || []).map(r => r.id)));
      } catch { showToast('角色列表加载失败', 'error'); }
      finally { setRolesLoading(false); }
    })();
  }, [isCreatingAdmin, isEditingAdmin]);

  // 编辑用户时显示额度余额（从已加载的用户数据获取）
  useEffect(() => {
    if (isEditingUser && user?.credit_balance != null) {
      setEditCreditBalance(user.credit_balance);
    }
  }, [isEditingUser, user]);

  const toggleRole = (rid: string) => {
    setSelectedRoleIds(prev => {
      const next = new Set(prev);
      if (next.has(rid)) next.delete(rid); else next.add(rid);
      return next;
    });
  };

  const submit = async (e: React.FormEvent) => { e.preventDefault();

    // 前端校验
    if (!dn.trim()) { showToast('请填写展示名称', 'error'); return; }
    if (isCreatingUser && !planId) { showToast('普通用户必须选择套餐', 'error'); return; }
    if (isCreatingAdmin && selectedRoleIds.size === 0) { showToast('管理员必须分配至少一个角色', 'error'); return; }

    setSaving(true);
    try {
      const body: Record<string, unknown> = { display_name: dn.trim() };
      if (planId) body.plan_id = planId;
      if (!isEdit && role !== 'user') body.role = role;
      if ((isCreatingAdmin || isEditingAdmin) && selectedRoleIds.size > 0) body.role_ids = [...selectedRoleIds];
      if (pw) body.password = pw;
      if (isEdit) {
        await apiRequest(`/admin/users/${user!.id}`, { method: 'PATCH', body });
        if (pw) await apiRequest(`/admin/users/${user!.id}/reset-password`, { method: 'POST', body: { new_password: pw } });
        if ((isCreatingAdmin || isEditingAdmin) && selectedRoleIds.size > 0) {
          await apiRequest(`/admin/users/${user!.id}/roles`, { method: 'POST', body: { role_ids: [...selectedRoleIds] } });
        }
      }
      else await apiRequest('/admin/users', { method: 'POST', body: { account: acc, password: pw, ...body } });
      showToast(isEdit ? '保存成功' : '创建成功', 'success');
      done();
    } catch (err: unknown) { showToast(err instanceof Error ? err.message : '保存失败', 'error'); }
    finally { setSaving(false); }
  };

  return (
    <Sheet title={isEdit ? `编辑: ${user!.account}` : (roleFilter === 'admin' ? '创建管理员' : '创建用户')} close={close}>
      <form onSubmit={submit}>
        {!isEdit && <>
          <Fld label="账号 *"><input value={acc} onChange={e => setAcc(e.target.value)} required style={finpS} /></Fld>
          <Fld label="密码 *"><input type="password" value={pw} onChange={e => setPw(e.target.value)} required style={finpS} /></Fld>
        </>}
        {isEdit && <Fld label="密码（留空则保持原密码）"><input type="password" value={pw} onChange={e => setPw(e.target.value)} placeholder="留空则保持原密码" style={finpS} /></Fld>}
        <Fld label="展示名称 *"><input value={dn} onChange={e => setDn(e.target.value)} required style={finpS} /></Fld>

        {/* 编辑用户时显示额度余额 */}
        {isEditingUser && editCreditBalance != null && (
          <Fld label="当前额度">
            <span style={{ fontSize: 18, fontWeight: 700, color: 'var(--orange)' }}>{editCreditBalance.toLocaleString()}</span>
            <span style={{ fontSize: 12, color: 'var(--gray-400)', marginLeft: 4 }}>额度</span>
          </Fld>
        )}
        <Fld label={isCreatingUser ? '套餐 *' : '套餐'}>
          {planLoading ? (
            <span style={{ fontSize: 12, color: 'var(--gray-400)' }}>加载中…</span>
          ) : planError ? (
            <span style={{ fontSize: 12, color: '#ff3b30' }} title={planError}>{planError}</span>
          ) : planOptions.length > 0 ? (
            <select
              value={planId}
              onChange={e => setPlanId(e.target.value)}
              required={isCreatingUser}
              style={finpS}
            >
              <option value="">{isCreatingUser ? '-- 必选 --' : '-- 选择套餐 --'}</option>
              {planOptions.map(o => (
                <option key={o.id} value={o.id}>{o.name}</option>
              ))}
            </select>
          ) : (
            <span style={{ fontSize: 12, color: 'var(--gray-400)' }}>暂无可用套餐</span>
          )}
        </Fld>
        <Fld label="角色">
          {roleLocked ? (
            <span style={{ fontSize: 14, fontWeight: 500, color: 'var(--gray-700)' }}>
              {role === 'admin' ? '管理员 (admin)' : '用户 (user)'}
            </span>
          ) : (
            <select value={role} onChange={e => setRole(e.target.value)} style={finpS}>
              <option value="user">user</option>
              <option value="admin">admin</option>
            </select>
          )}
        </Fld>

        {/* 创建管理员时显示角色分配 */}
        {(isCreatingAdmin || isEditingAdmin) && (
          <Fld label={isCreatingAdmin ? '分配角色 *' : '分配角色'}>
            {rolesLoading ? (
              <span style={{ fontSize: 12, color: 'var(--gray-400)' }}>加载中…</span>
            ) : (
              <div style={{ maxHeight: 200, overflowY: 'auto', border: '1px solid var(--gray-200)', borderRadius: 8, padding: 8 }}>
                {allRoles.map(r => (
                  <label key={r.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 4px', cursor: 'pointer', fontSize: 13, borderBottom: '1px solid var(--gray-100)' }}>
                    <input type="checkbox" checked={selectedRoleIds.has(r.id)} onChange={() => toggleRole(r.id)} />
                    <span style={{ fontWeight: 500 }}>{r.name}</span>
                    <code style={{ fontSize: 11, color: 'var(--gray-400)' }}>{r.code}</code>
                    {r.is_system && <span style={{ fontSize: 10, color: '#ff9500', background: 'rgba(255,149,0,0.1)', padding: '1px 6px', borderRadius: 8 }}>系统内置</span>}
                  </label>
                ))}
              </div>
            )}
          </Fld>
        )}

        <div style={{ display: 'flex', gap: 8, marginTop: 20 }}>
          <button type="submit" disabled={saving} style={priBtn}>{saving ? '保存中…' : '保存'}</button>
          <button type="button" onClick={close} style={secBtn}>取消</button>
        </div>
      </form>
    </Sheet>
  );
}

/** ==================== 角色分配弹窗（系统用户） ==================== */

function RoleAssignmentModal({ user, close, done }: { user: User; close: () => void; done: () => void }) {
  const [allRoles, setAllRoles] = useState<RoleOption[]>([]);
  const [assignedIds, setAssignedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [rolesRes, userRolesRes] = await Promise.all([
          apiRequest<{ items: RoleOption[] }>('/admin/roles'),
          apiRequest<RoleOption[]>(`/admin/users/${user.id}/roles`),
        ]);
        setAllRoles(rolesRes.items || []);
        setAssignedIds(new Set((userRolesRes || []).map(r => r.id)));
      } catch { showToast('角色数据加载失败', 'error'); }
      finally { setLoading(false); }
    })();
  }, [user.id]);

  const toggle = (roleId: string) => {
    setAssignedIds(prev => {
      const next = new Set(prev);
      if (next.has(roleId)) next.delete(roleId); else next.add(roleId);
      return next;
    });
  };

  const save = async () => {
    setSaving(true);
    try {
      await apiRequest(`/admin/users/${user.id}/roles`, { method: 'POST', body: { role_ids: [...assignedIds] } });
      showToast('角色分配成功', 'success');
      done();
    } catch (e: unknown) { showToast(e instanceof Error ? e.message : '保存失败', 'error'); }
    finally { setSaving(false); }
  };

  return (
    <Modal title={`角色权限: ${user.account}`} close={close} action={save}>
      {loading ? <p style={{ fontSize: 13, color: 'var(--gray-400)' }}>加载中…</p> : (
        <div style={{ maxHeight: 400, overflowY: 'auto' }}>
          {allRoles.map(r => (
            <label key={r.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0', borderBottom: '1px solid var(--gray-100)', cursor: 'pointer', fontSize: 13 }}>
              <input type="checkbox" checked={assignedIds.has(r.id)} onChange={() => toggle(r.id)} style={{ width: 16, height: 16 }} />
              <span style={{ fontWeight: 500 }}>{r.name}</span>
              <code style={{ fontSize: 11, color: 'var(--gray-400)' }}>{r.code}</code>
              {r.is_system && <span style={{ fontSize: 10, color: '#ff9500', background: 'rgba(255,149,0,0.1)', padding: '1px 6px', borderRadius: 8 }}>系统内置</span>}
            </label>
          ))}
        </div>
      )}
    </Modal>
  );
}

/** ==================== 额度调整弹窗（客户端用户） ==================== */

function CreditAdjustModal({ user, close, done }: { user: User; close: () => void; done: () => void }) {
  const [account, setAccount] = useState<CreditAccount | null>(null);
  const [loading, setLoading] = useState(true);
  const [amount, setAmount] = useState(0);
  const [desc, setDesc] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        // 通过 user_id 筛选查询该用户的额度账户
        const data = await apiRequest<{ items: CreditAccount[] }>('/admin/credits/accounts', { params: { user_id: user.id, limit: 1 } });
        if (data.items && data.items.length > 0) {
          setAccount(data.items[0]);
        } else {
          setAccount(null);
        }
      } catch {
        setAccount(null);
        showToast('额度账户加载失败', 'error');
      }
      finally { setLoading(false); }
    })();
  }, [user.id]);

  const adjust = async () => {
    if (amount === 0) { showToast('请输入调整额度', 'error'); return; }
    setSaving(true);
    try {
      await apiRequest('/admin/credits/adjust', { method: 'POST', body: { user_id: user.id, amount, description: desc || undefined } });
      showToast(`额度${amount > 0 ? '赠送' : '扣除'}成功`, 'success');
      done();
    } catch (e: unknown) { showToast(e instanceof Error ? e.message : '调整失败', 'error'); }
    finally { setSaving(false); }
  };

  return (
    <Modal title={`额度管理: ${user.account}`} close={close} action={adjust}>
      {loading ? <p style={{ fontSize: 13, color: 'var(--gray-400)' }}>加载中…</p> : (
        <div>
          <div style={{ marginBottom: 16, padding: '10px 14px', background: 'var(--gray-50)', borderRadius: 8 }}>
            <span style={{ fontSize: 12, color: 'var(--gray-500)' }}>当前余额：</span>
            <span style={{ fontSize: 20, fontWeight: 700, color: 'var(--gray-800)', marginLeft: 8 }}>
              {account ? account.balance.toLocaleString() : '—'}
            </span>
            {account && <span style={{ fontSize: 12, color: 'var(--gray-400)', marginLeft: 6 }}>额度</span>}
          </div>
          {account && (
            <div style={{ fontSize: 12, color: 'var(--gray-400)', marginBottom: 16 }}>
              套餐：{account.plan_name || '—'} · 状态：{account.status === 'active' ? '正常' : account.status}
            </div>
          )}
          <Fld label="调整额度（正数赠送，负数扣除）">
            <input type="number" value={amount} onChange={e => setAmount(Number(e.target.value))} style={finpS} placeholder="如 1000 或 -500" />
          </Fld>
          <Fld label="调整原因">
            <input value={desc} onChange={e => setDesc(e.target.value)} style={finpS} placeholder="选填" />
          </Fld>
        </div>
      )}
    </Modal>
  );
}
