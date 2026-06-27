-- ============================================================
-- 阶段三迁移：plan_code varchar → plan_id UUID FK
--
-- 涉及表：users, credit_accounts
-- 目标：新增 plan_id 列，回填数据，建立外键约束
--
-- 前置条件：
--   1. 运行 cloud/scripts/seed_plans.py 确保 plans 表有对应记录
--   2. 确保 plans 表包含所有 users.plan_code 引用的编码
-- ============================================================

BEGIN;

-- ============================================================
-- 1. 确保缺失的 plan_code 有对应的 plans 记录
-- ============================================================
-- 如果 users 中有 plan_code 在 plans 表中不存在，先补建 plans 记录
INSERT INTO plans (id, code, name, monthly_grant, enabled_features_json, status, created_at, updated_at)
SELECT
    gen_random_uuid(),
    u.plan_code,
    '自动迁移: ' || u.plan_code,
    0,
    '{}'::jsonb,
    'active',
    NOW(),
    NOW()
FROM (SELECT DISTINCT plan_code FROM users) u
WHERE u.plan_code NOT IN (SELECT code FROM plans)
  AND u.plan_code IS NOT NULL
  AND u.plan_code != '';

INSERT INTO plans (id, code, name, monthly_grant, enabled_features_json, status, created_at, updated_at)
SELECT
    gen_random_uuid(),
    ca.plan_code,
    '自动迁移: ' || ca.plan_code,
    0,
    '{}'::jsonb,
    'active',
    NOW(),
    NOW()
FROM (SELECT DISTINCT plan_code FROM credit_accounts) ca
WHERE ca.plan_code NOT IN (SELECT code FROM plans)
  AND ca.plan_code IS NOT NULL
  AND ca.plan_code != '';

-- ============================================================
-- 2. users 表
-- ============================================================

ALTER TABLE users ADD COLUMN IF NOT EXISTS plan_id uuid;

UPDATE users
SET plan_id = p.id
FROM plans p
WHERE users.plan_code = p.code
  AND users.plan_id IS NULL;

DO $$
DECLARE null_count INT;
BEGIN
    SELECT count(*) INTO null_count FROM users WHERE plan_id IS NULL;
    IF null_count > 0 THEN
        RAISE WARNING 'users: % 条记录的 plan_id 无法回填', null_count;
    END IF;
END $$;

ALTER TABLE users
  DROP CONSTRAINT IF EXISTS fk_users_plan,
  ADD CONSTRAINT fk_users_plan FOREIGN KEY (plan_id) REFERENCES plans(id);

CREATE INDEX IF NOT EXISTS idx_users_plan_id ON users(plan_id);

-- ============================================================
-- 3. credit_accounts 表
-- ============================================================

ALTER TABLE credit_accounts ADD COLUMN IF NOT EXISTS plan_id uuid;

UPDATE credit_accounts
SET plan_id = p.id
FROM plans p
WHERE credit_accounts.plan_code = p.code
  AND credit_accounts.plan_id IS NULL;

DO $$
DECLARE null_count INT;
BEGIN
    SELECT count(*) INTO null_count FROM credit_accounts WHERE plan_id IS NULL;
    IF null_count > 0 THEN
        RAISE WARNING 'credit_accounts: % 条记录的 plan_id 无法回填', null_count;
    END IF;
END $$;

ALTER TABLE credit_accounts
  DROP CONSTRAINT IF EXISTS fk_ca_plan,
  ADD CONSTRAINT fk_ca_plan FOREIGN KEY (plan_id) REFERENCES plans(id);

CREATE INDEX IF NOT EXISTS idx_ca_plan_id ON credit_accounts(plan_id);

COMMIT;

-- 验证
SELECT 'users' AS tbl, count(*) AS total,
       count(plan_id) AS filled,
       count(*) - count(plan_id) AS nulls
FROM users
UNION ALL
SELECT 'credit_accounts', count(*), count(plan_id), count(*) - count(plan_id)
FROM credit_accounts;
