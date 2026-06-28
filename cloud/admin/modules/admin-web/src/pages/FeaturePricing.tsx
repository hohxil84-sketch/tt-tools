import React, { useEffect, useState, useCallback } from 'react';
import { apiRequest } from '../api/client';
import { Card, Tbl, ActBtn, Sheet, Fld, priBtn, secBtn, finpS, showToast } from '../components/shared';

interface FP {
  feature_code: string; feature_name: string;
  min_credits: number; default_max_tokens: number;
  updated_at?: string;
}
interface SConfig { [key: string]: { value: string; updated_at: string | null } }

export default function FeaturePricingPage() {
  const [items, setItems] = useState<FP[]>([]);
  const [config, setConfig] = useState<SConfig>({});
  const [err, setErr] = useState('');
  const [edit, setEdit] = useState<FP | null>(null);
  const [rateVal, setRateVal] = useState('10');
  const [savingRate, setSavingRate] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const load = useCallback(async () => {
    setErr('');
    try {
      const [fp, sc] = await Promise.all([
        apiRequest<{ items: FP[] }>('/admin/billing/feature-pricing'),
        apiRequest<SConfig>('/admin/billing/system-config'),
      ]);
      setItems(fp.items);
      setConfig(sc);
      if (sc.credits_exchange_rate) setRateVal(sc.credits_exchange_rate.value);
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : '加载失败'); }
  }, [refreshKey]);
  useEffect(() => { load(); }, [load]);

  const saveRate = async () => {
    setSavingRate(true);
    try {
      await apiRequest('/admin/billing/system-config/credits_exchange_rate', {
        method: 'PUT', body: { value: rateVal },
      });
      showToast('汇率已更新', 'success');
      setRefreshKey(k => k + 1);
    } catch (e: unknown) { showToast(e instanceof Error ? e.message : '保存失败', 'error'); }
    finally { setSavingRate(false); }
  };

  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.02em', marginBottom: 20 }}>功能定价 & 汇率</h2>
      {err && <div style={{ color: 'var(--red)', fontSize: 12, marginBottom: 12 }}>{err}</div>}

      {/* 汇率配置 */}
      <Card style={{ marginBottom: 24, padding: '16px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 14, fontWeight: 600 }}>汇率：1 CNY =</span>
          <input type="number" step="0.1" value={rateVal} onChange={e => setRateVal(e.target.value)} style={{ width: 80, padding: '5px 8px', fontSize: 13, textAlign: 'center' }} />
          <span style={{ fontSize: 14, fontWeight: 600 }}>点</span>
          <button onClick={saveRate} disabled={savingRate} style={{ ...priBtn, fontSize: 12, padding: '5px 16px' }}>{savingRate ? '保存中' : '更新汇率'}</button>
          {config.credits_exchange_rate && (
            <span style={{ fontSize: 11, color: 'var(--gray-400)', marginLeft: 8 }}>
              上次更新: {config.credits_exchange_rate.updated_at ? new Date(config.credits_exchange_rate.updated_at).toLocaleString('zh-CN') : '—'}
            </span>
          )}
        </div>
      </Card>

      {/* 功能起步扣点 */}
      <Card><Tbl heads={['功能码', '功能名称', '起步扣点', '默认max_tokens', '更新时间', '']} colAligns={['l', 'l', 'r', 'r', 'l', 'r']}>
        {items.map(f => (
          <tr key={f.feature_code}>
            <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{f.feature_code}</td>
            <td style={{ fontSize: 13 }}>{f.feature_name}</td>
            <td style={{ fontSize: 14, fontWeight: 700, textAlign: 'right', color: 'var(--orange)' }}>{f.min_credits}</td>
            <td style={{ fontSize: 13, textAlign: 'right', color: 'var(--gray-500)' }}>{f.default_max_tokens}</td>
            <td style={{ fontSize: 12, color: 'var(--gray-500)' }}>{f.updated_at ? new Date(f.updated_at).toLocaleString('zh-CN') : '—'}</td>
            <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}><ActBtn kind="edit" onClick={() => setEdit(f)}>编辑</ActBtn></td>
          </tr>
        ))}
      </Tbl></Card>
      {edit && <FeatureEditForm item={edit} close={() => setEdit(null)} done={() => { setEdit(null); setRefreshKey(k => k + 1); load(); }} />}
    </div>
  );
}

function FeatureEditForm({ item, close, done }: { item: FP; close: () => void; done: () => void }) {
  const [credits, setCredits] = useState(item.min_credits.toString());
  const [maxTokens, setMaxTokens] = useState(item.default_max_tokens.toString());
  const [saving, setSaving] = useState(false);

  const submit = async (e: React.FormEvent) => { e.preventDefault(); setSaving(true);
    try {
      await apiRequest(`/admin/billing/feature-pricing/${item.feature_code}`, {
        method: 'PUT',
        body: { min_credits: parseInt(credits), default_max_tokens: parseInt(maxTokens) },
      });
      showToast('保存成功', 'success'); done();
    } catch (e: unknown) { showToast(e instanceof Error ? e.message : '保存失败', 'error'); }
    finally { setSaving(false); }
  };

  return <Sheet title={`编辑: ${item.feature_name} (${item.feature_code})`} close={close}>
    <form onSubmit={submit}>
      <Fld label="起步扣点（最少扣点数）"><input type="number" min={1} value={credits} onChange={e => setCredits(e.target.value)} required style={finpS} /></Fld>
      <Fld label="默认 max_tokens"><input type="number" min={1} value={maxTokens} onChange={e => setMaxTokens(e.target.value)} style={finpS} /></Fld>
      <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
        <button type="submit" disabled={saving} style={priBtn}>{saving ? '保存中…' : '保存'}</button>
        <button type="button" onClick={close} style={secBtn}>取消</button>
      </div>
    </form>
  </Sheet>;
}
