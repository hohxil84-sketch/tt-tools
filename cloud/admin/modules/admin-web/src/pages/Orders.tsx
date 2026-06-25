import React, { useEffect, useState, useCallback } from 'react';
import { apiRequest } from '../api/client';
import { Card, Tbl, Badge, LBtn, Pager, Sheet, DetailRows, secBtn, inpS, selS } from '../components/shared';

interface Ord { id: string; order_no: string; order_type: string; product_code: string; amount_cents: number; credit_amount: number | null; currency: string; status: string; paid_at: string | null; user_id: string; user_account: string | null; created_at: string; updated_at: string; user_display_name?: string | null; }
interface List { items: Ord[]; total: number; limit: number; offset: number; }
const PAGE = 20;
const SS: Record<string, string> = { pending: '待支付', paid: '已支付', closed: '已关闭', refunded: '已退款' };

export default function Orders() {
  const [d, setD] = useState<List | null>(null);
  const [uid, setUid] = useState(''); const [ot, setOt] = useState(''); const [sf, setSf] = useState('');
  const [pg, setPg] = useState(0); const [err, setErr] = useState(''); const [detail, setDetail] = useState<Ord | null>(null);

  const load = useCallback(async () => {
    setErr('');
    try { setD(await apiRequest<List>('/admin/orders', { params: { limit: PAGE, offset: pg * PAGE, user_id: uid || undefined, order_type: ot || undefined, status: sf || undefined } })); }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '加载失败'); }
  }, [pg, uid, ot, sf]);
  useEffect(() => { load(); }, [load]);
  const TP = d ? Math.ceil(d.total / PAGE) : 0;

  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.02em', marginBottom: 20 }}>订单管理</h2>
      <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
        <input placeholder="用户 ID" value={uid} onChange={e => { setUid(e.target.value); setPg(0); }} style={inpS} />
        <select value={ot} onChange={e => { setOt(e.target.value); setPg(0); }} style={selS}><option value="">全部类型</option><option value="plan">套餐</option><option value="credits">额度</option></select>
        <select value={sf} onChange={e => { setSf(e.target.value); setPg(0); }} style={selS}><option value="">全部状态</option><option value="pending">待支付</option><option value="paid">已支付</option><option value="closed">已关闭</option><option value="refunded">已退款</option></select>
        <button onClick={load} style={secBtn}>刷新</button>
      </div>
      {err && <div style={{ color: 'var(--red)', fontSize: 12, marginBottom: 12 }}>{err}</div>}
      <Card><Tbl heads={['订单号', '类型', '产品', '金额', '状态', '用户', '时间', '']}>
        {d?.items.map(o => (
          <tr key={o.id}>
            <td><code style={{ fontSize: 11, fontWeight: 600 }}>{o.order_no}</code></td>
            <td><Badge t={o.order_type === 'plan' ? '套餐' : '额度'} c={o.order_type === 'plan' ? 'var(--blue)' : 'var(--orange)'} /></td>
            <td>{o.product_code}</td>
            <td style={{ fontWeight: 600 }}>¥{(o.amount_cents / 100).toFixed(2)}</td>
            <td><span style={{ fontSize: 12, fontWeight: 500, color: o.status === 'paid' ? '#34c759' : 'var(--gray-500)' }}>{SS[o.status] || o.status}</span></td>
            <td style={{ color: 'var(--gray-500)', fontSize: 12 }}>{o.user_account || o.user_id.substring(0, 8)}</td>
            <td style={{ fontSize: 12, color: 'var(--gray-500)' }}>{new Date(o.created_at).toLocaleString('zh-CN')}</td>
            <td style={{ textAlign: 'right' }}><LBtn onClick={() => setDetail(o)}>详情</LBtn></td>
          </tr>
        ))}
      </Tbl></Card>
      <Pager pg={pg} tp={TP} total={d?.total || 0} onPrev={() => setPg(pg - 1)} onNext={() => setPg(pg + 1)} />
      {detail && <Sheet title="订单详情" close={() => setDetail(null)}>
        <DetailRows rows={[['订单号', detail.order_no], ['类型', detail.order_type], ['产品', detail.product_code], ['金额', `¥${(detail.amount_cents / 100).toFixed(2)}`], ['额度', detail.credit_amount], ['币种', detail.currency], ['状态', detail.status], ['支付时间', detail.paid_at ? new Date(detail.paid_at).toLocaleString('zh-CN') : '—'], ['用户', detail.user_account], ['用户名称', detail.user_display_name], ['创建', new Date(detail.created_at).toLocaleString('zh-CN')], ['更新', new Date(detail.updated_at).toLocaleString('zh-CN')]]} />
      </Sheet>}
    </div>
  );
}
