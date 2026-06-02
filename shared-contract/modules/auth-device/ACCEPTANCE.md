# ACCEPTANCE.md - contract-auth-device

## 验收状态

`REVIEWED_PASSED`

## 验收清单

- [x] 模块目标已实现：登录、刷新、退出、设备绑定 5 个 API 端点契约完整。
- [x] 不包含禁止内容：无密钥、无模型文件、无缓存、无构建产物。
- [x] 测试记录已写入 PROGRESS.md：Spectral lint 0 errors 0 warnings。
- [x] 新依赖和模型已登记：本模块无需新增依赖。
- [x] 代码关键逻辑有中文注释：OpenAPI description 和 summary 均为中文。

## 接口清单

| 端点 | 方法 | 认证 | 状态 |
|------|------|------|------|
| /api/v1/auth/login | POST | 无 | ✅ |
| /api/v1/auth/refresh | POST | 无 | ✅ |
| /api/v1/auth/logout | POST | 无 | ✅ |
| /api/v1/devices/current | GET | Bearer | ✅ |
| /api/v1/devices/bind | POST | Bearer | ✅ |

## API_INDEX.md 一致性

- [x] 所有 5 个端点的请求/响应字段与 OpenAPI 一致。

## 是否允许合并

是。模块契约已完成并通过校验。
