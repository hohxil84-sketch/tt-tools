"""
cloud-ai-copy 业务逻辑层。

实现 AI 文案生成的核心业务流程，遵循标准云端 AI 调用链
（对齐 MODULE_INTERFACES.md）：

    API endpoint -> auth/device check -> permission check -> credits precheck
    -> provider-runtime -> provider-call-log -> credits charge
    -> usage event -> unified response

关键规则：
- 不得直接调用 OpenAI、DeepSeek 或其他第三方 AI，必须通过 provider-runtime。
- 客户端不得提交 user_id、provider、model、estimated_cost、credits_charged。
- 跨模块数据访问使用 raw SQL（sqlalchemy.text），避免 ORM 模型重复注册。
  这是与 credits-billing 查询 users 表一致的既有模式。
- Provider 调用通过 provider-runtime 的 MockProvider + ProviderRouter 完成。
"""
from __future__ import annotations

import sys
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple, List

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from cloud.shared import ErrorCode, AppError

from schemas import AiCopyGenerateRequest, AiCopyGenerateData, GenerateContext


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

# 当前时间（UTC）获取函数
_utcnow = lambda: datetime.now(timezone.utc)


# ============================================================
# Prompt 模板构建
# ============================================================


def _build_system_prompt() -> str:
    """构建文案生成的系统提示词。"""
    return (
        "你是一个专业的广告文案撰写专家，精通各类广告文案创作。"
        "你的任务是根据用户提供的产品信息、卖点和场景要求，"
        "生成简洁有力、接地气、符合中文语境的广告文案。"
        "请严格按照用户指定的语气风格和平台要求进行创作。"
    )


def _build_user_prompt(req: AiCopyGenerateRequest) -> str:
    """根据请求参数构建用户提示词。"""
    parts = []

    # 场景标签映射
    scene_labels = {
        "poster": "海报宣传",
        "social_post": "社交媒体帖子",
        "ad_banner": "广告横幅",
        "flyer": "传单/宣传单",
        "slogan": "品牌口号/Slogan",
    }
    scene_label = scene_labels.get(req.scene, req.scene)
    parts.append(f"【场景】{scene_label}")

    # 产品信息
    parts.append(f"【产品/服务】{req.product_name}")

    # 卖点
    if req.selling_points:
        points = "、".join(req.selling_points)
        parts.append(f"【核心卖点】{points}")

    # 目标受众
    if req.target_audience:
        parts.append(f"【目标受众】{req.target_audience}")

    # 语气风格映射
    tone_labels = {
        "direct": "直接有力，简洁明快，直击痛点",
        "professional": "专业正式，用词精准，体现行业权威",
        "friendly": "亲切友好，温暖贴心，拉近距离",
        "urgent": "紧迫感强，强调限时和稀缺性，促使用户行动",
        "elegant": "优雅高级，富有格调，彰显品位",
    }
    tone_desc = tone_labels.get(req.tone, req.tone)
    parts.append(f"【语气风格】{tone_desc}")

    # 投放平台
    if req.platform:
        platform_labels = {
            "offline_poster": "线下海报/传单，适合印刷品阅读",
            "wechat": "微信公众号/朋友圈，适合移动端快速阅读",
            "xiaohongshu": "小红书，适合种草和分享风格",
            "douyin": "抖音，适合短视频口播文案",
        }
        platform_desc = platform_labels.get(req.platform, req.platform)
        parts.append(f"【投放平台】{platform_desc}")

    # 额外要求
    if req.extra_requirements:
        parts.append(f"【额外要求】{req.extra_requirements}")

    # 输出格式要求
    parts.append("")
    parts.append("请生成一条广告文案作为主文案，再生成一条备选文案变体。")

    return "\n".join(parts)


# ============================================================
# AI 文案生成核心逻辑
# ============================================================


async def generate_ai_copy(
    db: AsyncSession,
    req: AiCopyGenerateRequest,
    ctx: GenerateContext,
) -> AiCopyGenerateData:
    """执行 AI 文案生成，遵循标准云端 AI 调用链。

    调用链步骤（对齐 MODULE_INTERFACES.md）：
    1. 套餐权限检查（用户套餐是否支持 ai_copy_cloud）
    2. 额度预检查（余额是否足够）
    3. 调用 Provider Runtime 生成文案
    4. 写入 Provider 调用日志
    5. 扣除 AI 额度
    6. 返回生成结果
    """
    feature = "ai_copy_cloud"

    # ---- 步骤 1: 套餐权限检查 ----
    await _check_feature_permission(db, ctx.plan_id)

    # ---- 步骤 2: 额度预检查（从 DB 读起步扣点 + 按 max_tokens 预估） ----
    min_credits = await _get_min_credits(db, feature)
    max_tokens = 2048  # 当前固定值，后续可通过请求参数传入
    threshold = await _estimate_threshold(db, feature, "text", max_tokens,
        _build_user_prompt(req))
    await _check_credits_balance(db, ctx.user_id, threshold)

    # ---- 步骤 3: 构建 prompt 并调用 Provider Runtime ----
    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(req)

    provider_result = await _call_provider(
        model="route",  # router 自动选择
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        feature=feature,
        request_id=ctx.request_id,
    )

    # 检查 Provider 调用结果
    if provider_result.status == "failed":
        # Provider 调用失败，写入失败日志但不扣费
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
        raise AppError(
            code=provider_result.error_code or ErrorCode.PROVIDER_UNAVAILABLE,
            message=provider_result.error_message or "AI 服务暂时不可用，请稍后重试",
            status_code=502,
        )

    # ---- 步骤 4: 写入 Provider 调用日志（成功） ----
    # 先计算实际扣费（从 DB 定价表独立计算，不依赖 cost.py 硬编码）
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
        estimated_latency_ms=None,
    )

    # ---- 步骤 5: 扣除 AI 额度 ----
    await _consume_credits(
        db=db,
        user_id=ctx.user_id,
        amount=actual_credits,
        source_id=provider_call_id,
        description=f"AI 文案生成 · {req.scene} · {req.product_name}",
    )

    # ---- 步骤 6: 解析生成结果并返回 ----
    text, variants = _parse_generated_text(provider_result.text)

    return AiCopyGenerateData(
        feature=feature,
        text=text,
        variants=variants,
        provider=provider_result.provider,
        model=provider_result.model,
        estimated_cost=provider_result.estimated_cost,
        credits_charged=actual_credits,
        provider_call_id=provider_call_id,
    )


# ============================================================
# 调用链辅助函数（全部使用 raw SQL，避免 ORM 跨模块冲突）
# ============================================================


async def _check_feature_permission(
    db: AsyncSession,
    plan_id: Optional[str],
) -> None:
    """检查当前套餐是否支持 ai_copy_cloud 功能。

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
            message="当前套餐不支持 AI 文案生成功能，请升级套餐",
            status_code=403,
        )

    # 检查功能码是否全局启用
    fc_result = await db.execute(
        text("SELECT is_active FROM feature_codes WHERE code = :fcode"),
        {"fcode": "ai_copy_cloud"},
    )
    fc_row = fc_result.fetchone()
    if fc_row is None or not fc_row[0]:
        raise AppError(
            code=ErrorCode.PERMISSION_DENIED,
            message="AI 文案生成功能暂未开放",
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
            message="当前套餐不支持 AI 文案生成功能，请升级套餐",
            status_code=403,
        )

    # enabled_features_json 在 SQLite 中存储为 TEXT/JSON 字符串
    features_raw = row[0]
    if isinstance(features_raw, str):
        import json
        features = json.loads(features_raw)
    elif isinstance(features_raw, dict):
        features = features_raw
    else:
        features = {}

    ai_copy_enabled = features.get("ai_copy_cloud", False)

    if isinstance(ai_copy_enabled, dict):
        if not ai_copy_enabled:
            raise AppError(
                code=ErrorCode.PERMISSION_DENIED,
                message="当前套餐不支持 AI 文案生成功能，请升级套餐",
                status_code=403,
            )
    elif not ai_copy_enabled:
        raise AppError(
            code=ErrorCode.PERMISSION_DENIED,
            message="当前套餐不支持 AI 文案生成功能，请升级套餐",
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

        monthly_grant = 0
        if plan_id:
            plan_result = await db.execute(
                text("SELECT monthly_grant FROM plans WHERE id = :pid AND status = 'active'"),
                {"pid": plan_id},
            )
            plan_row = plan_result.fetchone()
            monthly_grant = plan_row[0] if plan_row else 0

        account_id = str(uuid.uuid4())
        now = _utcnow()
        balance = monthly_grant

        # 计费周期：从创建日起算，满一个月
        import calendar as _cal
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

        # 插入额度账户
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


async def _call_provider(
    model: str,
    system_prompt: str,
    user_prompt: str,
    feature: str,
    request_id: str,
):
    """调用 Provider Runtime 生成文案。

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

    router = get_global_router()
    result = await router.call_by_capability(
        request=call_request,
        capability="text",
    )

    return result


async def _insert_provider_log(
    db: AsyncSession,
    ctx: GenerateContext,
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
    estimated_latency_ms: Optional[int] = None,
) -> str:
    """写入 Provider 调用日志到 provider_call_log 表。

    使用 raw SQL INSERT 直接写入，避免导入 provider-log 的 ORM 模型。
    返回新写入的日志 UUID（供后续扣费关联使用）。

    对齐 DATABASE_SCHEMA.md provider_call_log 表定义和写入边界规则：
    provider_call_log 由 Provider Runtime 或其封装服务写入。
    """
    import json

    log_id = str(uuid.uuid4())
    raw_meta = json.dumps({"feature": "ai_copy_cloud", "mock": provider == "mock"})

    await db.execute(
        text(
            "INSERT INTO provider_call_log "
            "(id, request_id, user_id, device_id, feature, provider, model, "
            " status, error_code, input_tokens, output_tokens, total_tokens, "
            " reasoning_tokens, cached_tokens, image_count, estimated_cost, "
            " credits_charged, latency_ms, raw_usage_json, raw_meta_json, "
            " estimated_credits_before, estimated_latency_ms, created_at) "
            "VALUES (:id, :rid, :uid, :did, :feat, :prov, :mod, "
            " :st, :ec, :it, :ot, :tt, :rt, :ct, :ic, :ecost, "
            " :cc, :lat, :ruj, :rmj, :ecb, :elm, :now)"
        ),
        {
            "id": log_id,
            "rid": ctx.request_id,
            "uid": ctx.user_id,
            "did": ctx.device_id,
            "feat": "ai_copy_cloud",
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
            "elm": estimated_latency_ms,
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
    """扣除 AI 额度（原子操作，防并发超扣）。

    使用 raw SQL 原子更新：UPDATE ... SET balance = balance - :amt WHERE balance >= :amt，
    通过 rowcount 判断是否扣费成功，避免 TOCTOU 竞态条件。

    Args:
        db: 数据库异步会话
        user_id: 用户 ID
        amount: 扣除额度（正整数）
        source_id: 来源 ID（provider_call_log.id）
        description: 中文说明

    Raises:
        AppError: 额度不足或账户不存在
    """
    if amount <= 0:
        return  # 0 或负数不扣

    now = _utcnow()

    # 原子扣费：UPDATE WHERE balance >= amount，通过 rowcount 判断是否成功
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
        # 可能是账户不存在、已冻结、或余额不足；区分原因给出明确错误
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


def _parse_generated_text(raw_text: str) -> Tuple[str, List[str]]:
    """解析 Provider 返回的文本，提取主文案和变体。

    将原始文本按段落分割，第一段作为主文案，其余作为变体列表。

    Args:
        raw_text: Provider 生成的原始文本

    Returns:
        (主文案, 变体列表)
    """
    if not raw_text or not raw_text.strip():
        return "", []

    # 按双换行（段落）分割
    paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]

    if not paragraphs:
        # 按单换行分割
        lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
        if not lines:
            return raw_text.strip(), []
        text = lines[0]
        variants = lines[1:] if len(lines) > 1 else []
        return text, variants

    text = paragraphs[0]
    variants = paragraphs[1:] if len(paragraphs) > 1 else []

    return text, variants


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


async def _get_latency_estimate(
    db: AsyncSession, provider: str, model: str, capability: str
) -> dict:
    """从 provider_latency_stats 表查预估耗时。"""
    result = await db.execute(
        text(
            "SELECT p50_latency_ms, p95_latency_ms, sample_count "
            "FROM provider_latency_stats "
            "WHERE provider_name = :pn AND model_name = :mn AND capability = :cap"
        ),
        {"pn": provider, "mn": model, "cap": capability},
    )
    row = result.fetchone()
    if row is not None:
        p50, p95, cnt = row[0], row[1], row[2]
        return {
            "p50_ms": p50, "p95_ms": p95,
            "display": f"约 {p50 // 1000}-{p95 // 1000} 秒",
            "sample_count": cnt,
        }
    return {"p50_ms": 0, "p95_ms": 0, "display": "暂无耗时数据", "sample_count": 0}


async def _calculate_deduction(
    db: AsyncSession,
    feature: str,
    provider: str,
    model: str,
    usage,  # ProviderUsage
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
    db: AsyncSession,
    feature: str,
    capability: str,
    max_tokens: int,
    prompt_text: str,
) -> int:
    """预估最大扣点（预检查用）。按最坏情况（输出用满 max_tokens）计算。"""
    import math as _math

    min_credits = await _get_min_credits(db, feature)
    rate = await _get_exchange_rate(db)

    # 取最便宜活跃模型定价作为预估基准（router 默认选 cheap tier）
    result = await db.execute(
        text(
            "SELECT MIN(output_price), MIN(input_price) FROM provider_model_pricing "
            "WHERE is_active = TRUE AND model_name != '__default__'"
        ),
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
