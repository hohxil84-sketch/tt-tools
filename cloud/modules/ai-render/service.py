"""
cloud-ai-render 业务逻辑层。

实现 AI 效果图生成的核心业务流程，遵循标准云端 AI 调用链
（对齐 MODULE_INTERFACES.md）：

    API endpoint -> auth/device check -> permission check -> credits precheck
    -> create ai_task (queued) -> provider-runtime -> provider-call-log
    -> credits charge -> update ai_task (succeeded) -> unified response

当前阶段为 Mock 实现：
  - 创建任务后立即同步处理（模拟真实异步 worker）
  - 通过 MockProvider 获取模拟结果
  - 生成模拟效果图文件信息作为 result_files

关键规则：
- 不得直接调用 OpenAI、DeepSeek 或其他第三方 AI，必须通过 provider-runtime。
- 客户端不得提交 user_id、provider、model、estimated_cost、credits_charged。
- 跨模块数据访问使用 raw SQL（sqlalchemy.text），避免 ORM 模型重复注册。
- Provider 调用通过 provider-runtime 的 MockProvider + ProviderRouter 完成。
"""
from __future__ import annotations

import sys
import os
import uuid
import json
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from cloud.shared import ErrorCode, AppError

from schemas import (
    CreateAiRenderTaskRequest,
    CreatedTaskData,
    AiRenderTaskData,
    ResultFile,
    RenderContext,
)


# ============================================================
# 路径常量
# ============================================================

_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)

_PROVIDER_RUNTIME_DIR = os.path.join(
    _PROJECT_ROOT, "cloud", "modules", "provider-runtime"
)


# ============================================================
# 从 provider-runtime 导入（仅数据模型和无 ORM 的工具类）
# ============================================================

# provider-runtime 的文件不含 ORM 模型，不会注册表到 Base.metadata，
# 可以安全地通过 sys.path 临时切换导入。

# 可能冲突的模块名（provider-runtime 内部使用）
_PR_CONFLICT_NAMES = {"models", "mock", "router", "base", "errors", "cost"}


def _import_from_provider_runtime(source_name: str, *names: str):
    """从 provider-runtime 目录安全导入非 ORM 符号。

    Args:
        source_name: 源文件名（不含 .py）
        *names: 要导入的符号名称

    Returns:
        单个符号或多个符号的元组
    """
    _saved_path = list(sys.path)
    _saved_modules = {}
    for _cn in _PR_CONFLICT_NAMES:
        for k in list(sys.modules.keys()):
            if k == _cn or k.startswith(_cn + "."):
                _saved_modules[k] = sys.modules.pop(k)

    while _PROVIDER_RUNTIME_DIR in sys.path:
        sys.path.remove(_PROVIDER_RUNTIME_DIR)
    sys.path.insert(0, _PROVIDER_RUNTIME_DIR)

    try:
        mod = __import__(source_name)
        result = tuple(getattr(mod, n) for n in names)
    finally:
        sys.path.clear()
        sys.path.extend(_saved_path)
        for _cn in _PR_CONFLICT_NAMES:
            for k in list(sys.modules.keys()):
                if k == _cn or k.startswith(_cn + "."):
                    if k not in _saved_modules:
                        del sys.modules[k]
        for k, v in _saved_modules.items():
            sys.modules[k] = v

    return result[0] if len(result) == 1 else result


# 导入 provider-runtime 的核心类型和工具
ProviderCallRequest, ChatMessage = _import_from_provider_runtime(
    "models", "ProviderCallRequest", "ChatMessage",
)
MockProvider = _import_from_provider_runtime(
    "mock", "MockProvider",
)
ProviderRouter = _import_from_provider_runtime(
    "router", "ProviderRouter",
)


# ============================================================
# 常量
# ============================================================

# 默认使用 deepseek-chat（性价比高，中文能力强）
_DEFAULT_MODEL = "deepseek-chat"

# 每次调用消耗的默认额度
_DEFAULT_CREDITS_PER_CALL = 2

# 当前时间（UTC）获取函数
_utcnow = lambda: datetime.now(timezone.utc)

# Mock 效果图文件列表（模拟 AI 生成的结果文件）
_MOCK_RESULT_FILES: List[dict] = [
    {
        "file_id": "00000000-0000-0000-0000-000000000001",
        "url": "https://mock-cdn.tt-tools.com/render/result_01.png",
        "mime_type": "image/png",
        "width": 1920,
        "height": 1080,
    },
    {
        "file_id": "00000000-0000-0000-0000-000000000002",
        "url": "https://mock-cdn.tt-tools.com/render/result_02.png",
        "mime_type": "image/png",
        "width": 1024,
        "height": 1024,
    },
]


# ============================================================
# Prompt 模板构建
# ============================================================


def _build_system_prompt() -> str:
    """构建效果图生成的系统提示词。"""
    return (
        "你是一个专业的效果图渲染专家，精通室内设计、产品展示和海报设计。"
        "你的任务是根据用户提供的场景类型、提示词和输入文件信息，"
        "生成符合预期视觉效果的效果图描述。"
    )


def _build_user_prompt(req: CreateAiRenderTaskRequest) -> str:
    """根据请求参数构建用户提示词。

    将场景类型、提示词、风格、尺寸等信息组装为结构化的提示词。

    Args:
        req: 效果图生成请求

    Returns:
        结构化的用户提示词文本
    """
    parts = []

    # 场景类型映射
    scene_labels = {
        "interior_design": "室内设计",
        "product_showcase": "产品展示",
        "poster_design": "海报设计",
    }
    scene_label = scene_labels.get(req.scene_type, req.scene_type)
    parts.append(f"【场景类型】{scene_label}")

    # 提示词
    parts.append(f"【效果描述】{req.prompt}")

    # 输入文件信息（已上传文件数量）
    if req.input_file_ids:
        parts.append(f"【输入文件】共 {len(req.input_file_ids)} 个文件")

    # 风格参考
    if req.style:
        style_labels = {
            "modern": "现代简约",
            "minimalist": "极简主义",
            "chinese": "中式风格",
            "european": "欧式风格",
        }
        style_desc = style_labels.get(req.style, req.style)
        parts.append(f"【风格参考】{style_desc}")

    # 输出尺寸
    if req.size:
        parts.append(f"【输出尺寸】{req.size}")

    return "\n".join(parts)


# ============================================================
# AI 效果图生成核心逻辑
# ============================================================


async def create_render_task(
    db: AsyncSession,
    req: CreateAiRenderTaskRequest,
    ctx: RenderContext,
) -> CreatedTaskData:
    """创建并执行效果图生成任务，遵循标准云端 AI 调用链。

    调用链步骤（对齐 MODULE_INTERFACES.md）：
    1. 套餐权限检查（用户套餐是否支持 ai_render_cloud）
    2. 额度预检查（余额是否足够）
    3. 创建任务记录（ai_tasks 表，状态 queued）
    4. 调用 Provider Runtime 生成效果图
    5. 写入 Provider 调用日志
    6. 扣除 AI 额度
    7. 更新任务状态为 succeeded 并写入结果

    Args:
        db: 数据库异步会话
        req: 效果图生成请求
        ctx: 生成上下文（用户、设备、请求追踪信息）

    Returns:
        CreatedTaskData（包含 task_id、status、feature、estimated_credits）
    """
    # ---- 步骤 1: 套餐权限检查 ----
    await _check_feature_permission(db, ctx.plan_code)

    # ---- 步骤 2: 额度预检查 ----
    await _check_credits_balance(db, ctx.user_id, _DEFAULT_CREDITS_PER_CALL)

    # ---- 步骤 3: 创建任务记录（状态 queued） ----
    task_id = await _create_task_record(
        db=db,
        ctx=ctx,
        req=req,
        status="queued",
    )

    # ---- 步骤 4: 构建 prompt 并调用 Provider Runtime ----
    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(req)

    provider_result = await _call_provider(
        model=_DEFAULT_MODEL,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        feature="ai_render_cloud",
        request_id=ctx.request_id,
    )

    # 检查 Provider 调用结果
    if provider_result.status == "failed":
        # Provider 调用失败，写入失败日志，更新任务状态为 failed
        await _insert_provider_log(
            db=db,
            ctx=ctx,
            provider=provider_result.provider,
            model=provider_result.model,
            status="failed",
            error_code=provider_result.error_code,
            input_tokens=provider_result.usage.input_tokens,
            output_tokens=provider_result.usage.output_tokens,
            total_tokens=provider_result.usage.total_tokens,
            reasoning_tokens=provider_result.usage.reasoning_tokens,
            cached_tokens=provider_result.usage.cached_tokens,
            image_count=provider_result.usage.image_count,
            estimated_cost=0.0,
            credits_charged=0,
            latency_ms=provider_result.latency_ms or 0,
            raw_usage_json=provider_result.raw_usage_json,
        )
        # 更新任务状态为 failed
        await _update_task_status(
            db=db,
            task_id=task_id,
            status="failed",
            error_code=provider_result.error_code,
        )
        raise AppError(
            code=provider_result.error_code or ErrorCode.PROVIDER_UNAVAILABLE,
            message=provider_result.error_message or "AI 效果图服务暂时不可用，请稍后重试",
            status_code=502,
        )

    # ---- 步骤 5: 写入 Provider 调用日志（成功） ----
    provider_call_id = await _insert_provider_log(
        db=db,
        ctx=ctx,
        provider=provider_result.provider,
        model=provider_result.model,
        status="success",
        error_code=None,
        input_tokens=provider_result.usage.input_tokens,
        output_tokens=provider_result.usage.output_tokens,
        total_tokens=provider_result.usage.total_tokens,
        reasoning_tokens=provider_result.usage.reasoning_tokens,
        cached_tokens=provider_result.usage.cached_tokens,
        image_count=provider_result.usage.image_count,
        estimated_cost=provider_result.estimated_cost,
        credits_charged=_DEFAULT_CREDITS_PER_CALL,
        latency_ms=provider_result.latency_ms or 0,
        raw_usage_json=provider_result.raw_usage_json,
    )

    # ---- 步骤 6: 扣除 AI 额度 ----
    await _consume_credits(
        db=db,
        user_id=ctx.user_id,
        amount=_DEFAULT_CREDITS_PER_CALL,
        source_id=provider_call_id,
        description=f"AI 效果图生成 · {req.scene_type}",
    )

    # ---- 步骤 7: 更新任务为 succeeded，写入结果 ----
    mock_result_files = _build_mock_result_files()
    await _update_task_result(
        db=db,
        task_id=task_id,
        status="succeeded",
        provider_call_id=provider_call_id,
        provider=provider_result.provider,
        model=provider_result.model,
        estimated_cost=provider_result.estimated_cost,
        credits_charged=_DEFAULT_CREDITS_PER_CALL,
        result_files=mock_result_files,
    )

    return CreatedTaskData(
        task_id=task_id,
        status="succeeded",
        feature="ai_render_cloud",
        estimated_credits=_DEFAULT_CREDITS_PER_CALL,
    )


async def query_render_task(
    db: AsyncSession,
    task_id: str,
    user_id: str,
) -> AiRenderTaskData:
    """查询效果图生成任务的状态和结果。

    使用 raw SQL 查询 ai_tasks 表（对齐 DATABASE_SCHEMA.md），
    避免 ORM 模型注册冲突。

    Args:
        db: 数据库异步会话
        task_id: 任务 ID（UUID）
        user_id: 用户 ID（用于权限校验）

    Returns:
        AiRenderTaskData（任务状态和结果）

    Raises:
        AppError: 任务不存在或无权访问
    """
    result = await db.execute(
        text(
            "SELECT id, user_id, feature, status, input_json, result_json, "
            "provider_call_id, credits_charged, error_code, created_at, updated_at "
            "FROM ai_tasks WHERE id = :tid"
        ),
        {"tid": task_id},
    )
    row = result.fetchone()

    if row is None:
        raise AppError(
            code=ErrorCode.VALIDATION_ERROR,
            message="任务不存在",
            status_code=404,
        )

    # 校验任务归属（用户只能查询自己的任务）
    (
        tid, owner_id, feature, status, input_json_raw, result_json_raw,
        p_call_id, credits_charged, error_code, created_at, updated_at,
    ) = row

    if owner_id != user_id:
        raise AppError(
            code=ErrorCode.PERMISSION_DENIED,
            message="无权访问此任务",
            status_code=403,
        )

    # 解析结果文件
    result_files: List[ResultFile] = []
    provider = None
    model = None
    estimated_cost = None
    provider_call_id = None

    if result_json_raw:
        result_data = _parse_json_field(result_json_raw)
        if result_data:
            for f in result_data.get("files", []):
                result_files.append(ResultFile(
                    file_id=f.get("file_id", ""),
                    url=f.get("url"),
                    mime_type=f.get("mime_type", "image/png"),
                    width=f.get("width"),
                    height=f.get("height"),
                ))
            provider = result_data.get("provider")
            model = result_data.get("model")
            estimated_cost = result_data.get("estimated_cost")
            provider_call_id = result_data.get("provider_call_id") or p_call_id

    return AiRenderTaskData(
        task_id=tid,
        status=status,
        feature=feature,
        result_files=result_files,
        provider=provider,
        model=model,
        estimated_cost=estimated_cost,
        credits_charged=credits_charged if credits_charged else None,
        provider_call_id=provider_call_id or (str(p_call_id) if p_call_id else None),
    )


# ============================================================
# 调用链辅助函数（全部使用 raw SQL，避免 ORM 跨模块冲突）
# ============================================================


async def _check_feature_permission(
    db: AsyncSession,
    plan_code: str,
) -> None:
    """检查当前套餐是否支持 ai_render_cloud 功能。

    使用 raw SQL 查询 plans 表的 enabled_features_json 字段，
    避免导入 credits-billing 的 Plan ORM 模型（该模型注册到 Base.metadata）。

    Args:
        db: 数据库异步会话
        plan_code: 用户当前套餐编码

    Raises:
        AppError: 套餐不存在或不支持此功能
    """
    result = await db.execute(
        text(
            "SELECT enabled_features_json FROM plans "
            "WHERE code = :code AND status = 'active'"
        ),
        {"code": plan_code},
    )
    row = result.fetchone()

    if row is None:
        raise AppError(
            code=ErrorCode.PLAN_REQUIRED,
            message="当前套餐不支持 AI 效果图功能，请升级套餐",
            status_code=403,
        )

    # enabled_features_json 在 SQLite 中存储为 TEXT/JSON 字符串
    features = _parse_json_field(row[0])

    ai_render_enabled = features.get("ai_render_cloud", False)

    if isinstance(ai_render_enabled, dict):
        if not ai_render_enabled:
            raise AppError(
                code=ErrorCode.PERMISSION_DENIED,
                message="当前套餐不支持 AI 效果图功能，请升级套餐",
                status_code=403,
            )
    elif not ai_render_enabled:
        raise AppError(
            code=ErrorCode.PERMISSION_DENIED,
            message="当前套餐不支持 AI 效果图功能，请升级套餐",
            status_code=403,
        )


async def _check_credits_balance(
    db: AsyncSession,
    user_id: str,
    required_credits: int,
) -> None:
    """检查用户额度是否足够。

    使用 raw SQL 查询 credit_accounts 表（对齐 DATABASE_SCHEMA.md），
    优先复用已有额度账户，不存在则自动创建。

    Args:
        db: 数据库异步会话
        user_id: 用户 ID
        required_credits: 需要的额度数量

    Raises:
        AppError: 额度不足或账户冻结
    """
    # 查询或创建额度账户
    result = await db.execute(
        text(
            "SELECT id, balance, status FROM credit_accounts "
            "WHERE user_id = :user_id"
        ),
        {"user_id": user_id},
    )
    row = result.fetchone()

    if row is not None:
        account_id, balance, status = row[0], row[1], row[2]
        if status == "frozen":
            raise AppError(
                code=ErrorCode.PLAN_REQUIRED,
                message="账户已被冻结，请联系客服",
                status_code=403,
            )
    else:
        # 自动创建额度账户（获取用户套餐以确定赠额）
        user_result = await db.execute(
            text("SELECT plan_code FROM users WHERE id = :uid"),
            {"uid": user_id},
        )
        user_row = user_result.fetchone()
        plan_code = user_row[0] if user_row else "free"

        plan_result = await db.execute(
            text("SELECT monthly_grant FROM plans WHERE code = :code AND status = 'active'"),
            {"code": plan_code},
        )
        plan_row = plan_result.fetchone()
        monthly_grant = plan_row[0] if plan_row else 0

        account_id = str(uuid.uuid4())
        now = _utcnow()
        balance = monthly_grant

        # 插入额度账户
        await db.execute(
            text(
                "INSERT INTO credit_accounts "
                "(id, user_id, plan_code, balance, monthly_grant, "
                " period_start, period_end, status, created_at, updated_at) "
                "VALUES (:id, :uid, :pc, :bal, :mg, :ps, :pe, 'active', :now, :now)"
            ),
            {
                "id": account_id,
                "uid": user_id,
                "pc": plan_code,
                "bal": balance,
                "mg": monthly_grant,
                "ps": now.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
                "pe": _next_month_start(now),
                "now": now,
            },
        )

        # 写入初始赠送流水
        if monthly_grant > 0:
            await db.execute(
                text(
                    "INSERT INTO credit_ledger "
                    "(id, user_id, account_id, change_type, amount, balance_after, "
                    " source_type, description, created_at) "
                    "VALUES (:id, :uid, :aid, 'grant', :amt, :ba, 'system', :desc, :now)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "uid": user_id,
                    "aid": account_id,
                    "amt": monthly_grant,
                    "ba": balance,
                    "desc": "新账户初始赠送额度",
                    "now": now,
                },
            )

    # 重新查询最新余额（处理自动创建后的情况）
    result = await db.execute(
        text("SELECT balance FROM credit_accounts WHERE user_id = :user_id"),
        {"user_id": user_id},
    )
    row = result.fetchone()
    balance = row[0] if row else 0

    if balance < required_credits:
        raise AppError(
            code=ErrorCode.CREDITS_NOT_ENOUGH,
            message=(
                f"AI 额度不足（当前 {balance}"
                f"，需要 {required_credits}），请充值后再试"
            ),
            status_code=402,
        )


async def _create_task_record(
    db: AsyncSession,
    ctx: RenderContext,
    req: CreateAiRenderTaskRequest,
    status: str,
) -> str:
    """在 ai_tasks 表中创建任务记录。

    使用 raw SQL INSERT 直接写入，对齐 DATABASE_SCHEMA.md ai_tasks 表定义。

    Args:
        db: 数据库异步会话
        ctx: 生成上下文
        req: 创建请求
        status: 任务初始状态

    Returns:
        新创建的任务 ID（UUID）
    """
    task_id = str(uuid.uuid4())
    now = _utcnow()

    # 构造脱敏输入 JSON
    input_data = {
        "scene_type": req.scene_type,
        "prompt": req.prompt,
        "input_file_ids": req.input_file_ids,
        "style": req.style,
        "size": req.size,
        "client_request_id": req.client_request_id,
    }

    await db.execute(
        text(
            "INSERT INTO ai_tasks "
            "(id, user_id, device_id, feature, status, input_json, "
            " credits_charged, created_at, updated_at) "
            "VALUES (:id, :uid, :did, :feat, :st, :input, 0, :now, :now)"
        ),
        {
            "id": task_id,
            "uid": ctx.user_id,
            "did": ctx.device_id,
            "feat": "ai_render_cloud",
            "st": status,
            "input": json.dumps(input_data),
            "now": now,
        },
    )

    return task_id


async def _update_task_status(
    db: AsyncSession,
    task_id: str,
    status: str,
    error_code: Optional[str] = None,
) -> None:
    """更新任务状态。

    Args:
        db: 数据库异步会话
        task_id: 任务 ID
        status: 新状态
        error_code: 错误码（失败时写入）
    """
    now = _utcnow()
    await db.execute(
        text(
            "UPDATE ai_tasks SET status = :st, error_code = :ec, "
            "updated_at = :now WHERE id = :tid"
        ),
        {"st": status, "ec": error_code, "now": now, "tid": task_id},
    )


async def _update_task_result(
    db: AsyncSession,
    task_id: str,
    status: str,
    provider_call_id: str,
    provider: str,
    model: str,
    estimated_cost: float,
    credits_charged: int,
    result_files: List[dict],
) -> None:
    """更新任务为完成状态并写入结果。

    Args:
        db: 数据库异步会话
        task_id: 任务 ID
        status: 完成状态（succeeded）
        provider_call_id: Provider 调用日志 ID
        provider: Provider 名称
        model: 模型名称
        estimated_cost: 估算成本
        credits_charged: 扣除额度
        result_files: 结果文件列表
    """
    now = _utcnow()
    result_data = {
        "files": result_files,
        "provider": provider,
        "model": model,
        "estimated_cost": estimated_cost,
        "provider_call_id": provider_call_id,
    }

    await db.execute(
        text(
            "UPDATE ai_tasks SET status = :st, result_json = :result, "
            "provider_call_id = :pcid, credits_charged = :cc, "
            "updated_at = :now WHERE id = :tid"
        ),
        {
            "st": status,
            "result": json.dumps(result_data),
            "pcid": provider_call_id,
            "cc": credits_charged,
            "now": now,
            "tid": task_id,
        },
    )


async def _call_provider(
    model: str,
    system_prompt: str,
    user_prompt: str,
    feature: str,
    request_id: str,
):
    """调用 Provider Runtime 生成效果图。

    使用 MockProvider + ProviderRouter 执行调用。
    当前阶段全部使用 Mock Provider。
    """
    call_request = ProviderCallRequest(
        model=model,
        messages=[
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_prompt),
        ],
        feature=feature,
        max_tokens=2048,
        temperature=0.7,
        request_id=request_id,
    )

    provider = MockProvider()
    router = ProviderRouter()
    result = await router.call(request=call_request, provider=provider)

    return result


async def _insert_provider_log(
    db: AsyncSession,
    ctx: RenderContext,
    provider: str,
    model: str,
    status: str,
    error_code: Optional[str],
    input_tokens: int,
    output_tokens: int,
    total_tokens: int,
    reasoning_tokens: int,
    cached_tokens: int,
    image_count: int,
    estimated_cost: float,
    credits_charged: int,
    latency_ms: int,
    raw_usage_json: dict,
) -> str:
    """写入 Provider 调用日志到 provider_call_log 表。

    使用 raw SQL INSERT 直接写入，避免导入 provider-log 的 ORM 模型。
    返回新写入的日志 UUID（供后续扣费关联使用）。

    对齐 DATABASE_SCHEMA.md provider_call_log 表定义和写入边界规则：
    provider_call_log 由 Provider Runtime 或其封装服务写入。
    """
    log_id = str(uuid.uuid4())
    raw_meta = json.dumps({"feature": "ai_render_cloud", "mock": True})

    await db.execute(
        text(
            "INSERT INTO provider_call_log "
            "(id, request_id, user_id, device_id, feature, provider, model, "
            " status, error_code, input_tokens, output_tokens, total_tokens, "
            " reasoning_tokens, cached_tokens, image_count, estimated_cost, "
            " credits_charged, latency_ms, raw_usage_json, raw_meta_json, created_at) "
            "VALUES (:id, :rid, :uid, :did, :feat, :prov, :mod, "
            " :st, :ec, :it, :ot, :tt, :rt, :ct, :ic, :ecost, "
            " :cc, :lat, :ruj, :rmj, :now)"
        ),
        {
            "id": log_id,
            "rid": ctx.request_id,
            "uid": ctx.user_id,
            "did": ctx.device_id,
            "feat": "ai_render_cloud",
            "prov": provider,
            "mod": model,
            "st": status,
            "ec": error_code,
            "it": input_tokens,
            "ot": output_tokens,
            "tt": total_tokens,
            "rt": reasoning_tokens,
            "ct": cached_tokens,
            "ic": image_count,
            "ecost": estimated_cost,
            "cc": credits_charged,
            "lat": latency_ms,
            "ruj": json.dumps(raw_usage_json) if raw_usage_json else None,
            "rmj": raw_meta,
            "now": _utcnow(),
        },
    )

    return log_id


async def _consume_credits(
    db: AsyncSession,
    user_id: str,
    amount: int,
    source_id: str,
    description: str,
) -> None:
    """扣除 AI 额度。

    使用 raw SQL 更新 credit_accounts 表并写入 credit_ledger 流水。
    对齐 DATABASE_SCHEMA.md 写入边界规则：credit_ledger 由计费服务写入。

    Args:
        db: 数据库异步会话
        user_id: 用户 ID
        amount: 扣除额度（正整数）
        source_id: 来源 ID（provider_call_log.id）
        description: 中文说明

    Raises:
        AppError: 额度不足
    """
    # 查询当前余额和账户 ID
    result = await db.execute(
        text(
            "SELECT id, balance FROM credit_accounts "
            "WHERE user_id = :user_id AND status = 'active'"
        ),
        {"user_id": user_id},
    )
    row = result.fetchone()
    if row is None:
        raise AppError(
            code=ErrorCode.CREDITS_NOT_ENOUGH,
            message="未找到有效的额度账户",
            status_code=402,
        )
    account_id, balance = row[0], row[1]

    if balance < amount:
        raise AppError(
            code=ErrorCode.CREDITS_NOT_ENOUGH,
            message=f"AI 额度不足（当前 {balance}，需要 {amount}）",
            status_code=402,
        )

    new_balance = balance - amount
    now = _utcnow()

    # 更新余额
    await db.execute(
        text(
            "UPDATE credit_accounts SET balance = :bal, updated_at = :now "
            "WHERE id = :aid"
        ),
        {"bal": new_balance, "now": now, "aid": account_id},
    )

    # 写入额度流水
    await db.execute(
        text(
            "INSERT INTO credit_ledger "
            "(id, user_id, account_id, change_type, amount, balance_after, "
            " source_type, source_id, description, created_at) "
            "VALUES (:id, :uid, :aid, 'consume', :amt, :ba, "
            " 'provider_call', :sid, :desc, :now)"
        ),
        {
            "id": str(uuid.uuid4()),
            "uid": user_id,
            "aid": account_id,
            "amt": -amount,
            "ba": new_balance,
            "sid": source_id,
            "desc": description,
            "now": now,
        },
    )


# ============================================================
# 工具函数
# ============================================================


def _next_month_start(dt: datetime) -> datetime:
    """计算下一个月的第一天。

    Args:
        dt: 当前日期时间

    Returns:
        下个月第一天的 UTC datetime
    """
    if dt.month == 12:
        return dt.replace(year=dt.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return dt.replace(month=dt.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)


def _build_mock_result_files() -> List[dict]:
    """构建 Mock 效果图结果文件列表。

    Mock 阶段返回固定的模拟文件信息，模拟真实图片生成 Provider 的输出。
    后续接入真实图片 Provider 时替换此处逻辑。

    Returns:
        模拟结果文件列表
    """
    return _MOCK_RESULT_FILES


def _parse_json_field(raw) -> dict:
    """安全解析数据库中的 JSON 字段。

    兼容 SQLite（存储为 TEXT 字符串）和 PostgreSQL（存储为 JSONB）两种格式。

    Args:
        raw: 原始字段值（可能是 str、dict 或 None）

    Returns:
        解析后的 dict（解析失败返回空 dict）
    """
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}
