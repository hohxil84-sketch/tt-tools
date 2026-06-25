# NOTES.md - admin-web

## 模块状态

`DEVELOPMENT_DONE`

## 技术栈

- Vite 5.x + React 18.x + TypeScript 5.x + React Router 6.x
- 无额外 UI 框架（纯 CSS inline styles）

## 开发模式 vs 生产模式

### 开发模式

```bash
cd cloud/admin/modules/admin-web
npm install
npm run dev
# → http://localhost:5173/admin/login
```

- Vite dev server 托管前端（热更新）
- `/api` 请求由 Vite proxy 转发到 `http://127.0.0.1:8000`
- 需额外启动 FastAPI：`python cloud/app-shell/main.py`

### 生产模式

```bash
cd cloud/admin/modules/admin-web
npm run build    # 产物输出到 dist/
```

然后只启动 FastAPI 即可：

```bash
python cloud/app-shell/main.py
# → http://127.0.0.1:8000/admin/    （后台页面）
# → http://127.0.0.1:8000/api/v1/   （API）
```

- FastAPI 自动检测 `dist/` 目录是否存在
- 存在则挂载到 `/admin/` 路径（SPA fallback: html=True）
- 所有 `/admin/*` 路径返回 `index.html`，由 React Router 处理路由
- `/admin/assets/*` 返回实际 JS/CSS 文件
- API 路径 `/api/v1/admin/*` 不受影响
- 不需要 Vite dev server、不需要 npm

### SPA 路由

- React Router 使用 `basename="/admin"`
- `/admin/login` → 登录页
- `/admin/dashboard` → 仪表盘
- `/admin/users`、`/admin/plans` 等 → 各管理页
- 刷新 `/admin/users` 不会 404（FastAPI StaticFiles html=True）

### 前端 API 请求

- API base URL：`/api/v1`（相对路径，同源请求）
- 生产环境不写死 127.0.0.1
- 示例：前台在 `https://your-domain.com/admin/`，API 自动请求 `https://your-domain.com/api/v1/admin/users`

## 安全说明

### Token 存储

- Token 存储在 localStorage（开发版方案）
- 风险：localStorage 易受 XSS 攻击
- **生产环境应改用 httpOnly Cookie + CSRF 保护**

### 访问保护

- `/admin/` 登录页可公开访问（不含敏感数据）
- 所有 `/api/v1/admin/*` 必须 Bearer token 且 role=admin（后端强制）
- 普通用户访问 admin API → 403
- 未登录访问 admin API → 401
- Token 过期 → 前端自动跳转 `/admin/login`

### 禁止事项

- ❌ 不在前端代码中硬编码管理员账号、密码、API key、数据库地址
- ❌ 不返回 password_hash、refresh_token_hash
- ❌ 不返回完整设备指纹、IP、User-Agent
- ❌ 不返回 provider raw_usage_json、raw_meta_json

### 生产部署 checklist

- [ ] 使用 `npm run build` 构建生产产物
- [ ] FastAPI 托管 dist/ 到 /admin/
- [ ] 配置 HTTPS（生产必须）
- [ ] CORS `allowed_origins` 限定正式域名（不要 `["*"]` 搭配 credentials）
- [ ] 管理员初始密码通过环境变量或初始化脚本设置，不在代码中硬编码
- [ ] Token 改用 httpOnly Cookie（防 XSS）
- [ ] 部署前修改 `cloud/shared/config.py` 中 `auth_secret_key` 默认值

## 未实现功能

- 审计日志（admin_audit_logs 表未实现）
- 支付网关接入
- E2E 测试
