# 功能码

## 本地免费功能

本地执行，无需套餐权限，不消耗云端 AI 额度。

ocr_local、remove_bg_local、id_photo_local、preflight_check_local、format_convert_local。

## 本地付费功能

本地执行，需要登录和套餐权限（通过 `/api/v1/entitlements/check` 校验），不消耗云端 AI 额度。

resize_image_local_paid（图片改尺寸）、pdf_image_convert_local_paid（PDF/图片互转）。

后续新增本地付费功能码应追加到本清单，并在 `shared-contract/openapi/local-paid-tools.yaml` 中补充示例。

## 云端 AI 付费功能

云端执行，需要权限、额度预检查、Provider 调用、成本估算、扣费、日志。

ai_copy_cloud、ai_render_cloud、upscale_image_cloud、vectorize_image_cloud、ai_edit_image_cloud、remove_bg_cloud、ocr_cloud。

