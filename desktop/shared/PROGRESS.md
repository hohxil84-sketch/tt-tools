# PROGRESS.md - desktop-shared

## 2026-06-26 登录错误结果未返回 Bug 记录

- 分支：`fix/auth-device-login-no-response`
- 现象：云端返回 4xx/5xx 统一错误体时，桌面登录页拿不到真实错误信息，用户看到像是登录无响应。
- 根因：`CloudApiClient.SendAsync` 对非成功 HTTP 状态先调用 `EnsureSuccessStatusCode()`，导致后端 JSON 错误体被丢弃。
- 修复：先读取并反序列化统一 `ApiResponse<T>`；非 JSON 或空错误体再返回 `http_error`。
- 验证：
  - `dotnet test desktop\shared\DesktopShared.Tests\DesktopShared.Tests.csproj`：62 passed
  - `dotnet test desktop\modules\auth-device\DesktopAuthDevice.Tests\DesktopAuthDevice.Tests.csproj`：20 passed

## 当前状态

`DEVELOPMENT_COMPLETE`

## 分支

`feature/desktop-shared`

## 已完成

- 已创建模块文档骨架。
- 已创建 DesktopShared 类库项目（TTShared，net8.0-windows WPF Library）。
- 已实现 8 个子模块：
  - **Auth**：认证状态管理器（AuthState）、令牌安全存储（TokenStorage，Windows DPAPI 加密）、设备指纹生成器（DeviceFingerprint）。
  - **CloudApi**：云端 API HTTP 客户端（CloudApiClient），覆盖全部 7 个 OpenAPI 接口分类的 DTO（Auth/Device、Credits/Billing、AI Copy、AI Render、AI Image Tools、Provider Log），统一错误处理，自动令牌刷新。
  - **LocalRuntime**：本地 Python worker 进程客户端（LocalRuntimeClient），JSON 协议通信、超时和健康检查。
  - **FileSystem**：文件系统服务（FileSystemService），临时文件管理、文件类型检测、安全删除。
  - **JobSystem**：任务管理器（JobManager），任务生命周期管理（Queued→Running→Succeeded/Failed/Cancelled），进度跟踪、历史记录。
  - **Logging**：应用日志记录器（AppLogger），文件日志（按日轮转）、控制台输出、异步写入。
  - **Settings**：应用设置管理器（AppSettings），单例模式，JSON 持久化，INotifyPropertyChanged。
  - **UI**：BaseViewModel（INotifyPropertyChanged 基类）、RelayCommand/RelayCommand<T>（ICommand 实现）。
- 已创建测试项目 DesktopShared.Tests，59 项单元测试全部通过。
- 已登记新依赖 System.Security.Cryptography.ProtectedData 8.0.0 到全局依赖台账。
- 代码关键逻辑已添加中文注释。

## 未完成

- 无。

## 测试记录

```
日期：2026-06-03
测试命令：dotnet test
结果：通过（59 通过，0 失败，0 跳过）
失败原因：无
修复提交：无
中文备注：编译 0 错误 0 警告，全部单元测试通过，覆盖 Auth、CloudApi、FileSystem、JobSystem、Settings、UI 各子模块
```

## Bug 记录

暂无。

## 提交记录

待提交。

## 下一步

等待用户指定下一模块。
