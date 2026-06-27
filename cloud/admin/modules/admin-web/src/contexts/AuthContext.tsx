/**
 * 认证上下文。
 *
 * 管理登录状态、token 存储和用户信息。
 * 使用 localStorage 保存 token（开发版，生产应使用 httpOnly cookie）。
 */
import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import {
  apiRequest,
  setToken,
  setRefreshToken,
  setUser,
  getUser,
  clearAuth,
  isAuthenticated,
} from '../api/client';

interface User {
  id: string;
  account: string;
  display_name?: string;
  plan_code?: string;
  permissions?: string[];
}

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (account: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUserState] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // 启动时检查已有 token 是否有效
  useEffect(() => {
    const checkAuth = async () => {
      if (!isAuthenticated()) {
        setLoading(false);
        return;
      }
      try {
        // 调用 status 接口验证管理员权限
        await apiRequest('/admin/status');
        const savedUser = getUser();
        if (savedUser) {
          setUserState(savedUser);
        }
      } catch {
        clearAuth();
      } finally {
        setLoading(false);
      }
    };
    checkAuth();
  }, []);

  const login = useCallback(async (account: string, password: string) => {
    // 使用现有 auth-device 登录接口
    // 管理后台使用 admin-shell 的管理员登录接口
    const data = await apiRequest<{
      access_token: string;
      refresh_token: string;
      user: User;
    }>('/admin/auth/login', {
      method: 'POST',
      body: {
        account,
        password,
        device_fingerprint: 'admin-web-browser',
        device_name: 'Admin Web',
        client_version: '0.1.0',
      },
    });

    setToken(data.access_token);
    setRefreshToken(data.refresh_token);
    setUser(data.user);
    setUserState(data.user);

    // 验证管理员权限
    try {
      await apiRequest('/admin/status');
    } catch (e: unknown) {
      clearAuth();
      setUserState(null);
      if (e instanceof Error && e.message.includes('403')) {
        throw new Error('当前账号不是管理员，无法登录后台');
      }
      throw e;
    }
  }, []);

  const logout = useCallback(() => {
    clearAuth();
    setUserState(null);
    window.location.href = '/admin/login';
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
