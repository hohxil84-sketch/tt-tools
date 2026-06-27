-- ============================================================
-- 阶段五：彻底移除 plan_code 列
-- 日期：2026-06-28
-- 用途：从所有表中删除冗余的 plan_code varchar 列，
--       统一使用 plan_id UUID 外键引用 plans 表。
-- ============================================================

-- ① users 表 — 删除 plan_code 列和相关索引
DROP INDEX IF EXISTS idx_users_plan_code;
ALTER TABLE users DROP COLUMN IF EXISTS plan_code;

-- ② credit_accounts 表 — 删除 plan_code 列
ALTER TABLE credit_accounts DROP COLUMN IF EXISTS plan_code;

-- 验证
SELECT 'users' AS table_name, count(*) AS row_count FROM users
UNION ALL
SELECT 'credit_accounts', count(*) FROM credit_accounts;
