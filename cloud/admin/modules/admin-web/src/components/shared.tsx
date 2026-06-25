/** Apple-style shared components for admin pages. */
import React from 'react';

export const priBtn: React.CSSProperties = { padding: '7px 20px', borderRadius: 'var(--radius-md)', border: 'none', background: 'var(--blue)', color: '#fff', fontSize: 13, fontWeight: 500, letterSpacing: '-0.01em', cursor: 'pointer' };
export const secBtn: React.CSSProperties = { ...priBtn, background: 'var(--gray-200)', color: 'var(--gray-700)' };
export const inpS: React.CSSProperties = { padding: '8px 14px', border: '1px solid var(--gray-300)', borderRadius: 'var(--radius-md)', fontSize: 13, outline: 'none', color: 'var(--gray-800)', background: 'var(--white)', minWidth: 160 };
export const selS: React.CSSProperties = { ...inpS, minWidth: 120 };
export const finpS: React.CSSProperties = { ...inpS, width: '100%', boxSizing: 'border-box' };

export function Card({ children }: { children: React.ReactNode }) {
  return <div style={{ background: 'var(--white)', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--gray-200)', overflow: 'hidden' }}>{children}</div>;
}

export function Tbl({ heads, children }: { heads: string[]; children: React.ReactNode }) {
  return <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
    <thead><tr style={{ background: 'var(--gray-100)' }}>{heads.map((h, i) => <th key={i} style={{ padding: '10px 16px', textAlign: i === heads.length - 1 ? 'right' : 'left', fontWeight: 500, fontSize: 11, color: 'var(--gray-500)', letterSpacing: '0.02em', textTransform: 'uppercase', borderBottom: '1px solid var(--gray-200)' }}>{h}</th>)}</tr></thead>
    <tbody>{children}</tbody>
  </table>;
}

export function Badge({ t, c = 'var(--gray-500)' }: { t: string; c?: string }) {
  return <span style={{ display: 'inline-block', padding: '2px 10px', borderRadius: 20, background: c + '18', color: c, fontSize: 11, fontWeight: 500 }}>{t}</span>;
}

export function LBtn({ onClick, c = 'var(--blue)', children }: { onClick: () => void; c?: string; children: React.ReactNode }) {
  return <button onClick={onClick} style={{ background: 'none', border: 'none', color: c, fontSize: 12, fontWeight: 500, cursor: 'pointer', padding: '2px 6px' }}>{children}</button>;
}

export function Pager({ pg, tp, total, onPrev, onNext }: { pg: number; tp: number; total: number; onPrev: () => void; onNext: () => void }) {
  if (tp <= 1) return null;
  return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, marginTop: 20, fontSize: 12, color: 'var(--gray-500)' }}>
    <button disabled={pg === 0} onClick={onPrev} style={secBtn}>上一页</button>
    <span>第 {pg + 1}/{tp} 页（共 {total} 条）</span>
    <button disabled={pg >= tp - 1} onClick={onNext} style={secBtn}>下一页</button>
  </div>;
}

export function Sheet({ title, close, children }: { title: string; close: () => void; children?: React.ReactNode }) {
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.25)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }} onClick={close}>
      <div style={{ background: 'var(--white)', borderRadius: 'var(--radius-xl)', padding: '28px 32px', minWidth: 420, maxWidth: 620, maxHeight: '80vh', overflow: 'auto', boxShadow: 'var(--shadow-lg)' }} onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h3 style={{ fontSize: 17, fontWeight: 600, letterSpacing: '-0.02em', margin: 0 }}>{title}</h3>
          <button onClick={close} style={{ background: 'none', border: 'none', fontSize: 16, color: 'var(--gray-400)', cursor: 'pointer', padding: 4 }}>✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Modal({ title, close, action, danger, children }: { title: string; close: () => void; action: () => void; danger?: boolean; children: React.ReactNode }) {
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.25)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }} onClick={close}>
      <div style={{ background: 'var(--white)', borderRadius: 'var(--radius-xl)', padding: '28px 32px', minWidth: 380, boxShadow: 'var(--shadow-lg)' }} onClick={e => e.stopPropagation()}>
        <h3 style={{ fontSize: 17, fontWeight: 600, letterSpacing: '-0.02em', marginBottom: 12 }}>{title}</h3>
        <div style={{ fontSize: 13, color: 'var(--gray-700)', marginBottom: 20 }}>{children}</div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={action} style={{ ...priBtn, background: danger ? 'var(--red)' : 'var(--blue)' }}>确认</button>
          <button onClick={close} style={secBtn}>取消</button>
        </div>
      </div>
    </div>
  );
}

export function Fld({ label, children }: { label: string; children: React.ReactNode }) {
  return <div style={{ marginBottom: 14 }}><label style={{ display: 'block', marginBottom: 5, fontSize: 12, fontWeight: 500, color: 'var(--gray-700)', letterSpacing: '-0.01em' }}>{label}</label>{children}</div>;
}

export function DetailRows({ rows }: { rows: [string, string | number | null | undefined][] }) {
  return <>{rows.map(([l, v]) => <div key={l} style={{ display: 'flex', padding: '7px 0', borderBottom: '1px solid var(--gray-200)' }}>
    <span style={{ width: 100, flexShrink: 0, fontSize: 12, color: 'var(--gray-500)' }}>{l}</span>
    <span style={{ fontSize: 13, color: 'var(--gray-800)', wordBreak: 'break-all' }}>{v ?? '—'}</span>
  </div>)}</>;
}
