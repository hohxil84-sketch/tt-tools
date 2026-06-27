-- ============================================================
-- 阶段四补充：审计日志表增加操作人姓名字段
-- 日期：2026-06-28
-- 用途：admin_audit_logs 新增 admin_display_name 列，
--       使审计日志能展示操作人的真实姓名，而不仅是账号。
-- ============================================================

-- ① 添加列（允许 NULL，兼容已有数据）
ALTER TABLE admin_audit_logs ADD COLUMN IF NOT EXISTS admin_display_name VARCHAR(255);

-- ② 回填已有数据（从 users 表查询 display_name）
UPDATE admin_audit_logs SET admin_display_name = u.display_name
FROM users u
WHERE admin_audit_logs.admin_user_id = u.id
  AND admin_audit_logs.admin_display_name IS NULL;

-- 验证
SELECT count(*) AS null_display_name_count
FROM admin_audit_logs
WHERE admin_display_name IS NULL;
