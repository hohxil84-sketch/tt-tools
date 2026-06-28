"""
cloud-ai-image-tools 业务逻辑层。

实现高级图片 AI 处理的核心业务流程，遵循标准云端 AI 调用链
（对齐 MODULE_INTERFACES.md）：

    API endpoint -> auth/device check -> permission check -> credits precheck
    -> create ai_task (queued) -> provider-runtime -> provider-call-log
    -> credits charge -> update ai_task (succeeded) -> unified response

当前阶段为 Mock 实现：
  - 创建任务后立即同步处理（模拟真实异步 worker）
  - 通过 MockProvider 获取模拟结果
  - 根据不同子功能生成对应的 Mock 结果文件

支持 5 种高级图片 AI 子功能：
  - upscale_image_cloud（高清修复）：模拟输出高分辨率 PNG
  - vectorize_image_cloud（转矢量）：模拟输出 SVG 矢量文件
  - ai_edit_image_cloud（AI 改图）：模拟输出编辑后的图片
  - remove_bg_cloud（高级抠图）：模拟输出透明背景 PNG
  - ocr_cloud（高级 OCR）：模拟输出 OCR 文本识别结果

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
    CreateAiImageToolTaskRequest,
    CreatedTaskData,
    AiImageToolTaskData,
    ResultFile,
    ImageToolContext,
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


# 当前时间（UTC）获取函数
_utcnow = lambda: datetime.now(timezone.utc)


async def _get_feature_name(db: AsyncSession, feature: str) -> str:
    """从 feature_codes 表查功能中文名（替代 _FEATURE_LABELS 硬编码）。"""
    result = await db.execute(
        text("SELECT name FROM feature_codes WHERE code = :fc"),
        {"fc": feature},
    )
    row = result.fetchone()
    return row[0] if row else feature


# ============================================================
# Prompt 模板构建（按功能码构建不同的提示词）
# ============================================================


def _build_system_prompt(feature: str) -> str:
    """根据功能码构建系统提示词。

    Args:
        feature: AI 图片工具功能码

    Returns:
        对应功能的中文系统提示词
    """
    prompts = {
        "upscale_image_cloud": (
            "你是一个专业的高清图像修复专家，精通 AI 超分辨率技术。"
            "你的任务是对用户提供的图片进行高清修复，提升分辨率和细节表现。"
        ),
        "vectorize_image_cloud": (
            "你是一个专业的图像矢量化专家，精通位图转矢量技术。"
            "你的任务是将用户提供的位图转换为可缩放的矢量图形（SVG 格式）。"
        ),
        "ai_edit_image_cloud": (
            "你是一个专业的 AI 图像编辑专家，精通智能图像增强和修改。"
            "你的任务是根据用户需求对图片进行智能编辑、增强和美化。"
        ),
        "remove_bg_cloud": (
            "你是一个专业的背景移除专家，精通 AI 抠图技术。"
            "你的任务是精确识别图片主体并移除背景，输出透明背景图片。"
        ),
        "ocr_cloud": (
            "你是一个专业的 OCR 文字识别专家，精通多语言文字检测和识别。"
            "你的任务是识别图片中的文字内容，返回精确的文字和位置信息。"
        ),
    }
    return prompts.get(feature, prompts["ocr_cloud"])


def _build_user_prompt(req: CreateAiImageToolTaskRequest) -> str:
    """根据请求参数构建用户提示词。

    将功能码、输入文件和自定义选项组装为结构化的提示词。

    Args:
        req: 图片 AI 任务创建请求

    Returns:
        结构化的用户提示词文本
    """
    feature_label = req.feature  # 仅用于 prompt 构建，不需要查 DB
    parts = [f"【处理任务】{feature_label}"]

    # 输入文件信息
    if req.input_file_ids:
        parts.append(f"【输入文件】共 {len(req.input_file_ids)} 个文件")
    else:
        parts.append("【输入文件】无")

    # 自定义选项
    if req.options:
        parts.append(f"【处理选项】{json.dumps(req.options, ensure_ascii=False)}")

    return "\n".join(parts)


# ============================================================
# AI 图片处理核心逻辑
# ============================================================


async def create_image_tool_task(
    db: AsyncSession,
    req: CreateAiImageToolTaskRequest,
    ctx: ImageToolContext,
) -> CreatedTaskData:
    """创建并执行高级图片 AI 任务，遵循标准云端 AI 调用链。

    调用链步骤（对齐 MODULE_INTERFACES.md）：
    1. 套餐权限检查（用户套餐是否支持指定的功能码）
    2. 额度预检查（余额是否足够）
    3. 创建任务记录（ai_tasks 表，状态 queued）
    4. 调用 Provider Runtime 执行图片 AI 处理
    5. 写入 Provider 调用日志
    6. 扣除 AI 额度
    7. 更新任务状态为 succeeded 并写入结果

    Args:
        db: 数据库异步会话
        req: 图片 AI 任务创建请求
        ctx: 图片 AI 上下文（用户、设备、请求追踪信息）

    Returns:
        CreatedTaskData（包含 task_id、status、feature、estimated_credits）
    """
    # ---- 步骤 1: 套餐权限检查 ----
    await _check_feature_permission(db, ctx.plan_id, req.feature)

    # ---- 步骤 2: 额度预检查（从 DB 读起步扣点 + 预估最大成本） ----
    min_credits = await _get_min_credits(db, req.feature)
    threshold = await _estimate_threshold(db, req.feature, "image_edit", 2048,
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
    system_prompt = _build_system_prompt(req.feature)
    user_prompt = _build_user_prompt(req)

    provider_result = await _call_provider(
        model="route",
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        feature=req.feature,
        request_id=ctx.request_id,
    )

    # 检查 Provider 调用结果
    if provider_result.status == "failed":
        # Provider 调用失败，写入失败日志，更新任务状态为 failed
        await _insert_provider_log(
            db=db,
            ctx=ctx,
            feature=req.feature,
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
            message=provider_result.error_message or "AI 图片处理服务暂时不可用，请稍后重试",
            status_code=502,
        )

    # ---- 步骤 5: 写入 Provider 调用日志（成功） ----
    actual_credits = await _calculate_deduction(
        db, req.feature,
        provider_result.provider, provider_result.model,
        provider_result.usage,
    )

    provider_call_id = await _insert_provider_log(
        db=db,
        ctx=ctx,
        feature=req.feature,
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
    feature_label = await _get_feature_name(db, req.feature)
    await _consume_credits(
        db=db,
        user_id=ctx.user_id,
        amount=actual_credits,
        source_id=provider_call_id,
        description=f"AI 图片处理 · {feature_label}",
    )

    # ---- 步骤 7: 更新任务为 succeeded，写入结果 ----
    result_files = _normalize_result_files(provider_result)
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
        feature=req.feature,
        estimated_credits=actual_credits,
    )


async def query_image_tool_task(
    db: AsyncSession,
    task_id: str,
    user_id: str,
) -> AiImageToolTaskData:
    """查询高级图片 AI 任务的状态和结果。

    使用 raw SQL 查询 ai_tasks 表（对齐 DATABASE_SCHEMA.md），
    避免 ORM 模型注册冲突。

    Args:
        db: 数据库异步会话
        task_id: 任务 ID（UUID）
        user_id: 用户 ID（用于权限校验）

    Returns:
        AiImageToolTaskData（任务状态和结果）

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
    result_json: Optional[dict] = None
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
            result_json = result_data.get("result_json")

    return AiImageToolTaskData(
        task_id=tid,
        status=status,
        feature=feature,
        result_files=result_files,
        result_json=result_json,
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
    feature: str,
) -> None:
    """检查当前套餐是否支持指定的功能码。

    使用 raw SQL 查询 plans 表的 enabled_features_json 字段，
    避免导入 credits-billing 的 Plan ORM 模型（该模型注册到 Base.metadata）。

    Args:
        db: 数据库异步会话
        plan_id: 用户当前套餐 ID（UUID）
        feature: 要检查的功能码

    Raises:
        AppError: 套餐不存在或不支持此功能
    """
    if not plan_id:
        raise AppError(
            code=ErrorCode.PLAN_REQUIRED,
            message="当前套餐不支持此功能，请升级套餐",
            status_code=403,
        )

    # 检查功能码是否全局启用
    fc_result = await db.execute(
        text("SELECT is_active FROM feature_codes WHERE code = :fcode"),
        {"fcode": feature},
    )
    fc_row = fc_result.fetchone()
    if fc_row is None or not fc_row[0]:
        raise AppError(
            code=ErrorCode.PERMISSION_DENIED,
            message=f"该功能（{feature}）暂未开放",
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
            message="当前套餐不支持此功能，请升级套餐",
            status_code=403,
        )

    # enabled_features_json 在 SQLite 中存储为 TEXT/JSON 字符串
    features = _parse_json_field(row[0])

    # 直接检查子功能码是否启用（每个子功能独立控制）
    feature_enabled = features.get(feature, False)
    if not _is_feature_enabled(feature_enabled):
        raise AppError(
            code=ErrorCode.PERMISSION_DENIED,
            message=f"当前套餐不支持此功能（{feature}），请升级套餐",
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

        # 插入额度账户（按周年计费：从今天起 1 个月）
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
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
    ctx: ImageToolContext,
    req: CreateAiImageToolTaskRequest,
    status: str,
) -> str:
    """在 ai_tasks 表中创建任务记录。

    使用 raw SQL INSERT 直接写入，对齐 DATABASE_SCHEMA.md ai_tasks 表定义。

    Args:
        db: 数据库异步会话
        ctx: 图片 AI 上下文
        req: 创建请求
        status: 任务初始状态

    Returns:
        新创建的任务 ID（UUID）
    """
    task_id = str(uuid.uuid4())
    now = _utcnow()

    # 构造脱敏输入 JSON
    input_data = {
        "feature": req.feature,
        "input_file_ids": req.input_file_ids,
        "options": req.options,
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
            "feat": req.feature,
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
    result_json: Optional[dict] = None,
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
        result_json: 各功能自定义结果数据
    """
    now = _utcnow()
    result_data = {
        "files": result_files,
        "provider": provider,
        "model": model,
        "estimated_cost": estimated_cost,
        "provider_call_id": provider_call_id,
    }
    # 各子功能的自定义结果数据（如 OCR 文本、矢量图层信息等）
    if result_json is not None:
        result_data["result_json"] = result_json

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
    """调用 Provider Runtime 执行图片 AI 处理。

    使用 MockProvider + ProviderRouter 执行调用。
    当前阶段全部使用 Mock Provider。

    Args:
        model: 模型名称
        system_prompt: 系统提示词
        user_prompt: 用户提示词
        feature: 功能码
        request_id: 请求追踪 ID

    Returns:
        Provider 调用结果
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

    router = get_global_router()
    result = await router.call_by_capability(
        request=call_request,
        capability="image_edit",
    )

    return result


async def _insert_provider_log(
    db: AsyncSession,
    ctx: ImageToolContext,
    feature: str,
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
    raw_meta = json.dumps({"feature": feature, "mock": provider == "mock"})

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
            "feat": feature,
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
    """扣除 AI 额度（原子 UPDATE，防止并发超扣）。

    使用 raw SQL 原子更新 credit_accounts 表并写入 credit_ledger 流水。
    对齐 DATABASE_SCHEMA.md 写入边界规则：credit_ledger 由计费服务写入。

    Args:
        db: 数据库异步会话
        user_id: 用户 ID
        amount: 扣除额度（正整数）
        source_id: 来源 ID（provider_call_log.id）
        description: 中文说明

    Raises:
        AppError: 额度不足或账户异常
    """
    if amount <= 0:
        return

    now = _utcnow()
    # 原子 UPDATE：余额 >= amount 时才执行，避免并发超扣
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
        # 更新失败，检查具体原因
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


def _is_feature_enabled(value) -> bool:
    """判断功能开关是否启用。兼容 bool 值和 dict 格式。"""
    if isinstance(value, bool):
        return value
    if isinstance(value, dict):
        return bool(value)
    return False


def _normalize_result_files(provider_result) -> List[dict]:
    """从 Provider 返回中提取规范化文件列表。不 Mock。"""
    if getattr(provider_result, "files", None):
        return provider_result.files
    return []


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


# ============================================================
# DB 驱动定价辅助函数（使用 raw SQL）
# ============================================================


async def _get_min_credits(db: AsyncSession, feature: str) -> int:
    result = await db.execute(
        text("SELECT min_credits FROM feature_pricing WHERE feature_code = :fc"),
        {"fc": feature},
    )
    row = result.fetchone()
    return row[0] if row else 1


async def _get_exchange_rate(db: AsyncSession) -> float:
    result = await db.execute(
        text("SELECT value FROM system_config WHERE key = 'credits_exchange_rate'"),
    )
    row = result.fetchone()
    return float(row[0]) if row else 10.0


async def _get_model_pricing(db: AsyncSession, provider: str, model: str) -> dict:
    result = await db.execute(
        text(
            "SELECT input_price, output_price FROM provider_model_pricing "
            "WHERE provider_name = :pn AND model_name = :mn AND is_active = TRUE"
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
    import math as _math
    min_credits = await _get_min_credits(db, feature)
    pricing = await _get_model_pricing(db, provider, model)
    rate = await _get_exchange_rate(db)
    input_cost = (usage.input_tokens / 1_000_000) * pricing["input_price"]
    output_cost = (usage.output_tokens / 1_000_000) * pricing["output_price"]
    cost_credits = _math.ceil((input_cost + output_cost) * rate)
    return max(min_credits, cost_credits)


async def _estimate_threshold(
    db: AsyncSession, feature: str, capability: str,
    max_tokens: int, prompt_text: str,
) -> int:
    import math as _math
    min_credits = await _get_min_credits(db, feature)
    rate = await _get_exchange_rate(db)
    result = await db.execute(
        text("SELECT MAX(output_price), MAX(input_price) FROM provider_model_pricing WHERE is_active = TRUE"),
    )
    row = result.fetchone()
    output_price = float(row[0]) if row and row[0] is not None else 2.0
    input_price = float(row[1]) if row and row[1] is not None else 1.0
    estimated_input = max(1, int(len(prompt_text) * 1.2))
    max_cost_cny = (estimated_input / 1_000_000) * input_price + (max_tokens / 1_000_000) * output_price
    return max(min_credits, _math.ceil(max_cost_cny * rate))
