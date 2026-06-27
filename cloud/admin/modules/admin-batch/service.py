"""
admin-batch 业务逻辑层。
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from schemas import BatchStatusRequest, BatchAdjustRequest, BatchResult, BatchResultItem


async def batch_update_user_status(
    db: AsyncSession, req: BatchStatusRequest,
) -> BatchResult:
    """批量修改用户状态。"""
    results = []
    succeeded = 0
    now_utc = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).replace(tzinfo=None)

    for user_id in req.ids:
        try:
            result = await db.execute(
                text("SELECT id FROM users WHERE id = :uid"), {"uid": user_id}
            )
            if result.first() is None:
                results.append(BatchResultItem(id=user_id, success=False, message="用户不存在"))
                continue

            await db.execute(
                text("UPDATE users SET status = :status, updated_at = :now WHERE id = :uid"),
                {"status": req.status, "now": now_utc, "uid": user_id},
            )
            results.append(BatchResultItem(id=user_id, success=True))
            succeeded += 1
        except Exception as e:
            results.append(BatchResultItem(id=user_id, success=False, message=str(e)))

    await db.flush()
    return BatchResult(total=len(req.ids), succeeded=succeeded,
                       failed=len(req.ids) - succeeded, results=results)


async def batch_adjust_credits(
    db: AsyncSession, req: BatchAdjustRequest,
) -> BatchResult:
    """批量调整额度。"""
    from datetime import datetime, timezone
    import uuid as _uuid

    results = []
    succeeded = 0
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    for user_id in req.user_ids:
        try:
            # 查询用户
            user_result = await db.execute(
                text("SELECT id FROM users WHERE id = :uid"), {"uid": user_id}
            )
            if user_result.first() is None:
                results.append(BatchResultItem(id=user_id, success=False, message="用户不存在"))
                continue

            # 查询或创建额度账户
            acct_result = await db.execute(
                text("SELECT id, balance FROM credit_accounts WHERE user_id = :uid"),
                {"uid": user_id},
            )
            acct = acct_result.first()
            if acct is None:
                # 创建新账户
                acct_id = str(_uuid.uuid4())
                await db.execute(
                    text("INSERT INTO credit_accounts (id, user_id, balance, plan_code, status, created_at, updated_at) "
                         "VALUES (:id, :uid, 0, 'free', 'active', :now, :now)"),
                    {"id": acct_id, "uid": user_id, "now": now_utc},
                )
                current_balance = 0
                account_id = acct_id
            else:
                account_id, current_balance = acct[0], acct[1]

            new_balance = current_balance + req.amount
            if new_balance < 0:
                results.append(BatchResultItem(
                    id=user_id, success=False,
                    message=f"余额不足：当前 {current_balance}，调整 {req.amount}"
                ))
                continue

            await db.execute(
                text("UPDATE credit_accounts SET balance = :bal, updated_at = :now WHERE id = :aid"),
                {"bal": new_balance, "now": now_utc, "aid": account_id},
            )
            # 写入流水
            ledger_id = str(_uuid.uuid4())
            change_type = "grant" if req.amount > 0 else "adjust"
            await db.execute(
                text("INSERT INTO credit_ledger (id, user_id, account_id, change_type, amount, balance_after, source_type, description, created_at) "
                     "VALUES (:id, :uid, :aid, :ctype, :amt, :bal, 'admin', :desc, :now)"),
                {"id": ledger_id, "uid": user_id, "aid": account_id,
                 "ctype": change_type, "amt": req.amount, "bal": new_balance,
                 "desc": req.description or f"批量调整额度 {req.amount}", "now": now_utc},
            )
            results.append(BatchResultItem(id=user_id, success=True))
            succeeded += 1
        except Exception as e:
            results.append(BatchResultItem(id=user_id, success=False, message=str(e)))

    await db.flush()
    return BatchResult(total=len(req.user_ids), succeeded=succeeded,
                       failed=len(req.user_ids) - succeeded, results=results)


async def batch_cancel_orders(
    db: AsyncSession, ids: list[str],
) -> BatchResult:
    """批量取消订单。"""
    from datetime import datetime, timezone

    results = []
    succeeded = 0
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    for order_id in ids:
        try:
            result = await db.execute(
                text("SELECT id, status FROM orders WHERE id = :oid"), {"oid": order_id}
            )
            row = result.first()
            if row is None:
                results.append(BatchResultItem(id=order_id, success=False, message="订单不存在"))
                continue
            if row[1] != "pending":
                results.append(BatchResultItem(id=order_id, success=False, message=f"状态为 {row[1]}，不可取消"))
                continue

            await db.execute(
                text("UPDATE orders SET status = 'closed', updated_at = :now WHERE id = :oid"),
                {"now": now_utc, "oid": order_id},
            )
            results.append(BatchResultItem(id=order_id, success=True))
            succeeded += 1
        except Exception as e:
            results.append(BatchResultItem(id=order_id, success=False, message=str(e)))

    await db.flush()
    return BatchResult(total=len(ids), succeeded=succeeded,
                       failed=len(ids) - succeeded, results=results)
