# ACCEPTANCE.md - desktop-export-settings

## 验收状态

`READY_FOR_REVIEW`

## 验收清单

- [x] 模块目标已实现：导出、设置、日志查看、版本更新入口
- [x] 不包含禁止内容
- [x] 测试记录已写入 PROGRESS.md（85 项单元测试全部通过）
- [x] 新依赖和模型已登记（无新增依赖）
- [x] 代码关键逻辑有中文注释

## 实现内容

### 导出功能
- ExportConfig 导出配置模型（格式、质量、DPI、覆盖策略等）
- ExportResult 导出结果模型（成功数、失败数、错误详情）
- ExportService 导出服务（文件复制导出，支持进度报告、取消、文件名冲突处理）
- ExportView + ExportViewModel（文件列表、配置面板、进度条、结果展示）

### 设置功能
- SettingsViewModel 包装 AppSettings.Instance（服务器、主题、语言、Python路径、并发数等）
- SettingsView 设置界面（保存/重置、未保存提示）
- 设置持久化到本地 JSON 文件

### 日志查看
- LogReaderService 日志读取服务（解析日志行、过滤、搜索）
- LogFilterOptions 过滤选项（日期范围、级别、类别、关键词）
- LogDisplayEntry 日志展示条目
- LogViewerView + LogViewerViewModel（过滤栏、日志列表、搜索、清除、导出）

### 版本更新
- UpdateCheckService 版本检查服务（版本比较、检查框架）
- UpdateInfo 更新信息模型
- UpdateView + UpdateViewModel（当前版本展示、检查更新、下载/发布说明入口）

## 是否允许合并

是。模块已完成开发和测试，可以合并到 dev/full-product。
