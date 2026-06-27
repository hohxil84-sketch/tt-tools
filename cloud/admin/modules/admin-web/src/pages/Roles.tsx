import React, { useEffect, useState, useCallback } from 'react';
import { apiRequest } from '../api/client';
import { Card, Tbl, Badge, LBtn, Pager, Sheet, DetailRows, secBtn, inpS, priBtn } from '../components/shared';

interface Role { id: string; name: string; code: string; is_system: boolean; created_at: string; description?: string | null; permissions?: Perm[]; }
interface Perm { id: string; code: string; name: string; resource: string; action: string; }
interface RoleList { items: Role[]; total: number; limit: number; offset: number; }
const PAGE = 50;

export default function Roles() {
  const [d, setD] = useState<RoleList | null>(null);
  const [pg, setPg] = useState(0); const [err, setErr] = useState('');
  const [detail, setDetail] = useState<Role | null>(null);
  const [allPerms, setAllPerms] = useState<Perm[]>([]);
  const [create, setCreate] = useState(false);
  const [form, setForm] = useState({ name: '', code: '', description: '' });
  const [permForm, setPermForm] = useState<string[]>([]);

  const load = useCallback(async () => {
    setErr('');
    try { setD(await apiRequest<RoleList>('/admin/roles', { params: { limit: PAGE, offset: pg * PAGE } })); }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '加载失败'); }
  }, [pg]);
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
    try { await apiRequest('/admin/roles', { method: 'POST', body: form }); setCreate(false); setForm({ name: '', code: '', description: '' }); load(); }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '创建失败'); }
  };

  const doDelete = async (id: string) => {
    if (!confirm('确认删除此角色？')) return;
    try { await apiRequest(`/admin/roles/${id}`, { method: 'DELETE' }); load(); }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '删除失败'); }
  };

  const savePerms = async () => {
    if (!detail) return;
    try { await apiRequest(`/admin/roles/${detail.id}/permissions`, { method: 'POST', body: { permission_ids: permForm } }); loadDetail(detail.id); }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '保存权限失败'); }
  };

  const togglePerm = (pid: string) => {
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
      {err && <div style={{ color: 'var(--red)', fontSize: 12, marginBottom: 12 }}>{err}</div>}
      <Card><Tbl heads={['角色名称', '编码', '系统内置', '创建时间', '']}>
        {d?.items.map(r => (
          <tr key={r.id}>
            <td style={{ fontWeight: 600 }}>{r.name}</td>
            <td><code style={{ fontSize: 12 }}>{r.code}</code></td>
            <td><Badge t={r.is_system ? '是' : '否'} c={r.is_system ? 'var(--orange)' : 'var(--gray-400)'} /></td>
            <td style={{ fontSize: 12, color: 'var(--gray-500)' }}>{new Date(r.created_at).toLocaleString('zh-CN')}</td>
            <td style={{ textAlign: 'right' }}>
              <LBtn onClick={() => loadDetail(r.id)}>权限</LBtn>
              {!r.is_system && <LBtn onClick={() => doDelete(r.id)}>删除</LBtn>}
            </td>
          </tr>
        ))}
      </Tbl></Card>
      <Pager pg={pg} tp={TP} total={d?.total || 0} onPrev={() => setPg(pg - 1)} onNext={() => setPg(pg + 1)} />

      {/* 权限管理 Sheet */}
      {detail && <Sheet title={`${detail.name} — 权限配置`} close={() => setDetail(null)}>
        <div style={{ marginBottom: 16 }}>
          {Object.entries(permsByResource).map(([resource, perms]) => (
            <div key={resource} style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4, color: 'var(--gray-600)' }}>{resource}</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {perms.map(p => (
                  <label key={p.id} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, padding: '4px 8px', borderRadius: 4, background: permForm.includes(p.id) ? 'var(--blue-50)' : 'var(--gray-50)', cursor: 'pointer', border: '1px solid ' + (permForm.includes(p.id) ? 'var(--blue)' : 'var(--gray-200)') }}>
                    <input type="checkbox" checked={permForm.includes(p.id)} onChange={() => togglePerm(p.id)} style={{ margin: 0 }} />
                    {p.name}
                  </label>
                ))}
              </div>
            </div>
          ))}
        </div>
        <button onClick={savePerms} style={priBtn}>保存权限</button>
      </Sheet>}

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
