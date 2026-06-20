# ACCEPTANCE.md - desktop-auth-device

## 验收状态

`READY_FOR_REVIEW`

## 验收清单

- [x] 模块目标已实现（登录、退出、设备绑定状态展示）。
- [x] 不包含禁止内容（无密钥、无模型大文件、无缓存、无构建产物）。
- [x] 测试记录已写入 PROGRESS.md（20/20 通过）。
- [x] 无新依赖和模型（仅引用已有的 desktop-shared 和 .NET 8 内置功能）。
- [x] 代码关键逻辑有中文注释。

## 模块产出

| 文件 | 说明 |
|---|---|
| DesktopAuthDevice/ViewModels/LoginViewModel.cs | 登录表单逻辑，调用 CloudApiClient.LoginAsync |
| DesktopAuthDevice/ViewModels/DeviceStatusViewModel.cs | 设备绑定状态展示，调用 GetCurrentDeviceAsync |
| DesktopAuthDevice/ViewModels/AsyncRelayCommand.cs | 异步 ICommand 封装 |
| DesktopAuthDevice/Views/LoginView.xaml | 登录界面 |
| DesktopAuthDevice/Views/LoginView.xaml.cs | 登录界面代码后置 |
| DesktopAuthDevice/Views/DeviceStatusView.xaml | 设备状态展示界面 |
| DesktopAuthDevice/Views/DeviceStatusView.xaml.cs | 设备状态界面代码后置 |
| DesktopAuthDevice.Tests/ViewModels/LoginViewModelTests.cs | LoginViewModel 单元测试（9 项） |
| DesktopAuthDevice.Tests/ViewModels/DeviceStatusViewModelTests.cs | DeviceStatusViewModel 单元测试（11 项） |
| DesktopAuthDevice.Tests/TestHelpers/MockHttpMessageHandler.cs | HTTP mock 工具类 |

## 是否允许合并

是。模块开发完成，测试通过，可合并到 dev/full-product。

