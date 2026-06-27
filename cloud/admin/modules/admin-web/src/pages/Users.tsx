import React, { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { apiRequest } from '../api/client';
import { Card, Tbl, Badge, LBtn, Pager, Sheet, Modal, Fld, DetailRows, priBtn, secBtn, inpS, selS, finpS } from '../components/shared';

interface User { id: string; account: string; display_name: string | null; role: string; status: string; plan_code: string; created_at: string; updated_at?: string; }
interface List { items: User[]; total: number; limit: number; offset: number; }
const PAGE = 20;
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

  // URL 参数 ?action=create 自动打开创建表单
  useEffect(() => {
    if (searchParams.get('action') === 'create') {
      setShowCreate(true);
    }
  }, [searchParams]);

  const load = useCallback(async () => {
    setErr('');
    try {
      const params: Record<string, string | number | undefined> = { limit: PAGE, offset: pg * PAGE, search: q || undefined, status: sf || undefined };
      // 根据 roleFilter 附加角色筛选参数
      if (roleFilter) params.role = roleFilter;
      setD(await apiRequest<List>('/admin/users', { params }));
    }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '加载失败'); }
  }, [pg, q, sf, roleFilter]);
  useEffect(() => { load(); }, [load]);

  const updStatus = async (id: string, ns: string) => {
    await apiRequest(`/admin/users/${id}/status`, { method: 'PATCH', body: { status: ns } });
    setCa(null); load();
  };
  const del = async () => { if (!cd) return; await apiRequest(`/admin/users/${cd.id}`, { method: 'DELETE' }); setCd(null); load(); };
  const TP = d ? Math.ceil(d.total / PAGE) : 0;
  const title = getTitle(roleFilter);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.02em' }}>{title}</h2>
        <button onClick={() => setShowCreate(true)} style={priBtn}>+ 创建{roleFilter === 'admin' ? '管理员' : '用户'}</button>
      </div>
      <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
        <input placeholder="搜索账号或名称…" value={q} onChange={e => { setQ(e.target.value); setPg(0); }} style={inpS} />
        <select value={sf} onChange={e => { setSf(e.target.value); setPg(0); }} style={selS}>
          <option value="">全部状态</option><option value="active">正常</option><option value="blocked">已封禁</option><option value="deleted">已删除</option>
        </select>
        <button onClick={load} style={secBtn}>刷新</button>
      </div>
      {err && <div style={{ color: 'var(--red)', fontSize: 12, marginBottom: 12 }}>{err}</div>}
      <Card>
        <Tbl heads={['账号', '名称', '角色', '套餐', '状态', '注册时间', '']}>
          {d?.items.map(u => (
            <tr key={u.id}>
              <td style={{ fontWeight: 500 }}>{u.account}</td>
              <td style={{ color: 'var(--gray-500)' }}>{u.display_name || '—'}</td>
              <td><Badge t={u.role === 'admin' ? '管理员' : '用户'} c={u.role === 'admin' ? 'var(--blue)' : 'var(--gray-500)'} /></td>
              <td><code style={{ fontSize: 12, color: 'var(--gray-600)' }}>{u.plan_code}</code></td>
              <td><span style={{ fontSize: 12, fontWeight: 500, color: SC[u.status] }}>{SL[u.status]}</span></td>
              <td style={{ color: 'var(--gray-500)', fontSize: 12 }}>{new Date(u.created_at).toLocaleString('zh-CN')}</td>
              <td style={{ textAlign: 'right' }}>
                <LBtn onClick={() => setDetail(u)}>详情</LBtn>
                <LBtn onClick={() => setEdit(u)}>编辑</LBtn>
                {u.status === 'active' && <LBtn c="#ff9500" onClick={() => setCa({ id: u.id, s: 'blocked' })}>封禁</LBtn>}
                {u.status === 'blocked' && <LBtn c="#34c759" onClick={() => setCa({ id: u.id, s: 'active' })}>解封</LBtn>}
                <LBtn c="#ff3b30" onClick={() => setCd(u)}>删除</LBtn>
              </td>
            </tr>
          ))}
        </Tbl>
      </Card>
      <Pager pg={pg} tp={TP} total={d?.total || 0} onPrev={() => setPg(pg - 1)} onNext={() => setPg(pg + 1)} />
      {detail && <Sheet title="用户详情" close={() => setDetail(null)}>
        <DetailRows rows={[['ID', detail.id], ['账号', detail.account], ['名称', detail.display_name], ['角色', detail.role], ['套餐', detail.plan_code], ['状态', detail.status], ['注册', new Date(detail.created_at).toLocaleString('zh-CN')], ['更新', detail.updated_at ? new Date(detail.updated_at).toLocaleString('zh-CN') : null]]} />
      </Sheet>}
      {ca && <Modal title="确认操作" close={() => setCa(null)} action={() => updStatus(ca.id, ca.s)} danger>
        <p>将用户状态改为 <b>{SL[ca.s]}</b>？</p>
      </Modal>}
      {cd && <Modal title="删除用户" close={() => setCd(null)} action={del} danger>
        <p>永久删除 <b>{cd.account}</b>？此操作不可撤销。</p>
      </Modal>}
      {showCreate && <UserForm roleFilter={roleFilter} close={() => setShowCreate(false)} done={() => { setShowCreate(false); load(); }} />}
      {edit && <UserForm roleFilter={roleFilter} user={edit} close={() => setEdit(null)} done={() => { setEdit(null); load(); }} />}
    </div>
  );
}

function UserForm({ user, roleFilter, close, done }: { user?: User; roleFilter?: string; close: () => void; done: () => void }) {
  const [acc, setAcc] = useState(user?.account || '');
  const [pw, setPw] = useState('');
  const [dn, setDn] = useState(user?.display_name || '');
  // 角色默认值：roleFilter 锁定时使用 roleFilter，否则沿用 user 角色
  const defaultRole = roleFilter || user?.role || 'user';
  const [role, setRole] = useState(defaultRole);
  const [pc, setPc] = useState(user?.plan_code || 'free');
  const [saving, setSaving] = useState(false);
  const isEdit = !!user;
  // 当 roleFilter 存在时，角色字段不可更改
  const roleLocked = !!roleFilter;

  const submit = async (e: React.FormEvent) => { e.preventDefault(); setSaving(true);
    try {
      if (isEdit) await apiRequest(`/admin/users/${user!.id}`, { method: 'PATCH', body: { display_name: dn || null, plan_code: pc, role } });
      else await apiRequest('/admin/users', { method: 'POST', body: { account: acc, password: pw, display_name: dn || null, role, plan_code: pc } });
      done();
    } catch (err: unknown) { alert(err instanceof Error ? err.message : '保存失败'); }
    finally { setSaving(false); }
  };

  return (
    <Sheet title={isEdit ? `编辑: ${user!.account}` : (roleFilter === 'admin' ? '创建管理员' : '创建用户')} close={close}>
      <form onSubmit={submit}>
        {!isEdit && <>
          <Fld label="账号 *"><input value={acc} onChange={e => setAcc(e.target.value)} required style={finpS} /></Fld>
          <Fld label="密码 *"><input type="password" value={pw} onChange={e => setPw(e.target.value)} required style={finpS} /></Fld>
        </>}
        <Fld label="展示名称"><input value={dn} onChange={e => setDn(e.target.value)} style={finpS} /></Fld>
        <Fld label="套餐编码"><input value={pc} onChange={e => setPc(e.target.value)} style={finpS} /></Fld>
        <Fld label="角色">
          {roleLocked ? (
            // 角色锁定时显示只读文本
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
        <div style={{ display: 'flex', gap: 8, marginTop: 20 }}>
          <button type="submit" disabled={saving} style={priBtn}>{saving ? '保存中…' : '保存'}</button>
          <button type="button" onClick={close} style={secBtn}>取消</button>
        </div>
      </form>
    </Sheet>
  );
}
