# PROGRESS.md - desktop-ocr

## 当前状态

`DEVELOPED`

## 分支

`feature/desktop-ocr`

## 已完成

- 已创建模块文档骨架。
- 已创建 DesktopOcr 主项目（WPF Library，net8.0-windows）。
- 已实现 OcrService 服务层：通过 LocalRuntimeClient + Python router 脚本调用 local-worker-ocr。
- 已创建 Python router 脚本（ocr_router.py）：stdin/stdout JSON 协议桥接到 RapidOCR 引擎。
- 已实现 OcrViewModel：文件选择（对话框 + 拖拽）、识别触发、结果展示、复制文本、置信度阈值调节。
- 已实现 OcrView WPF 界面：工具栏、结果列表、详情预览、置信度颜色指示、进度条、拖拽支持。
- 已实现 OcrJobResult 模型：从 local-worker OCR JSON 响应反序列化的结构化模型。
- 已创建 DesktopOcr.Tests 测试项目并编写测试（33 项全部通过）。

## 未完成

- 暂无。

## 测试记录

```
日期：2026-06-20
测试命令：dotnet test
结果：通过 — 33 项全部通过，0 失败，0 跳过
失败原因：无
修复提交：无
中文备注：全量单元测试通过，覆盖 ViewModel、Service、Model 各层。
```

## Bug 记录

暂无。

## 提交记录

待首次提交。

## 下一步

提交、推送当前 feature 分支，并等待用户决定是否合并到 dev/full-product。
