import React, { useEffect, useState, useCallback } from 'react';
import { Link, useLocation, Outlet } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { apiRequest } from '../api/client';

interface MenuItem {
  id: string; title: string; icon: string; path: string;
  children?: MenuItem[] | null;
}

export default function Layout() {
  const { user, logout } = useAuth();
  const loc = useLocation();
  const [menu, setMenu] = useState<MenuItem[]>([]);
  const [collapsed, setCollapsed] = useState(false);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [highlightedId, setHighlightedId] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<{ menu: MenuItem[] }>('/admin/menu').then(d => setMenu(d.menu)).catch(() => {});
  }, []);

  const toPath = (p: string) => p.replace(/^\/admin/, '') || '/';
  const active = (p: string) => {
    const n = toPath(p);
    return loc.pathname === n || loc.pathname.startsWith(n + '/');
  };

  // 路由变化时：自动高亮当前激活页面的父级 + 自动展开
  useEffect(() => {
    for (const item of menu) {
      if (item.children && item.children.some(c => active(c.path))) {
        setHighlightedId(item.id);
        setExpandedIds(prev => prev.has(item.id) ? prev : new Set([item.id]));
        return;
      }
    }
  }, [loc.pathname, menu]);

  const handleParentClick = useCallback((id: string) => {
    setHighlightedId(id); // 点击瞬间高亮切换
    setExpandedIds(prev => {
      if (prev.has(id)) {
        const next = new Set(prev);
        next.delete(id);
        return next;
      }
      return new Set([id]);
    });
  }, []);

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar — 纯白底色 */}
      <aside style={{
        width: collapsed ? 64 : 248,
        background: '#ffffff',
        color: 'var(--gray-800)',
        display: 'flex', flexDirection: 'column', flexShrink: 0,
        transition: 'width 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
        borderRight: '1px solid rgba(0, 113, 227, 0.08)',
        zIndex: 100,
      }}>
        <div style={{
          height: 56, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: collapsed ? '0 18px' : '0 22px',
          borderBottom: '1px solid rgba(0, 113, 227, 0.08)',
        }}>
          {!collapsed && (
            <span style={{ fontSize: 17, fontWeight: 700, letterSpacing: '0.01em', color: '#0071e3', display: 'flex', alignItems: 'center', gap: 9 }}>
              <img src="/admin/app-icon.png" alt="" style={{ width: 24, height: 24, borderRadius: 6, objectFit: 'contain' }} />
              Alphoria
            </span>
          )}
          <button onClick={() => setCollapsed(!collapsed)} style={{
            background: 'none', border: 'none', color: 'var(--gray-400)',
            fontSize: 14, cursor: 'pointer', padding: 4,
          }}>
            {collapsed ? '▶' : '◀'}
          </button>
        </div>

        <nav style={{ flex: 1, overflowY: 'auto', padding: '10px 0' }}>
          {menu.map(item => {
            const hasChildren = !!(item.children && item.children.length > 0);
            const isExpanded = expandedIds.has(item.id);
            const highlighted = highlightedId === item.id;
            const childCount = item.children?.length || 0;

            return (
            <div key={item.id} style={{ marginBottom: 2 }}>
              {/* 一级菜单 — 点谁谁高亮 */}
              {hasChildren ? (
                <div
                  onClick={() => handleParentClick(item.id)}
                  style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: collapsed ? '14px 0' : '13px 22px',
                    margin: collapsed ? '4px 10px' : '5px 8px',
                    borderRadius: 8,
                    color: highlighted ? '#0071e3' : 'var(--gray-800)',
                    background: highlighted ? '#e3f0fd' : 'transparent',
                    fontSize: 16, fontWeight: highlighted ? 600 : 500,
                    letterSpacing: '0.01em',
                    cursor: 'pointer', userSelect: 'none',
                    transition: 'all 0.15s ease',
                  }}
                  title={collapsed ? item.title : undefined}
                >
                  <span>{collapsed ? '' : item.title}</span>
                  {!collapsed && (
                    <span style={{
                      fontSize: 10, opacity: highlighted ? 0.6 : 0.3,
                      transition: 'transform 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
                      transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                    }}>
                      ▶
                    </span>
                  )}
                </div>
              ) : (
                <Link to={toPath(item.path)} style={{
                  display: 'flex', alignItems: 'center',
                  padding: collapsed ? '14px 0' : '13px 22px',
                  justifyContent: collapsed ? 'center' : 'flex-start',
                  margin: collapsed ? '4px 10px' : '5px 8px',
                  borderRadius: 8,
                  color: highlighted ? '#0071e3' : 'var(--gray-800)',
                  background: highlighted ? '#e3f0fd' : 'transparent',
                  fontSize: 16, fontWeight: highlighted ? 600 : 500,
                  letterSpacing: '0.01em',
                  transition: 'all 0.15s ease',
                }}
                  title={collapsed ? item.title : undefined}
                >
                  {!collapsed && item.title}
                </Link>
              )}

              {/* 二级菜单 — 丝滑展开/收起 */}
              <div style={{
                maxHeight: (!collapsed && isExpanded) ? (childCount * 42 + 8) : 0,
                overflow: 'hidden',
                opacity: (!collapsed && isExpanded) ? 1 : 0,
                transition: 'max-height 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.25s ease',
              }}>
                {!collapsed && hasChildren && item.children!.map(c => (
                  <Link key={c.id} to={toPath(c.path)} style={{
                    display: 'block',
                    padding: '10px 22px 10px 32px',
                    color: active(c.path) ? '#0071e3' : 'var(--gray-800)',
                    background: active(c.path) ? 'rgba(227, 240, 253, 0.70)' : 'transparent',
                    borderRadius: active(c.path) ? 6 : 0,
                    margin: active(c.path) ? '2px 8px' : '2px 8px',
                    fontSize: 14, fontWeight: active(c.path) ? 500 : 400,
                    letterSpacing: '0.01em',
                    transition: 'all 0.15s ease',
                  }}>
                    {c.title}
                  </Link>
                ))}
              </div>
            </div>
          )})}
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
