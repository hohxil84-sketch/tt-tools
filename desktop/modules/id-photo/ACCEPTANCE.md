# ACCEPTANCE.md - desktop-id-photo

## 验收状态

`PASSED`

## 验收清单

- [x] 模块目标已实现。（证件照换底色桌面入口、底色选择、规格选择、导出）
- [x] 不包含禁止内容。（无跨模块修改、无未登记依赖、无密钥/模型/缓存/构建产物）
- [x] 测试记录已写入 PROGRESS.md。（20 项 C# 单元测试 + 4 项 Python router 协议测试）
- [x] 新依赖和模型已登记。（本模块无新增依赖，Python 和 OpenCV 由 local-worker-id-photo 管理）
- [x] 代码关键逻辑有中文注释。

## 模块文件清单

```
desktop/modules/id-photo/
  DesktopIdPhoto/
    DesktopIdPhoto.csproj          # WPF 类库项目
    id_photo_router.py              # Python stdin/stdout 路由脚本
    Models/
      IdPhotoResult.cs             # 处理结果 + 规格 + 底色数据模型
    Services/
      IdPhotoService.cs            # LocalRuntimeClient 封装服务
    ViewModels/
      IdPhotoViewModel.cs          # MVVM 主 ViewModel
    Views/
      IdPhotoView.xaml             # WPF 用户控件视图
      IdPhotoView.xaml.cs          # 拖拽支持和值转换器
  DesktopIdPhoto.Tests/
    DesktopIdPhoto.Tests.csproj    # xUnit 测试项目
    Models/
      IdPhotoResultTests.cs        # 模型单元测试 (7 项)
    ViewModels/
      IdPhotoViewModelTests.cs     # ViewModel 单元测试 (13 项)
```

## 是否允许合并

是。模块已开发完成，20 项 C# 测试 + 4 项 Python router 测试全部通过。
