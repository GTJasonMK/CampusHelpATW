-- CampusHelpATW
-- MySQL Guards & Procedures v0.1
-- 目标：任务状态流转兜底校验 + 积分一致性存储过程
-- 依赖：请先执行 mysql_schema_v0.1.sql

SET NAMES utf8mb4;
USE `campus_help_atw`;

DELIMITER $$

-- =========================
-- 1) 任务状态流转守卫触发器
-- =========================

DROP TRIGGER IF EXISTS `tr_tasks_before_update_status_guard` $$
CREATE TRIGGER `tr_tasks_before_update_status_guard`
BEFORE UPDATE ON `tasks`
FOR EACH ROW
BEGIN
  DECLARE v_valid_transition TINYINT DEFAULT 0;

  -- 仅当状态变化时校验
  IF NEW.`status` <> OLD.`status` THEN
    SET v_valid_transition = (
      CASE
        WHEN OLD.`status` = 'OPEN' AND NEW.`status` IN ('ACCEPTED', 'CANCELED') THEN 1
        WHEN OLD.`status` = 'ACCEPTED' AND NEW.`status` IN ('IN_PROGRESS', 'CANCELED') THEN 1
        WHEN OLD.`status` = 'IN_PROGRESS' AND NEW.`status` IN ('PENDING_CONFIRM', 'CANCELED', 'DISPUTED') THEN 1
        WHEN OLD.`status` = 'PENDING_CONFIRM' AND NEW.`status` IN ('DONE', 'DISPUTED') THEN 1
        WHEN OLD.`status` = 'DISPUTED' AND NEW.`status` IN ('DONE', 'CANCELED') THEN 1
        ELSE 0
      END
    );

    IF v_valid_transition = 0 THEN
      SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'invalid task status transition';
    END IF;

    -- 自动维护关键时间戳
    IF NEW.`status` = 'ACCEPTED' AND NEW.`accepted_at` IS NULL THEN
      SET NEW.`accepted_at` = CURRENT_TIMESTAMP(3);
    END IF;

    IF NEW.`status` = 'DONE' AND NEW.`completed_at` IS NULL THEN
      SET NEW.`completed_at` = CURRENT_TIMESTAMP(3);
    END IF;

    IF NEW.`status` = 'CANCELED' AND NEW.`canceled_at` IS NULL THEN
      SET NEW.`canceled_at` = CURRENT_TIMESTAMP(3);
    END IF;
  END IF;
END $$

-- =========================
-- 2) 任务状态流转过程（带日志）
-- =========================

DROP PROCEDURE IF EXISTS `sp_task_transition` $$
CREATE PROCEDURE `sp_task_transition` (
  IN p_task_id BIGINT UNSIGNED,
  IN p_to_status VARCHAR(32),
  IN p_operator_user_id BIGINT UNSIGNED,
  IN p_reason VARCHAR(255)
)
BEGIN
  DECLARE v_from_status VARCHAR(32);
  DECLARE v_locked_task_id BIGINT UNSIGNED DEFAULT NULL;
  DECLARE v_locked_user_id BIGINT UNSIGNED DEFAULT NULL;

  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  START TRANSACTION;

  SELECT `id` INTO v_locked_user_id
  FROM `users`
  WHERE `id` = p_operator_user_id
  LIMIT 1;

  IF v_locked_user_id IS NULL THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'operator user not found';
  END IF;

  SELECT `id`, `status` INTO v_locked_task_id, v_from_status
  FROM `tasks`
  WHERE `id` = p_task_id
  FOR UPDATE;

  IF v_locked_task_id IS NULL THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'task not found';
  END IF;

  IF p_to_status NOT IN (
    'OPEN', 'ACCEPTED', 'IN_PROGRESS', 'PENDING_CONFIRM', 'DONE', 'CANCELED', 'DISPUTED'
  ) THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'invalid target status';
  END IF;

  UPDATE `tasks`
  SET `status` = p_to_status
  WHERE `id` = p_task_id;

  INSERT INTO `task_status_logs` (
    `task_id`, `from_status`, `to_status`, `operator_user_id`, `reason`
  )
  VALUES (
    p_task_id, v_from_status, p_to_status, p_operator_user_id, p_reason
  );

  COMMIT;
END $$

-- =========================
-- 3) 积分变更过程（事务一致）
-- =========================

DROP PROCEDURE IF EXISTS `sp_add_points` $$
CREATE PROCEDURE `sp_add_points` (
  IN p_user_id BIGINT UNSIGNED,
  IN p_point_type VARCHAR(16),
  IN p_change_amount INT,
  IN p_biz_type VARCHAR(32),
  IN p_biz_id BIGINT UNSIGNED,
  IN p_remark VARCHAR(255)
)
BEGIN
  DECLARE v_locked_user_id BIGINT UNSIGNED DEFAULT NULL;
  DECLARE v_help_balance INT;
  DECLARE v_honor_balance INT;
  DECLARE v_balance_after INT;

  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  START TRANSACTION;

  SELECT `id`, `help_points_balance`, `honor_points_balance`
  INTO v_locked_user_id, v_help_balance, v_honor_balance
  FROM `users`
  WHERE `id` = p_user_id
  FOR UPDATE;

  IF v_locked_user_id IS NULL THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'user not found';
  END IF;

  IF p_point_type = 'HELP' THEN
    SET v_balance_after = v_help_balance + p_change_amount;

    IF v_balance_after < 0 THEN
      SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'insufficient HELP points';
    END IF;

    UPDATE `users`
    SET `help_points_balance` = v_balance_after
    WHERE `id` = p_user_id;

  ELSEIF p_point_type = 'HONOR' THEN
    SET v_balance_after = v_honor_balance + p_change_amount;

    IF v_balance_after < 0 THEN
      SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'insufficient HONOR points';
    END IF;

    UPDATE `users`
    SET `honor_points_balance` = v_balance_after
    WHERE `id` = p_user_id;

  ELSE
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'invalid point type';
  END IF;

  INSERT INTO `point_ledger` (
    `user_id`, `point_type`, `change_amount`, `balance_after`, `biz_type`, `biz_id`, `remark`
  )
  VALUES (
    p_user_id, p_point_type, p_change_amount, v_balance_after, p_biz_type, p_biz_id, p_remark
  );

  COMMIT;
END $$

DELIMITER ;

-- 使用示例：
-- CALL sp_task_transition(1001, 'ACCEPTED', 2, '用户接单');
-- CALL sp_add_points(2, 'HELP', 3, 'TASK_COMPLETE', 1001, '完成任务奖励');
