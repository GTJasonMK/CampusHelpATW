-- CampusHelpATW
-- MySQL Sanity Checks v0.1（联调验收查询）
-- 用法：
--   在执行 schema + seed + guards + mock_data 后运行本脚本
--   观察每条检查的 result 列，PASS 表示符合预期

SET NAMES utf8mb4;
USE `campus_help_atw`;

-- =========================
-- 1) 联调任务数量
-- =========================
SELECT
  'mock_tasks_total_should_be_10' AS check_name,
  COUNT(*) AS actual,
  10 AS expected,
  CASE WHEN COUNT(*) = 10 THEN 'PASS' ELSE 'WARN' END AS result
FROM `tasks`
WHERE `title` LIKE '联调任务-%';

-- =========================
-- 2) 联调任务状态分布
-- 预期：OPEN=3, ACCEPTED=2, IN_PROGRESS=2, PENDING_CONFIRM=1, DONE=1, DISPUTED=1
-- =========================
SELECT
  'mock_task_status_distribution' AS check_name,
  SUM(CASE WHEN `status` = 'OPEN' THEN 1 ELSE 0 END) AS open_count,
  SUM(CASE WHEN `status` = 'ACCEPTED' THEN 1 ELSE 0 END) AS accepted_count,
  SUM(CASE WHEN `status` = 'IN_PROGRESS' THEN 1 ELSE 0 END) AS in_progress_count,
  SUM(CASE WHEN `status` = 'PENDING_CONFIRM' THEN 1 ELSE 0 END) AS pending_confirm_count,
  SUM(CASE WHEN `status` = 'DONE' THEN 1 ELSE 0 END) AS done_count,
  SUM(CASE WHEN `status` = 'DISPUTED' THEN 1 ELSE 0 END) AS disputed_count,
  CASE
    WHEN SUM(CASE WHEN `status` = 'OPEN' THEN 1 ELSE 0 END) = 3
     AND SUM(CASE WHEN `status` = 'ACCEPTED' THEN 1 ELSE 0 END) = 2
     AND SUM(CASE WHEN `status` = 'IN_PROGRESS' THEN 1 ELSE 0 END) = 2
     AND SUM(CASE WHEN `status` = 'PENDING_CONFIRM' THEN 1 ELSE 0 END) = 1
     AND SUM(CASE WHEN `status` = 'DONE' THEN 1 ELSE 0 END) = 1
     AND SUM(CASE WHEN `status` = 'DISPUTED' THEN 1 ELSE 0 END) = 1
    THEN 'PASS' ELSE 'WARN'
  END AS result
FROM `tasks`
WHERE `title` LIKE '联调任务-%';

-- =========================
-- 3) 状态日志覆盖检查（非 OPEN 状态至少有一条日志）
-- =========================
SELECT
  'non_open_task_should_have_status_logs' AS check_name,
  COUNT(*) AS bad_rows,
  0 AS expected,
  CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'WARN' END AS result
FROM (
  SELECT t.`id`
  FROM `tasks` t
  LEFT JOIN `task_status_logs` l ON l.`task_id` = t.`id`
  WHERE t.`title` LIKE '联调任务-%'
    AND t.`status` <> 'OPEN'
  GROUP BY t.`id`
  HAVING COUNT(l.`id`) = 0
) x;

-- =========================
-- 4) 已完成任务评价检查（任务 09 应有 2 条评价）
-- =========================
SELECT
  'task_09_reviews_should_be_2' AS check_name,
  COUNT(*) AS actual,
  2 AS expected,
  CASE WHEN COUNT(*) = 2 THEN 'PASS' ELSE 'WARN' END AS result
FROM `task_reviews` r
JOIN `tasks` t ON t.`id` = r.`task_id`
WHERE t.`title` = '联调任务-09-已完成';

-- =========================
-- 5) 积分流水检查（任务 09 预期至少 3 条联调流水）
-- =========================
SELECT
  'task_09_point_ledger_should_be_at_least_3' AS check_name,
  COUNT(*) AS actual,
  3 AS expected_min,
  CASE WHEN COUNT(*) >= 3 THEN 'PASS' ELSE 'WARN' END AS result
FROM `point_ledger`
WHERE (`biz_type` = 'TASK_COMPLETE' OR `biz_type` = 'TASK_CONFIRM')
  AND `biz_id` = (
    SELECT `id` FROM `tasks` WHERE `title` = '联调任务-09-已完成' LIMIT 1
  );

-- =========================
-- 6) 聊天消息检查（联调任务应至少有 8 条消息）
-- =========================
SELECT
  'mock_chat_messages_should_be_at_least_8' AS check_name,
  COUNT(*) AS actual,
  8 AS expected_min,
  CASE WHEN COUNT(*) >= 8 THEN 'PASS' ELSE 'WARN' END AS result
FROM `chat_messages` m
JOIN `task_chats` c ON c.`id` = m.`chat_id`
JOIN `tasks` t ON t.`id` = c.`task_id`
WHERE t.`title` LIKE '联调任务-%';

-- =========================
-- 7) 举报记录检查（任务 10 应至少 1 条）
-- =========================
SELECT
  'task_10_reports_should_be_at_least_1' AS check_name,
  COUNT(*) AS actual,
  1 AS expected_min,
  CASE WHEN COUNT(*) >= 1 THEN 'PASS' ELSE 'WARN' END AS result
FROM `reports`
WHERE `target_type` = 'TASK'
  AND `target_id` = (
    SELECT `id` FROM `tasks` WHERE `title` = '联调任务-10-申诉中' LIMIT 1
  );

-- =========================
-- 8) 辅助查看：联调任务概览
-- =========================
SELECT
  t.`id`, t.`title`, t.`status`, t.`publisher_id`, t.`acceptor_id`,
  t.`reward_amount`, t.`created_at`
FROM `tasks` t
WHERE t.`title` LIKE '联调任务-%'
ORDER BY t.`id`;
