# ACCEPTANCE.md - desktop-format-convert

## 验收状态

`READY_FOR_REVIEW`

## 验收清单

- [x] 模块目标已实现：图片格式转换、压缩、裁剪、旋转入口。
- [x] 不包含禁止内容：无密钥、模型大文件、缓存、构建产物提交。
- [x] 测试记录已写入 PROGRESS.md。
- [x] 无需新依赖（仅引用 desktop-shared，.NET 8 SDK 和 Pillow 已由 local-worker-format-convert 登记）。
- [x] 代码关键逻辑有中文注释。

## 实现说明

- 模块是本地免费功能（feature code: format_convert_local），无需套餐权限校验，不消耗云端 AI 额度。
- 通过 format_convert_router.py 桥接 local-worker format-convert 引擎（Pillow）。
- 支持 4 种操作：格式转换（PNG/JPEG/BMP/TIFF/WEBP/GIF/ICO）、压缩（有损/无损）、裁剪（坐标/锚点）、旋转（直角/任意角度）。
- 桌面端通过 LocalRuntimeClient（stdin/stdout JSON 协议）与 Python worker 通信。

## 是否允许合并

是。模块开发完成，测试通过，待用户审查后合并到 dev/full-product。
