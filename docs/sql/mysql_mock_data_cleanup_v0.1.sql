-- CampusHelpATW
-- MySQL Mock Data Cleanup v0.1
-- 目标：清理 mysql_mock_data_v0.1.sql 生成的联调数据
-- 风险提示：
--   本脚本包含 DELETE 操作，只应在开发/测试环境使用
-- 依赖：
--   已执行 mysql_schema_v0.1.sql

SET NAMES utf8mb4;
USE `campus_help_atw`;

DELIMITER $$

DROP PROCEDURE IF EXISTS `sp_cleanup_mock_data_v0_1` $$
CREATE PROCEDURE `sp_cleanup_mock_data_v0_1` (IN p_confirm VARCHAR(16))
proc: BEGIN
  IF p_confirm <> 'CONFIRM' THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'cleanup aborted: please pass CONFIRM';
  END IF;

  START TRANSACTION;

  CREATE TEMPORARY TABLE IF NOT EXISTS `tmp_mock_task_ids` (
    `id` BIGINT UNSIGNED PRIMARY KEY
  ) ENGINE=Memory;
  TRUNCATE TABLE `tmp_mock_task_ids`;

  INSERT INTO `tmp_mock_task_ids` (`id`)
  SELECT `id` FROM `tasks` WHERE `title` LIKE '联调任务-%';

  CREATE TEMPORARY TABLE IF NOT EXISTS `tmp_mock_post_ids` (
    `id` BIGINT UNSIGNED PRIMARY KEY
  ) ENGINE=Memory;
  TRUNCATE TABLE `tmp_mock_post_ids`;

  INSERT INTO `tmp_mock_post_ids` (`id`)
  SELECT `id` FROM `posts` WHERE `title` LIKE '联调帖-%';

  -- 1) 先删依赖表
  DELETE FROM `task_reviews`
  WHERE `task_id` IN (SELECT `id` FROM `tmp_mock_task_ids`);

  DELETE FROM `point_ledger`
  WHERE (`biz_id` IN (SELECT `id` FROM `tmp_mock_task_ids`)
     AND `biz_type` IN ('TASK_COMPLETE', 'TASK_CONFIRM'))
     OR `remark` LIKE '联调任务%';

  DELETE FROM `chat_messages`
  WHERE `chat_id` IN (
    SELECT `id` FROM `task_chats`
    WHERE `task_id` IN (SELECT `id` FROM `tmp_mock_task_ids`)
  );

  DELETE FROM `task_chats`
  WHERE `task_id` IN (SELECT `id` FROM `tmp_mock_task_ids`);

  DELETE FROM `task_status_logs`
  WHERE `task_id` IN (SELECT `id` FROM `tmp_mock_task_ids`);

  DELETE FROM `reports`
  WHERE (`target_type` = 'TASK' AND `target_id` IN (SELECT `id` FROM `tmp_mock_task_ids`))
     OR (`target_type` = 'POST' AND `target_id` IN (SELECT `id` FROM `tmp_mock_post_ids`))
     OR (`reason_text` LIKE '联调%');

  DELETE FROM `admin_operation_logs`
  WHERE (`target_type` = 'TASK' AND `target_id` IN (SELECT `id` FROM `tmp_mock_task_ids`))
     OR (`target_type` = 'POST' AND `target_id` IN (SELECT `id` FROM `tmp_mock_post_ids`))
     OR (`detail` LIKE '联调%');

  DELETE FROM `post_likes`
  WHERE `post_id` IN (SELECT `id` FROM `tmp_mock_post_ids`);

  DELETE FROM `post_comments`
  WHERE `post_id` IN (SELECT `id` FROM `tmp_mock_post_ids`);

  DELETE FROM `posts`
  WHERE `id` IN (SELECT `id` FROM `tmp_mock_post_ids`);

  -- 2) 删除任务主表
  DELETE FROM `tasks`
  WHERE `id` IN (SELECT `id` FROM `tmp_mock_task_ids`);

  -- 3) 清理联调创建用户（仅删除 charlie/diana，且确保无残留依赖）
  DELETE FROM `users`
  WHERE `campus_email` IN ('charlie@campus.local', 'diana@campus.local')
    AND `id` NOT IN (SELECT `publisher_id` FROM `tasks`)
    AND `id` NOT IN (SELECT `acceptor_id` FROM `tasks` WHERE `acceptor_id` IS NOT NULL);

  -- 4) 清理联调标记
  DELETE FROM `system_configs`
  WHERE `config_key` = 'seed.mock_data_v0_1_applied';

  DROP TEMPORARY TABLE IF EXISTS `tmp_mock_task_ids`;
  DROP TEMPORARY TABLE IF EXISTS `tmp_mock_post_ids`;

  COMMIT;
END $$

-- 执行清理（必须显式确认）
CALL `sp_cleanup_mock_data_v0_1` ('CONFIRM') $$
DROP PROCEDURE IF EXISTS `sp_cleanup_mock_data_v0_1` $$

DELIMITER ;
