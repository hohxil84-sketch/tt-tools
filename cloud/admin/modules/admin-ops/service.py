"""
admin-ops 业务逻辑层。

提供后台运维管理的核心逻辑：
- Provider 调用日志：跨用户列表查询、详情查询
- 成本统计：聚合统计（总调用数、总 token、总成本、总扣费）
- 风控日志：列表查询、详情查询
- 功能开关：按套餐查询、合并更新

模型复用策略：
本模块定义 RiskLog ORM 模型，并通过 importlib 加载已有模块的模型：
- ProviderCallLog ← cloud/modules/provider-log/models.py
- Plan ← cloud/modules/credits-billing/models.py
- User ← cloud/admin/modules/admin-users/models.py

调用方（conftest）需要预先将模型类注册到 sys.modules 的别名键下，
service.py 通过 _get_model() 惰性加载。

成本统计不写入任何数据，仅为只读聚合查询。
功能开关直接操作 plans 表的 enabled_features_json 字段（JSON 合并更新）。
"""
from __future__ import annotations

import importlib.util
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func, and_, cast, Integer, Numeric
from sqlalchemy.ext.asyncio import AsyncSession

from cloud.shared import ErrorCode, AppError
from cloud.shared.database import Base

from models import RiskLog

from schemas import (
    AdminProviderCallLogItem,
    AdminProviderCallLogDetail,
    AdminProviderCallLogListData,
    CostBreakdownItem,
    CostStatsData,
    RiskLogItem,
    RiskLogDetail,
    RiskLogListData,
    PlanFeatureFlagsItem,
    FeatureFlagsListData,
)

# ============================================================
# 分页常量
# ============================================================

MAX_LIMIT = 100

# ============================================================
# 跨模块模型加载（惰性加载 + 缓存）
# ============================================================

# 缓存的模型类引用
_ProviderCallLog = None
_Plan = None
_User = None
_FeatureCode = None
_Device = None


def _get_project_root() -> str:
    """获取项目根目录的绝对路径。

    从当前文件向上：admin-ops → modules → admin → cloud → TT Tools
    """
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
    )


def _import_model_file(module_dir_parts: list[str], module_dir_name: str,
                       module_file: str, alias: str):
    """通过 importlib 按文件路径加载模块。

    Args:
        module_dir_parts: 模块目录路径段列表（相对于项目根目录）
        module_dir_name: 模块目录名（用于 sys.path 插入）
        module_file: 文件名（如 models、service）
        alias: 在 sys.modules 中注册的别名

    Returns:
        加载的模块对象
    """
    root = _get_project_root()
    dir_path = os.path.join(root, *module_dir_parts)
    file_path = os.path.join(dir_path, f"{module_file}.py")

    # 临时将目录加入 sys.path
    _orig_path = list(sys.path)
    if dir_path in sys.path:
        sys.path.remove(dir_path)
    sys.path.insert(0, dir_path)

    # 保存可能冲突的模块
    _saved = {}
    for _key in ("models", "service", "schemas", "router"):
        if _key in sys.modules:
            _saved[_key] = sys.modules.pop(_key)

    try:
        spec = importlib.util.spec_from_file_location(alias, file_path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[alias] = mod
        spec.loader.exec_module(mod)
        return mod
    finally:
        # 恢复 sys.modules
        for _key in ("models", "service", "schemas", "router"):
            sys.modules.pop(_key, None)
        for _key, _val in _saved.items():
            sys.modules[_key] = _val
        # 恢复 sys.path
        sys.path.clear()
        sys.path.extend(_orig_path)


def _find_model_class_in_modules(table_name: str, class_name: str):
    """在 sys.modules 中搜索已注册的 ORM 模型类。

    当表已在 Base.metadata 中注册但无法通过预期别名找到时使用。
    遍历 sys.modules 查找具有指定类名且 __tablename__ 匹配的类。

    Args:
        table_name: 数据库表名（如 feature_codes、plans）
        class_name: 模型类名（如 FeatureCode、Plan）

    Returns:
        找到的 ORM 模型类，找不到返回 None
    """
    for mod in sys.modules.values():
        cls = getattr(mod, class_name, None)
        if cls is not None and getattr(cls, "__tablename__", "") == table_name:
            return cls
    return None


def _safe_load_model(table_name: str, class_name: str, alias: str,
                      module_dir_parts: list[str], module_dir_name: str):
    """安全加载跨模块 ORM 模型类，避免重复注册表。

    加载顺序：
    1. 从 sys.modules 别名获取
    2. 从 Base.metadata 确认表已注册 → 搜索 sys.modules 获取类
    3. 回退到 importlib 文件加载

    Args:
        table_name: 数据库表名
        class_name: 模型类名
        alias: sys.modules 别名
        module_dir_parts: 模块目录路径段列表
        module_dir_name: 模块目录名

    Returns:
        ORM 模型类
    """
    # 1) 从预期别名获取
    if alias in sys.modules:
        return getattr(sys.modules[alias], class_name)

    # 2) 表已在 Base.metadata 中注册（app-shell 启动时已加载）→ 全局搜索
    if table_name in Base.metadata.tables:
        cls = _find_model_class_in_modules(table_name, class_name)
        if cls is not None:
            return cls

    # 3) 回退：importlib 文件加载
    mod = _import_model_file(module_dir_parts, module_dir_name, "models", alias)
    return getattr(mod, class_name)


def _load_module_models():
    """惰性加载所有跨模块模型类引用。

    预期调用方（conftest）已将模型类注册到 sys.modules 的别名键下：
    - "provider_log_models" → provider-log 的 models 模块
    - "credits_billing_models" → credits-billing 的 models 模块
    - "admin_users_models" → admin-users 的 models 模块
    - "admin_feature_codes_models" → admin-feature-codes 的 models 模块

    如果 sys.modules 中不存在，则回退到文件级 importlib 加载。
    如果表已在 Base.metadata 中注册（被 app-shell 启动时加载），则从已注册元数据中获取类。
    """
    global _ProviderCallLog, _Plan, _User, _FeatureCode, _Device

    if _ProviderCallLog is not None:
        return  # 已加载

    # 加载 ProviderCallLog（provider-log 模型）
    _ProviderCallLog = _safe_load_model(
        "provider_call_log", "ProviderCallLog", "provider_log_models",
        ["cloud", "modules", "provider-log"], "provider-log",
    )

    # 加载 Plan（credits-billing 模型）
    _Plan = _safe_load_model(
        "plans", "Plan", "credits_billing_models",
        ["cloud", "modules", "credits-billing"], "credits-billing",
    )

    # 加载 User 和 Device（admin-users 模型）
    if "admin_users_models" in sys.modules:
        _User = sys.modules["admin_users_models"].UserAdmin
        _Device = sys.modules["admin_users_models"].DeviceAdmin

    # 加载 FeatureCode（admin-feature-codes 模型）
    _FeatureCode = _safe_load_model(
        "feature_codes", "FeatureCode", "admin_feature_codes_models",
        ["cloud", "admin", "modules", "admin-feature-codes"], "admin-feature-codes",
    )


# ============================================================
# Provider 调用日志
# ============================================================


async def list_provider_call_logs(
    db: AsyncSession,
    limit: int = 20,
    offset: int = 0,
    user_id: Optional[str] = None,
    feature: Optional[str] = None,
    provider: Optional[str] = None,
    status: Optional[str] = None,
) -> AdminProviderCallLogListData:
    """查询全部 Provider 调用日志（管理员视角，跨用户）。

    支持按 user_id、feature、provider、status 多条件筛选和分页。
    关联 users 表获取用户账号信息。
    不返回 raw_usage_json、raw_meta_json 等隐私字段。

    Args:
        db: 数据库异步会话
        limit: 每页条数
        offset: 偏移量
        user_id: 按用户 ID 筛选
        feature: 按功能码筛选
        provider: 按 Provider 名称筛选
        status: 按调用状态筛选

    Returns:
        AdminProviderCallLogListData 调用日志列表及分页信息
    """
    _load_module_models()

    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)

    # 构建筛选条件
    conditions = []
    if user_id:
        conditions.append(_ProviderCallLog.user_id == user_id)
    if feature:
        conditions.append(_ProviderCallLog.feature == feature)
    if provider:
        conditions.append(_ProviderCallLog.provider == provider)
    if status:
        conditions.append(_ProviderCallLog.status == status)

    # 查询总数
    count_query = select(func.count()).select_from(_ProviderCallLog)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # 查询分页数据（按创建时间倒序）
    query = (
        select(_ProviderCallLog)
        .where(and_(*conditions) if conditions else True)
        .order_by(_ProviderCallLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    logs = result.scalars().all()

    # 批量查询关联用户账号（避免 N+1 查询）
    user_ids = list({log.user_id for log in logs})
    user_map = await _get_user_account_map(db, user_ids)

    # 批量查询功能码中文名
    feature_codes_set = list({log.feature for log in logs if log.feature})
    feature_name_map = await _get_feature_name_map(db, feature_codes_set)

    items = [
        AdminProviderCallLogItem(
            id=log.id,
            request_id=log.request_id,
            user_id=log.user_id,
            user_account=user_map.get(log.user_id),
            feature=log.feature,
            feature_name=feature_name_map.get(log.feature),
            provider=log.provider,
            model=log.model,
            status=log.status,
            error_code=log.error_code,
            input_tokens=log.input_tokens,
            output_tokens=log.output_tokens,
            total_tokens=log.total_tokens,
            estimated_cost=float(log.estimated_cost) if log.estimated_cost else 0.0,
            credits_charged=log.credits_charged,
            latency_ms=log.latency_ms,
            created_at=log.created_at,
        )
        for log in logs
    ]

    return AdminProviderCallLogListData(
        items=items, total=total, limit=limit, offset=offset
    )


async def get_provider_call_log_detail(
    db: AsyncSession, log_id: str
) -> AdminProviderCallLogDetail:
    """查询单条 Provider 调用日志详情（管理员视角）。

    Args:
        db: 数据库异步会话
        log_id: 调用日志 ID（UUID）

    Returns:
        AdminProviderCallLogDetail 日志详情（含用户信息）

    Raises:
        AppError: 日志不存在时抛出 404
    """
    _load_module_models()

    result = await db.execute(
        select(_ProviderCallLog).where(_ProviderCallLog.id == log_id)
    )
    log = result.scalar_one_or_none()

    if log is None:
        raise AppError(
            code="PROVIDER_CALL_LOG_NOT_FOUND",
            message=f"调用日志 {log_id} 不存在",
            status_code=404,
        )

    # 查询关联用户信息
    user_account = None
    user_display_name = None
    if _User is not None:
        user_result = await db.execute(
            select(_User.account, _User.display_name).where(
                _User.id == log.user_id
            )
        )
        user_row = user_result.one_or_none()
        if user_row:
            user_account = user_row[0]
            user_display_name = user_row[1]

    # 查询关联功能码中文名
    feature_name = None
    if log.feature:
        feature_name_map = await _get_feature_name_map(db, [log.feature])
        feature_name = feature_name_map.get(log.feature)

    return AdminProviderCallLogDetail(
        id=log.id,
        request_id=log.request_id,
        user_id=log.user_id,
        user_account=user_account,
        user_display_name=user_display_name,
        feature=log.feature,
        feature_name=feature_name,
        provider=log.provider,
        model=log.model,
        status=log.status,
        error_code=log.error_code,
        input_tokens=log.input_tokens,
        output_tokens=log.output_tokens,
        total_tokens=log.total_tokens,
        estimated_cost=float(log.estimated_cost) if log.estimated_cost else 0.0,
        credits_charged=log.credits_charged,
        latency_ms=log.latency_ms,
        created_at=log.created_at,
    )


# ============================================================
# 成本统计
# ============================================================


async def get_cost_stats(db: AsyncSession) -> CostStatsData:
    """获取成本/用量聚合统计数据。

    从 provider_call_log 表聚合全局统计，并按功能码和 Provider 细分。
    纯只读操作，不写入任何数据。

    Args:
        db: 数据库异步会话

    Returns:
        CostStatsData 聚合统计数据
    """
    _load_module_models()

    # 全局聚合统计：总调用数、总 token、总成本、总扣费
    global_result = await db.execute(
        select(
            func.count().label("total_calls"),
            func.sum(_ProviderCallLog.total_tokens).label("total_tokens"),
            func.sum(_ProviderCallLog.estimated_cost).label("total_cost"),
            func.sum(_ProviderCallLog.credits_charged).label("total_credits"),
        )
    )
    global_row = global_result.one()

    total_calls = global_row[0] if global_row[0] is not None else 0
    total_tokens = global_row[1] if global_row[1] is not None else 0
    total_cost = (
        float(global_row[2]) if global_row[2] is not None else 0.0
    )
    total_credits = global_row[3] if global_row[3] is not None else 0

    # 按功能码分组统计
    feature_result = await db.execute(
        select(
            _ProviderCallLog.feature.label("key"),
            func.count().label("calls"),
            func.sum(_ProviderCallLog.total_tokens).label("total_tokens"),
            func.sum(_ProviderCallLog.estimated_cost).label("total_cost"),
            func.sum(_ProviderCallLog.credits_charged).label("total_credits"),
        )
        .group_by(_ProviderCallLog.feature)
        .order_by(func.count().desc())
    )
    feature_rows = feature_result.all()

    # 批量查询功能码中文名
    feature_keys = [row[0] for row in feature_rows if row[0]]
    feature_name_map = await _get_feature_name_map(db, feature_keys)

    by_feature = [
        CostBreakdownItem(
            key=row[0] or "unknown",
            key_name=feature_name_map.get(row[0]),
            calls=row[1],
            total_tokens=row[2] if row[2] is not None else 0,
            total_cost=float(row[3]) if row[3] is not None else 0.0,
            total_credits=row[4] if row[4] is not None else 0,
        )
        for row in feature_rows
    ]

    # 按 Provider 分组统计
    provider_result = await db.execute(
        select(
            _ProviderCallLog.provider.label("key"),
            func.count().label("calls"),
            func.sum(_ProviderCallLog.total_tokens).label("total_tokens"),
            func.sum(_ProviderCallLog.estimated_cost).label("total_cost"),
            func.sum(_ProviderCallLog.credits_charged).label("total_credits"),
        )
        .group_by(_ProviderCallLog.provider)
        .order_by(func.count().desc())
    )
    provider_rows = provider_result.all()

    by_provider = [
        CostBreakdownItem(
            key=row[0] or "unknown",
            calls=row[1],
            total_tokens=row[2] if row[2] is not None else 0,
            total_cost=float(row[3]) if row[3] is not None else 0.0,
            total_credits=row[4] if row[4] is not None else 0,
        )
        for row in provider_rows
    ]

    return CostStatsData(
        total_calls=total_calls,
        total_tokens=total_tokens,
        total_cost=total_cost,
        total_credits_charged=total_credits,
        by_feature=by_feature,
        by_provider=by_provider,
    )


# ============================================================
# 风控日志
# ============================================================


async def list_risk_logs(
    db: AsyncSession,
    limit: int = 20,
    offset: int = 0,
    user_id: Optional[str] = None,
    risk_type: Optional[str] = None,
    severity: Optional[str] = None,
) -> RiskLogListData:
    """查询风控日志列表。

    支持按 user_id、risk_type、severity 多条件筛选和分页。
    关联 users 表获取用户账号。

    Args:
        db: 数据库异步会话
        limit: 每页条数
        offset: 偏移量
        user_id: 按用户 ID 筛选
        risk_type: 按风险类型筛选
        severity: 按严重程度筛选

    Returns:
        RiskLogListData 风控日志列表及分页信息
    """
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)

    # 构建筛选条件
    conditions = []
    if user_id:
        conditions.append(RiskLog.user_id == user_id)
    if risk_type:
        conditions.append(RiskLog.risk_type == risk_type)
    if severity:
        conditions.append(RiskLog.severity == severity)

    # 查询总数
    count_query = select(func.count()).select_from(RiskLog)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # 查询分页数据（按创建时间倒序）
    query = (
        select(RiskLog)
        .where(and_(*conditions) if conditions else True)
        .order_by(RiskLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    logs = result.scalars().all()

    # 批量查询关联用户账号（需要 _User 模型）
    user_map = {}
    if _User is not None:
        user_ids = list({log.user_id for log in logs if log.user_id})
        user_map = await _get_user_account_map(db, user_ids)

    # 批量查询关联设备名称
    device_ids = list({log.device_id for log in logs if log.device_id})
    device_name_map = await _get_device_name_map(db, device_ids)

    items = [
        RiskLogItem(
            id=log.id,
            user_id=log.user_id,
            user_account=user_map.get(log.user_id) if log.user_id else None,
            device_id=log.device_id,
            device_name=device_name_map.get(log.device_id) if log.device_id else None,
            risk_type=log.risk_type,
            severity=log.severity,
            created_at=log.created_at,
        )
        for log in logs
    ]

    return RiskLogListData(items=items, total=total, limit=limit, offset=offset)


async def get_risk_log_detail(db: AsyncSession, log_id: str) -> RiskLogDetail:
    """查询风控日志详情。

    Args:
        db: 数据库异步会话
        log_id: 风控日志 ID（UUID）

    Returns:
        RiskLogDetail 日志详情（含用户信息和脱敏详情）

    Raises:
        AppError: 日志不存在时抛出 404
    """
    result = await db.execute(select(RiskLog).where(RiskLog.id == log_id))
    log = result.scalar_one_or_none()

    if log is None:
        raise AppError(
            code="RISK_LOG_NOT_FOUND",
            message=f"风控日志 {log_id} 不存在",
            status_code=404,
        )

    # 查询关联用户信息（需要 _User 模型）
    user_account = None
    user_display_name = None
    if log.user_id and _User is not None:
        user_result = await db.execute(
            select(_User.account, _User.display_name).where(
                _User.id == log.user_id
            )
        )
        user_row = user_result.one_or_none()
        if user_row:
            user_account = user_row[0]
            user_display_name = user_row[1]

    # 查询关联设备名称
    device_name = None
    if log.device_id:
        device_name_map = await _get_device_name_map(db, [log.device_id])
        device_name = device_name_map.get(log.device_id)

    return RiskLogDetail(
        id=log.id,
        user_id=log.user_id,
        user_account=user_account,
        user_display_name=user_display_name,
        device_id=log.device_id,
        device_name=device_name,
        risk_type=log.risk_type,
        severity=log.severity,
        details_json=log.details_json or {},
        created_at=log.created_at,
    )


# ============================================================
# 功能开关
# ============================================================


async def get_feature_flags(
    db: AsyncSession, plan_id: Optional[str] = None
) -> FeatureFlagsListData:
    """查询各套餐的功能开关配置。

    Args:
        db: 数据库异步会话
        plan_id: 按套餐 ID 筛选（可选，不传返回所有套餐）

    Returns:
        FeatureFlagsListData 各套餐功能开关配置列表
    """
    _load_module_models()

    conditions = []
    if plan_id:
        conditions.append(_Plan.id == plan_id)

    query = (
        select(_Plan)
        .where(and_(*conditions) if conditions else True)
        .order_by(_Plan.created_at)
    )
    result = await db.execute(query)
    plans = result.scalars().all()

    items = [
        PlanFeatureFlagsItem(
            plan_id=p.id,
            plan_name=p.name,
            enabled_features_json=p.enabled_features_json or {},
            plan_status=p.status,
        )
        for p in plans
    ]

    return FeatureFlagsListData(items=items)


async def update_feature_flags(
    db: AsyncSession,
    plan_id: str,
    enabled_features_json: dict,
) -> PlanFeatureFlagsItem:
    """更新指定套餐的功能开关配置（合并更新）。

    只更新传入的 key，未传入的 key 保持原值不变。
    例如：现有 {"a": true, "b": false}，传入 {"b": true, "c": true}
    结果：{"a": true, "b": true, "c": true}

    Args:
        db: 数据库异步会话
        plan_id: 套餐 ID（UUID）
        enabled_features_json: 要更新的功能开关配置（合并到现有配置）

    Returns:
        PlanFeatureFlagsItem 更新后的配置

    Raises:
        AppError: 套餐不存在时抛出 404
    """
    _load_module_models()

    result = await db.execute(select(_Plan).where(_Plan.id == plan_id))
    plan = result.scalar_one_or_none()

    if plan is None:
        raise AppError(
            code="PLAN_NOT_FOUND",
            message=f"套餐 {plan_id} 不存在",
            status_code=404,
        )

    # 合并更新：以现有配置为基础，用传入的 key 覆盖
    current_features = dict(plan.enabled_features_json or {})
    current_features.update(enabled_features_json)
    plan.enabled_features_json = current_features
    plan.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.flush()

    return PlanFeatureFlagsItem(
        plan_id=plan.id,
        plan_name=plan.name,
        enabled_features_json=plan.enabled_features_json or {},
        plan_status=plan.status,
    )


# ============================================================
# 内部辅助函数
# ============================================================


async def _get_user_account_map(
    db: AsyncSession, user_ids: list[str]
) -> dict[str, Optional[str]]:
    """批量查询用户 ID → 账号的映射，避免 N+1 查询。

    Args:
        db: 数据库异步会话
        user_ids: 用户 ID 列表

    Returns:
        dict: user_id → user_account 映射
    """
    if not user_ids or _User is None:
        return {}

    result = await db.execute(
        select(_User.id, _User.account).where(_User.id.in_(user_ids))
    )
    rows = result.all()
    return {row[0]: row[1] for row in rows}


async def _get_feature_name_map(
    db: AsyncSession, feature_codes: list[str]
) -> dict[str, Optional[str]]:
    """批量查询功能码 → 中文名称的映射，避免 N+1 查询。

    Args:
        db: 数据库异步会话
        feature_codes: 功能码字符串列表

    Returns:
        dict: feature_code → feature_name 映射
    """
    if not feature_codes or _FeatureCode is None:
        return {}

    result = await db.execute(
        select(_FeatureCode.code, _FeatureCode.name).where(
            _FeatureCode.code.in_(feature_codes)
        )
    )
    rows = result.all()
    return {row[0]: row[1] for row in rows}


async def _get_device_name_map(
    db: AsyncSession, device_ids: list[str]
) -> dict[str, Optional[str]]:
    """批量查询设备 ID → 设备名称的映射，避免 N+1 查询。

    Args:
        db: 数据库异步会话
        device_ids: 设备 ID 列表

    Returns:
        dict: device_id → device_name 映射
    """
    if not device_ids or _Device is None:
        return {}

    result = await db.execute(
        select(_Device.id, _Device.device_name).where(
            _Device.id.in_(device_ids)
        )
    )
    rows = result.all()
    return {row[0]: row[1] for row in rows}
