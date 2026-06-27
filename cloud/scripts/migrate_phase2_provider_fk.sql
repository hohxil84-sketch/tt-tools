-- ============================================================
-- 阶段二迁移：provider varchar → provider_id UUID FK
--
-- 涉及表：provider_call_log
-- 目标：新增 provider_id 列，回填数据，建立外键约束
--
-- 注意事项：
--   1. 迁移前必须确保 providers 表已包含所有被引用的 provider
--   2. 新列暂为 nullable，后续写入方全部更新后再加 NOT NULL
--   3. 旧列 provider 暂时保留，过渡期双写
-- ============================================================

BEGIN;

-- ① 加新列
ALTER TABLE provider_call_log ADD COLUMN IF NOT EXISTS provider_id uuid;

-- ② 回填数据（用 provider 字符串匹配 providers.name）
UPDATE provider_call_log pcl
SET provider_id = p.id
FROM providers p
WHERE pcl.provider = p.name
  AND pcl.provider_id IS NULL;

-- ③ 确认无未匹配的记录
DO $$
DECLARE
    null_count INT;
BEGIN
    SELECT count(*) INTO null_count FROM provider_call_log WHERE provider_id IS NULL;
    IF null_count > 0 THEN
        RAISE WARNING 'provider_call_log: % 条记录的 provider_id 无法回填，providers 表可能缺少对应 Provider', null_count;
    END IF;
END $$;

-- ④ 加外键约束
ALTER TABLE provider_call_log
  DROP CONSTRAINT IF EXISTS fk_pcl_provider,
  ADD CONSTRAINT fk_pcl_provider FOREIGN KEY (provider_id) REFERENCES providers(id);

-- ⑤ 加索引
CREATE INDEX IF NOT EXISTS idx_pcl_provider_id ON provider_call_log(provider_id);

COMMIT;

-- 验证
SELECT count(*) AS total,
       count(provider_id) AS filled,
       count(*) - count(provider_id) AS nulls
FROM provider_call_log;
