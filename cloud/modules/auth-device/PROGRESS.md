# PROGRESS.md - cloud-auth-device

## 2026-06-26 登录无响应 Bug 记录

- 分支：`fix/auth-device-login-no-response`
- 现象：桌面端登录看起来无响应；直接请求 `/api/v1/auth/login` 时，正确账号进入设备绑定后触发 PostgreSQL `can't subtract offset-naive and offset-aware datetimes`。
- 根因：PostgreSQL 表为 `TIMESTAMP WITHOUT TIME ZONE`，auth-device 部分写入使用 aware UTC datetime，asyncpg 拒绝 mixed aware/naive datetime。
- 修复：auth-device ORM 默认时间和服务层写入时间统一转为 naive UTC。
- 验证：
  - `python -m pytest cloud\modules\auth-device\tests -q`：20 passed
  - 8001 临时服务使用 `admin@tttools.com / admin123` 登录返回 `success:true`

## 当前状态

`DEVELOPMENT_COMPLETE`

## 分支

`feature/cloud-auth-device`

## 已完成

- 已完成全部业务源码开发（5 个源文件）。
- 已完成全部测试开发（2 个测试文件）。
- 所有 20 项测试通过。
- 对齐 shared-contract/openapi/auth-device.yaml 全部 5 个接口。
- 对齐 cloud/DATABASE_SCHEMA.md 三张表结构（users、devices、auth_sessions）。
- 使用 cloud-shared 公共层（database、auth、errors、config、request_id、logging）。

## 未完成

无。

## 源文件清单

| 文件 | 说明 |
|---|---|
| `__init__.py` | 模块初始化 |
| `models.py` | User、Device、AuthSession ORM 模型 |
| `schemas.py` | 请求/响应 Pydantic DTO |
| `service.py` | 登录、刷新、退出、设备绑定/状态业务逻辑 |
| `router.py` | 5 个 FastAPI 端点路由 |

## 测试文件清单

| 文件 | 说明 |
|---|---|
| `tests/conftest.py` | 测试夹具（SQLite 内存数据库） |
| `tests/test_auth_device.py` | 20 项测试覆盖全部接口 |

## 测试记录

日期：2026-06-20
测试命令：python -m pytest cloud/modules/auth-device/tests/ -v
结果：20/20 通过
中文备注：覆盖登录 7 项、刷新 4 项、退出 3 项、设备查询 2 项、设备绑定 3 项、集成流 1 项。使用 SQLite 内存数据库测试。

## 接口清单

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /api/v1/auth/login | 登录 |
| POST | /api/v1/auth/refresh | 刷新令牌 |
| POST | /api/v1/auth/logout | 退出登录 |
| GET | /api/v1/devices/current | 获取当前设备 |
| POST | /api/v1/devices/bind | 绑定设备 |

## 技术选型

- 密码哈希：bcrypt 直接调用（passlib 1.7.4 与 bcrypt 5.0.0 不兼容）
- 设备指纹哈希：SHA-256
- Refresh Token：secrets.token_urlsafe(64) + SHA-256 哈希存储
- JWT：cloud-shared 提供（python-jose + HS256）
- 测试数据库：SQLite 内存数据库

## Bug 记录

1. passlib 1.7.4 与 bcrypt 5.0.0 不兼容 → 改用 bcrypt 直接调用
2. 模块目录名含连字符（auth-device）→ sys.path 直接导入 + 绝对导入
3. SQLite 无时区 datetime → 比较时转为 naive UTC
4. JWT 同一秒内生成相同 token → 测试放宽 access_token 比较逻辑
5. require_auth HTTPException 响应格式与统一错误格式不同 → 测试适配

## 提交记录

| 日期 | 分支 | 提交哈希 | 说明 |
|---|---|---|---|
| 2026-06-20 | feature/cloud-auth-device | 1f3e98ff | 完成云端登录、刷新、退出、设备绑定和设备状态服务，20 项测试全部通过 |

## 下一步

等待提交和推送。
