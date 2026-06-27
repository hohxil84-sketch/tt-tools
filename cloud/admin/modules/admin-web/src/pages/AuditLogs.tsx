import React, { useEffect, useState, useCallback } from 'react';
import { apiRequest } from '../api/client';
import { Card, Tbl, Badge, LBtn, Pager, Sheet, DetailRows, secBtn, inpS, selS } from '../components/shared';

interface Log { id: string; admin_user_id: string; admin_account: string; action: string; target_type: string; target_id: string | null; summary: string; ip_address: string | null; created_at: string; details_json?: any; }
interface List { items: Log[]; total: number; limit: number; offset: number; }
const PAGE = 20;

const ACTION_LABELS: Record<string, string> = {
  create: '创建', update: '更新', delete: '删除', status_change: '状态变更',
  adjust: '额度调整', refund: '退款', cancel: '取消', batch: '批量操作',
};
const TARGET_LABELS: Record<string, string> = {
  user: '用户', device: '设备', order: '订单', plan: '套餐', credits: '额度',
  feature_flag: '功能开关', provider: 'Provider', audit_log: '审计日志', role: '角色权限', feature_code: '功能码',
};

export default function AuditLogs() {
  const [d, setD] = useState<List | null>(null);
  const [action, setAction] = useState(''); const [targetType, setTargetType] = useState('');
  const [pg, setPg] = useState(0); const [err, setErr] = useState(''); const [detail, setDetail] = useState<Log | null>(null);

  const load = useCallback(async () => {
    setErr('');
    try {
      setD(await apiRequest<List>('/admin/audit-logs', {
        params: { limit: PAGE, offset: pg * PAGE, action: action || undefined, target_type: targetType || undefined },
      }));
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : '加载失败'); }
  }, [pg, action, targetType]);
  useEffect(() => { load(); }, [load]);
  const TP = d ? Math.ceil(d.total / PAGE) : 0;

  const loadDetail = async (id: string) => {
    try { setDetail(await apiRequest<Log>(`/admin/audit-logs/${id}`)); }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : '加载详情失败'); }
  };

  // Format details_json as pretty JSON
  const formatDetails = (details: any) => {
    if (!details) return '—';
    try { return JSON.stringify(details, null, 2); }
    catch { return String(details); }
  };

  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.02em', marginBottom: 20 }}>审计日志</h2>
      <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
        <select value={action} onChange={e => { setAction(e.target.value); setPg(0); }} style={selS}>
          <option value="">全部操作</option>
          <option value="create">创建</option><option value="update">更新</option>
          <option value="delete">删除</option><option value="status_change">状态变更</option>
          <option value="adjust">额度调整</option><option value="refund">退款</option>
          <option value="cancel">取消</option><option value="batch">批量操作</option>
        </select>
        <select value={targetType} onChange={e => { setTargetType(e.target.value); setPg(0); }} style={selS}>
          <option value="">全部目标</option>
          <option value="user">用户</option><option value="device">设备</option>
          <option value="order">订单</option><option value="plan">套餐</option>
          <option value="credits">额度</option><option value="feature_flag">功能开关</option>
        </select>
        <button onClick={load} style={secBtn}>刷新</button>
      </div>
      {err && <div style={{ color: 'var(--red)', fontSize: 12, marginBottom: 12 }}>{err}</div>}
      <Card><Tbl heads={['时间', '操作人', '操作', '目标', '摘要', 'IP', '']}>
        {d?.items.map(l => (
          <tr key={l.id}>
            <td style={{ fontSize: 12, color: 'var(--gray-500)', whiteSpace: 'nowrap' }}>{new Date(l.created_at).toLocaleString('zh-CN')}</td>
            <td style={{ fontSize: 12, fontWeight: 500 }}>{l.admin_account}</td>
            <td><Badge t={ACTION_LABELS[l.action] || l.action} c={l.action === 'delete' ? 'var(--red)' : 'var(--blue)'} /></td>
            <td style={{ fontSize: 12 }}>{(TARGET_LABELS[l.target_type] || l.target_type) + (l.target_id ? ` (${l.target_id.substring(0, 8)}...)` : '')}</td>
            <td style={{ fontSize: 12, maxWidth: 250, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{l.summary}</td>
            <td style={{ fontSize: 11, color: 'var(--gray-400)', fontFamily: 'monospace' }}>{l.ip_address || '—'}</td>
            <td style={{ textAlign: 'right' }}><LBtn onClick={() => loadDetail(l.id)}>详情</LBtn></td>
          </tr>
        ))}
      </Tbl></Card>
      <Pager pg={pg} tp={TP} total={d?.total || 0} onPrev={() => setPg(pg - 1)} onNext={() => setPg(pg + 1)} />
      {detail && <Sheet title="审计日志详情" close={() => setDetail(null)}>
        <DetailRows rows={[
          ['ID', detail.id],
          ['操作人', detail.admin_account],
          ['操作类型', ACTION_LABELS[detail.action] || detail.action],
          ['目标类型', TARGET_LABELS[detail.target_type] || detail.target_type],
          ['目标 ID', detail.target_id || '—'],
          ['摘要', detail.summary],
          ['IP 地址', detail.ip_address || '—'],
          ['时间', new Date(detail.created_at).toLocaleString('zh-CN')],
        ]} />
        {detail.details_json && (
          <div style={{ marginTop: 16 }}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, color: 'var(--gray-600)' }}>操作详情</div>
            <pre style={{
              background: 'var(--gray-50)', padding: 12, borderRadius: 6, fontSize: 11,
              fontFamily: 'monospace', overflow: 'auto', maxHeight: 300,
              border: '1px solid var(--gray-200)',
            }}>{formatDetails(detail.details_json)}</pre>
          </div>
        )}
      </Sheet>}
    </div>
  );
}
