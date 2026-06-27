import React, { useEffect, useState, useCallback } from 'react';
import { apiRequest } from '../api/client';
import { Card, Tbl, Badge, LBtn, Pager, Sheet, secBtn, inpS, selS, priBtn } from '../components/shared';

interface FC { id: string; code: string; name: string; category: string; is_active: boolean; description?: string | null; created_at: string; }
interface List { items: FC[]; total: number; limit: number; offset: number; }
const PAGE = 50;
const CATS: Record<string, string> = { local_free: '本地免费', local_paid: '本地付费', cloud_ai: '云端AI' };

export default function FeatureCodes() {
  const [d, setD] = useState<List | null>(null);
  const [cat, setCat] = useState(''); const [pg, setPg] = useState(0); const [err, setErr] = useState('');
  const [create, setCreate] = useState(false);
  const [edit, setEdit] = useState<FC | null>(null);
  const [form, setForm] = useState({ code: '', name: '', category: 'cloud_ai', description: '' });

  const load = useCallback(async () => {
    setErr('');
    try { setD(await apiRequest<List>('/admin/feature-codes/list', { params: { limit: PAGE, offset: pg * PAGE, category: cat || undefined } })); }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '加载失败'); }
  }, [pg, cat]);
  useEffect(() => { load(); }, [load]);
  const TP = d ? Math.ceil(d.total / PAGE) : 0;

  const doCreate = async () => {
    try {
      await apiRequest('/admin/feature-codes', { method: 'POST', body: { code: form.code, name: form.name, category: form.category, description: form.description || undefined } });
      setCreate(false); setForm({ code: '', name: '', category: 'cloud_ai', description: '' }); load();
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : '创建失败'); }
  };

  const doEdit = async () => {
    if (!edit) return;
    try {
      await apiRequest(`/admin/feature-codes/${edit.id}`, { method: 'PATCH', body: { name: form.name, category: form.category, description: form.description || undefined } });
      setEdit(null); load();
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : '编辑失败'); }
  };

  const doDelete = async (id: string) => {
    if (!confirm('确认删除此功能码？')) return;
    try { await apiRequest(`/admin/feature-codes/${id}`, { method: 'DELETE' }); load(); }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '删除失败'); }
  };

  const doToggle = async (fc: FC) => {
    try { await apiRequest(`/admin/feature-codes/${fc.id}`, { method: 'PATCH', body: { is_active: !fc.is_active } }); load(); }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '操作失败'); }
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
      <Card><Tbl heads={['功能码', '名称', '分类', '状态', '说明', '创建时间', '']}>
        {d?.items.map(fc => (
          <tr key={fc.id}>
            <td><code style={{ fontSize: 12, fontWeight: 600 }}>{fc.code}</code></td>
            <td style={{ fontWeight: 500 }}>{fc.name}</td>
            <td><Badge t={CATS[fc.category] || fc.category} c="var(--blue)" /></td>
            <td><span style={{ fontSize: 12, fontWeight: 500, color: fc.is_active ? '#34c759' : 'var(--gray-400)', cursor: 'pointer' }} onClick={() => doToggle(fc)}>{fc.is_active ? '启用' : '禁用'}</span></td>
            <td style={{ fontSize: 12, color: 'var(--gray-500)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>{fc.description || '—'}</td>
            <td style={{ fontSize: 12, color: 'var(--gray-500)' }}>{new Date(fc.created_at).toLocaleString('zh-CN')}</td>
            <td style={{ textAlign: 'right' }}>
              <LBtn onClick={() => { setEdit(fc); setForm({ code: fc.code, name: fc.name, category: fc.category, description: fc.description || '' }); }}>编辑</LBtn>
              <LBtn onClick={() => doDelete(fc.id)}>删除</LBtn>
            </td>
          </tr>
        ))}
      </Tbl></Card>
      <Pager pg={pg} tp={TP} total={d?.total || 0} onPrev={() => setPg(pg - 1)} onNext={() => setPg(pg + 1)} />

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
