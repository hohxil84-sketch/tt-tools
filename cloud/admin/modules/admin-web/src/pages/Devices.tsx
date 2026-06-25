import React, { useEffect, useState, useCallback } from 'react';
import { apiRequest } from '../api/client';
import { Card, Tbl, Badge, LBtn, Pager, Sheet, Modal, secBtn, inpS, selS } from '../components/shared';

interface Dev { id: string; user_id: string; device_name: string | null; client_version: string | null; status: string; bound_at: string; last_seen_at: string | null; created_at?: string; updated_at?: string; }
interface List { items: Dev[]; total: number; limit: number; offset: number; }
const PAGE = 20;
const SL: Record<string, string> = { active: '正常', blocked: '已封禁', removed: '已移除' };
const SC: Record<string, string> = { active: '#34c759', blocked: '#ff9500', removed: '#ff3b30' };

export default function Devices() {
  const [d, setD] = useState<List | null>(null);
  const [sf, setSf] = useState(''); const [pg, setPg] = useState(0);
  const [err, setErr] = useState(''); const [detail, setDetail] = useState<Dev | null>(null);
  const [ca, setCa] = useState<{ id: string; s: string } | null>(null);
  const [cd, setCd] = useState<string | null>(null);

  const load = useCallback(async () => {
    setErr('');
    try { setD(await apiRequest<List>('/admin/devices', { params: { limit: PAGE, offset: pg * PAGE, status: sf || undefined } })); }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '加载失败'); }
  }, [pg, sf]);
  useEffect(() => { load(); }, [load]);

  const upd = async (id: string, ns: string) => { await apiRequest(`/admin/devices/${id}/status`, { method: 'PATCH', body: { status: ns } }); setCa(null); load(); };
  const del = async () => { if (!cd) return; await apiRequest(`/admin/devices/${cd}`, { method: 'DELETE' }); setCd(null); load(); };
  const TP = d ? Math.ceil(d.total / PAGE) : 0;

  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.02em', marginBottom: 20 }}>设备管理</h2>
      <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
        <select value={sf} onChange={e => { setSf(e.target.value); setPg(0); }} style={selS}><option value="">全部</option><option value="active">正常</option><option value="blocked">已封禁</option><option value="removed">已移除</option></select>
        <button onClick={load} style={secBtn}>刷新</button>
      </div>
      {err && <div style={{ color: 'var(--red)', fontSize: 12, marginBottom: 12 }}>{err}</div>}
      <Card><Tbl heads={['设备', '用户 ID', '版本', '状态', '绑定时间', '最近活跃', '']}>
        {d?.items.map(x => (
          <tr key={x.id}>
            <td style={{ fontWeight: 500 }}>{x.device_name || '—'}</td>
            <td style={{ color: 'var(--gray-500)', fontSize: 12 }}>{x.user_id.substring(0, 10)}…</td>
            <td style={{ color: 'var(--gray-500)' }}>{x.client_version || '—'}</td>
            <td><span style={{ fontSize: 12, fontWeight: 500, color: SC[x.status] }}>{SL[x.status]}</span></td>
            <td style={{ fontSize: 12, color: 'var(--gray-500)' }}>{new Date(x.bound_at).toLocaleString('zh-CN')}</td>
            <td style={{ fontSize: 12, color: 'var(--gray-500)' }}>{x.last_seen_at ? new Date(x.last_seen_at).toLocaleString('zh-CN') : '—'}</td>
            <td style={{ textAlign: 'right' }}>
              <LBtn onClick={() => setDetail(x)}>详情</LBtn>
              {x.status === 'active' && <LBtn c="#ff9500" onClick={() => setCa({ id: x.id, s: 'blocked' })}>封禁</LBtn>}
              {x.status === 'blocked' && <LBtn c="#34c759" onClick={() => setCa({ id: x.id, s: 'active' })}>解封</LBtn>}
              <LBtn c="#ff3b30" onClick={() => setCd(x.id)}>删除</LBtn>
            </td>
          </tr>
        ))}
      </Tbl></Card>
      <Pager pg={pg} tp={TP} total={d?.total || 0} onPrev={() => setPg(pg - 1)} onNext={() => setPg(pg + 1)} />
      {detail && <Sheet title="设备详情" close={() => setDetail(null)}>
        <div>{[['ID', detail.id], ['名称', detail.device_name], ['用户', detail.user_id], ['版本', detail.client_version], ['状态', detail.status], ['绑定', new Date(detail.bound_at).toLocaleString('zh-CN')], ['最近活跃', detail.last_seen_at ? new Date(detail.last_seen_at).toLocaleString('zh-CN') : '—'], ['创建', detail.created_at ? new Date(detail.created_at).toLocaleString('zh-CN') : '—'], ['更新', detail.updated_at ? new Date(detail.updated_at).toLocaleString('zh-CN') : '—']].map(([l, v]) => <div key={l} style={{ display: 'flex', padding: '6px 0', borderBottom: '1px solid var(--gray-200)' }}><span style={{ width: 90, fontSize: 12, color: 'var(--gray-500)' }}>{l}</span><span style={{ fontSize: 13 }}>{v || '—'}</span></div>)}</div>
      </Sheet>}
      {ca && <Modal title="确认" close={() => setCa(null)} action={() => upd(ca.id, ca.s)} danger><p>将设备状态改为 <b>{SL[ca.s]}</b>？</p></Modal>}
      {cd && <Modal title="删除设备" close={() => setCd(null)} action={del} danger><p>永久删除该设备？此操作不可撤销。</p></Modal>}
    </div>
  );
}
