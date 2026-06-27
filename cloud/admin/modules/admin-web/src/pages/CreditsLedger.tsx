import React, { useEffect, useState, useCallback } from 'react';
import { apiRequest } from '../api/client';
import { Card, Tbl, Badge, Pager, Modal, Fld, priBtn, secBtn, inpS, selS, finpS, showToast } from '../components/shared';

interface Led { id: string; user_id: string; user_account: string | null; account_id: string; change_type: string; amount: number; balance_after: number; source_type: string; source_id: string | null; description: string | null; created_at: string; }
interface List { items: Led[]; total: number; limit: number; offset: number; }
const TL: Record<string, string> = { grant: '赠送', consume: '消费', recharge: '充值', refund: '退款', adjust: '调整' };
const TC: Record<string, string> = { grant: '#34c759', consume: '#ff3b30', recharge: '#0071e3', refund: '#ff9500', adjust: '#af52de' };

export default function CreditsLedger() {
  const [d, setD] = useState<List | null>(null);
  const [uid, setUid] = useState(''); const [ct, setCt] = useState(''); const [st, setSt] = useState('');
  const [pg, setPg] = useState(0); const [err, setErr] = useState(''); const [showAdj, setShowAdj] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [limit, setLimit] = useState(10);

  const load = useCallback(async () => {
    setErr('');
    try { setD(await apiRequest<List>('/admin/credits/ledger', { params: { limit, offset: pg * limit, user_id: uid || undefined, change_type: ct || undefined, source_type: st || undefined } })); }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '加载失败'); }
  }, [pg, uid, ct, st, limit, refreshKey]);
  useEffect(() => { load(); }, [load]);
  const TP = d ? Math.ceil(d.total / limit) : 0;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.02em', margin: 0 }}>额度流水</h2>
        <button onClick={() => setShowAdj(true)} style={priBtn}>+ 调整额度</button>
      </div>
      <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
        <input placeholder="用户 ID" value={uid} onChange={e => { setUid(e.target.value); setPg(0); }} style={inpS} />
        <select value={ct} onChange={e => { setCt(e.target.value); setPg(0); }} style={selS}><option value="">全部类型</option><option value="grant">赠送</option><option value="consume">消费</option><option value="recharge">充值</option><option value="refund">退款</option><option value="adjust">调整</option></select>
        <select value={st} onChange={e => { setSt(e.target.value); setPg(0); }} style={selS}><option value="">全部来源</option><option value="provider_call">调用</option><option value="order">订单</option><option value="system">系统</option><option value="admin">管理员</option></select>
        <button onClick={load} style={secBtn}>刷新</button>
      </div>
      {err && <div style={{ color: 'var(--red)', fontSize: 12, marginBottom: 12 }}>{err}</div>}
      <Card><Tbl heads={['用户', '类型', '金额', '余额', '来源', '说明', '时间']} colAligns={['c','c','c','c','c','c','c']}>
        {d?.items.map(e => (
          <tr key={e.id}>
            <td style={{ fontWeight: 500, fontSize: 13, width: '15%', textAlign: 'center' }}>{e.user_account || e.user_id.substring(0, 8)}</td>
            <td style={{ fontSize: 13, width: '10%', textAlign: 'center' }}><Badge t={TL[e.change_type] || e.change_type} c={TC[e.change_type] || 'var(--gray-500)'} /></td>
            <td style={{ fontWeight: 700, fontSize: 13, width: '12%', textAlign: 'center', paddingRight: 24, color: e.amount >= 0 ? '#34c759' : '#ff3b30' }}>{e.amount > 0 ? '+' : ''}{e.amount.toLocaleString()}</td>
            <td style={{ fontSize: 13, width: '12%', textAlign: 'center', paddingRight: 24 }}>{e.balance_after.toLocaleString()}</td>
            <td style={{ fontSize: 12, color: 'var(--gray-500)', width: '10%', textAlign: 'center' }}>{e.source_type}</td>
            <td style={{ fontSize: 12, color: 'var(--gray-500)', width: '18%', maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', textAlign: 'center' }}>{e.description || '—'}</td>
            <td style={{ fontSize: 12, color: 'var(--gray-500)', width: '16%', textAlign: 'center' }}>{new Date(e.created_at).toLocaleString('zh-CN')}</td>
          </tr>
        ))}
      </Tbl></Card>
      <Pager pg={pg} tp={TP} total={d?.total || 0} limit={limit} onLimitChange={(n) => { setLimit(n); setPg(0); }} onPrev={() => setPg(pg - 1)} onNext={() => setPg(pg + 1)} />
      {showAdj && <AdjustModal close={() => setShowAdj(false)} done={() => { setShowAdj(false); setRefreshKey(k => k + 1); load(); }} />}
    </div>
  );
}

function AdjustModal({ close, done }: { close: () => void; done: () => void }) {
  const [uid, setUid] = useState(''); const [amt, setAmt] = useState(0); const [desc, setDesc] = useState('');
  const [saving, setSaving] = useState(false); const [confirmed, setConfirmed] = useState(false);

  const submit = async () => { setSaving(true);
    try { await apiRequest('/admin/credits/adjust', { method: 'POST', body: { user_id: uid, amount: amt, description: desc || undefined } }); showToast('额度调整成功', 'success'); done(); }
    catch (e: unknown) { showToast(e instanceof Error ? e.message : '调整失败', 'error'); }
    finally { setSaving(false); }
  };

  return <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.25)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }} onClick={close}>
    <div style={{ background: 'var(--white)', borderRadius: 'var(--radius-xl)', padding: '28px 32px', minWidth: 420, boxShadow: 'var(--shadow-lg)' }} onClick={e => e.stopPropagation()}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20 }}>
        <h3 style={{ fontSize: 17, fontWeight: 600, letterSpacing: '-0.02em', margin: 0 }}>调整额度</h3>
        <button onClick={close} style={{ background: 'none', border: 'none', fontSize: 16, color: 'var(--gray-400)', cursor: 'pointer' }}>✕</button>
      </div>
      {!confirmed ? <>
        <Fld label="用户 ID"><input value={uid} onChange={e => setUid(e.target.value)} style={finpS} /></Fld>
        <Fld label="额度（正数增加，负数扣减）"><input type="number" value={amt} onChange={e => setAmt(Number(e.target.value))} style={finpS} /></Fld>
        <Fld label="说明"><input value={desc} onChange={e => setDesc(e.target.value)} style={finpS} /></Fld>
        <button onClick={() => setConfirmed(true)} disabled={!uid || amt === 0} style={priBtn}>下一步</button>
      </> : <>
        <div style={{ background: '#fff9f0', borderRadius: 'var(--radius-md)', padding: 12, marginBottom: 16, fontSize: 13 }}>
          <p style={{ fontWeight: 600 }}>确认调整？</p>
          <p style={{ marginTop: 4 }}>用户: {uid}</p>
          <p style={{ color: amt > 0 ? '#34c759' : '#ff3b30', fontWeight: 600 }}>额度: {amt > 0 ? '+' : ''}{amt}</p>
          {desc && <p style={{ color: 'var(--gray-500)', fontSize: 12 }}>{desc}</p>}
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={submit} disabled={saving} style={{ ...priBtn, background: '#ff3b30' }}>{saving ? '处理中…' : '确认调整'}</button>
          <button onClick={() => setConfirmed(false)} style={secBtn}>返回</button>
          <button onClick={close} style={secBtn}>取消</button>
        </div>
      </>}
    </div>
  </div>;
}
