import React, { useEffect, useState, useCallback } from 'react';
import { apiRequest } from '../api/client';
import { Card, Tbl, ActBtn, Sheet, Fld, priBtn, secBtn, inpS, finpS, showToast } from '../components/shared';

interface CapInfo { id: string; code: string; name: string; }
interface Pricing {
  id: string; provider_id: string;
  provider_name: string; model_name: string;
  input_price: number; output_price: number;
  currency: string; is_active: boolean;
  created_at: string; updated_at?: string;
  capabilities?: CapInfo[];
}

interface Provider { id: string; name: string; }

export default function ProviderModelPricing() {
  const [items, setItems] = useState<Pricing[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [allCaps, setAllCaps] = useState<CapInfo[]>([]);
  const [err, setErr] = useState('');
  const [edit, setEdit] = useState<Pricing | null>(null);
  const [showNew, setShowNew] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const load = useCallback(async () => {
    setErr('');
    try {
      const [d, pd, cd] = await Promise.all([
        apiRequest<{ items: Pricing[] }>('/admin/billing/model-pricing'),
        apiRequest<{ items: Provider[] }>('/admin/providers'),
        apiRequest<{ items: CapInfo[] }>('/admin/billing/capabilities'),
      ]);
      setItems(d.items);
      setProviders(pd.items?.filter((p: any) => p.is_enabled) || []);
      setAllCaps(cd.items || []);
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
      <Card><Tbl heads={['Provider', '模型', '能力', '输入价(¥/百万)', '输出价(¥/百万)', '币种', '状态', '']} colAligns={['l', 'l', 'l', 'r', 'r', 'c', 'c', 'r']}>
        {items.map(p => (
          <tr key={p.id}>
            <td style={{ fontWeight: 600, fontSize: 13 }}>{p.provider_name}</td>
            <td style={{ fontSize: 13, fontFamily: 'monospace' }}>{p.model_name}</td>
            <td style={{ fontSize: 12, color: 'var(--gray-600)' }}>
              {(p.capabilities || []).length > 0
                ? p.capabilities!.map(c => (
                  <span key={c.code} style={{ display: 'inline-block', margin: '1px 2px', padding: '1px 6px', borderRadius: 8, background: 'var(--blue-50)', color: 'var(--blue)', fontSize: 11, fontWeight: 500 }}>{c.name}</span>
                ))
                : <span style={{ color: 'var(--gray-400)' }}>—</span>
              }
            </td>
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
              <ActBtn kind="delete" onClick={async () => {
                if (!confirm(`确定删除 ${p.provider_name}/${p.model_name} 的定价？`)) return;
                try {
                  await apiRequest(`/admin/billing/model-pricing/${p.id}`, { method: 'DELETE' });
                  showToast('已删除', 'success');
                  setRefreshKey(k => k + 1);
                } catch (e: unknown) { showToast(e instanceof Error ? e.message : '删除失败', 'error'); }
              }}>删除</ActBtn>
            </td>
          </tr>
        ))}
      </Tbl></Card>
      {(edit || showNew) && <PricingForm item={edit} providers={providers} allCaps={allCaps} close={() => { setEdit(null); setShowNew(false); }} done={() => { setEdit(null); setShowNew(false); setRefreshKey(k => k + 1); }} />}
    </div>
  );
}

function PricingForm({ item, providers, allCaps, close, done }: { item?: Pricing | null; providers: Provider[]; allCaps: CapInfo[]; close: () => void; done: () => void }) {
  const isEdit = !!item;
  const [providerId, setProviderId] = useState(item?.provider_id || '');
  const [modelName, setModelName] = useState(item?.model_name || '');
  const [inputPrice, setInputPrice] = useState(item?.input_price?.toString() || '1.0');
  const [outputPrice, setOutputPrice] = useState(item?.output_price?.toString() || '2.0');
  const [currency, setCurrency] = useState(item?.currency || 'CNY');
  const initCaps = item?.capabilities?.map(c => c.id) || [];
  const [selectedCapIds, setSelectedCapIds] = useState<Set<string>>(new Set(initCaps));
  const [saving, setSaving] = useState(false);

  const toggleCap = (id: string) => {
    setSelectedCapIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const submit = async (e: React.FormEvent) => { e.preventDefault(); setSaving(true);
    try {
      if (isEdit) {
        await apiRequest(`/admin/billing/model-pricing/${item!.id}`, {
          method: 'PUT',
          body: { input_price: parseFloat(inputPrice), output_price: parseFloat(outputPrice), currency, is_active: item!.is_active },
        });
        // 更新能力关联
        await apiRequest(`/admin/billing/model-pricing/${item!.id}/capabilities`, {
          method: 'PUT',
          body: { capability_ids: [...selectedCapIds] },
        });
        showToast('保存成功', 'success'); done();
      } else {
        if (selectedCapIds.size === 0) { showToast('请至少选择一个能力', 'error'); setSaving(false); return; }
        await apiRequest('/admin/billing/model-pricing', {
          method: 'POST',
          body: { provider_id: providerId, model_name: modelName.trim(), input_price: parseFloat(inputPrice), output_price: parseFloat(outputPrice), currency, capability_ids: [...selectedCapIds] },
        });
        showToast('创建成功', 'success'); done();
      }
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
      </>}
      <Fld label={isEdit ? '能力（可多选）' : '能力类型（可多选）'}>
        {allCaps.length === 0 ? (
          <span style={{ fontSize: 12, color: 'var(--gray-400)' }}>暂无可用的能力，请先初始化 ai_capability 数据</span>
        ) : (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, padding: '4px 0' }}>
            {allCaps.map(cap => (
              <label key={cap.id} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 13, cursor: 'pointer', padding: '4px 10px', borderRadius: 6, background: selectedCapIds.has(cap.id) ? 'var(--blue-50)' : 'var(--gray-50)', border: selectedCapIds.has(cap.id) ? '1px solid var(--blue)' : '1px solid var(--gray-200)' }}>
                <input type="checkbox" checked={selectedCapIds.has(cap.id)} onChange={() => toggleCap(cap.id)} />
                <span style={{ fontWeight: 500 }}>{cap.name}</span>
                <code style={{ fontSize: 10, color: 'var(--gray-400)', marginLeft: 2 }}>{cap.code}</code>
              </label>
            ))}
          </div>
        )}
      </Fld>
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
