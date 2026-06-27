import React, { useEffect, useState, useCallback } from 'react';
import { apiRequest } from '../api/client';
import { Card, Tbl, Badge, ActBtn, Pager, Sheet, Modal, secBtn, inpS, selS, showToast } from '../components/shared';

interface Dev { id: string; user_id: string; user_account?: string | null; device_name: string | null; client_version: string | null; status: string; bound_at: string; last_seen_at: string | null; created_at?: string; updated_at?: string; }
interface List { items: Dev[]; total: number; limit: number; offset: number; }
const SL: Record<string, string> = { active: '正常', blocked: '已封禁', removed: '已移除' };
const SC: Record<string, string> = { active: '#34c759', blocked: '#ff9500', removed: '#ff3b30' };

export default function Devices() {
  const [d, setD] = useState<List | null>(null);
  const [search, setSearch] = useState(''); const [sf, setSf] = useState(''); const [pg, setPg] = useState(0);
  const [err, setErr] = useState(''); const [detail, setDetail] = useState<Dev | null>(null);
  const [ca, setCa] = useState<{ id: string; s: string } | null>(null);
  const [cd, setCd] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [limit, setLimit] = useState(10);

  const load = useCallback(async () => {
    setErr('');
    try { setD(await apiRequest<List>('/admin/devices', { params: { limit, offset: pg * limit, search: search || undefined, status: sf || undefined } })); }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '加载失败'); }
  }, [pg, search, sf, limit, refreshKey]);
  useEffect(() => { load(); }, [load]);

  const upd = async (id: string, ns: string) => { try { await apiRequest(`/admin/devices/${id}/status`, { method: 'PATCH', body: { status: ns } }); showToast('操作成功', 'success'); setCa(null); setRefreshKey(k => k + 1); load(); } catch (e: unknown) { showToast(e instanceof Error ? e.message : '操作失败', 'error'); } };
  const del = async () => { if (!cd) return; try { await apiRequest(`/admin/devices/${cd}`, { method: 'DELETE' }); showToast('删除成功', 'success'); setCd(null); setRefreshKey(k => k + 1); load(); } catch (e: unknown) { showToast(e instanceof Error ? e.message : '删除失败', 'error'); } };
  const TP = d ? Math.ceil(d.total / limit) : 0;

  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.02em', marginBottom: 20 }}>设备管理</h2>
      <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
        <input placeholder="搜索用户..." value={search} onChange={e => { setSearch(e.target.value); setPg(0); }} style={inpS} />
        <select value={sf} onChange={e => { setSf(e.target.value); setPg(0); }} style={selS}><option value="">全部</option><option value="active">正常</option><option value="blocked">已封禁</option><option value="removed">已移除</option></select>
        <button onClick={load} style={secBtn}>刷新</button>
      </div>
      {err && <div style={{ color: 'var(--red)', fontSize: 12, marginBottom: 12 }}>{err}</div>}
      <Card><Tbl heads={['设备', '用户 ID', '版本', '状态', '绑定时间', '最近活跃', '']} colAligns={['c','c','c','c','c','c','r']}>
        {d?.items.map(x => (
          <tr key={x.id}>
            <td style={{ fontWeight: 600, fontSize: 13, width: '24%', textAlign: 'center' }}>{x.device_name || '—'}</td>
            <td style={{ color: 'var(--gray-500)', fontSize: 12, width: '14%', textAlign: 'center' }}>{x.user_account || x.user_id.substring(0, 8) + '…'}</td>
            <td style={{ color: 'var(--gray-500)', fontSize: 13, width: '10%', textAlign: 'center' }}>{x.client_version || '—'}</td>
            <td style={{ fontSize: 13, width: '8%', textAlign: 'center' }}><span style={{ fontSize: 12, fontWeight: 500, color: SC[x.status] }}>{SL[x.status]}</span></td>
            <td style={{ fontSize: 12, color: 'var(--gray-500)', width: '16%', textAlign: 'center' }}>{new Date(x.bound_at).toLocaleString('zh-CN')}</td>
            <td style={{ fontSize: 12, color: 'var(--gray-500)', width: '16%', textAlign: 'center' }}>{x.last_seen_at ? new Date(x.last_seen_at).toLocaleString('zh-CN') : '—'}</td>
            <td style={{ textAlign: 'right', width: '12%', whiteSpace: 'nowrap' }}>
              <ActBtn kind="detail" onClick={() => setDetail(x)}>详情</ActBtn>
              {x.status === 'active' && <ActBtn kind="block" onClick={() => setCa({ id: x.id, s: 'blocked' })}>封禁</ActBtn>}
              {x.status === 'blocked' && <ActBtn kind="unblock" onClick={() => setCa({ id: x.id, s: 'active' })}>解封</ActBtn>}
              <ActBtn kind="delete" onClick={() => setCd(x.id)}>删除</ActBtn>
            </td>
          </tr>
        ))}
      </Tbl></Card>
      <Pager pg={pg} tp={TP} total={d?.total || 0} limit={limit} onLimitChange={(n) => { setLimit(n); setPg(0); }} onPrev={() => setPg(pg - 1)} onNext={() => setPg(pg + 1)} />
      {detail && <Sheet title="设备详情" close={() => setDetail(null)}>
        <div>{[['ID', detail.id], ['名称', detail.device_name], ['用户', detail.user_id], ['版本', detail.client_version], ['状态', detail.status], ['绑定', new Date(detail.bound_at).toLocaleString('zh-CN')], ['最近活跃', detail.last_seen_at ? new Date(detail.last_seen_at).toLocaleString('zh-CN') : '—'], ['创建', detail.created_at ? new Date(detail.created_at).toLocaleString('zh-CN') : '—'], ['更新', detail.updated_at ? new Date(detail.updated_at).toLocaleString('zh-CN') : '—']].map(([l, v]) => <div key={l} style={{ display: 'flex', padding: '6px 0', borderBottom: '1px solid var(--gray-200)' }}><span style={{ width: 90, fontSize: 12, color: 'var(--gray-500)' }}>{l}</span><span style={{ fontSize: 13 }}>{v || '—'}</span></div>)}</div>
      </Sheet>}
      {ca && <Modal title="确认" close={() => setCa(null)} action={() => upd(ca.id, ca.s)} danger><p>将设备状态改为 <b>{SL[ca.s]}</b>？</p></Modal>}
      {cd && <Modal title="删除设备" close={() => setCd(null)} action={del} danger><p>永久删除该设备？此操作不可撤销。</p></Modal>}
    </div>
  );
}
