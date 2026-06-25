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

  // 401 → 跳转登录
  if (response.status === 401) {
    localStorage.removeItem('admin_token');
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

  // 成功但无 data 字段
  if (json?.data === undefined) {
    throw new ApiError(`响应缺少 data 字段: ${JSON.stringify(json).slice(0, 200)}`, 'NO_DATA', response.status);
  }

  return json.data as T;
}

// 登录相关
export function setToken(token: string) {
  localStorage.setItem('admin_token', token);
}

export function setUser(user: { id: string; account: string; display_name?: string }) {
  localStorage.setItem('admin_user', JSON.stringify(user));
}

export function getUser(): { id: string; account: string; display_name?: string } | null {
  try {
    const raw = localStorage.getItem('admin_user');
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function clearAuth() {
  localStorage.removeItem('admin_token');
  localStorage.removeItem('admin_user');
}

export function isAuthenticated(): boolean {
  return !!getToken();
}
