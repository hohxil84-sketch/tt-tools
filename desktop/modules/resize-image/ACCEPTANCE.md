# ACCEPTANCE.md - desktop-resize-image

## 验收状态

`REVIEWED`

## 验收清单

- [x] 模块目标已实现：桌面图片改尺寸入口，本地执行 + 云端套餐权限校验
- [x] C1: 权限 fail closed — 未登录/网络错误/401/null/Allowed=false 全部拒绝
- [x] C1: 每个文件 resize 前都调用一次 entitlement check（不缓存）
- [x] C1: 权限拒绝时不启动 resize、不创建输出文件、不调用 worker
- [x] C4: output_path 外部传入时校验扩展名和父目录
- [x] Job: 权限拒绝标记 Failed，worker 失败标记 Failed，成功标记 Succeeded
- [x] Python bridge ping/list_presets/resize 各有独立 smoke test
- [x] 代码关键逻辑有中文注释
- [x] 不包含禁止内容（无密钥、模型文件、缓存、构建产物）
- [x] 测试记录已写入 PROGRESS.md
- [x] 新依赖（无）已确认无需登记
- [x] C5: 桌面壳注册已完成 — TTShell.csproj 引用、导航按钮、switch 入口均已添加
- [ ] 剩余集成项：壳层统一 DI 就位后替换 ViewModel 默认构造函数为带参注入

## 是否允许合并

是。模块已完成开发，54 项 C# 单元测试 + 4 项 Python bridge smoke tests 全部通过，0 失败 0 警告。
