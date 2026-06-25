import React, { useEffect, useState } from 'react';
import { apiRequest } from '../api/client';

interface Brk { key: string; calls: number; total_tokens: number; total_cost: number; total_credits: number; }
interface Stats { total_calls: number; total_tokens: number; total_cost: number; total_credits_charged: number; by_feature: Brk[]; by_provider: Brk[]; }

export default function CostStats() {
  const [d, setD] = useState<Stats | null>(null);
  const [err, setErr] = useState('');
  useEffect(() => { apiRequest<Stats>('/admin/cost-stats').then(setD).catch(e => setErr(e.message)); }, []);
  if (err) return <div style={{ color: 'var(--red)', fontSize: 13 }}>{err}</div>;
  if (!d) return <div style={{ color: 'var(--gray-500)', fontSize: 13 }}>加载中…</div>;

  const cards = [
    { l: '总调用次数', v: d.total_calls.toLocaleString(), c: '#0071e3' },
    { l: '总 Token', v: d.total_tokens.toLocaleString(), c: '#34c759' },
    { l: '总成本 (USD)', v: `$${d.total_cost.toFixed(4)}`, c: '#ff9500' },
    { l: '总扣额度', v: d.total_credits_charged.toLocaleString(), c: '#af52de' },
  ];

  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.02em', marginBottom: 24 }}>成本统计</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 14, marginBottom: 28 }}>
        {cards.map(c => <div key={c.l} style={{ background: 'var(--white)', borderRadius: 'var(--radius-lg)', padding: '18px 22px', border: '1px solid var(--gray-200)', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ fontSize: 11, fontWeight: 500, color: 'var(--gray-500)', marginBottom: 5, letterSpacing: '0.02em', textTransform: 'uppercase' }}>{c.l}</div>
          <div style={{ fontSize: 26, fontWeight: 600, color: c.c, letterSpacing: '-0.02em' }}>{c.v}</div>
        </div>)}
      </div>
      <Section title="按功能码" items={d.by_feature} />
      <Section title="按 Provider" items={d.by_provider} />
    </div>
  );
}

function Section({ title, items }: { title: string; items: Brk[] }) {
  return (
    <div style={{ background: 'var(--white)', borderRadius: 'var(--radius-lg)', padding: '20px 24px', border: '1px solid var(--gray-200)', boxShadow: 'var(--shadow-sm)', marginBottom: 18 }}>
      <h3 style={{ fontSize: 14, fontWeight: 600, letterSpacing: '-0.01em', marginBottom: 14 }}>{title}</h3>
      {items.length === 0 ? <div style={{ color: 'var(--gray-400)', fontSize: 12 }}>暂无数据</div> : <table className="admin-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead><tr>
          <th style={{ textAlign: 'left' }}>名称</th>
          <th style={{ textAlign: 'right' }}>调用</th>
          <th style={{ textAlign: 'right' }}>Token</th>
          <th style={{ textAlign: 'right' }}>成本</th>
          <th style={{ textAlign: 'right' }}>额度</th>
        </tr></thead>
        <tbody>{items.map(i => <tr key={i.key}>
          <td><code style={{ fontSize: 12, color: 'var(--blue)' }}>{i.key}</code></td>
          <td style={{ textAlign: 'right' }}>{i.calls.toLocaleString()}</td>
          <td style={{ textAlign: 'right' }}>{i.total_tokens.toLocaleString()}</td>
          <td style={{ textAlign: 'right' }}>${i.total_cost.toFixed(4)}</td>
          <td style={{ textAlign: 'right' }}>{i.total_credits.toLocaleString()}</td>
        </tr>)}</tbody>
      </table>}
    </div>
  );
}
