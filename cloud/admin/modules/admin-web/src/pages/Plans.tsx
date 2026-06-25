import React, { useEffect, useState, useCallback } from 'react';
import { apiRequest } from '../api/client';
import { Card, Tbl, LBtn, Sheet, Modal, Fld, priBtn, secBtn, finpS } from '../components/shared';

interface Plan { id: string; code: string; name: string; monthly_grant: number; status: string; created_at: string; enabled_features_json?: Record<string, unknown>; updated_at?: string; }

export default function Plans() {
  const [items, setItems] = useState<Plan[]>([]);
  const [err, setErr] = useState('');
  const [edit, setEdit] = useState<Plan | null>(null);
  const [showNew, setShowNew] = useState(false);
  const [ct, setCt] = useState<Plan | null>(null);
  const [cd, setCd] = useState<Plan | null>(null);

  const load = useCallback(async () => {
    setErr('');
    try { const d = await apiRequest<{ items: Plan[] }>('/admin/plans'); setItems(d.items); }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '加载失败'); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const toggle = async (id: string, ns: string) => { await apiRequest(`/admin/plans/${id}/status`, { method: 'PATCH', body: { status: ns } }); setCt(null); load(); };
  const del = async () => { if (!cd) return; await apiRequest(`/admin/plans/${cd.id}`, { method: 'DELETE' }); setCd(null); load(); };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.02em', margin: 0 }}>套餐管理</h2>
        <button onClick={() => setShowNew(true)} style={priBtn}>+ 新建套餐</button>
      </div>
      {err && <div style={{ color: 'var(--red)', fontSize: 12, marginBottom: 12 }}>{err}</div>}
      <Card><Tbl heads={['编码', '名称', '月赠额度', '状态', '创建时间', '']}>
        {items.map(p => (
          <tr key={p.id}>
            <td><code style={{ fontSize: 12, fontWeight: 600, color: 'var(--blue)' }}>{p.code}</code></td>
            <td style={{ fontWeight: 500 }}>{p.name}</td>
            <td>{p.monthly_grant.toLocaleString()}</td>
            <td><span style={{ fontSize: 12, fontWeight: 500, color: p.status === 'active' ? '#34c759' : 'var(--gray-500)' }}>{p.status === 'active' ? '启用' : '停用'}</span></td>
            <td style={{ fontSize: 12, color: 'var(--gray-500)' }}>{new Date(p.created_at).toLocaleString('zh-CN')}</td>
            <td style={{ textAlign: 'right' }}>
              <LBtn onClick={() => setEdit(p)}>编辑</LBtn>
              <LBtn c={p.status === 'active' ? '#ff9500' : '#34c759'} onClick={() => setCt(p)}>{p.status === 'active' ? '停用' : '启用'}</LBtn>
              <LBtn c="#ff3b30" onClick={() => setCd(p)}>删除</LBtn>
            </td>
          </tr>
        ))}
      </Tbl></Card>
      {ct && <Modal title="确认" close={() => setCt(null)} action={() => toggle(ct.id, ct.status === 'active' ? 'disabled' : 'active')} danger><p>{ct.status === 'active' ? '停用' : '启用'}套餐 <b>{ct.name}</b>？</p></Modal>}
      {cd && <Modal title="删除套餐" close={() => setCd(null)} action={del} danger><p>永久删除 <b>{cd.name}</b> ({cd.code})？</p></Modal>}
      {(edit || showNew) && <PlanForm plan={edit} close={() => { setEdit(null); setShowNew(false); }} done={() => { setEdit(null); setShowNew(false); load(); }} />}
    </div>
  );
}

function PlanForm({ plan, close, done }: { plan?: Plan | null; close: () => void; done: () => void }) {
  const [code, setCode] = useState(plan?.code || '');
  const [name, setName] = useState(plan?.name || '');
  const [mg, setMg] = useState(plan?.monthly_grant || 0);
  const [fj, setFj] = useState(JSON.stringify(plan?.enabled_features_json || {}, null, 2));
  const [saving, setSaving] = useState(false);
  const isEdit = !!plan;

  const submit = async (e: React.FormEvent) => { e.preventDefault(); setSaving(true);
    let pf: Record<string, unknown> = {}; try { pf = JSON.parse(fj); } catch { alert('JSON 格式错误'); setSaving(false); return; }
    try {
      if (isEdit) await apiRequest(`/admin/plans/${plan!.id}`, { method: 'PATCH', body: { name, monthly_grant: mg, enabled_features_json: pf } });
      else await apiRequest('/admin/plans', { method: 'POST', body: { code, name, monthly_grant: mg, enabled_features_json: pf } });
      done();
    } catch (e: unknown) { alert(e instanceof Error ? e.message : '保存失败'); }
    finally { setSaving(false); }
  };

  return <Sheet title={isEdit ? `编辑: ${plan!.name}` : '新建套餐'} close={close}>
    <form onSubmit={submit}>
      {!isEdit && <Fld label="编码 *"><input value={code} onChange={e => setCode(e.target.value)} required style={finpS} /></Fld>}
      <Fld label="名称"><input value={name} onChange={e => setName(e.target.value)} required style={finpS} /></Fld>
      <Fld label="月赠额度"><input type="number" value={mg} onChange={e => setMg(Number(e.target.value))} min={0} style={finpS} /></Fld>
      <Fld label="功能开关 (JSON)"><textarea value={fj} onChange={e => setFj(e.target.value)} rows={5} style={{ ...finpS, fontFamily: 'SF Mono, Monaco, monospace', fontSize: 12 }} /></Fld>
      <div style={{ display: 'flex', gap: 8, marginTop: 16 }}><button type="submit" disabled={saving} style={priBtn}>{saving ? '保存中…' : '保存'}</button><button type="button" onClick={close} style={secBtn}>取消</button></div>
    </form>
  </Sheet>;
}
