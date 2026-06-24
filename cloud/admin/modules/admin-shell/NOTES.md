# NOTES.md - admin-shell

## 设计备注

后台基础入口、导航、权限框架和基础布局。

### 架构设计

- admin-shell 是后台管理系统的"外壳"模块，提供统一的 `/api/v1/admin` 前缀路由。
- 所有后台端点使用 `cloud.shared.require_admin` 依赖进行管理员鉴权守卫。
- 后续后台模块（admin-users、admin-billing、admin-ops）在本模块基础上扩展各自子路由。
- 路由注册到 cloud-app-shell main.py 的方式：将 `cloud/admin/modules/admin-shell/` 加入 sys.path 后 `from router import router as admin_router`，再 `app.include_router(admin_router, prefix="/api/v1")`。

### 端点设计

| 端点 | 方法 | 说明 |
|------|------|------|
| `/admin/dashboard` | GET | 仪表盘核心统计（骨架占位，后续由子模块注入真实数据） |
| `/admin/menu` | GET | 后台导航菜单结构（当前包含 dashboard / users / billing / ops） |
| `/admin/status` | GET | 服务运行状态（版本号、健康状态、运行时长） |

### 仪表盘骨架

当前 `get_dashboard_stats()` 返回占位值（全部为 0）。待 admin-users、admin-billing、admin-ops 模块完成后，通过数据库查询聚合真实统计指标。函数参数已预留 `db: AsyncSession`。

### 导航菜单

当前菜单为静态定义，包含 4 个顶级菜单项：
1. 首页仪表盘（dashboard）
2. 用户管理（users）
3. 计费管理（billing）
4. 运维管理（ops）

后续后台子模块完成后可追加新菜单项或修改路径。

### 鉴权流程

```
客户端请求 → Bearer Token
  → cloud-app-shell 中间件注入 X-Request-ID
  → require_admin 依赖（cloud-shared）
    → require_auth：验证 JWT 有效性
    → 检查 role == "admin"
  → admin-shell 端点处理
  → 统一响应格式
```

## 选型记录

无需额外选型。复用 cloud-shared 已有的 FastAPI + Pydantic + SQLAlchemy 技术栈。
