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
import calendar as _cal
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
_PR_CONFLICT_NAMES = {
    "models", "mock", "router", "base", "errors", "cost",
    "registry", "config", "deepseek", "doubao", "http_utils",
}


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
get_global_router = _import_from_provider_runtime(
    "registry", "get_global_router",
)


# ============================================================
# 常量
# ============================================================

# 默认使用 deepseek-chat（性价比高，中文能力强）
# 当前时间（UTC）获取函数
_utcnow = lambda: datetime.now(timezone.utc)


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
    feature = "ai_render_cloud"

    # ---- 步骤 1: 套餐权限检查 ----
    await _check_feature_permission(db, ctx.plan_id)

    # ---- 步骤 2: 额度预检查（从 DB 读起步扣点 + 预估最大成本） ----
    min_credits = await _get_min_credits(db, feature)
    threshold = await _estimate_threshold(db, feature, "image_generation", 2048,
        _build_user_prompt(req))
    await _check_credits_balance(db, ctx.user_id, threshold)

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
        model="deepseek-chat",
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
    actual_credits = await _calculate_deduction(
        db, feature,
        provider_result.provider, provider_result.model,
        provider_result.usage,
    )

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
        credits_charged=actual_credits,
        latency_ms=provider_result.latency_ms or 0,
        raw_usage_json=provider_result.raw_usage_json,
        estimated_credits_before=threshold,
    )

    # ---- 步骤 6: 扣除 AI 额度 ----
    await _consume_credits(
        db=db,
        user_id=ctx.user_id,
        amount=actual_credits,
        source_id=provider_call_id,
        description=f"AI 效果图生成 · {req.scene_type}",
    )

    # ---- 步骤 7: 更新任务为 succeeded，写入结果 ----
    result_files = _normalize_result_files(provider_result.files or [])
    await _update_task_result(
        db=db,
        task_id=task_id,
        status="succeeded",
        provider_call_id=provider_call_id,
        provider=provider_result.provider,
        model=provider_result.model,
        estimated_cost=provider_result.estimated_cost,
        credits_charged=actual_credits,
        result_files=result_files,
        estimated_credits_before=threshold,
    )

    return CreatedTaskData(
        task_id=task_id,
        status="succeeded",
        feature=feature,
        estimated_credits=actual_credits,
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
    plan_id: Optional[str],
) -> None:
    """检查当前套餐是否支持 ai_render_cloud 功能。

    使用 raw SQL 查询 plans 表的 enabled_features_json 字段，
    避免导入 credits-billing 的 Plan ORM 模型（该模型注册到 Base.metadata）。

    Args:
        db: 数据库异步会话
        plan_id: 用户当前套餐 ID（UUID）

    Raises:
        AppError: 套餐不存在或不支持此功能
    """
    if not plan_id:
        raise AppError(
            code=ErrorCode.PLAN_REQUIRED,
            message="当前套餐不支持 AI 效果图功能，请升级套餐",
            status_code=403,
        )

    # 检查功能码是否全局启用
    fc_result = await db.execute(
        text("SELECT is_active FROM feature_codes WHERE code = :fcode"),
        {"fcode": "ai_render_cloud"},
    )
    fc_row = fc_result.fetchone()
    if fc_row is None or not fc_row[0]:
        raise AppError(
            code=ErrorCode.PERMISSION_DENIED,
            message="AI 效果图功能暂未开放",
            status_code=403,
        )

    result = await db.execute(
        text(
            "SELECT enabled_features_json FROM plans "
            "WHERE id = :pid AND status = 'active'"
        ),
        {"pid": plan_id},
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
            text("SELECT plan_id FROM users WHERE id = :uid"),
            {"uid": user_id},
        )
        user_row = user_result.fetchone()
        plan_id = user_row[0] if user_row else None

        plan_result = await db.execute(
            text("SELECT monthly_grant FROM plans WHERE id = :pid AND status = 'active'"),
            {"pid": plan_id},
        )
        plan_row = plan_result.fetchone()
        monthly_grant = plan_row[0] if plan_row else 0

        account_id = str(uuid.uuid4())
        now = _utcnow()
        balance = monthly_grant

        # 插入额度账户（周年计费：从今天到一个月后的同一天）
        period_start = now
        if now.month == 12:
            next_year, next_month = now.year + 1, 1
        else:
            next_year, next_month = now.year, now.month + 1
        last_day = _cal.monthrange(next_year, next_month)[1]
        period_end = now.replace(
            year=next_year, month=next_month,
            day=min(now.day, last_day),
            hour=0, minute=0, second=0, microsecond=0,
        )

        await db.execute(
            text(
                "INSERT INTO credit_accounts "
                "(id, user_id, plan_id, balance, monthly_grant, "
                " period_start, period_end, status, created_at, updated_at) "
                "VALUES (:id, :uid, :pid, :bal, :mg, :ps, :pe, 'active', :now, :now)"
            ),
            {
                "id": account_id,
                "uid": user_id,
                "pid": plan_id,
                "bal": balance,
                "mg": monthly_grant,
                "ps": period_start,
                "pe": period_end,
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
            " credits_charged, estimated_credits_before, created_at, updated_at) "
            "VALUES (:id, :uid, :did, :feat, :st, :input, 0, :ecb, :now, :now)"
        ),
        {
            "id": task_id,
            "uid": ctx.user_id,
            "did": ctx.device_id,
            "feat": "ai_render_cloud",
            "st": status,
            "input": json.dumps(input_data),
            "ecb": 0,  # 创建时填 0，完成时更新为实际预估
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
    estimated_credits_before: Optional[int] = None,
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
            "estimated_credits_before = :ecb, "
            "updated_at = :now WHERE id = :tid"
        ),
        {
            "st": status,
            "result": json.dumps(result_data),
            "pcid": provider_call_id,
            "cc": credits_charged,
            "ecb": estimated_credits_before,
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

    使用全局 Router 走真实图片生成路由。
    所有 Provider 从数据库加载，不再硬编码。

    Doubao 图片生成端从 messages 中提取 user 消息作为 prompt，
    system 消息会被忽略，因此 system_prompt 中的风格指引
    已合并到 user_prompt 中传入。
    """
    # 将 system prompt 的风格指引合并到 user prompt 中
    # （图片生成 API 只用单一 prompt，不用 system/user 分离）
    full_prompt = user_prompt
    if system_prompt:
        full_prompt = f"{system_prompt}\n\n{user_prompt}"

    call_request = ProviderCallRequest(
        model=model,
        messages=[
            ChatMessage(role="user", content=full_prompt),
        ],
        feature=feature,
        capability="image_generation",
        tier="cheap",
        max_tokens=2048,
        temperature=0.7,
        request_id=request_id,
    )

    router = get_global_router()
    result = await router.call_by_capability(
        request=call_request,
        capability="image_generation",
    )
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
    estimated_credits_before: Optional[int] = None,
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
            " credits_charged, latency_ms, raw_usage_json, raw_meta_json, "
            " estimated_credits_before, created_at) "
            "VALUES (:id, :rid, :uid, :did, :feat, :prov, :mod, "
            " :st, :ec, :it, :ot, :tt, :rt, :ct, :ic, :ecost, "
            " :cc, :lat, :ruj, :rmj, :ecb, :now)"
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
            "ecb": estimated_credits_before,
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
    if amount <= 0:
        return

    now = _utcnow()

    # 原子扣减：在 UPDATE 中检查余额 >= amount，避免并发超扣
    result = await db.execute(
        text(
            "UPDATE credit_accounts SET balance = balance - :amt, updated_at = :now "
            "WHERE user_id = :uid AND status = 'active' AND balance >= :amt "
            "RETURNING id, balance"
        ),
        {"amt": amount, "now": now, "uid": user_id},
    )
    updated = result.fetchone()

    if updated is None:
        # 扣减失败，区分无账户 / 冻结 / 余额不足
        check_result = await db.execute(
            text("SELECT id, balance, status FROM credit_accounts WHERE user_id = :uid"),
            {"uid": user_id},
        )
        row = check_result.fetchone()
        if row is None:
            raise AppError(
                code=ErrorCode.CREDITS_NOT_ENOUGH,
                message="未找到有效的额度账户",
                status_code=402,
            )
        acct_id, balance, status = row[0], row[1], row[2]
        if status != "active":
            raise AppError(
                code=ErrorCode.PLAN_REQUIRED,
                message="账户已被冻结，请联系客服",
                status_code=403,
            )
        raise AppError(
            code=ErrorCode.CREDITS_NOT_ENOUGH,
            message=f"AI 额度不足（当前 {balance}，需要 {amount}）",
            status_code=402,
        )

    account_id, new_balance = updated[0], updated[1]

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


def _normalize_result_files(provider_files: List[dict]) -> List[dict]:
    """将 Provider 返回的文件列表规范化为 ResultFile 格式。

    不再回退 Mock——Provider 无返回则返回空列表。
    """
    if not provider_files:
        return []

    normalized = []
    for f in provider_files:
        normalized.append({
            "file_id": f.get("file_id") or str(uuid.uuid4()),
            "url": f.get("url"),
            "mime_type": f.get("mime_type", "image/png"),
            "width": f.get("width"),
            "height": f.get("height"),
        })
    return normalized


def _parse_json_field(raw) -> dict:
    """安全解析数据库中的 JSON 字段。"""
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


# ============================================================
# DB 驱动定价辅助函数（使用 raw SQL 避免 ORM 跨模块冲突）
# ============================================================


async def _get_min_credits(db: AsyncSession, feature: str) -> int:
    """从 feature_pricing 表查起步扣点。"""
    result = await db.execute(
        text("SELECT min_credits FROM feature_pricing WHERE feature_code = :fc"),
        {"fc": feature},
    )
    row = result.fetchone()
    return row[0] if row else 1


async def _get_exchange_rate(db: AsyncSession) -> float:
    """从 system_config 表查汇率。"""
    result = await db.execute(
        text("SELECT value FROM system_config WHERE key = 'credits_exchange_rate'"),
    )
    row = result.fetchone()
    return float(row[0]) if row else 10.0


async def _get_model_pricing(
    db: AsyncSession, provider: str, model: str
) -> dict:
    """从 provider_model_pricing 表查模型定价。"""
    result = await db.execute(
        text(
            "SELECT pmp.input_price, pmp.output_price "
            "FROM provider_model_pricing pmp "
            "JOIN providers p ON pmp.provider_id = p.id "
            "WHERE p.name = :pn AND pmp.model_name = :mn AND pmp.is_active = TRUE"
        ),
        {"pn": provider, "mn": model},
    )
    row = result.fetchone()
    if row is not None:
        return {"input_price": float(row[0]), "output_price": float(row[1])}
    return {"input_price": 1.0, "output_price": 2.0}


async def _calculate_deduction(
    db: AsyncSession, feature: str, provider: str, model: str, usage,
) -> int:
    """计算实际扣点数。公式：max(起步扣点, ceil(实际CNY成本 × 汇率))"""
    import math as _math

    min_credits = await _get_min_credits(db, feature)
    pricing = await _get_model_pricing(db, provider, model)
    rate = await _get_exchange_rate(db)

    input_cost = (usage.input_tokens / 1_000_000) * pricing["input_price"]
    output_cost = (usage.output_tokens / 1_000_000) * pricing["output_price"]
    actual_cost_cny = input_cost + output_cost

    cost_credits = _math.ceil(actual_cost_cny * rate)
    return max(min_credits, cost_credits)


async def _estimate_threshold(
    db: AsyncSession, feature: str, capability: str,
    max_tokens: int, prompt_text: str,
) -> int:
    """预估最大扣点（预检查用）。"""
    import math as _math

    min_credits = await _get_min_credits(db, feature)
    rate = await _get_exchange_rate(db)

    result = await db.execute(
        text("SELECT MIN(output_price), MIN(input_price) FROM provider_model_pricing WHERE is_active = TRUE AND model_name != '__default__'"),
    )
    row = result.fetchone()
    output_price = float(row[0]) if row and row[0] is not None else 2.0
    input_price = float(row[1]) if row and row[1] is not None else 1.0

    estimated_input = max(1, int(len(prompt_text) * 1.2))
    input_cost = (estimated_input / 1_000_000) * input_price
    output_cost = (max_tokens / 1_000_000) * output_price
    max_cost_cny = input_cost + output_cost

    max_credits = _math.ceil(max_cost_cny * rate)
    return max(min_credits, max_credits)
