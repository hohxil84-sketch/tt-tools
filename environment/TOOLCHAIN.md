# TOOLCHAIN.md

- Windows 客户端：Windows 10/11、C#、.NET 8、WPF。
- 本地 worker：Python 3.11 优先，OpenCV/Pillow/ONNX 按模块登记。
- 云端：Python 3.11、FastAPI、PostgreSQL、Redis。
- 通用工具：Git、GitHub CLI、PowerShell。

## 本地依赖根目录

所有下载、安装包、模型、工具缓存、Python 虚拟环境和外部资源优先放到：

```text
D:\localPath
```

如果某个工具必须安装到系统目录，下载安装包、缓存和离线资源仍放到 `D:\localPath`，并在依赖台账里写明原因。
