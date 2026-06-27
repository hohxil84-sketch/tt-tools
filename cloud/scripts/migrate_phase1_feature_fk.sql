-- ============================================================
-- 阶段一迁移：feature varchar → feature_code_id UUID FK
--
-- 涉及表：provider_call_log, usage_events, ai_tasks
-- 目标：新增 feature_code_id 列，回填数据，建立外键约束
--
-- 注意事项：
--   1. 迁移前必须确保 feature_codes 表已包含所有被引用的功能码
--      （运行 cloud/scripts/seed_feature_codes.py）
--   2. 新列暂为 nullable，后续写入方全部更新后再加 NOT NULL
--   3. 旧列 feature 暂时保留，过渡期双写
--   4. 本脚本在 PostgreSQL 上执行，建议先备份
-- ============================================================

BEGIN;

-- ============================================================
-- 1. provider_call_log
-- ============================================================

-- ① 加新列（先 nullable，不回填完再加 NOT NULL）
ALTER TABLE provider_call_log ADD COLUMN IF NOT EXISTS feature_code_id uuid;

-- ② 回填数据（用 feature 字符串匹配 feature_codes.code）
UPDATE provider_call_log pcl
SET feature_code_id = fc.id
FROM feature_codes fc
WHERE pcl.feature = fc.code
  AND pcl.feature_code_id IS NULL;

-- ③ 确认无未匹配的记录
DO $$
DECLARE
    null_count INT;
BEGIN
    SELECT count(*) INTO null_count FROM provider_call_log WHERE feature_code_id IS NULL;
    IF null_count > 0 THEN
        RAISE WARNING 'provider_call_log: % 条记录的 feature_code_id 无法回填，feature_codes 表可能缺少对应功能码', null_count;
    END IF;
END $$;

-- ④ 加外键约束（即使有少量 NULL 也能建立 FK，NULL 值不检查）
ALTER TABLE provider_call_log
  DROP CONSTRAINT IF EXISTS fk_pcl_feature_code,
  ADD CONSTRAINT fk_pcl_feature_code FOREIGN KEY (feature_code_id) REFERENCES feature_codes(id);

-- ⑤ 加索引
CREATE INDEX IF NOT EXISTS idx_pcl_feature_code_id ON provider_call_log(feature_code_id);

-- ============================================================
-- 2. usage_events
-- ============================================================

ALTER TABLE usage_events ADD COLUMN IF NOT EXISTS feature_code_id uuid;

UPDATE usage_events ue
SET feature_code_id = fc.id
FROM feature_codes fc
WHERE ue.feature = fc.code
  AND ue.feature_code_id IS NULL;

DO $$
DECLARE
    null_count INT;
BEGIN
    SELECT count(*) INTO null_count FROM usage_events WHERE feature_code_id IS NULL;
    IF null_count > 0 THEN
        RAISE WARNING 'usage_events: % 条记录的 feature_code_id 无法回填', null_count;
    END IF;
END $$;

ALTER TABLE usage_events
  DROP CONSTRAINT IF EXISTS fk_ue_feature_code,
  ADD CONSTRAINT fk_ue_feature_code FOREIGN KEY (feature_code_id) REFERENCES feature_codes(id);

CREATE INDEX IF NOT EXISTS idx_ue_feature_code_id ON usage_events(feature_code_id);

-- ============================================================
-- 3. ai_tasks
-- ============================================================

ALTER TABLE ai_tasks ADD COLUMN IF NOT EXISTS feature_code_id uuid;

UPDATE ai_tasks at_
SET feature_code_id = fc.id
FROM feature_codes fc
WHERE at_.feature = fc.code
  AND at_.feature_code_id IS NULL;

DO $$
DECLARE
    null_count INT;
BEGIN
    SELECT count(*) INTO null_count FROM ai_tasks WHERE feature_code_id IS NULL;
    IF null_count > 0 THEN
        RAISE WARNING 'ai_tasks: % 条记录的 feature_code_id 无法回填', null_count;
    END IF;
END $$;

ALTER TABLE ai_tasks
  DROP CONSTRAINT IF EXISTS fk_ait_feature_code,
  ADD CONSTRAINT fk_ait_feature_code FOREIGN KEY (feature_code_id) REFERENCES feature_codes(id);

CREATE INDEX IF NOT EXISTS idx_ait_feature_code_id ON ai_tasks(feature_code_id);

COMMIT;

-- ============================================================
-- 验证
-- ============================================================
-- 查看各表回填情况
SELECT 'provider_call_log' AS tbl, count(*) AS total,
       count(feature_code_id) AS filled,
       count(*) - count(feature_code_id) AS nulls
FROM provider_call_log
UNION ALL
SELECT 'usage_events', count(*), count(feature_code_id), count(*) - count(feature_code_id)
FROM usage_events
UNION ALL
SELECT 'ai_tasks', count(*), count(feature_code_id), count(*) - count(feature_code_id)
FROM ai_tasks;
