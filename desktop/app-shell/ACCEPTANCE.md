# ACCEPTANCE.md - desktop-app-shell

## 验收状态

`PASSED`

## 验收清单

- [x] 模块目标已实现：WPF 主程序外壳，包含启动、主窗口、导航、主题、基础布局和模块入口装配。
- [x] 不包含禁止内容：无密钥、无模型、无缓存、无构建产物提交；无跨模块修改；无未登记依赖。
- [x] 测试记录已写入 PROGRESS.md：dotnet build 通过，0 错误 0 警告。
- [x] 新依赖和模型已登记：.NET SDK 8.0.421 已登记到 INSTALLED_DEPENDENCIES.md，安装动作已记录到 SETUP_HISTORY.md。本模块不涉及模型。
- [x] 代码关键逻辑有中文注释：App.xaml.cs、MainWindow.xaml.cs 所有关键方法均有中文注释。

## 是否允许合并

是。模块已完成开发、编译通过、文档齐全，可合并到 dev/full-product。
