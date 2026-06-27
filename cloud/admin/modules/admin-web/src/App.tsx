/**
 * 后台管理 App 根组件。
 *
 * SPA 路由挂载在 /admin/ 下（BrowserRouter basename="/admin"）：
 * - /admin/login → 登录页
 * - /admin/ → 仪表盘（需登录）
 * - /admin/users、/admin/plans 等 → 各管理页面（需登录）
 *
 * 生产模式：FastAPI 托管 dist/ 到 /admin/，html=True 实现 SPA fallback。
 * 开发模式：Vite dev server + proxy /api → 127.0.0.1:8000。
 */
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ToastContainer } from './components/shared';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Users from './pages/Users';
import SystemUsers from './pages/SystemUsers';
import ClientUsers from './pages/ClientUsers';
import Devices from './pages/Devices';
import Plans from './pages/Plans';
import Orders from './pages/Orders';
import CreditsAccounts from './pages/CreditsAccounts';
import CreditsLedger from './pages/CreditsLedger';
import ProviderCallLogs from './pages/ProviderCallLogs';
import CostStats from './pages/CostStats';
import RiskLogs from './pages/RiskLogs';
import FeatureFlags from './pages/FeatureFlags';
import AuditLogs from './pages/AuditLogs';
import Roles from './pages/Roles';
import Providers from './pages/Providers';
import FeatureCodes from './pages/FeatureCodes';

/** 需要登录才能访问的受保护路由 */
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
        <span>加载中...</span>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter basename="/admin">
      <AuthProvider>
        <ToastContainer />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="users" element={<Users />} />
            <Route path="system-users" element={<SystemUsers />} />
            <Route path="client-users" element={<ClientUsers />} />
            <Route path="devices" element={<Devices />} />
            <Route path="plans" element={<Plans />} />
            <Route path="orders" element={<Orders />} />
            <Route path="credits/accounts" element={<CreditsAccounts />} />
            <Route path="credits/ledger" element={<CreditsLedger />} />
            <Route path="provider-call-logs" element={<ProviderCallLogs />} />
            <Route path="cost-stats" element={<CostStats />} />
            <Route path="risk-logs" element={<RiskLogs />} />
            <Route path="feature-flags" element={<FeatureFlags />} />
            <Route path="audit-logs" element={<AuditLogs />} />
            <Route path="roles" element={<Roles />} />
            <Route path="providers" element={<Providers />} />
            <Route path="feature-codes" element={<FeatureCodes />} />
          </Route>
          <Route path="*" element={<Navigate to="dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
