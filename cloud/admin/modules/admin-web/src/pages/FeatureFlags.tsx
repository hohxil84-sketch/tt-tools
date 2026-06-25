import React, { useEffect, useState, useCallback } from 'react';
import { apiRequest } from '../api/client';
import { Fld, Sheet, priBtn, secBtn, inpS, finpS } from '../components/shared';

interface Feat { plan_id: string; plan_code: string; plan_name: string; enabled_features_json: Record<string, unknown>; plan_status: string; }

export default function FeatureFlags() {
  const [items, setItems] = useState<Feat[]>([]);
  const [pc, setPc] = useState(''); const [err, setErr] = useState('');
  const [edit, setEdit] = useState<Feat | null>(null);

  const load = useCallback(async () => {
    setErr('');
    try { const d = await apiRequest<{ items: Feat[] }>('/admin/feature-flags', { params: { plan_code: pc || undefined } }); setItems(d.items); }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '加载失败'); }
  }, [pc]);
  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.02em', marginBottom: 20 }}>功能开关</h2>
      <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
        <input placeholder="套餐编码筛选" value={pc} onChange={e => setPc(e.target.value)} style={inpS} />
        <button onClick={load} style={secBtn}>刷新</button>
      </div>
      {err && <div style={{ color: 'var(--red)', fontSize: 12, marginBottom: 12 }}>{err}</div>}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 16 }}>
        {items.map(it => (
          <div key={it.plan_id} style={{ background: 'var(--white)', borderRadius: 'var(--radius-lg)', padding: '20px 24px', border: '1px solid var(--gray-200)', boxShadow: 'var(--shadow-sm)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
              <div>
                <h4 style={{ fontSize: 15, fontWeight: 600, marginBottom: 2 }}>{it.plan_name}</h4>
                <code style={{ fontSize: 12, color: 'var(--blue)' }}>{it.plan_code}</code>
                <span style={{ marginLeft: 8, fontSize: 11, color: it.plan_status === 'active' ? '#34c759' : 'var(--gray-400)', fontWeight: 500 }}>{it.plan_status === 'active' ? '● 启用' : '○ 停用'}</span>
              </div>
              <button onClick={() => setEdit(it)} style={{ ...secBtn, fontSize: 11, padding: '4px 14px' }}>编辑</button>
            </div>
            <pre style={{ background: 'var(--gray-100)', padding: 10, borderRadius: 'var(--radius-sm)', fontSize: 11, maxHeight: 140, overflow: 'auto', margin: 0, fontFamily: 'SF Mono, Monaco, monospace' }}>
              {JSON.stringify(it.enabled_features_json, null, 2)}
            </pre>
          </div>
        ))}
        {items.length === 0 && <div style={{ color: 'var(--gray-400)', fontSize: 13 }}>暂无配置</div>}
      </div>
      {edit && <EditModal item={edit} close={() => setEdit(null)} done={() => { setEdit(null); load(); }} />}
    </div>
  );
}

function EditModal({ item, close, done }: { item: Feat; close: () => void; done: () => void }) {
  const [fj, setFj] = useState(JSON.stringify(item.enabled_features_json, null, 2));
  const [saving, setSaving] = useState(false);
  const [confirmed, setConfirmed] = useState(false);

  const save = async () => { setSaving(true);
    let pf: Record<string, unknown> = {}; try { pf = JSON.parse(fj); } catch { alert('JSON 格式错误'); setSaving(false); return; }
    try { await apiRequest(`/admin/plans/${item.plan_id}/features`, { method: 'PATCH', body: { enabled_features_json: pf } }); done(); }
    catch (e: unknown) { alert(e instanceof Error ? e.message : '保存失败'); }
    finally { setSaving(false); }
  };

  return <Sheet title={`编辑: ${item.plan_name}`} close={close}>
    <p style={{ fontSize: 12, color: 'var(--gray-500)', marginBottom: 12 }}>合并更新，只更新传入的 key。</p>
    <Fld label="功能开关 (JSON)"><textarea value={fj} onChange={e => setFj(e.target.value)} rows={10} style={{ ...finpS, fontFamily: 'SF Mono, Monaco, monospace', fontSize: 12 }} /></Fld>
    {!confirmed ? <button onClick={() => setConfirmed(true)} style={{ ...priBtn, background: '#ff9500' }}>提交（需二次确认）</button> : <div style={{ marginTop: 12 }}>
      <div style={{ background: '#fff9f0', borderRadius: 'var(--radius-md)', padding: 10, marginBottom: 12, fontSize: 12 }}>⚠️ 确认更新 <b>{item.plan_name}</b> 的功能开关？</div>
      <div style={{ display: 'flex', gap: 8 }}><button onClick={save} disabled={saving} style={{ ...priBtn, background: '#ff3b30' }}>{saving ? '保存中…' : '确认更新'}</button><button onClick={() => setConfirmed(false)} style={secBtn}>返回</button><button onClick={close} style={secBtn}>取消</button></div>
    </div>}
  </Sheet>;
}
