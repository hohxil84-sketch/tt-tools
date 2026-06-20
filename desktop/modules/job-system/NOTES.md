# NOTES.md - desktop-job-system

## 设计备注

统一任务状态、任务历史、失败重试和任务详情。

### 架构层次

- **Models**：`JobFilterOptions`（过滤/排序/分页）、`JobReport`（按状态统计）
- **Services**：`JobHistoryStore`（JSON 持久化历史）、`JobRetryService`（失败重试 + DefaultRetryPolicy）
- **ViewModels**：`JobDetailViewModel`（包装 JobRecord）、`JobListViewModel`（主 VM）、`JobStatsViewModel`（统计）

### 关键设计决策

1. **不修改 shared 层**：遵循跨模块修改规则，所有功能在模块内实现，通过 Inject `JobManager` 协作。
2. **CreateJob 不触发事件**：shared 的 `JobManager.CreateJob` 不触发 `JobStatusChanged`（仅在 `UpdateJobStatus` 时触发），因此模块在重试等操作后手动同步 `_allJobs`。
3. **重试策略**：`DefaultRetryPolicy` 支持最大重试次数限制（默认 3 次），记录重试关系链（原始→重试→重试的重试）。
4. **历史持久化**：`JobHistoryStore` 使用 JSON 文件保存在 `%LocalAppData%/TTTools/job-history.json`，最多保留 1000 条记录，通过 DTO 序列化避免运行时状态污染。
5. **过滤和排序**：`JobFilterOptions.Matches()` 支持状态、功能码、名称搜索、日期范围的组合过滤；`ApplySort()` 支持按创建时间、完成时间、名称、状态、功能码排序。

## 选型记录

- **持久化方案**：JSON 文件（System.Text.Json），无需额外依赖，适合桌面端本地存储场景。
- **重试方案**：内存记录重试关系，不跨会话（历史已持久化，重试次数可从历史推断）。
- **无新增 NuGet 依赖**：仅使用 .NET 8 标准库（System.Text.Json、System.Collections.Concurrent）和 `desktop-shared` 项目引用。
