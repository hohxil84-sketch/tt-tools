import React, { useEffect, useState, useCallback } from 'react';
import { apiRequest } from '../api/client';
import { Card, Tbl, Badge, ActBtn, Pager, Sheet, Modal, DetailRows, secBtn, inpS, priBtn, showToast } from '../components/shared';

interface Role { id: string; name: string; code: string; is_system: boolean; created_at: string; description?: string | null; permissions?: Perm[]; }
interface Perm { id: string; code: string; name: string; resource: string; action: string; }
interface RoleList { items: Role[]; total: number; limit: number; offset: number; }
const PAGE = 50;

export default function Roles() {
  const [d, setD] = useState<RoleList | null>(null);
  const [search, setSearch] = useState(''); const [pg, setPg] = useState(0); const [err, setErr] = useState('');
  const [detail, setDetail] = useState<Role | null>(null);
  const [allPerms, setAllPerms] = useState<Perm[]>([]);
  const [create, setCreate] = useState(false);
  const [delTarget, setDelTarget] = useState<Role | null>(null);
  const [form, setForm] = useState({ name: '', code: '', description: '' });
  const [permForm, setPermForm] = useState<string[]>([]);

  // 资源分类中文名映射
  const RES_CN: Record<string, string> = {
    dashboard: '仪表盘', users: '用户管理', devices: '设备管理',
    orders: '订单管理', plans: '套餐管理', credits: '额度管理',
    providers: 'Provider 管理', features: '功能码管理', roles: '角色权限',
    audit: '审计日志', ops: '运维管理', batch: '批量操作', export: '数据导出',
  };

  const load = useCallback(async () => {
    setErr('');
    try { setD(await apiRequest<RoleList>('/admin/roles', { params: { limit: PAGE, offset: pg * PAGE, search: search || undefined } })); }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '加载失败'); }
  }, [pg, search]);
  useEffect(() => { load(); }, [load]);
  const TP = d ? Math.ceil(d.total / PAGE) : 0;

  const loadDetail = async (id: string) => {
    try {
      const [role, perms] = await Promise.all([
        apiRequest<Role>(`/admin/roles/${id}`),
        apiRequest<{ items: Perm[] }>('/admin/permissions'),
      ]);
      setDetail(role);
      setAllPerms(perms.items);
      setPermForm((role.permissions || []).map(p => p.id));
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : '加载详情失败'); }
  };

  const doCreate = async () => {
    try { await apiRequest('/admin/roles', { method: 'POST', body: form }); showToast('创建成功', 'success'); setCreate(false); setForm({ name: '', code: '', description: '' }); load(); }
    catch (e: unknown) { showToast(e instanceof Error ? e.message : '创建失败', 'error'); }
  };

  const doDelete = async () => {
    if (!delTarget) return;
    try { await apiRequest(`/admin/roles/${delTarget.id}`, { method: 'DELETE' }); showToast('删除成功', 'success'); setDelTarget(null); load(); }
    catch (e: unknown) { showToast(e instanceof Error ? e.message : '删除失败', 'error'); }
  };

  const savePerms = async () => {
    if (!detail) return;
    const dashPermId = allPerms.find(p => p.code === 'dashboard.read')?.id;
    const finalIds = dashPermId && !permForm.includes(dashPermId)
      ? [...permForm, dashPermId] : permForm;
    try {
      await apiRequest(`/admin/roles/${detail.id}/permissions`, { method: 'POST', body: { permission_ids: finalIds } });
      showToast('权限保存成功', 'success');
      setDetail(null);
    }
    catch (e: unknown) { showToast(e instanceof Error ? e.message : '保存权限失败', 'error'); }
  };

  const togglePerm = (pid: string) => {
    // dashboard.read 为必选，不允许取消
    const dashP = allPerms.find(p => p.code === 'dashboard.read');
    if (dashP && pid === dashP.id) return;
    setPermForm(prev => prev.includes(pid) ? prev.filter(id => id !== pid) : [...prev, pid]);
  };

  // Group permissions by resource
  const permsByResource: Record<string, Perm[]> = {};
  for (const p of allPerms) {
    if (!permsByResource[p.resource]) permsByResource[p.resource] = [];
    permsByResource[p.resource].push(p);
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.02em', margin: 0 }}>角色权限管理</h2>
        <button onClick={() => { setCreate(true); setForm({ name: '', code: '', description: '' }); }} style={priBtn}>新增角色</button>
      </div>
      <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
        <input placeholder="搜索角色名称..." value={search} onChange={e => { setSearch(e.target.value); setPg(0); }} style={inpS} />
        <button onClick={load} style={secBtn}>刷新</button>
      </div>
      {err && <div style={{ color: 'var(--red)', fontSize: 12, marginBottom: 12 }}>{err}</div>}
      <Card><Tbl heads={['角色名称', '编码', '系统内置', '创建时间', '']}>
        {d?.items.map(r => (
          <tr key={r.id}>
            <td style={{ fontWeight: 600 }}>{r.name}</td>
            <td><code style={{ fontSize: 12 }}>{r.code}</code></td>
            <td><Badge t={r.is_system ? '是' : '否'} c={r.is_system ? 'var(--orange)' : 'var(--gray-400)'} /></td>
            <td style={{ fontSize: 12, color: 'var(--gray-500)' }}>{new Date(r.created_at).toLocaleString('zh-CN')}</td>
            <td style={{ textAlign: 'right' }}>
              <ActBtn kind="role" onClick={() => loadDetail(r.id)}>权限</ActBtn>
              {!r.is_system && <ActBtn kind="delete" onClick={() => setDelTarget(r)}>删除</ActBtn>}
            </td>
          </tr>
        ))}
      </Tbl></Card>
      <Pager pg={pg} tp={TP} total={d?.total || 0} onPrev={() => setPg(pg - 1)} onNext={() => setPg(pg + 1)} />

      {/* 权限管理 Sheet */}
      {detail && <Sheet title={`${detail.name} — 权限配置`} close={() => setDetail(null)} maxHeight="none">
        <div style={{ marginBottom: 16 }}>
          {Object.entries(permsByResource).map(([resource, perms]) => (
            <div key={resource} style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4, color: 'var(--gray-600)' }}>{RES_CN[resource] || resource}</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {perms.map(p => {
                  const isMandatory = p.code === 'dashboard.read';
                  return (
                  <label key={p.id} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, padding: '4px 8px', borderRadius: 4, background: permForm.includes(p.id) ? 'var(--blue-50)' : 'var(--gray-50)', cursor: isMandatory ? 'default' : 'pointer', border: '1px solid ' + (permForm.includes(p.id) ? 'var(--blue)' : 'var(--gray-200)'), opacity: isMandatory ? 0.7 : 1 }}>
                    <input type="checkbox" checked={permForm.includes(p.id)} onChange={() => togglePerm(p.id)} disabled={isMandatory} style={{ margin: 0 }} />
                    {p.name}
                    {isMandatory && <span style={{ fontSize: 10, color: '#ff9500', marginLeft: 2 }}>(必选)</span>}
                  </label>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
        <button onClick={savePerms} style={priBtn}>保存权限</button>
      </Sheet>}

      {delTarget && <Modal title="删除角色" close={() => setDelTarget(null)} action={doDelete} danger>
        <p>确认删除角色 <b>{delTarget.name}</b>？此操作不可撤销。</p>
      </Modal>}

      {create && <Sheet title="新增角色" close={() => setCreate(false)}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <input placeholder="名称" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} style={inpS} />
          <input placeholder="编码 (如 editor)" value={form.code} onChange={e => setForm({ ...form, code: e.target.value })} style={inpS} />
          <input placeholder="描述（可选）" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} style={inpS} />
          <button onClick={doCreate} style={priBtn}>创建</button>
        </div>
      </Sheet>}
    </div>
  );
}
