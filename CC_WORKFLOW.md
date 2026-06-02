# CC_WORKFLOW.md

## 标准工作流

用户会指定一个模块目录，例如：按 desktop/modules/ocr/TASK.md 开发 OCR 模块。

CC 必须执行：

1. 阅读根目录规则文档。
2. 阅读 shared-contract/API_INDEX.md、shared-contract/CONTRACT_TESTING.md、shared-contract/openapi/*.yaml、cloud/DATABASE_SCHEMA.md、docs/architecture/MODULE_INTERFACES.md。
3. 阅读模块目录下所有执行文档。
4. 检查全局依赖台账，不重复安装已登记依赖。
5. 确认或创建模块分支。
6. 只在允许目录内开发。
7. 开发完成后运行模块测试。
8. 测试失败必须先定位根因，再修复。
9. 修复后重新运行失败测试和模块完整测试。
10. 更新模块 PROGRESS.md、ACCEPTANCE.md。
11. 提交、推送，并写中文备注。
12. 停止开发，等待用户指定下一个模块。

如果模块需要新增接口、字段、DTO、数据库表或模块调用关系，必须先更新对应权威规格文档，再写代码。涉及接口联调时，必须先让 mock API 和桌面端 API client 对齐 OpenAPI。
