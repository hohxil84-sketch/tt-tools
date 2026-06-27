import React, { useEffect, useState, useCallback } from 'react';
import { apiRequest } from '../api/client';
import { Card, Tbl, Badge, ActBtn, Pager, Sheet, DetailRows, secBtn, inpS, selS } from '../components/shared';

interface Log { id: string; request_id: string; user_id: string; user_account: string | null; feature: string; feature_name?: string | null; provider: string; model: string; status: string; error_code: string | null; input_tokens: number; output_tokens: number; total_tokens: number; estimated_cost: number; credits_charged: number; latency_ms: number | null; created_at: string; user_display_name?: string | null; }
interface List { items: Log[]; total: number; limit: number; offset: number; }
export default function ProviderCallLogs() {
  const [d, setD] = useState<List | null>(null);
  const [uid, setUid] = useState(''); const [feat, setFeat] = useState(''); const [prov, setProv] = useState(''); const [sf, setSf] = useState('');
  const [pg, setPg] = useState(0); const [err, setErr] = useState(''); const [detail, setDetail] = useState<Log | null>(null);
  const [limit, setLimit] = useState(10);

  const load = useCallback(async () => {
    setErr('');
    try { setD(await apiRequest<List>('/admin/provider-call-logs', { params: { limit, offset: pg * limit, user_id: uid || undefined, feature: feat || undefined, provider: prov || undefined, status: sf || undefined } })); }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '加载失败'); }
  }, [pg, uid, feat, prov, sf, limit]);
  useEffect(() => { load(); }, [load]);
  const TP = d ? Math.ceil(d.total / limit) : 0;

  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.02em', marginBottom: 20 }}>AI 调用日志</h2>
      <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
        <input placeholder="用户 ID" value={uid} onChange={e => { setUid(e.target.value); setPg(0); }} style={inpS} />
        <input placeholder="功能码" value={feat} onChange={e => { setFeat(e.target.value); setPg(0); }} style={inpS} />
        <select value={prov} onChange={e => { setProv(e.target.value); setPg(0); }} style={selS}><option value="">全部 Provider</option><option value="deepseek">DeepSeek</option><option value="openai">OpenAI</option><option value="doubao">豆包</option><option value="mock">Mock</option></select>
        <select value={sf} onChange={e => { setSf(e.target.value); setPg(0); }} style={selS}><option value="">全部</option><option value="success">成功</option><option value="failed">失败</option><option value="timeout">超时</option></select>
        <button onClick={load} style={secBtn}>刷新</button>
      </div>
      {err && <div style={{ color: 'var(--red)', fontSize: 12, marginBottom: 12 }}>{err}</div>}
      <Card><Tbl heads={['用户', '功能', 'Provider', '模型', '状态', 'Token', '成本', '额度', '延迟', '时间', '']} colAligns={['c','c','c','c','c','c','c','c','c','c','r']}>
        {d?.items.map(l => (
          <tr key={l.id}>
            <td style={{ fontWeight: 500, fontSize: 13, width: '12%', textAlign: 'center' }}>{l.user_account || l.user_id.substring(0, 8)}</td>
            <td style={{ fontSize: 12, width: '12%', textAlign: 'center' }}>
              {l.feature_name ? (
                <><span style={{ fontWeight: 500 }}>{l.feature_name}</span><br /><code style={{ fontSize: 10, color: 'var(--gray-400)' }}>{l.feature}</code></>
              ) : (
                <code style={{ fontSize: 11, color: 'var(--blue)' }}>{l.feature}</code>
              )}
            </td>
            <td style={{ fontSize: 13, width: '9%', textAlign: 'center' }}>{l.provider}</td>
            <td style={{ fontSize: 12, color: 'var(--gray-500)', width: '9%', textAlign: 'center' }}>{l.model}</td>
            <td style={{ fontSize: 13, width: '7%', textAlign: 'center' }}><Badge t={l.status} c={l.status === 'success' ? '#34c759' : '#ff3b30'} /></td>
            <td style={{ fontSize: 13, width: '7%', textAlign: 'center', paddingRight: 24 }}>{l.total_tokens.toLocaleString()}</td>
            <td style={{ fontSize: 13, width: '7%', textAlign: 'center', paddingRight: 24 }}>${l.estimated_cost?.toFixed(4)}</td>
            <td style={{ fontWeight: 600, fontSize: 13, width: '6%', textAlign: 'center', paddingRight: 24 }}>{l.credits_charged}</td>
            <td style={{ fontSize: 12, color: 'var(--gray-500)', width: '7%', textAlign: 'center', paddingRight: 24 }}>{l.latency_ms != null ? `${l.latency_ms}ms` : '—'}</td>
            <td style={{ fontSize: 12, color: 'var(--gray-500)', width: '13%', textAlign: 'center' }}>{new Date(l.created_at).toLocaleString('zh-CN')}</td>
            <td style={{ textAlign: 'right', width: '6%', whiteSpace: 'nowrap' }}><ActBtn kind="detail" onClick={() => setDetail(l)}>详情</ActBtn></td>
          </tr>
        ))}
      </Tbl></Card>
      <Pager pg={pg} tp={TP} total={d?.total || 0} limit={limit} onLimitChange={(n) => { setLimit(n); setPg(0); }} onPrev={() => setPg(pg - 1)} onNext={() => setPg(pg + 1)} />
      {detail && <Sheet title="调用详情" close={() => setDetail(null)}>
        <DetailRows rows={[['ID', detail.id], ['Request ID', detail.request_id], ['用户', detail.user_account || detail.user_id], ['名称', detail.user_display_name], ['功能', detail.feature], ['Provider', detail.provider], ['模型', detail.model], ['状态', detail.status], ['错误码', detail.error_code], ['输入 Token', detail.input_tokens], ['输出 Token', detail.output_tokens], ['总 Token', detail.total_tokens], ['成本', `$${detail.estimated_cost?.toFixed(6)}`], ['额度', detail.credits_charged], ['延迟', detail.latency_ms != null ? `${detail.latency_ms}ms` : '—'], ['时间', new Date(detail.created_at).toLocaleString('zh-CN')]]} />
      </Sheet>}
    </div>
  );
}
