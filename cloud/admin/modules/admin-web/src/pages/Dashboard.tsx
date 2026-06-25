import React, { useEffect, useState } from 'react';
import { apiRequest } from '../api/client';

interface Stats { users_total: number; orders_today: number; revenue_today_cents: number; active_devices: number; server_status: string; }
interface Status { status: string; version: string; uptime_seconds: number; }

export default function Dashboard() {
  const [s, setS] = useState<Stats | null>(null);
  const [st, setSt] = useState<Status | null>(null);
  const [err, setErr] = useState('');

  useEffect(() => {
    Promise.all([apiRequest<Stats>('/admin/dashboard'), apiRequest<Status>('/admin/status')])
      .then(([a, b]) => { setS(a); setSt(b); }).catch(e => setErr(e.message));
  }, []);

  if (err) return <div style={{ color: 'var(--red)', fontSize: 13 }}>加载失败: {err}</div>;
  if (!s) return <div style={{ color: 'var(--gray-500)', fontSize: 13 }}>加载中…</div>;

  const cards = [
    { label: '用户总数', value: s.users_total.toLocaleString(), color: '#0071e3' },
    { label: '今日订单', value: s.orders_today.toLocaleString(), color: '#34c759' },
    { label: '今日收入', value: `¥${(s.revenue_today_cents / 100).toFixed(2)}`, color: '#ff9500' },
    { label: '活跃设备', value: s.active_devices.toLocaleString(), color: '#af52de' },
  ];

  const fmt = (sec: number) => {
    const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60);
    return `${h} 时 ${m} 分`;
  };

  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.02em', marginBottom: 24 }}>
        仪表盘
      </h2>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 28 }}>
        {cards.map(c => (
          <div key={c.label} style={{
            background: 'var(--white)', borderRadius: 'var(--radius-lg)', padding: '20px 24px',
            boxShadow: 'var(--shadow-sm)', border: '1px solid var(--gray-200)',
          }}>
            <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--gray-500)', marginBottom: 6, letterSpacing: '-0.01em' }}>
              {c.label}
            </div>
            <div style={{ fontSize: 30, fontWeight: 600, color: c.color, letterSpacing: '-0.02em' }}>
              {c.value}
            </div>
          </div>
        ))}
      </div>

      {st && (
        <div style={{
          background: 'var(--white)', borderRadius: 'var(--radius-lg)', padding: '20px 24px',
          boxShadow: 'var(--shadow-sm)', border: '1px solid var(--gray-200)',
        }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, letterSpacing: '-0.01em' }}>
            服务状态
          </h3>
          <div style={{ display: 'flex', gap: 32, fontSize: 13 }}>
            <Item label="状态" value={st.status} dot={st.status === 'healthy' ? 'var(--green)' : 'var(--red)'} />
            <Item label="版本" value={st.version} />
            <Item label="运行时长" value={fmt(st.uptime_seconds)} />
          </div>
        </div>
      )}
    </div>
  );
}

function Item({ label, value, dot }: { label: string; value: string; dot?: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      {dot && <span style={{ width: 7, height: 7, borderRadius: '50%', background: dot, display: 'inline-block' }} />}
      <span style={{ color: 'var(--gray-500)' }}>{label}</span>
      <span style={{ fontWeight: 500, color: 'var(--gray-800)' }}>{value}</span>
    </div>
  );
}
