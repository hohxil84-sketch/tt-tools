import React, { useEffect, useState } from 'react';
import { Link, useLocation, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { apiRequest } from '../api/client';

interface MenuItem {
  id: string; title: string; icon: string; path: string;
  children?: MenuItem[] | null;
}

/** 跨平台菜单图标映射 — 使用通用 Unicode 字符替代 SF Symbols */
const iconMap: Record<string, string> = {
  dashboard: '◆', users: '●', billing: '◇', ops: '✦',
  list: '▸', devices: '◻', plan: '▤', order: '◎',
  credits: '◆', ledger: '◈', log: '▥', cost: '◉',
  risk: '⚠', feature: '⚙',
};

export default function Layout() {
  const { user, logout } = useAuth();
  const loc = useLocation();
  const navigate = useNavigate();
  const [menu, setMenu] = useState<MenuItem[]>([]);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    apiRequest<{ menu: MenuItem[] }>('/admin/menu').then(d => setMenu(d.menu)).catch(() => {});
  }, []);

  const toPath = (p: string) => p.replace(/^\/admin/, '') || '/';
  const active = (p: string) => {
    const n = toPath(p);
    return loc.pathname === n || loc.pathname.startsWith(n + '/');
  };

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar */}
      <aside style={{
        width: collapsed ? 64 : 232,
        background: 'rgba(29,29,31,0.95)',
        backdropFilter: 'blur(40px)',
        WebkitBackdropFilter: 'blur(40px)',
        color: '#f5f5f7',
        display: 'flex', flexDirection: 'column', flexShrink: 0,
        transition: 'width 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
        borderRight: '1px solid rgba(255,255,255,0.08)',
        zIndex: 100,
      }}>
        <div style={{
          height: 52, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: collapsed ? '0 18px' : '0 20px',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
        }}>
          {!collapsed && (
            <span style={{ fontSize: 17, fontWeight: 700, letterSpacing: '0.01em', color: '#ffffff', display: 'flex', alignItems: 'center', gap: 9 }}>
              <img src="/admin/app-icon.png" alt="" style={{ width: 24, height: 24, borderRadius: 6, objectFit: 'contain' }} />
              Alphoria
            </span>
          )}
          <button onClick={() => setCollapsed(!collapsed)} style={{
            background: 'none', border: 'none', color: 'rgba(255,255,255,0.5)',
            fontSize: 14, cursor: 'pointer', padding: 4,
          }}>
            {collapsed ? '▶' : '◀'}
          </button>
        </div>

        <nav style={{ flex: 1, overflowY: 'auto', padding: '10px 0' }}>
          {menu.map(item => (
            <div key={item.id} style={{ marginBottom: 2 }}>
              {/* 一级菜单 — 纯白/米白，更大字体，更突出 */}
              <Link to={toPath(item.path)} style={{
                display: 'flex', alignItems: 'center', gap: collapsed ? 0 : 12,
                padding: collapsed ? '12px 0' : '11px 20px',
                justifyContent: collapsed ? 'center' : 'flex-start',
                margin: collapsed ? '3px 10px' : '4px 8px',
                borderRadius: 8,
                color: active(item.path) ? '#ffffff' : '#f5f5f7',
                background: active(item.path) ? 'rgba(255,255,255,0.15)' : 'transparent',
                fontSize: 15, fontWeight: active(item.path) ? 600 : 500,
                letterSpacing: '0.01em',
                transition: 'all 0.15s ease',
              }}
                title={collapsed ? item.title : undefined}
              >
                <span style={{ fontSize: collapsed ? 20 : 16, opacity: active(item.path) ? 1 : 0.85 }}>
                  {iconMap[item.icon] || '◆'}
                </span>
                {!collapsed && item.title}
              </Link>
              {/* 二级菜单 — 稍小字体，米白色 */}
              {!collapsed && item.children?.map(c => (
                <Link key={c.id} to={toPath(c.path)} style={{
                  display: 'block',
                  padding: '8px 20px 8px 52px',
                  color: active(c.path) ? '#ffffff' : '#e8e8ed',
                  fontSize: 13, fontWeight: active(c.path) ? 500 : 400,
                  letterSpacing: '0.01em',
                  transition: 'all 0.15s ease',
                  opacity: active(c.path) ? 1 : 0.85,
                }}>
                  {c.title}
                </Link>
              ))}
            </div>
          ))}
        </nav>
      </aside>

      {/* Main */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <header style={{
          height: 52, background: 'rgba(255,255,255,0.72)',
          backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)',
          borderBottom: '1px solid var(--gray-300)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '0 28px', flexShrink: 0, zIndex: 50,
        }}>
          <span style={{ fontSize: 15, fontWeight: 600, color: 'var(--gray-800)', letterSpacing: '-0.01em' }}>
            Alphoria 管理后台
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <span style={{ fontSize: 13, color: 'var(--gray-500)' }}>
              {user?.account}
            </span>
            <button onClick={() => { logout(); }} style={{
              padding: '5px 14px', borderRadius: 20, border: 'none',
              background: 'var(--gray-200)', color: 'var(--gray-700)',
              fontSize: 12, fontWeight: 500, letterSpacing: '-0.01em',
              transition: 'all 0.15s ease',
            }}>
              退出
            </button>
          </div>
        </header>

        <main style={{ flex: 1, padding: '28px', overflowY: 'auto' }}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
