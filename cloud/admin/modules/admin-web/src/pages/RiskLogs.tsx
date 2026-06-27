import React, { useEffect, useState, useCallback } from 'react';
import { apiRequest } from '../api/client';
import { Card, Tbl, Badge, ActBtn, Pager, Sheet, secBtn, inpS, selS } from '../components/shared';

interface Risk { id: string; user_id: string | null; user_account: string | null; device_id: string | null; device_name?: string | null; risk_type: string; severity: string; created_at: string; user_display_name?: string | null; details_json?: Record<string, unknown>; }
interface List { items: Risk[]; total: number; limit: number; offset: number; }
const SC: Record<string, string> = { low: '#34c759', medium: '#ff9500', high: '#ff3b30' };

export default function RiskLogs() {
  const [d, setD] = useState<List | null>(null);
  const [uid, setUid] = useState(''); const [rt, setRt] = useState(''); const [sv, setSv] = useState('');
  const [pg, setPg] = useState(0); const [err, setErr] = useState(''); const [detail, setDetail] = useState<Risk | null>(null);
  const [limit, setLimit] = useState(10);

  const load = useCallback(async () => {
    setErr('');
    try { setD(await apiRequest<List>('/admin/risk-logs', { params: { limit, offset: pg * limit, user_id: uid || undefined, risk_type: rt || undefined, severity: sv || undefined } })); }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '加载失败'); }
  }, [pg, uid, rt, sv, limit]);
  useEffect(() => { load(); }, [load]);
  const TP = d ? Math.ceil(d.total / limit) : 0;

  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.02em', marginBottom: 20 }}>风控日志</h2>
      <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
        <input placeholder="用户 ID" value={uid} onChange={e => { setUid(e.target.value); setPg(0); }} style={inpS} />
        <input placeholder="风险类型" value={rt} onChange={e => { setRt(e.target.value); setPg(0); }} style={inpS} />
        <select value={sv} onChange={e => { setSv(e.target.value); setPg(0); }} style={selS}><option value="">全部级别</option><option value="low">低</option><option value="medium">中</option><option value="high">高</option></select>
        <button onClick={load} style={secBtn}>刷新</button>
      </div>
      {err && <div style={{ color: 'var(--red)', fontSize: 12, marginBottom: 12 }}>{err}</div>}
      <Card><Tbl heads={['类型', '级别', '用户', '设备', '时间', '']} colAligns={['c','c','c','c','c','r']}>
        {d?.items.map(r => (
          <tr key={r.id} style={{ background: r.severity === 'high' ? 'rgba(255,59,48,0.03)' : undefined }}>
            <td style={{ fontWeight: 500, fontSize: 13, width: '18%', textAlign: 'center' }}>{r.risk_type}</td>
            <td style={{ fontSize: 13, width: '10%', textAlign: 'center' }}><Badge t={r.severity.toUpperCase()} c={SC[r.severity] || 'var(--gray-500)'} /></td>
            <td style={{ fontSize: 12, color: 'var(--gray-500)', width: '18%', textAlign: 'center' }}>{r.user_account || r.user_id?.substring(0, 8) || '—'}</td>
            <td style={{ fontSize: 12, color: 'var(--gray-500)', width: '18%', textAlign: 'center' }}>{r.device_name || (r.device_id ? r.device_id.substring(0, 8) + '…' : '—')}</td>
            <td style={{ fontSize: 12, color: 'var(--gray-500)', width: '20%', textAlign: 'center' }}>{new Date(r.created_at).toLocaleString('zh-CN')}</td>
            <td style={{ textAlign: 'right', width: '8%', whiteSpace: 'nowrap' }}><ActBtn kind="detail" onClick={() => setDetail(r)}>详情</ActBtn></td>
          </tr>
        ))}
      </Tbl></Card>
      <Pager pg={pg} tp={TP} total={d?.total || 0} limit={limit} onLimitChange={(n) => { setLimit(n); setPg(0); }} onPrev={() => setPg(pg - 1)} onNext={() => setPg(pg + 1)} />
      {detail && <Sheet title="风控详情" close={() => setDetail(null)}>
        <div>
          {[['类型', detail.risk_type], ['级别', detail.severity], ['用户', detail.user_account || detail.user_id], ['名称', detail.user_display_name], ['设备', detail.device_name || detail.device_id], ['时间', new Date(detail.created_at).toLocaleString('zh-CN')]].map(([l, v]) => <div key={l} style={{ display: 'flex', padding: '6px 0', borderBottom: '1px solid var(--gray-200)' }}><span style={{ width: 80, fontSize: 12, color: 'var(--gray-500)' }}>{l}</span><span style={{ fontSize: 13 }}>{v || '—'}</span></div>)}
        </div>
        {detail.details_json && <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 500, color: 'var(--gray-500)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.02em' }}>详情</div>
          <pre style={{ background: 'var(--gray-100)', padding: 12, borderRadius: 'var(--radius-md)', fontSize: 11, maxHeight: 180, overflow: 'auto', margin: 0 }}>{JSON.stringify(detail.details_json, null, 2)}</pre>
        </div>}
      </Sheet>}
    </div>
  );
}
