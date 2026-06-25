# PROGRESS.md - desktop-ocr

## 当前状态

`DEVELOPED`

## 分支

`feature/ocr-low-confidence-placeholder` (当前工作分支)

## 已完成

- 已创建模块文档骨架。
- 已创建 DesktopOcr 主项目（WPF Library，net8.0-windows）。
- 已实现 OcrService 服务层：通过 LocalRuntimeClient + Python router 脚本调用 local-worker-ocr。
- 已创建 Python router 脚本（ocr_router.py）：stdin/stdout JSON 协议桥接到 RapidOCR 引擎。
- 已实现 OcrViewModel：文件选择（对话框 + 拖拽）、识别触发、结果展示、复制文本、置信度阈值调节。
- 已实现 OcrView WPF 界面：工具栏、结果列表、详情预览、置信度颜色指示、进度条、拖拽支持。
- 已实现 OcrJobResult 模型：从 local-worker OCR JSON 响应反序列化的结构化模型。
- 已创建 DesktopOcr.Tests 测试项目并编写测试（45 项全部通过）。
- 已实现 5 项功能修复（见下方 2026-06-25 提交记录）。
- 已实现低置信度占位符从 * 替换为 □。

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

```
日期：2026-06-25
测试命令：dotnet test + pytest
结果：C# 45 项全部通过，Python 37 项全部通过
失败原因：无
修复提交：a585ed4
中文备注：5 项 OCR 功能修复 + 低置信度占位符 *→□，全部测试通过。
```

## Bug 记录

- 2026-06-24: **OCR 引擎未连接 + 选择图片无反应**
  - 现象：导航到 OCR 模块后显示"OCR 引擎未连接"，"开始识别"按钮灰色不可用
  - 根因：OcrViewModel 默认构造函数 `OcrViewModel()` → `OcrViewModel(null, new FileSystemService())`，`_ocrService` 为 null，`IsServiceAvailable` 始终为 false，且 `InitializeAsync()` 从未被调用
  - 修复：默认构造函数自动检测 Python 环境和 router 脚本路径创建 OcrService；OcrView 加载时自动调用 InitializeAsync
  - 修复分支：`fix/desktop-ocr-service-init`
  - 修复提交：`d340d38`
  - 测试结果：33/33 通过

- 2026-06-24: **OCR 识别结果中文乱码**
  - 现象：识别成功但结果中的中文字符全部显示为乱码
  - 根因：Windows 上 Python 默认 stdout 编码为 GBK/cp936，而 C# LocalRuntimeClient 以 UTF-8 读取，导致中文编码不匹配
  - 修复：`ocr_router.py` 启动时显式设置 `sys.stdout.reconfigure(encoding='utf-8')` 和 `sys.stdin.reconfigure(encoding='utf-8')`
  - 修复提交：`0c74eb7`
  - 测试结果：33/33 通过

## 提交记录

- 2026-06-20: `222a78f` - feat(desktop-ocr): 完成 OCR 桌面入口模块基础能力
  - 14 个文件变更，+2344 -20
  - 分支已推送 origin/feature/desktop-ocr
  - 33 项单元测试全部通过

- 2026-06-25: `a585ed4` - fix(ocr): 低置信度占位符从 * 替换为 □
  - 11 个文件变更，+1075 -187
  - 分支已推送 origin/feature/ocr-low-confidence-placeholder
  - Python 37 项 + C# 45 项测试全部通过

## 下一步

提交、推送当前 feature 分支，并等待用户决定是否合并到 dev/full-product。
