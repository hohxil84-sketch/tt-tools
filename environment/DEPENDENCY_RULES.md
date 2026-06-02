# DEPENDENCY_RULES.md

## 原则

依赖必须按全局台账增量管理。后续模块不得重复扫描、重复安装已登记依赖。

## 开发前必须读取

- environment/TOOLCHAIN.md
- environment/INSTALLED_DEPENDENCIES.md
- environment/SETUP_HISTORY.md
- environment/MODEL_REGISTRY.md

## 新依赖规则

- 只有模块 ENVIRONMENT.md 明确要求的新依赖才允许安装。
- 如果依赖已登记为 installed，不得重复安装。
- 下载依赖、安装包、模型、工具缓存或任何外部资源时，必须优先放到 D:\localPath。
- 如果工具必须安装到系统目录，下载安装包、缓存和离线资源仍必须先放到 D:\localPath，并在台账备注原因。
- Python 虚拟环境、NuGet 缓存、OpenAPI 工具缓存、模型缓存、临时下载文件都应优先放到 D:\localPath 下的分类目录。
- 安装新依赖后必须更新 INSTALLED_DEPENDENCIES.md。
- 安装动作必须更新 SETUP_HISTORY.md。
- 新模型必须更新 MODEL_REGISTRY.md。

## D:\localPath 目录建议

```text
D:\localPath\
  downloads\        # 安装包和压缩包
  tools\            # CLI 工具和便携工具
  caches\           # NuGet、pip、OpenAPI 工具等缓存
  venvs\            # Python 虚拟环境
  models\           # OCR、抠图、ONNX 等模型
  logs\             # 安装和验证日志
```

## 登记要求

每次新增依赖必须在 `INSTALLED_DEPENDENCIES.md` 写明：

- 名称
- 类型
- 版本
- 安装位置
- 下载或缓存位置，优先为 D:\localPath 下路径
- 用途
- 首次引入模块
- 验证命令
- 状态
- 中文备注
