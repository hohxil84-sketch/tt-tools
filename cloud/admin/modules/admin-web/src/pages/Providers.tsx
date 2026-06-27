import React, { useEffect, useState, useCallback } from 'react';
import { apiRequest } from '../api/client';
import { Card, Tbl, Badge, ActBtn, Pager, Sheet, Modal, DetailRows, secBtn, inpS, selS, priBtn, showToast } from '../components/shared';

interface P { id: string; name: string; provider_type: string; is_enabled: boolean; priority?: number; created_at: string; api_key_encrypted?: string | null; base_url?: string | null; models_json?: any; updated_at?: string; }
interface List { items: P[]; total: number; limit: number; offset: number; }
const PAGE = 20;

export default function Providers() {
  const [d, setD] = useState<List | null>(null);
  const [providerType, setProviderType] = useState(''); const [sf, setSf] = useState(''); const [pg, setPg] = useState(0); const [err, setErr] = useState('');
  const [detail, setDetail] = useState<P | null>(null);
  const [edit, setEdit] = useState<P | null>(null);
  const [create, setCreate] = useState(false);
  const [delTarget, setDelTarget] = useState<P | null>(null);
  const [form, setForm] = useState({ name: '', provider_type: 'deepseek', api_key_encrypted: '', base_url: '', models_json: '', priority: '0' });

  const load = useCallback(async () => {
    setErr('');
    try { setD(await apiRequest<List>('/admin/providers', { params: { limit: PAGE, offset: pg * PAGE, provider_type: providerType || undefined, status: sf || undefined } })); }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '加载失败'); }
  }, [pg, providerType, sf]);
  useEffect(() => { load(); }, [load]);
  const TP = d ? Math.ceil(d.total / PAGE) : 0;

  const loadDetail = async (id: string) => {
    try { setDetail(await apiRequest<P>(`/admin/providers/${id}`)); }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '加载详情失败'); }
  };

  const doCreate = async () => {
    try {
      let models: any = undefined;
      if (form.models_json.trim()) { try { models = JSON.parse(form.models_json); } catch { setErr('models_json 格式错误'); return; } }
      await apiRequest('/admin/providers', { method: 'POST', body: { name: form.name, provider_type: form.provider_type, api_key_encrypted: form.api_key_encrypted || undefined, base_url: form.base_url || undefined, models_json: models, priority: parseInt(form.priority) || 0 } });
      showToast('创建成功', 'success');
      setCreate(false); setForm({ name: '', provider_type: 'deepseek', api_key_encrypted: '', base_url: '', models_json: '', priority: '0' }); load();
    } catch (e: unknown) { showToast(e instanceof Error ? e.message : '创建失败', 'error'); }
  };

  const doUpdate = async () => {
    if (!edit) return;
    try {
      let models: any = undefined;
      if (form.models_json.trim()) { try { models = JSON.parse(form.models_json); } catch { setErr('models_json 格式错误'); return; } }
      await apiRequest(`/admin/providers/${edit.id}`, { method: 'PATCH', body: { name: form.name, provider_type: form.provider_type, api_key_encrypted: form.api_key_encrypted || undefined, base_url: form.base_url || undefined, models_json: models, priority: parseInt(form.priority) || 0 } });
      showToast('保存成功', 'success');
      setEdit(null); load();
    } catch (e: unknown) { showToast(e instanceof Error ? e.message : '更新失败', 'error'); }
  };

  const doDelete = async () => {
    if (!delTarget) return;
    try { await apiRequest(`/admin/providers/${delTarget.id}`, { method: 'DELETE' }); showToast('删除成功', 'success'); setDelTarget(null); load(); }
    catch (e: unknown) { showToast(e instanceof Error ? e.message : '删除失败', 'error'); }
  };

  const openEdit = (p: P) => {
    setEdit(p);
    setForm({ name: p.name, provider_type: p.provider_type, api_key_encrypted: '', base_url: p.base_url || '', models_json: p.models_json ? JSON.stringify(p.models_json) : '', priority: String(p.priority ?? 0) });
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.02em', margin: 0 }}>Provider 管理</h2>
        <button onClick={() => { setCreate(true); setForm({ name: '', provider_type: 'deepseek', api_key_encrypted: '', base_url: '', models_json: '', priority: '0' }); }} style={priBtn}>新增 Provider</button>
      </div>
      <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
        <input placeholder="Provider 类型" value={providerType} onChange={e => { setProviderType(e.target.value); setPg(0); }} style={inpS} />
        <select value={sf} onChange={e => { setSf(e.target.value); setPg(0); }} style={selS}><option value="">全部</option><option value="active">启用</option><option value="disabled">禁用</option></select>
        <button onClick={load} style={secBtn}>刷新</button>
      </div>
      {err && <div style={{ color: 'var(--red)', fontSize: 12, marginBottom: 12 }}>{err}</div>}
      <Card><Tbl heads={['名称', '类型', '优先级', '状态', '创建时间', '']}>
        {d?.items.map(p => (
          <tr key={p.id}>
            <td style={{ fontWeight: 600 }}>{p.name}</td>
            <td><Badge t={p.provider_type} c="var(--blue)" /></td>
            <td style={{ fontSize: 13, fontWeight: 600, color: (p.priority || 0) > 0 ? 'var(--blue)' : 'var(--gray-400)' }}>{p.priority ?? 0}</td>
            <td><Badge t={p.is_enabled ? '启用' : '禁用'} c={p.is_enabled ? '#34c759' : 'var(--gray-400)'} /></td>
            <td style={{ fontSize: 12, color: 'var(--gray-500)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>{p.base_url || '—'}</td>
            <td style={{ fontSize: 12, color: 'var(--gray-500)' }}>{new Date(p.created_at).toLocaleString('zh-CN')}</td>
            <td style={{ textAlign: 'right' }}>
              <ActBtn kind="detail" onClick={() => loadDetail(p.id)}>详情</ActBtn>
              <ActBtn kind="edit" onClick={() => openEdit(p)}>编辑</ActBtn>
              <ActBtn kind="delete" onClick={() => setDelTarget(p)}>删除</ActBtn>
            </td>
          </tr>
        ))}
      </Tbl></Card>
      <Pager pg={pg} tp={TP} total={d?.total || 0} onPrev={() => setPg(pg - 1)} onNext={() => setPg(pg + 1)} />

      {/* 详情 Sheet */}
      {detail && <Sheet title="Provider 详情" close={() => setDetail(null)}>
        <DetailRows rows={[
          ['名称', detail.name], ['类型', detail.provider_type],
          ['API URL', detail.base_url || '—'], ['状态', detail.is_enabled ? '启用' : '禁用'],
          ['创建时间', new Date(detail.created_at).toLocaleString('zh-CN')],
          ['更新时间', detail.updated_at ? new Date(detail.updated_at).toLocaleString('zh-CN') : '—'],
        ]} />
        {detail.models_json && <pre style={{ marginTop: 12, padding: 8, background: 'var(--gray-50)', borderRadius: 4, fontSize: 11 }}>{JSON.stringify(detail.models_json, null, 2)}</pre>}
      </Sheet>}

      {/* 创建/编辑 Sheet */}
      {delTarget && <Modal title="删除 Provider" close={() => setDelTarget(null)} action={doDelete} danger>
        <p>确认删除 Provider <b>{delTarget.name}</b>？此操作不可撤销。</p>
      </Modal>}
      {(create || edit) && <Sheet title={create ? '新增 Provider' : '编辑 Provider'} close={() => { setCreate(false); setEdit(null); }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <input placeholder="名称" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} style={inpS} />
          <input placeholder="类型 (如 deepseek / openai / anthropic)" value={form.provider_type} onChange={e => setForm({ ...form, provider_type: e.target.value })} style={inpS} />
          <input placeholder="留空则保持原 Key" type="password" value={form.api_key_encrypted} onChange={e => setForm({ ...form, api_key_encrypted: e.target.value })} style={inpS} />
          <input placeholder="Base URL (如 https://api.deepseek.com)" value={form.base_url} onChange={e => setForm({ ...form, base_url: e.target.value })} style={inpS} />
          <textarea placeholder='models_json (如 {"text":"deepseek-chat","image":"doubao-image"})' value={form.models_json} onChange={e => setForm({ ...form, models_json: e.target.value })} style={{ ...inpS, minHeight: 80, fontFamily: 'monospace' }} />
          <input placeholder="优先级 (数字越大越优先，默认 0)" type="number" value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })} style={inpS} />
          <button type="button" onClick={create ? doCreate : doUpdate} style={priBtn}>{create ? '创建' : '保存'}</button>
        </div>
      </Sheet>}
    </div>
  );
}
