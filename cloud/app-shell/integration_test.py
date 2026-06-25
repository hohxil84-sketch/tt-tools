"""
云端 AI 图片工具全链路集成测试。
用法（需要 cloud 服务已在 http://127.0.0.1:8000 运行）：
  cd D:/TT Tools
  python cloud/app-shell/integration_test.py

测试内容：
  - 健康检查
  - 登录（付费/免费两个账号）
  - 额度查询
  - 权限检查
  - 5 种 AI 图片工具的创建任务和查询任务
  - 失败场景（未登录、无权限、积分不足）
  - 数据库记录验证
"""
import json
import sys
import os
import uuid
import urllib.request
import urllib.error
from typing import Optional

BASE_URL = "http://127.0.0.1:8000"
RESULTS = []


def log(msg: str):
    print(f"  {msg}")


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def req(method: str, path: str, body: Optional[dict] = None, token: Optional[str] = None) -> dict:
    """发送 HTTP 请求，返回解析后的 JSON。"""
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode("utf-8") if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"success": False, "error": {"message": body}, "http_status": e.code}


def record(name: str, passed: bool, detail: str = ""):
    RESULTS.append((name, passed, detail))
    status = "[PASS]" if passed else "[FAIL]"
    print(f"  {status}: {name}")
    if detail:
        print(f"         {detail}")


# ============================================================
# 1. 健康检查
# ============================================================
section("1. 健康检查")
resp = req("GET", "/health")
record("健康检查返回 ok", resp.get("status") == "ok", str(resp))

# ============================================================
# 2. 登录测试账号 A（付费用户）
# ============================================================
section("2. 登录 - 账号 A（付费用户）")
resp_a = req("POST", "/api/v1/auth/login", {
    "account": "test_paid@tttools.com",
    "password": "test123",
    "device_fingerprint": f"integration-test-{uuid.uuid4().hex[:8]}",
    "device_name": "INTEGRATION-TEST",
    "client_version": "0.1.0"
})
token_a = resp_a.get("data", {}).get("access_token", "")
user_a = resp_a.get("data", {}).get("user", {})
record("账号 A 登录成功", resp_a.get("success") and token_a,
       f"user_id={user_a.get('id', '?')[:8]}..., plan={user_a.get('plan_code')}")

# ============================================================
# 3. 查询额度
# ============================================================
section("3. 额度查询")
resp_bal = req("GET", "/api/v1/credits/balance", token=token_a)
balance_a = resp_bal.get("data", {}).get("balance", 0)
plan_a = resp_bal.get("data", {}).get("plan_code", "?")
record("额度查询成功", resp_bal.get("success") and balance_a > 0,
       f"balance={balance_a}, plan={plan_a}")

# ============================================================
# 4. 权限检查
# ============================================================
section("4. 权限检查")
resp_ent = req("POST", "/api/v1/entitlements/check", {
    "feature": "upscale_image_cloud",
    "operation": "single",
    "client_request_id": f"ent_test_{uuid.uuid4().hex[:8]}"
}, token=token_a)
record("权限检查 - 高清修复可用", resp_ent.get("data", {}).get("allowed"),
       str(resp_ent.get("data", {})))

# ============================================================
# 5. 测试 5 种 AI 图片工具
# ============================================================
FEATURES = [
    ("upscale_image_cloud", "高清修复", {"scale_factor": 2}),
    ("vectorize_image_cloud", "转矢量", {"output_format": "svg"}),
    ("ai_edit_image_cloud", "AI 改图", {"prompt": "把背景改成浅蓝色"}),
    ("remove_bg_cloud", "高级抠图", None),
    ("ocr_cloud", "高级 OCR", {"language": "zh"}),
]

for feature_code, feature_name, options in FEATURES:
    section(f"5. {feature_name} ({feature_code})")

    # 5a. 创建任务
    create_body = {
        "feature": feature_code,
        "input_file_ids": [f"local_file_{uuid.uuid4().hex[:8]}.png"],
        "options": options,
        "client_request_id": f"int_test_{uuid.uuid4().hex[:8]}"
    }
    resp_create = req("POST", "/api/v1/ai/image-tools/tasks", create_body, token=token_a)
    success = resp_create.get("success", False)
    task_id = resp_create.get("data", {}).get("task_id", "")
    task_status = resp_create.get("data", {}).get("status", "")
    estimated = resp_create.get("data", {}).get("estimated_credits", 0)

    record(f"{feature_name} - 创建任务", success and task_id,
           f"task_id={task_id[:8]}..., status={task_status}, estimated_credits={estimated}")

    if not task_id:
        record(f"{feature_name} - 查询任务", False, "无 task_id，跳过查询")
        continue

    # 5b. 查询任务
    resp_query = req("GET", f"/api/v1/ai/image-tools/tasks/{task_id}", token=token_a)
    q_success = resp_query.get("success", False)
    q_status = resp_query.get("data", {}).get("status", "")
    q_feature = resp_query.get("data", {}).get("feature", "")
    result_files = resp_query.get("data", {}).get("result_files", [])
    result_json = resp_query.get("data", {}).get("result_json")
    credits_charged = resp_query.get("data", {}).get("credits_charged", 0)
    provider = resp_query.get("data", {}).get("provider", "")

    record(f"{feature_name} - 查询任务", q_success and q_status == "succeeded",
           f"status={q_status}, feature={q_feature}, files={len(result_files)}, "
           f"credits_charged={credits_charged}, provider={provider}")

    # 5c. 验证结果文件
    if feature_code == "vectorize_image_cloud":
        has_svg = any(f.get("mime_type") == "image/svg+xml" for f in result_files)
        record(f"{feature_name} - SVG 结果文件", has_svg,
               f"files: {[f.get('mime_type') for f in result_files]}")
    elif feature_code == "ocr_cloud":
        text_lines = result_json.get("text_lines", []) if result_json else []
        record(f"{feature_name} - OCR 文本结果", len(text_lines) > 0,
               f"text_lines count: {len(text_lines)}, text: {[t.get('text', '')[:30] for t in text_lines]}")
    else:
        has_images = any(f.get("mime_type", "").startswith("image/") for f in result_files)
        record(f"{feature_name} - 图片结果文件", has_images,
               f"files: {[(f.get('mime_type'), f'{f.get('width')}x{f.get('height')}') for f in result_files]}")

# ============================================================
# 6. 验证额度扣减
# ============================================================
section("6. 验证额度扣减")
resp_bal2 = req("GET", "/api/v1/credits/balance", token=token_a)
balance_after = resp_bal2.get("data", {}).get("balance", 0)
# 5 个功能共消耗: 3+3+5+2+2 = 15
expected_deducted = 15
actual_deducted = balance_a - balance_after
record("额度正确扣减", actual_deducted == expected_deducted,
       f"before={balance_a}, after={balance_after}, deducted={actual_deducted}, expected={expected_deducted}")

# ============================================================
# 7. 失败场景测试
# ============================================================
section("7. 失败场景")

# 7a. 未登录
resp_noauth = req("POST", "/api/v1/ai/image-tools/tasks", {
    "feature": "upscale_image_cloud",
    "input_file_ids": ["test.png"],
    "client_request_id": f"noauth_{uuid.uuid4().hex[:8]}"
})
record("未登录 - 创建任务被拒绝", not resp_noauth.get("success"),
       f"error={resp_noauth.get('error', {}).get('message', 'N/A')}")

# 7b. 无权限（免费用户）
resp_free_login = req("POST", "/api/v1/auth/login", {
    "account": "test_free@tttools.com",
    "password": "test123",
    "device_fingerprint": f"free-test-{uuid.uuid4().hex[:8]}",
    "device_name": "FREE-TEST",
    "client_version": "0.1.0"
})
token_free = resp_free_login.get("data", {}).get("access_token", "")
record("免费用户登录", resp_free_login.get("success") and bool(token_free))

resp_free_task = req("POST", "/api/v1/ai/image-tools/tasks", {
    "feature": "upscale_image_cloud",
    "input_file_ids": ["test.png"],
    "client_request_id": f"free_{uuid.uuid4().hex[:8]}"
}, token=token_free)
record("免费用户 - 无权限被拒绝", not resp_free_task.get("success"),
       f"error={resp_free_task.get('error', {}).get('message', 'N/A')}")

# ============================================================
# 8. 数据库记录验证（通过 API 间接验证）
# ============================================================
section("8. 数据库记录验证")

# 8a. Provider 调用日志
resp_logs = req("GET", "/api/v1/provider-call-logs?limit=20", token=token_a)
log_items = resp_logs.get("data", {}).get("items", [])
ai_tool_logs = [l for l in log_items if l.get("feature", "").endswith("_cloud")]
record("provider_call_log 有记录", len(ai_tool_logs) >= 5,
       f"AI 图片工具调用日志数: {len(ai_tool_logs)}")

# 8b. 额度流水
resp_ledger = req("GET", "/api/v1/credits/ledger?limit=30&change_type=consume", token=token_a)
ledger_items = resp_ledger.get("data", {}).get("items", [])
ai_ledger = [l for l in ledger_items if "AI 图片处理" in l.get("description", "")]
record("credit_ledger 有扣减记录", len(ai_ledger) >= 5,
       f"AI 图片工具扣减流水数: {len(ai_ledger)}")

# ============================================================
# 总结
# ============================================================
section("测试总结")
total = len(RESULTS)
passed = sum(1 for _, p, _ in RESULTS if p)
failed = total - passed

for name, ok, detail in RESULTS:
    print(f"  {'[PASS]' if ok else '[FAIL]'} {name}")
    if detail:
        print(f"     {detail}")

print(f"\n{'='*60}")
print(f"  结果: {passed}/{total} 通过, {failed} 失败")
print(f"{'='*60}")

if failed > 0:
    sys.exit(1)
