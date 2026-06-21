"""
cloud-ai-copy —— 云端文案生成业务模块。

提供 AI 广告文案生成接口，必须通过 provider-runtime 调用模型，
并经过权限检查、额度预检查、Provider 日志记录、额度扣费和统一响应。

本模块是 library + API 模块，暴露 FastAPI 路由端点。
对齐 shared-contract/openapi/ai-copy.yaml 和 API_INDEX.md。

注意：cloud/modules/provider-runtime 和 cloud/modules/credits-billing 目录
含连字符，Python 无法直接 import。使用本模块时需将对应目录加入 sys.path。

标准调用链（对齐 MODULE_INTERFACES.md）：
    API endpoint -> auth/device check -> permission check -> credits precheck
    -> provider-runtime -> provider-call-log -> credits charge
    -> usage event -> unified response
"""
from __future__ import annotations
