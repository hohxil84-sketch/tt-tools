/** Apple-style shared components for admin pages. */
import React, { useState, useEffect } from 'react';

export const priBtn: React.CSSProperties = { padding: '7px 20px', borderRadius: 'var(--radius-md)', border: 'none', background: 'var(--blue)', color: '#fff', fontSize: 13, fontWeight: 500, letterSpacing: '-0.01em', cursor: 'pointer', transition: 'all 0.15s ease' };
export const secBtn: React.CSSProperties = { ...priBtn, background: 'var(--gray-200)', color: 'var(--gray-700)' };
export const inpS: React.CSSProperties = { padding: '8px 14px', border: '1px solid var(--gray-300)', borderRadius: 'var(--radius-md)', fontSize: 13, outline: 'none', color: 'var(--gray-800)', background: 'var(--white)', minWidth: 160 };
export const selS: React.CSSProperties = { ...inpS, minWidth: 120 };
export const finpS: React.CSSProperties = { ...inpS, width: '100%', boxSizing: 'border-box' };

// ============================================================
// Toast 通知系统（全局事件驱动，无需 Context）
// ============================================================

type ToastItem = { id: number; message: string; type: 'success' | 'error' };
let _toastId = 0;
let _addToast: ((t: ToastItem) => void) | null = null;

/** 任何组件可直接调用，弹出右上角通知 */
export function showToast(message: string, type: 'success' | 'error') {
  _toastId += 1;
  if (_addToast) _addToast({ id: _toastId, message, type });
}

/** 放在 App 根节点下，全局唯一 */
export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  useEffect(() => {
    _addToast = (t: ToastItem) => {
      setToasts(prev => [...prev, t]);
      setTimeout(() => { setToasts(prev => prev.filter(x => x.id !== t.id)); }, 2500);
    };
    return () => { _addToast = null; };
  }, []);
  if (toasts.length === 0) return null;
  return (
    <div style={{ position: 'fixed', top: 24, right: 24, zIndex: 3000, display: 'flex', flexDirection: 'column', gap: 8 }}>
      {toasts.map(t => (
        <div key={t.id} style={{ padding: '12px 24px', borderRadius: 8, background: t.type === 'success' ? '#34c759' : '#ff3b30', color: '#fff', fontSize: 14, fontWeight: 500, boxShadow: '0 4px 12px rgba(0,0,0,0.15)', animation: 'fadeIn 0.3s ease', maxWidth: 360 }}>
          {t.type === 'success' ? '✓ ' : '✕ '}{t.message}
        </div>
      ))}
    </div>
  );
}

// ============================================================
// ActBtn — 彩色操作按钮（替代纯文字 LBtn）
// ============================================================

const _abS: React.CSSProperties = {
  display: 'inline-block', padding: '3px 10px', borderRadius: 4, border: 'none',
  fontSize: 11, fontWeight: 500, cursor: 'pointer', letterSpacing: '-0.01em',
  transition: 'all 0.12s ease', margin: '0 1px',
};

const _abColors: Record<string, string> = {
  detail: '#8e8e93',   // 灰 — 详情
  edit: '#007aff',     // 蓝 — 编辑
  role: '#af52de',     // 紫 — 角色/权限
  credit: '#ff9500',   // 橙 — 算力
  password: '#5ac8fa', // 青蓝 — 密码
  block: '#ff9500',    // 橙 — 封禁/停用
  unblock: '#34c759',  // 绿 — 解封/启用
  delete: '#ff3b30',   // 红 — 删除
};

/** 彩色操作按钮 */
export function ActBtn({ onClick, kind, children }: { onClick: () => void; kind: keyof typeof _abColors; children: React.ReactNode }) {
  const c = _abColors[kind] || '#8e8e93';
  return <button onClick={onClick} style={{ ..._abS, background: c, color: '#fff' }}>{children}</button>;
}

/** 旧版文字链接按钮（过渡期兼容） */
export function LBtn({ onClick, c = 'var(--blue)', children }: { onClick: () => void; c?: string; children: React.ReactNode }) {
  return <button onClick={onClick} style={{ background: 'none', border: 'none', color: c, fontSize: 12, fontWeight: 500, cursor: 'pointer', padding: '2px 6px' }}>{children}</button>;
}

export function Card({ children }: { children: React.ReactNode }) {
  return <div style={{ background: 'var(--white)', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--gray-200)', overflow: 'hidden' }}>{children}</div>;
}

export function Tbl({ heads, colAligns, children }: { heads: (string | React.ReactNode)[]; colAligns?: ('l' | 'r' | 'c')[]; children: React.ReactNode }) {
  const align = (i: number): React.CSSProperties['textAlign'] => {
    const a = (colAligns || [])[i] || 'l';
    return a === 'r' ? 'right' : a === 'c' ? 'center' : 'left';
  };
  return <table className="admin-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, tableLayout: 'fixed' }}>
    <thead><tr>{heads.map((h, i) => <th key={i} style={{ padding: '10px 8px', textAlign: align(i), width: i === 0 && typeof h !== 'string' ? 36 : undefined }}>{h}</th>)}</tr></thead>
    <tbody>{children}</tbody>
  </table>;
}

export function Badge({ t, c = 'var(--gray-500)' }: { t: string; c?: string }) {
  return <span style={{ display: 'inline-block', padding: '2px 10px', borderRadius: 20, background: c + '18', color: c, fontSize: 11, fontWeight: 500 }}>{t}</span>;
}

export function Pager({ pg, tp, total, limit, order, onOrderChange, onLimitChange, onPrev, onNext }: { pg: number; tp: number; total: number; limit: number; order?: string; onOrderChange?: (o: string) => void; onLimitChange: (n: number) => void; onPrev: () => void; onNext: () => void }) {
  return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, marginTop: 20, fontSize: 12, color: 'var(--gray-500)' }}>
    <button disabled={pg === 0} onClick={onPrev} style={secBtn}>上一页</button>
    <span>第 {pg + 1}/{tp} 页（共 {total} 条）</span>
    <button disabled={pg >= tp - 1} onClick={onNext} style={secBtn}>下一页</button>
    <select value={limit} onChange={e => onLimitChange(Number(e.target.value))} style={{ ...selS, minWidth: 80, fontSize: 12, marginLeft: 8 }}>
      <option value={10}>10条/页</option><option value={20}>20条/页</option><option value={50}>50条/页</option><option value={100}>100条/页</option>
    </select>
    {onOrderChange && <select value={order || 'desc'} onChange={e => onOrderChange(e.target.value)} style={{ ...selS, minWidth: 80, fontSize: 12 }}>
      <option value="desc">倒序</option><option value="asc">正序</option>
    </select>}
  </div>;
}

export function Sheet({ title, close, maxHeight, children }: { title: string; close: () => void; maxHeight?: string; children?: React.ReactNode }) {
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.25)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <div style={{ background: 'var(--white)', borderRadius: 'var(--radius-xl)', padding: '28px 32px', minWidth: 420, maxWidth: 680, maxHeight: maxHeight || '80vh', overflow: maxHeight ? 'auto' : 'visible', boxShadow: 'var(--shadow-lg)' }} onClick={e => e.stopPropagation()}>
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
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.25)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
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
