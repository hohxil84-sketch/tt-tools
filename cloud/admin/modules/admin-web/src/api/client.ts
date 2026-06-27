/**
 * API 客户端模块。
 *
 * 提供统一的 HTTP 请求封装，自动注入 Bearer token，
 * 处理 401/403 错误并跳转登录页。
 * 所有后台 API 调用通过此模块进行。
 */

const API_BASE = '/api/v1';

// 从 localStorage 读取 token
function getToken(): string | null {
  try {
    return localStorage.getItem('admin_token');
  } catch {
    return null;
  }
}

function getRefreshToken(): string | null {
  try {
    return localStorage.getItem('admin_refresh_token');
  } catch {
    return null;
  }
}

// 是否正在刷新 token（防止并发刷新）
let _refreshing = false;
let _refreshPromise: Promise<boolean> | null = null;

// 请求选项类型
interface RequestOptions {
  method?: string;
  body?: unknown;
  params?: Record<string, string | number | undefined>;
}

// API 错误类
export class ApiError extends Error {
  code: string;
  status: number;

  constructor(message: string, code: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

/**
 * 统一 API 请求函数。
 * 自动注入 Authorization header，处理错误响应。
 */
export async function apiRequest<T = unknown>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const { method = 'GET', body, params } = options;

  // 构建 URL
  let url = `${API_BASE}${path}`;
  if (params) {
    const searchParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== '') {
        searchParams.set(key, String(value));
      }
    }
    const qs = searchParams.toString();
    if (qs) url += `?${qs}`;
  }

  // 构建 headers
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  const token = getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  // 401 → 尝试刷新 token，失败则跳转登录
  if (response.status === 401) {
    // 如果已经是刷新请求本身失败，直接踢出
    if (path === '/admin/auth/refresh') {
      localStorage.removeItem('admin_token');
      localStorage.removeItem('admin_refresh_token');
      localStorage.removeItem('admin_user');
      if (window.location.pathname !== '/admin/login') {
        window.location.href = '/admin/login';
      }
      throw new ApiError('登录已过期，请重新登录', 'AUTH_REQUIRED', 401);
    }

    // 尝试静默刷新
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      // 刷新成功，用新 token 重试原请求
      const newToken = getToken();
      if (newToken) {
        headers['Authorization'] = `Bearer ${newToken}`;
      }
      const retryResponse = await fetch(url, { method, headers, body: body ? JSON.stringify(body) : undefined });
      // 递归解析重试结果
      if (retryResponse.ok) {
        const retryJson = await retryResponse.json();
        if (retryJson?.data !== undefined) return retryJson.data as T;
        return null as T;
      }
      if (retryResponse.status === 403) {
        throw new ApiError('需要管理员权限', 'PERMISSION_DENIED', 403);
      }
    }

    // 刷新失败，清除认证信息并跳转
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_refresh_token');
    localStorage.removeItem('admin_user');
    if (window.location.pathname !== '/admin/login') {
      window.location.href = '/admin/login';
    }
    throw new ApiError('登录已过期，请重新登录', 'AUTH_REQUIRED', 401);
  }

  // 403 → 权限不足
  if (response.status === 403) {
    throw new ApiError('需要管理员权限', 'PERMISSION_DENIED', 403);
  }

  let json: any;
  try {
    const text = await response.text();
    try {
      json = JSON.parse(text);
    } catch {
      throw new ApiError(`服务器返回非 JSON (HTTP ${response.status}): ${text.slice(0, 200)}`, 'PARSE_ERROR', response.status);
    }
  } catch (e) {
    if (e instanceof ApiError) throw e;
    throw new ApiError(`无法读取服务器响应 (HTTP ${response.status})`, 'READ_ERROR', response.status);
  }

  // 先检查业务层 success 字段
  const isSuccess = json?.success;
  if (isSuccess === false) {
    const msg = json?.error?.message || json?.detail?.message || `业务错误: ${JSON.stringify(json)}`;
    throw new ApiError(msg, json?.error?.code || json?.detail?.code || 'UNKNOWN', response.status);
  }

  // HTTP 错误
  if (!response.ok) {
    const msg = json?.error?.message || json?.detail?.message || `HTTP ${response.status}`;
    throw new ApiError(msg, json?.error?.code || json?.detail?.code || 'UNKNOWN', response.status);
  }

  // 成功但无 data 字段 — 有些端点（如 DELETE）返回 data: null
  if (json?.data === undefined) {
    // 204 No Content 或无 data 字段视为正常（某些操作不返回数据）
    if (response.status === 204 || response.status === 200) {
      return null as T;
    }
    throw new ApiError(`响应缺少 data 字段: ${JSON.stringify(json).slice(0, 200)}`, 'NO_DATA', response.status);
  }

  return json.data as T;
}

// 登录相关
export function setToken(token: string) {
  localStorage.setItem('admin_token', token);
}

export function setRefreshToken(token: string) {
  localStorage.setItem('admin_refresh_token', token);
}

/**
 * 尝试用 refresh_token 静默刷新 access_token。
 * 返回 true 表示刷新成功，false 表示需要重新登录。
 */
async function tryRefreshToken(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  // 防止并发刷新
  if (_refreshing && _refreshPromise) return _refreshPromise;
  _refreshing = true;
  _refreshPromise = (async () => {
    try {
      const response = await fetch(`${API_BASE}/admin/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) return false;
      const json = await response.json();
      if (json?.data?.access_token) {
        setToken(json.data.access_token);
        if (json.data.refresh_token) {
          setRefreshToken(json.data.refresh_token);
        }
        return true;
      }
      return false;
    } catch {
      return false;
    } finally {
      _refreshing = false;
      _refreshPromise = null;
    }
  })();
  return _refreshPromise;
}

export function setUser(user: { id: string; account: string; display_name?: string; permissions?: string[] }) {
  localStorage.setItem('admin_user', JSON.stringify(user));
  // 同时单独存储权限列表，方便快速读取
  if (user.permissions) {
    localStorage.setItem('admin_permissions', JSON.stringify(user.permissions));
  }
}

export function getUser(): { id: string; account: string; display_name?: string; permissions?: string[] } | null {
  try {
    const raw = localStorage.getItem('admin_user');
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

/** 获取当前用户的权限码列表（RBAC） */
export function getPermissions(): string[] {
  try {
    const raw = localStorage.getItem('admin_permissions');
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

/** 检查当前用户是否拥有指定权限 */
export function hasPermission(code: string): boolean {
  return getPermissions().includes(code);
}

export function clearAuth() {
  localStorage.removeItem('admin_token');
  localStorage.removeItem('admin_refresh_token');
  localStorage.removeItem('admin_user');
  localStorage.removeItem('admin_permissions');
}

export function isAuthenticated(): boolean {
  return !!getToken();
}
