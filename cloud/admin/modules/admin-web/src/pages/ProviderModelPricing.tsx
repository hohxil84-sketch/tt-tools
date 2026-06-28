import React, { useEffect, useState, useCallback } from 'react';
import { apiRequest } from '../api/client';
import { Card, Tbl, ActBtn, Sheet, Fld, priBtn, secBtn, inpS, finpS, showToast } from '../components/shared';

interface Pricing {
  id: string; provider_id: string;
  provider_name: string; model_name: string; capability?: string;
  input_price: number; output_price: number;
  currency: string; is_active: boolean;
  created_at: string; updated_at?: string;
}

interface Provider { id: string; name: string; }

export default function ProviderModelPricing() {
  const [items, setItems] = useState<Pricing[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [err, setErr] = useState('');
  const [edit, setEdit] = useState<Pricing | null>(null);
  const [showNew, setShowNew] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const load = useCallback(async () => {
    setErr('');
    try {
      const [d, pd] = await Promise.all([
        apiRequest<{ items: Pricing[] }>('/admin/billing/model-pricing'),
        apiRequest<{ items: Provider[] }>('/admin/providers'),
      ]);
      setItems(d.items);
      setProviders(pd.items?.filter((p: any) => p.is_enabled) || []);
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : '加载失败'); }
  }, [refreshKey]);
  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.02em', margin: 0 }}>模型定价管理</h2>
        <button onClick={() => setShowNew(true)} style={priBtn}>+ 新增模型定价</button>
      </div>
      {err && <div style={{ color: 'var(--red)', fontSize: 12, marginBottom: 12 }}>{err}</div>}
      <Card><Tbl heads={['Provider', '模型', '能力', '输入价(¥/百万)', '输出价(¥/百万)', '币种', '状态', '']} colAligns={['l', 'l', 'c', 'r', 'r', 'c', 'c', 'r']}>
        {items.map(p => (
          <tr key={p.id}>
            <td style={{ fontWeight: 600, fontSize: 13 }}>{p.provider_name}</td>
            <td style={{ fontSize: 13, fontFamily: 'monospace' }}>{p.model_name}</td>
            <td style={{ fontSize: 12, textAlign: 'center', color: 'var(--gray-500)' }}>{p.capability || 'text'}</td>
            <td style={{ fontSize: 13, textAlign: 'right' }}>{p.input_price.toFixed(4)}</td>
            <td style={{ fontSize: 13, textAlign: 'right' }}>{p.output_price.toFixed(4)}</td>
            <td style={{ fontSize: 12, textAlign: 'center', color: 'var(--gray-500)' }}>{p.currency}</td>
            <td style={{ fontSize: 13, textAlign: 'center' }}>
              <span style={{ fontWeight: 600, color: p.is_active ? '#34c759' : 'var(--gray-400)' }}>
                {p.is_active ? '● 启用' : '○ 停用'}
              </span>
            </td>
            <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
              <ActBtn kind="edit" onClick={() => setEdit(p)}>编辑</ActBtn>
            </td>
          </tr>
        ))}
      </Tbl></Card>
      {(edit || showNew) && <PricingForm item={edit} providers={providers} close={() => { setEdit(null); setShowNew(false); }} done={() => { setEdit(null); setShowNew(false); setRefreshKey(k => k + 1); }} />}
    </div>
  );
}

function PricingForm({ item, providers, close, done }: { item?: Pricing | null; providers: Provider[]; close: () => void; done: () => void }) {
  const isEdit = !!item;
  const [providerId, setProviderId] = useState(item?.provider_id || '');
  const [modelName, setModelName] = useState(item?.model_name || '');
  const [inputPrice, setInputPrice] = useState(item?.input_price?.toString() || '1.0');
  const [outputPrice, setOutputPrice] = useState(item?.output_price?.toString() || '2.0');
  const [currency, setCurrency] = useState(item?.currency || 'CNY');
  const [capability, setCapability] = useState(item?.capability || 'text');
  const [saving, setSaving] = useState(false);

  const submit = async (e: React.FormEvent) => { e.preventDefault(); setSaving(true);
    try {
      if (isEdit) {
        await apiRequest(`/admin/billing/model-pricing/${item!.id}`, {
          method: 'PUT',
          body: { input_price: parseFloat(inputPrice), output_price: parseFloat(outputPrice), currency, is_active: item!.is_active },
        });
      } else {
        await apiRequest('/admin/billing/model-pricing', {
          method: 'POST',
          body: { provider_id: providerId, model_name: modelName, capability, input_price: parseFloat(inputPrice), output_price: parseFloat(outputPrice), currency },
        });
      }
      showToast('保存成功', 'success'); done();
    } catch (e: unknown) { showToast(e instanceof Error ? e.message : '保存失败', 'error'); }
    finally { setSaving(false); }
  };

  return <Sheet title={isEdit ? `编辑: ${item!.provider_name}/${item!.model_name}` : '新增模型定价'} close={close}>
    <form onSubmit={submit}>
      {!isEdit && <>
        <Fld label="Provider">
          <select value={providerId} onChange={e => setProviderId(e.target.value)} required style={{ padding: '7px 12px', width: '100%', border: '1px solid var(--gray-300)', borderRadius: 'var(--radius-sm)', fontSize: 13, background: 'var(--white)' }}>
            <option value="">-- 选择 Provider --</option>
            {providers.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </Fld>
        <Fld label="模型名称"><input value={modelName} onChange={e => setModelName(e.target.value)} required style={finpS} placeholder="如 deepseek-chat, gpt-4o" /></Fld>
        <Fld label="能力类型">
          <select value={capability} onChange={e => setCapability(e.target.value)} style={{ padding: '7px 12px', width: '100%', border: '1px solid var(--gray-300)', borderRadius: 'var(--radius-sm)', fontSize: 13, background: 'var(--white)' }}>
            <option value="text">text（文本生成）</option>
            <option value="image_generation">image_generation（图片生成）</option>
            <option value="image_edit">image_edit（图片编辑）</option>
          </select>
        </Fld>
      </>}
      <Fld label="输入单价 (¥/百万token)"><input type="number" step="0.0001" value={inputPrice} onChange={e => setInputPrice(e.target.value)} required style={finpS} /></Fld>
      <Fld label="输出单价 (¥/百万token)"><input type="number" step="0.0001" value={outputPrice} onChange={e => setOutputPrice(e.target.value)} required style={finpS} /></Fld>
      <Fld label="币种"><input value={currency} onChange={e => setCurrency(e.target.value)} style={finpS} /></Fld>
      <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
        <button type="submit" disabled={saving} style={priBtn}>{saving ? '保存中…' : '保存'}</button>
        <button type="button" onClick={close} style={secBtn}>取消</button>
      </div>
    </form>
  </Sheet>;
}
