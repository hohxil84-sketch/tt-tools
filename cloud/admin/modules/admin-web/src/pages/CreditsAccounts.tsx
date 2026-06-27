import React, { useEffect, useState, useCallback } from 'react';
import { apiRequest } from '../api/client';
import { Card, Tbl, Badge, ActBtn, Pager, Sheet, DetailRows, secBtn, inpS, selS } from '../components/shared';

interface Acc { id: string; user_id: string; user_account: string | null; plan_name?: string | null; balance: number; monthly_grant: number; status: string; period_start: string | null; period_end: string | null; updated_at: string; user_display_name?: string | null; created_at?: string; }
interface List { items: Acc[]; total: number; limit: number; offset: number; }
const PAGE = 20;

export default function CreditsAccounts() {
  const [d, setD] = useState<List | null>(null);
  const [uid, setUid] = useState(''); const [sf, setSf] = useState(''); const [pc, setPc] = useState('');
  const [pg, setPg] = useState(0); const [err, setErr] = useState('');
  const [detail, setDetail] = useState<Acc | null>(null);

  const load = useCallback(async () => {
    setErr('');
    try { setD(await apiRequest<List>('/admin/credits/accounts', { params: { limit: PAGE, offset: pg * PAGE, user_id: uid || undefined, status: sf || undefined, plan_name: pc || undefined } })); }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '加载失败'); }
  }, [pg, uid, sf, pc]);
  useEffect(() => { load(); }, [load]);
  const TP = d ? Math.ceil(d.total / PAGE) : 0;

  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.02em', marginBottom: 20 }}>额度账户</h2>
      <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
        <input placeholder="用户 ID" value={uid} onChange={e => { setUid(e.target.value); setPg(0); }} style={inpS} />
        <select value={sf} onChange={e => { setSf(e.target.value); setPg(0); }} style={selS}><option value="">全部</option><option value="active">正常</option><option value="frozen">冻结</option></select>
        <input placeholder="套餐名称" value={pc} onChange={e => { setPc(e.target.value); setPg(0); }} style={inpS} />
        <button onClick={load} style={secBtn}>刷新</button>
      </div>
      {err && <div style={{ color: 'var(--red)', fontSize: 12, marginBottom: 12 }}>{err}</div>}
      <Card><Tbl heads={['用户', '套餐', '余额', '月赠', '状态', '周期', '更新', '']}>
        {d?.items.map(a => (
          <tr key={a.id}>
            <td style={{ fontWeight: 500 }}>{a.user_account || a.user_id.substring(0, 8)}</td>
            <td><Badge t={a.plan_name || '—'} c={a.plan_name ? undefined : '#ff3b30'} /></td>
            <td style={{ fontWeight: 700, fontSize: 15 }}>{a.balance.toLocaleString()}</td>
            <td>{a.monthly_grant.toLocaleString()}</td>
            <td><span style={{ fontSize: 12, color: a.status === 'active' ? '#34c759' : '#ff3b30' }}>{a.status === 'active' ? '正常' : '冻结'}</span></td>
            <td style={{ fontSize: 12, color: 'var(--gray-500)' }}>{a.period_start ? new Date(a.period_start).toLocaleDateString('zh-CN') : '—'} ~ {a.period_end ? new Date(a.period_end).toLocaleDateString('zh-CN') : '—'}</td>
            <td style={{ fontSize: 12, color: 'var(--gray-500)' }}>{new Date(a.updated_at).toLocaleString('zh-CN')}</td>
            <td style={{ textAlign: 'right' }}><ActBtn kind="detail" onClick={() => setDetail(a)}>详情</ActBtn></td>
          </tr>
        ))}
      </Tbl></Card>
      <Pager pg={pg} tp={TP} total={d?.total || 0} onPrev={() => setPg(pg - 1)} onNext={() => setPg(pg + 1)} />
      {detail && <Sheet title="账户详情" close={() => setDetail(null)}>
        <DetailRows rows={[['账户 ID', detail.id], ['用户', detail.user_account], ['名称', detail.user_display_name], ['套餐', detail.plan_name || '—'], ['余额', detail.balance], ['月赠', detail.monthly_grant], ['状态', detail.status], ['周期开始', detail.period_start ? new Date(detail.period_start).toLocaleString('zh-CN') : '—'], ['周期结束', detail.period_end ? new Date(detail.period_end).toLocaleString('zh-CN') : '—'], ['创建', detail.created_at ? new Date(detail.created_at).toLocaleString('zh-CN') : '—'], ['更新', new Date(detail.updated_at).toLocaleString('zh-CN')]]} />
      </Sheet>}
    </div>
  );
}
