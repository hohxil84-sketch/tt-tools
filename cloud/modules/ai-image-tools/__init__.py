"""
cloud-ai-image-tools —— 云端高级图片 AI 业务模块。

提供高清修复、转矢量、AI 改图、高级抠图和高级 OCR 的统一任务入口。
所有功能必须通过 provider-runtime 调用模型，并经过权限检查、额度预检查、
Provider 日志记录、额度扣费和统一响应。

本模块是 library + API 模块，暴露 FastAPI 路由端点。
对齐 shared-contract/openapi/ai-image-tools.yaml 和 API_INDEX.md。

注意：cloud/modules/provider-runtime 目录含连字符，Python 无法直接 import。
使用本模块时需将对应目录加入 sys.path。

标准调用链（对齐 MODULE_INTERFACES.md）：
    API endpoint -> auth/device check -> permission check -> credits precheck
    -> create ai_task (queued) -> provider-runtime -> provider-call-log
    -> credits charge -> update ai_task (succeeded) -> unified response

支持的功能码（对齐 shared-contract/feature-codes.md）：
- upscale_image_cloud：高清修复
- vectorize_image_cloud：转矢量
- ai_edit_image_cloud：AI 改图
- remove_bg_cloud：高级抠图
- ocr_cloud：高级 OCR
"""
from __future__ import annotations
