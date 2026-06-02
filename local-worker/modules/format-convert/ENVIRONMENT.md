# ENVIRONMENT.md - local-worker-format-convert

## 开发前必须读取

- `environment/TOOLCHAIN.md`
- `environment/DEPENDENCY_RULES.md`
- `environment/INSTALLED_DEPENDENCIES.md`
- `environment/SETUP_HISTORY.md`
- `environment/MODEL_REGISTRY.md`

## 已有依赖处理

如果依赖已经登记为 `installed`，不得重复安装，也不要重新扫描整套环境。

## 本模块新增依赖计划

可能新增 Pillow/OpenCV；按实际登记。

## 安装规则

安装新依赖后必须更新全局依赖台账和安装历史；新增模型必须更新模型登记表。

