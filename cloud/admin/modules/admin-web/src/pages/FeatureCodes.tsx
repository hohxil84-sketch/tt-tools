import React, { useEffect, useState, useCallback } from 'react';
import { apiRequest } from '../api/client';
import { Card, Tbl, Badge, ActBtn, Pager, Sheet, Modal, secBtn, inpS, selS, priBtn, showToast } from '../components/shared';

interface FC { id: string; code: string; name: string; category: string; is_active: boolean; plan_count?: number; description?: string | null; created_at: string; }
interface List { items: FC[]; total: number; limit: number; offset: number; }
const CATS: Record<string, string> = { local_free: '本地免费', local_paid: '本地付费', cloud_ai: '云端AI' };

export default function FeatureCodes() {
  const [d, setD] = useState<List | null>(null);
  const [cat, setCat] = useState(''); const [pg, setPg] = useState(0); const [err, setErr] = useState('');
  const [create, setCreate] = useState(false);
  const [delTarget, setDelTarget] = useState<FC | null>(null);
  const [edit, setEdit] = useState<FC | null>(null);
  const [toggleTarget, setToggleTarget] = useState<FC | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [limit, setLimit] = useState(10);
  const [form, setForm] = useState({ code: '', name: '', category: 'cloud_ai', description: '' });

  const load = useCallback(async () => {
    setErr('');
    try { setD(await apiRequest<List>('/admin/feature-codes/list', { params: { limit, offset: pg * limit, category: cat || undefined } })); }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '加载失败'); }
  }, [pg, cat, limit, refreshKey]);
  useEffect(() => { load(); }, [load]);
  const TP = d ? Math.ceil(d.total / limit) : 0;

  const doCreate = async () => {
    try {
      await apiRequest('/admin/feature-codes', { method: 'POST', body: { code: form.code, name: form.name, category: form.category, description: form.description || undefined } });
      showToast('创建成功', 'success');
      setCreate(false); setForm({ code: '', name: '', category: 'cloud_ai', description: '' }); setRefreshKey(k => k + 1); load();
    } catch (e: unknown) { showToast(e instanceof Error ? e.message : '创建失败', 'error'); }
  };

  const doEdit = async () => {
    if (!edit) return;
    try {
      await apiRequest(`/admin/feature-codes/${edit.id}`, { method: 'PATCH', body: { name: form.name, category: form.category, description: form.description || undefined } });
      showToast('保存成功', 'success');
      setEdit(null); setRefreshKey(k => k + 1); load();
    } catch (e: unknown) { showToast(e instanceof Error ? e.message : '编辑失败', 'error'); }
  };

  const doDelete = async () => {
    if (!delTarget) return;
    try { await apiRequest(`/admin/feature-codes/${delTarget.id}`, { method: 'DELETE' }); showToast('删除成功', 'success'); setDelTarget(null); setRefreshKey(k => k + 1); load(); }
    catch (e: unknown) { showToast(e instanceof Error ? e.message : '删除失败', 'error'); }
  };

  const doToggle = async (fc: FC) => {
    try { await apiRequest(`/admin/feature-codes/${fc.id}`, { method: 'PATCH', body: { is_active: !fc.is_active } }); showToast(fc.is_active ? '已禁用' : '已启用', 'success'); setRefreshKey(k => k + 1); load(); }
    catch (e: unknown) { showToast(e instanceof Error ? e.message : '操作失败', 'error'); }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.02em', margin: 0 }}>功能码管理</h2>
        <button onClick={() => { setCreate(true); setForm({ code: '', name: '', category: 'cloud_ai', description: '' }); }} style={priBtn}>新增功能码</button>
      </div>
      <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
        <select value={cat} onChange={e => { setCat(e.target.value); setPg(0); }} style={selS}>
          <option value="">全部分类</option><option value="local_free">本地免费</option><option value="local_paid">本地付费</option><option value="cloud_ai">云端AI</option>
        </select>
        <button onClick={load} style={secBtn}>刷新</button>
      </div>
      {err && <div style={{ color: 'var(--red)', fontSize: 12, marginBottom: 12 }}>{err}</div>}
      <Card><Tbl heads={['功能码', '名称', '分类', '状态', '关联套餐', '说明', '创建时间', '']} colAligns={['c','c','c','c','c','c','c','r']}>
        {d?.items.map(fc => (
          <tr key={fc.id}>
            <td style={{ fontSize: 13, width: '11%', textAlign: 'center' }}><code style={{ fontSize: 12, fontWeight: 600 }}>{fc.code}</code></td>
            <td style={{ fontWeight: 500, fontSize: 13, width: '13%', textAlign: 'center' }}>{fc.name}</td>
            <td style={{ fontSize: 13, width: '9%', textAlign: 'center' }}><Badge t={CATS[fc.category] || fc.category} c="var(--blue)" /></td>
            <td style={{ fontSize: 13, width: '8%', textAlign: 'center' }}><span style={{ fontSize: 12, fontWeight: 500, color: fc.is_active ? '#34c759' : 'var(--gray-400)', cursor: 'pointer' }} onClick={() => setToggleTarget(fc)}>{fc.is_active ? '启用' : '禁用'}</span></td>
            <td style={{ fontSize: 13, width: '8%', textAlign: 'center', paddingRight: 24 }}><span style={{ fontSize: 13, fontWeight: 600, color: (fc.plan_count || 0) > 0 ? 'var(--blue)' : 'var(--gray-400)' }}>{fc.plan_count ?? 0}</span></td>
            <td style={{ fontSize: 12, color: 'var(--gray-500)', width: '18%', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', textAlign: 'center' }}>{fc.description || '—'}</td>
            <td style={{ fontSize: 12, color: 'var(--gray-500)', width: '14%', textAlign: 'center' }}>{new Date(fc.created_at).toLocaleString('zh-CN')}</td>
            <td style={{ textAlign: 'right', width: '12%', whiteSpace: 'nowrap' }}>
              <ActBtn kind="edit" onClick={() => { setEdit(fc); setForm({ code: fc.code, name: fc.name, category: fc.category, description: fc.description || '' }); }}>编辑</ActBtn>
              <ActBtn kind="delete" onClick={() => setDelTarget(fc)}>删除</ActBtn>
            </td>
          </tr>
        ))}
      </Tbl></Card>
      <Pager pg={pg} tp={TP} total={d?.total || 0} limit={limit} onLimitChange={(n) => { setLimit(n); setPg(0); }} onPrev={() => setPg(pg - 1)} onNext={() => setPg(pg + 1)} />

      {delTarget && <Modal title="删除功能码" close={() => setDelTarget(null)} action={doDelete} danger>
        <p>确认删除功能码 <b>{delTarget.code}</b>？此操作不可撤销。</p>
      </Modal>}

      {toggleTarget && <Modal title={toggleTarget.is_active ? '禁用功能码' : '启用功能码'} close={() => setToggleTarget(null)} action={() => { doToggle(toggleTarget); setToggleTarget(null); }} danger={toggleTarget.is_active}>
        <p>确认{toggleTarget.is_active ? '禁用' : '启用'}功能码 <b>{toggleTarget.code}</b>？</p>
      </Modal>}

      {/* 新建 Sheet */}
      {create && <Sheet title="新增功能码" close={() => setCreate(false)}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <input placeholder="功能码 (如 my_new_feature_cloud)" value={form.code} onChange={e => setForm({ ...form, code: e.target.value })} style={inpS} />
          <input placeholder="名称" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} style={inpS} />
          <select value={form.category} onChange={e => setForm({ ...form, category: e.target.value })} style={{ ...inpS, width: '100%' }}>
            <option value="cloud_ai">云端AI</option><option value="local_paid">本地付费</option><option value="local_free">本地免费</option>
          </select>
          <input placeholder="说明（可选）" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} style={inpS} />
          <button onClick={doCreate} style={priBtn}>创建</button>
        </div>
      </Sheet>}

      {/* 编辑 Sheet */}
      {edit && <Sheet title={`编辑: ${edit.code}`} close={() => setEdit(null)}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <Fld label="功能码"><code style={{ fontSize: 12, color: 'var(--blue)' }}>{edit.code}</code></Fld>
          <Fld label="名称"><input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} style={inpS} /></Fld>
          <Fld label="分类">
            <select value={form.category} onChange={e => setForm({ ...form, category: e.target.value })} style={{ ...inpS, width: '100%' }}>
              <option value="cloud_ai">云端AI</option><option value="local_paid">本地付费</option><option value="local_free">本地免费</option>
            </select>
          </Fld>
          <Fld label="说明"><input value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} style={inpS} placeholder="说明（可选）" /></Fld>
          <button onClick={doEdit} style={priBtn}>保存</button>
        </div>
      </Sheet>}
    </div>
  );
}

/** 简单表单项 */
function Fld({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: 'var(--gray-600)', marginBottom: 4 }}>{label}</label>
      {children}
    </div>
  );
}
