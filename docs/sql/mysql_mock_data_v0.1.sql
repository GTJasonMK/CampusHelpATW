-- CampusHelpATW
-- MySQL Mock Data v0.1（本地联调用）
-- 目标：生成 10 条任务 + 聊天 + 评价 + 举报 + 积分流水
-- 依赖：
--   1) mysql_schema_v0.1.sql
--   2) mysql_seed_v0.1.sql
--   3) mysql_guards_v0.1.sql
-- 说明：
--   - 本脚本通过 system_configs 中的标记键实现“只生效一次”
--   - 若要重复导入，请先删除 config_key='seed.mock_data_v0_1_applied'

SET NAMES utf8mb4;
USE `campus_help_atw`;

DELIMITER $$

DROP PROCEDURE IF EXISTS `sp_seed_mock_data_v0_1` $$
CREATE PROCEDURE `sp_seed_mock_data_v0_1` ()
proc: BEGIN
  DECLARE v_applied INT DEFAULT 0;
  DECLARE v_exists INT DEFAULT 0;
  DECLARE v_admin_id BIGINT UNSIGNED;
  DECLARE v_alice_id BIGINT UNSIGNED;
  DECLARE v_bob_id BIGINT UNSIGNED;
  DECLARE v_charlie_id BIGINT UNSIGNED;
  DECLARE v_diana_id BIGINT UNSIGNED;

  DECLARE v_t1 BIGINT UNSIGNED;
  DECLARE v_t2 BIGINT UNSIGNED;
  DECLARE v_t3 BIGINT UNSIGNED;
  DECLARE v_t4 BIGINT UNSIGNED;
  DECLARE v_t5 BIGINT UNSIGNED;
  DECLARE v_t6 BIGINT UNSIGNED;
  DECLARE v_t7 BIGINT UNSIGNED;
  DECLARE v_t8 BIGINT UNSIGNED;
  DECLARE v_t9 BIGINT UNSIGNED;
  DECLARE v_t10 BIGINT UNSIGNED;

  DECLARE v_c6 BIGINT UNSIGNED;
  DECLARE v_c8 BIGINT UNSIGNED;
  DECLARE v_c9 BIGINT UNSIGNED;
  DECLARE v_c10 BIGINT UNSIGNED;

  DECLARE v_status VARCHAR(32);

  SELECT COUNT(1) INTO v_applied
  FROM `system_configs`
  WHERE `config_key` = 'seed.mock_data_v0_1_applied';

  IF v_applied > 0 THEN
    LEAVE proc;
  END IF;

  -- 1) 补充联调账号
  INSERT INTO `users` (
    `campus_email`, `password_hash`, `nickname`, `school_name`, `college_name`,
    `reputation_score`, `help_points_balance`, `honor_points_balance`, `status`
  )
  VALUES
    (
      'charlie@campus.local',
      '$2b$12$8f2FG8rN5m8nU9x9C2hI3eX7xVd8xg4wIgjlUi1xjtcgYjNAn8HzS',
      'Charlie',
      'CampusHelpATW',
      '数学学院',
      6, 12, 3, 'ACTIVE'
    ),
    (
      'diana@campus.local',
      '$2b$12$8f2FG8rN5m8nU9x9C2hI3eX7xVd8xg4wIgjlUi1xjtcgYjNAn8HzS',
      'Diana',
      'CampusHelpATW',
      '外语学院',
      7, 18, 4, 'ACTIVE'
    )
  ON DUPLICATE KEY UPDATE
    `nickname` = VALUES(`nickname`),
    `school_name` = VALUES(`school_name`),
    `college_name` = VALUES(`college_name`),
    `status` = VALUES(`status`);

  SELECT `id` INTO v_admin_id FROM `users` WHERE `campus_email` = 'admin@campus.local' LIMIT 1;
  SELECT `id` INTO v_alice_id FROM `users` WHERE `campus_email` = 'alice@campus.local' LIMIT 1;
  SELECT `id` INTO v_bob_id FROM `users` WHERE `campus_email` = 'bob@campus.local' LIMIT 1;
  SELECT `id` INTO v_charlie_id FROM `users` WHERE `campus_email` = 'charlie@campus.local' LIMIT 1;
  SELECT `id` INTO v_diana_id FROM `users` WHERE `campus_email` = 'diana@campus.local' LIMIT 1;

  IF v_admin_id IS NULL OR v_alice_id IS NULL OR v_bob_id IS NULL OR v_charlie_id IS NULL OR v_diana_id IS NULL THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'required seed users are missing';
  END IF;

  -- 2) 生成 10 条联调任务（先统一插入 OPEN，再按目标状态流转）
  INSERT INTO `tasks` (
    `publisher_id`, `title`, `description`, `category`, `location_text`,
    `reward_amount`, `reward_type`, `deadline_at`, `status`
  )
  SELECT v_alice_id, '联调任务-01-待接单', '帮忙代取快递，今晚 9 点前', 'ERRAND', '东区菜鸟驿站', 5.00, 'CASH', DATE_ADD(NOW(3), INTERVAL 1 DAY), 'OPEN'
  WHERE NOT EXISTS (SELECT 1 FROM `tasks` WHERE `title` = '联调任务-01-待接单');

  INSERT INTO `tasks` (
    `publisher_id`, `title`, `description`, `category`, `location_text`,
    `reward_amount`, `reward_type`, `deadline_at`, `status`
  )
  SELECT v_bob_id, '联调任务-02-待接单', '图书馆借书代办', 'DOC', '校图书馆一层', 0.00, 'NONE', DATE_ADD(NOW(3), INTERVAL 2 DAY), 'OPEN'
  WHERE NOT EXISTS (SELECT 1 FROM `tasks` WHERE `title` = '联调任务-02-待接单');

  INSERT INTO `tasks` (
    `publisher_id`, `title`, `description`, `category`, `location_text`,
    `reward_amount`, `reward_type`, `deadline_at`, `status`
  )
  SELECT v_charlie_id, '联调任务-03-待接单', '线代题目讲解 30 分钟', 'STUDY', '线上语音', 10.00, 'CASH', DATE_ADD(NOW(3), INTERVAL 2 DAY), 'OPEN'
  WHERE NOT EXISTS (SELECT 1 FROM `tasks` WHERE `title` = '联调任务-03-待接单');

  INSERT INTO `tasks` (
    `publisher_id`, `title`, `description`, `category`, `location_text`,
    `reward_amount`, `reward_type`, `deadline_at`, `status`
  )
  SELECT v_alice_id, '联调任务-04-已接单', '代买文具并送到宿舍楼下', 'LIFE', '南门文具店', 4.00, 'CASH', DATE_ADD(NOW(3), INTERVAL 1 DAY), 'OPEN'
  WHERE NOT EXISTS (SELECT 1 FROM `tasks` WHERE `title` = '联调任务-04-已接单');

  INSERT INTO `tasks` (
    `publisher_id`, `title`, `description`, `category`, `location_text`,
    `reward_amount`, `reward_type`, `deadline_at`, `status`
  )
  SELECT v_bob_id, '联调任务-05-已接单', '晚饭代排队打饭', 'LIFE', '一食堂', 3.00, 'CASH', DATE_ADD(NOW(3), INTERVAL 1 DAY), 'OPEN'
  WHERE NOT EXISTS (SELECT 1 FROM `tasks` WHERE `title` = '联调任务-05-已接单');

  INSERT INTO `tasks` (
    `publisher_id`, `title`, `description`, `category`, `location_text`,
    `reward_amount`, `reward_type`, `deadline_at`, `status`
  )
  SELECT v_alice_id, '联调任务-06-进行中', '数据库作业答疑', 'STUDY', '线上会议', 8.00, 'CASH', DATE_ADD(NOW(3), INTERVAL 1 DAY), 'OPEN'
  WHERE NOT EXISTS (SELECT 1 FROM `tasks` WHERE `title` = '联调任务-06-进行中');

  INSERT INTO `tasks` (
    `publisher_id`, `title`, `description`, `category`, `location_text`,
    `reward_amount`, `reward_type`, `deadline_at`, `status`
  )
  SELECT v_diana_id, '联调任务-07-进行中', '代取社团活动物资', 'ERRAND', '活动中心仓库', 6.00, 'CASH', DATE_ADD(NOW(3), INTERVAL 1 DAY), 'OPEN'
  WHERE NOT EXISTS (SELECT 1 FROM `tasks` WHERE `title` = '联调任务-07-进行中');

  INSERT INTO `tasks` (
    `publisher_id`, `title`, `description`, `category`, `location_text`,
    `reward_amount`, `reward_type`, `deadline_at`, `status`
  )
  SELECT v_charlie_id, '联调任务-08-待确认', '帮忙打印并装订材料', 'DOC', '教学楼打印店', 5.00, 'CASH', DATE_ADD(NOW(3), INTERVAL 1 DAY), 'OPEN'
  WHERE NOT EXISTS (SELECT 1 FROM `tasks` WHERE `title` = '联调任务-08-待确认');

  INSERT INTO `tasks` (
    `publisher_id`, `title`, `description`, `category`, `location_text`,
    `reward_amount`, `reward_type`, `deadline_at`, `status`
  )
  SELECT v_alice_id, '联调任务-09-已完成', '期末复习资料整理', 'STUDY', '线上共享文档', 12.00, 'CASH', DATE_ADD(NOW(3), INTERVAL 1 DAY), 'OPEN'
  WHERE NOT EXISTS (SELECT 1 FROM `tasks` WHERE `title` = '联调任务-09-已完成');

  INSERT INTO `tasks` (
    `publisher_id`, `title`, `description`, `category`, `location_text`,
    `reward_amount`, `reward_type`, `deadline_at`, `status`
  )
  SELECT v_bob_id, '联调任务-10-申诉中', '代送文件到行政楼', 'ERRAND', '行政楼一层', 6.00, 'CASH', DATE_ADD(NOW(3), INTERVAL 1 DAY), 'OPEN'
  WHERE NOT EXISTS (SELECT 1 FROM `tasks` WHERE `title` = '联调任务-10-申诉中');

  SELECT `id` INTO v_t1 FROM `tasks` WHERE `title` = '联调任务-01-待接单' LIMIT 1;
  SELECT `id` INTO v_t2 FROM `tasks` WHERE `title` = '联调任务-02-待接单' LIMIT 1;
  SELECT `id` INTO v_t3 FROM `tasks` WHERE `title` = '联调任务-03-待接单' LIMIT 1;
  SELECT `id` INTO v_t4 FROM `tasks` WHERE `title` = '联调任务-04-已接单' LIMIT 1;
  SELECT `id` INTO v_t5 FROM `tasks` WHERE `title` = '联调任务-05-已接单' LIMIT 1;
  SELECT `id` INTO v_t6 FROM `tasks` WHERE `title` = '联调任务-06-进行中' LIMIT 1;
  SELECT `id` INTO v_t7 FROM `tasks` WHERE `title` = '联调任务-07-进行中' LIMIT 1;
  SELECT `id` INTO v_t8 FROM `tasks` WHERE `title` = '联调任务-08-待确认' LIMIT 1;
  SELECT `id` INTO v_t9 FROM `tasks` WHERE `title` = '联调任务-09-已完成' LIMIT 1;
  SELECT `id` INTO v_t10 FROM `tasks` WHERE `title` = '联调任务-10-申诉中' LIMIT 1;

  -- 3) 绑定接单人
  UPDATE `tasks` SET `acceptor_id` = v_bob_id WHERE `id` = v_t4 AND `acceptor_id` IS NULL;
  UPDATE `tasks` SET `acceptor_id` = v_diana_id WHERE `id` = v_t5 AND `acceptor_id` IS NULL;
  UPDATE `tasks` SET `acceptor_id` = v_charlie_id WHERE `id` = v_t6 AND `acceptor_id` IS NULL;
  UPDATE `tasks` SET `acceptor_id` = v_bob_id WHERE `id` = v_t7 AND `acceptor_id` IS NULL;
  UPDATE `tasks` SET `acceptor_id` = v_alice_id WHERE `id` = v_t8 AND `acceptor_id` IS NULL;
  UPDATE `tasks` SET `acceptor_id` = v_diana_id WHERE `id` = v_t9 AND `acceptor_id` IS NULL;
  UPDATE `tasks` SET `acceptor_id` = v_charlie_id WHERE `id` = v_t10 AND `acceptor_id` IS NULL;

  -- 4) 状态流转（通过过程写入日志）
  -- T4 -> ACCEPTED
  SELECT `status` INTO v_status FROM `tasks` WHERE `id` = v_t4;
  IF v_status = 'OPEN' THEN
    CALL `sp_task_transition`(v_t4, 'ACCEPTED', v_bob_id, '联调数据：用户接单');
  END IF;

  -- T5 -> ACCEPTED
  SELECT `status` INTO v_status FROM `tasks` WHERE `id` = v_t5;
  IF v_status = 'OPEN' THEN
    CALL `sp_task_transition`(v_t5, 'ACCEPTED', v_diana_id, '联调数据：用户接单');
  END IF;

  -- T6 -> IN_PROGRESS
  SELECT `status` INTO v_status FROM `tasks` WHERE `id` = v_t6;
  IF v_status = 'OPEN' THEN
    CALL `sp_task_transition`(v_t6, 'ACCEPTED', v_charlie_id, '联调数据：用户接单');
  END IF;
  SELECT `status` INTO v_status FROM `tasks` WHERE `id` = v_t6;
  IF v_status = 'ACCEPTED' THEN
    CALL `sp_task_transition`(v_t6, 'IN_PROGRESS', v_charlie_id, '联调数据：开始处理');
  END IF;

  -- T7 -> IN_PROGRESS
  SELECT `status` INTO v_status FROM `tasks` WHERE `id` = v_t7;
  IF v_status = 'OPEN' THEN
    CALL `sp_task_transition`(v_t7, 'ACCEPTED', v_bob_id, '联调数据：用户接单');
  END IF;
  SELECT `status` INTO v_status FROM `tasks` WHERE `id` = v_t7;
  IF v_status = 'ACCEPTED' THEN
    CALL `sp_task_transition`(v_t7, 'IN_PROGRESS', v_bob_id, '联调数据：开始处理');
  END IF;

  -- T8 -> PENDING_CONFIRM
  SELECT `status` INTO v_status FROM `tasks` WHERE `id` = v_t8;
  IF v_status = 'OPEN' THEN
    CALL `sp_task_transition`(v_t8, 'ACCEPTED', v_alice_id, '联调数据：用户接单');
  END IF;
  SELECT `status` INTO v_status FROM `tasks` WHERE `id` = v_t8;
  IF v_status = 'ACCEPTED' THEN
    CALL `sp_task_transition`(v_t8, 'IN_PROGRESS', v_alice_id, '联调数据：开始处理');
  END IF;
  SELECT `status` INTO v_status FROM `tasks` WHERE `id` = v_t8;
  IF v_status = 'IN_PROGRESS' THEN
    CALL `sp_task_transition`(v_t8, 'PENDING_CONFIRM', v_alice_id, '联调数据：提交完成');
  END IF;

  -- T9 -> DONE
  SELECT `status` INTO v_status FROM `tasks` WHERE `id` = v_t9;
  IF v_status = 'OPEN' THEN
    CALL `sp_task_transition`(v_t9, 'ACCEPTED', v_diana_id, '联调数据：用户接单');
  END IF;
  SELECT `status` INTO v_status FROM `tasks` WHERE `id` = v_t9;
  IF v_status = 'ACCEPTED' THEN
    CALL `sp_task_transition`(v_t9, 'IN_PROGRESS', v_diana_id, '联调数据：开始处理');
  END IF;
  SELECT `status` INTO v_status FROM `tasks` WHERE `id` = v_t9;
  IF v_status = 'IN_PROGRESS' THEN
    CALL `sp_task_transition`(v_t9, 'PENDING_CONFIRM', v_diana_id, '联调数据：提交完成');
  END IF;
  SELECT `status` INTO v_status FROM `tasks` WHERE `id` = v_t9;
  IF v_status = 'PENDING_CONFIRM' THEN
    CALL `sp_task_transition`(v_t9, 'DONE', v_alice_id, '联调数据：发布者确认');
  END IF;

  -- T10 -> DISPUTED
  SELECT `status` INTO v_status FROM `tasks` WHERE `id` = v_t10;
  IF v_status = 'OPEN' THEN
    CALL `sp_task_transition`(v_t10, 'ACCEPTED', v_charlie_id, '联调数据：用户接单');
  END IF;
  SELECT `status` INTO v_status FROM `tasks` WHERE `id` = v_t10;
  IF v_status = 'ACCEPTED' THEN
    CALL `sp_task_transition`(v_t10, 'IN_PROGRESS', v_charlie_id, '联调数据：开始处理');
  END IF;
  SELECT `status` INTO v_status FROM `tasks` WHERE `id` = v_t10;
  IF v_status = 'IN_PROGRESS' THEN
    CALL `sp_task_transition`(v_t10, 'DISPUTED', v_bob_id, '联调数据：发起申诉');
  END IF;

  -- 5) 聊天会话与消息（任务 6/8/9/10）
  INSERT IGNORE INTO `task_chats` (`task_id`) VALUES (v_t6), (v_t8), (v_t9), (v_t10);

  SELECT `id` INTO v_c6 FROM `task_chats` WHERE `task_id` = v_t6 LIMIT 1;
  SELECT `id` INTO v_c8 FROM `task_chats` WHERE `task_id` = v_t8 LIMIT 1;
  SELECT `id` INTO v_c9 FROM `task_chats` WHERE `task_id` = v_t9 LIMIT 1;
  SELECT `id` INTO v_c10 FROM `task_chats` WHERE `task_id` = v_t10 LIMIT 1;

  INSERT INTO `chat_messages` (`chat_id`, `sender_id`, `message_type`, `content`)
  SELECT v_c6, v_alice_id, 'TEXT', '你好，这个答疑任务今晚可以开始吗？'
  WHERE NOT EXISTS (
    SELECT 1 FROM `chat_messages`
    WHERE `chat_id` = v_c6
      AND `sender_id` = v_alice_id
      AND `content` = '你好，这个答疑任务今晚可以开始吗？'
  );

  INSERT INTO `chat_messages` (`chat_id`, `sender_id`, `message_type`, `content`)
  SELECT v_c6, v_charlie_id, 'TEXT', '可以，20:00 开始。'
  WHERE NOT EXISTS (
    SELECT 1 FROM `chat_messages`
    WHERE `chat_id` = v_c6
      AND `sender_id` = v_charlie_id
      AND `content` = '可以，20:00 开始。'
  );

  INSERT INTO `chat_messages` (`chat_id`, `sender_id`, `message_type`, `content`)
  SELECT v_c8, v_charlie_id, 'TEXT', '材料我发你邮箱了，麻烦帮忙打印。'
  WHERE NOT EXISTS (
    SELECT 1 FROM `chat_messages`
    WHERE `chat_id` = v_c8
      AND `sender_id` = v_charlie_id
      AND `content` = '材料我发你邮箱了，麻烦帮忙打印。'
  );

  INSERT INTO `chat_messages` (`chat_id`, `sender_id`, `message_type`, `content`)
  SELECT v_c8, v_alice_id, 'TEXT', '收到，稍后去打印店。'
  WHERE NOT EXISTS (
    SELECT 1 FROM `chat_messages`
    WHERE `chat_id` = v_c8
      AND `sender_id` = v_alice_id
      AND `content` = '收到，稍后去打印店。'
  );

  INSERT INTO `chat_messages` (`chat_id`, `sender_id`, `message_type`, `content`)
  SELECT v_c9, v_diana_id, 'TEXT', '资料已整理完，已共享给你。'
  WHERE NOT EXISTS (
    SELECT 1 FROM `chat_messages`
    WHERE `chat_id` = v_c9
      AND `sender_id` = v_diana_id
      AND `content` = '资料已整理完，已共享给你。'
  );

  INSERT INTO `chat_messages` (`chat_id`, `sender_id`, `message_type`, `content`)
  SELECT v_c9, v_alice_id, 'TEXT', '已确认，非常感谢！'
  WHERE NOT EXISTS (
    SELECT 1 FROM `chat_messages`
    WHERE `chat_id` = v_c9
      AND `sender_id` = v_alice_id
      AND `content` = '已确认，非常感谢！'
  );

  INSERT INTO `chat_messages` (`chat_id`, `sender_id`, `message_type`, `content`)
  SELECT v_c10, v_charlie_id, 'TEXT', '我已经到行政楼，门卫不让进。'
  WHERE NOT EXISTS (
    SELECT 1 FROM `chat_messages`
    WHERE `chat_id` = v_c10
      AND `sender_id` = v_charlie_id
      AND `content` = '我已经到行政楼，门卫不让进。'
  );

  INSERT INTO `chat_messages` (`chat_id`, `sender_id`, `message_type`, `content`)
  SELECT v_c10, v_bob_id, 'TEXT', '我这边显示你未到达，先发起申诉。'
  WHERE NOT EXISTS (
    SELECT 1 FROM `chat_messages`
    WHERE `chat_id` = v_c10
      AND `sender_id` = v_bob_id
      AND `content` = '我这边显示你未到达，先发起申诉。'
  );

  -- 6) 论坛帖子、评论、点赞
  INSERT INTO `posts` (`author_id`, `title`, `content`, `status`)
  SELECT v_alice_id, '联调帖-01-求推荐自习室', '晚上 9 点后人少的自习室有推荐吗？', 'NORMAL'
  WHERE NOT EXISTS (
    SELECT 1 FROM `posts` WHERE `title` = '联调帖-01-求推荐自习室'
  );

  INSERT INTO `posts` (`author_id`, `title`, `content`, `status`)
  SELECT v_bob_id, '联调帖-02-求代取资料', '明天上午帮忙取下实验资料。', 'NORMAL'
  WHERE NOT EXISTS (
    SELECT 1 FROM `posts` WHERE `title` = '联调帖-02-求代取资料'
  );

  INSERT INTO `post_comments` (`post_id`, `author_id`, `content`)
  SELECT p.`id`, v_charlie_id, '推荐理科楼 3 楼，晚上比较安静。'
  FROM `posts` p
  WHERE p.`title` = '联调帖-01-求推荐自习室'
    AND NOT EXISTS (
      SELECT 1 FROM `post_comments` c
      WHERE c.`post_id` = p.`id`
        AND c.`author_id` = v_charlie_id
        AND c.`content` = '推荐理科楼 3 楼，晚上比较安静。'
    );

  INSERT INTO `post_comments` (`post_id`, `author_id`, `content`)
  SELECT p.`id`, v_diana_id, '我这边明早有空，可以帮你取。'
  FROM `posts` p
  WHERE p.`title` = '联调帖-02-求代取资料'
    AND NOT EXISTS (
      SELECT 1 FROM `post_comments` c
      WHERE c.`post_id` = p.`id`
        AND c.`author_id` = v_diana_id
        AND c.`content` = '我这边明早有空，可以帮你取。'
    );

  INSERT INTO `post_likes` (`post_id`, `user_id`)
  SELECT p.`id`, v_bob_id
  FROM `posts` p
  WHERE p.`title` = '联调帖-01-求推荐自习室'
  ON DUPLICATE KEY UPDATE `created_at` = `created_at`;

  INSERT INTO `post_likes` (`post_id`, `user_id`)
  SELECT p.`id`, v_alice_id
  FROM `posts` p
  WHERE p.`title` = '联调帖-02-求代取资料'
  ON DUPLICATE KEY UPDATE `created_at` = `created_at`;

  -- 7) 已完成任务评价（任务 9）
  INSERT INTO `task_reviews` (`task_id`, `reviewer_id`, `reviewee_id`, `rating`, `content`)
  VALUES
    (v_t9, v_alice_id, v_diana_id, 5, '交付及时，沟通顺畅。'),
    (v_t9, v_diana_id, v_alice_id, 5, '需求描述清晰，确认很快。')
  ON DUPLICATE KEY UPDATE
    `rating` = VALUES(`rating`),
    `content` = VALUES(`content`);

  -- 8) 任务 9 的积分流水（一次性）
  SELECT COUNT(1) INTO v_exists
  FROM `point_ledger`
  WHERE `user_id` = v_diana_id
    AND `point_type` = 'HELP'
    AND `biz_type` = 'TASK_COMPLETE'
    AND `biz_id` = v_t9;
  IF v_exists = 0 THEN
    CALL `sp_add_points`(v_diana_id, 'HELP', 3, 'TASK_COMPLETE', v_t9, '联调任务完成奖励');
  END IF;

  SELECT COUNT(1) INTO v_exists
  FROM `point_ledger`
  WHERE `user_id` = v_diana_id
    AND `point_type` = 'HONOR'
    AND `biz_type` = 'TASK_COMPLETE'
    AND `biz_id` = v_t9;
  IF v_exists = 0 THEN
    CALL `sp_add_points`(v_diana_id, 'HONOR', 2, 'TASK_COMPLETE', v_t9, '联调任务完成奖励');
  END IF;

  SELECT COUNT(1) INTO v_exists
  FROM `point_ledger`
  WHERE `user_id` = v_alice_id
    AND `point_type` = 'HONOR'
    AND `biz_type` = 'TASK_CONFIRM'
    AND `biz_id` = v_t9;
  IF v_exists = 0 THEN
    CALL `sp_add_points`(v_alice_id, 'HONOR', 1, 'TASK_CONFIRM', v_t9, '联调任务确认奖励');
  END IF;

  -- 9) 举报与管理处理（任务 10）
  INSERT INTO `reports` (
    `reporter_id`, `target_type`, `target_id`, `reason_code`, `reason_text`,
    `status`, `handler_admin_id`, `handle_result`, `handled_at`
  )
  SELECT
    v_bob_id, 'TASK', v_t10, 'DISPUTE', '任务履约存在争议，申请平台仲裁',
    'PROCESSING', v_admin_id, NULL, NULL
  WHERE NOT EXISTS (
    SELECT 1 FROM `reports`
    WHERE `reporter_id` = v_bob_id
      AND `target_type` = 'TASK'
      AND `target_id` = v_t10
      AND `reason_code` = 'DISPUTE'
  );

  INSERT INTO `reports` (
    `reporter_id`, `target_type`, `target_id`, `reason_code`, `reason_text`,
    `status`, `handler_admin_id`, `handle_result`, `handled_at`
  )
  SELECT
    v_alice_id, 'POST',
    p.`id`,
    'SPAM', '疑似重复发布',
    'RESOLVED', v_admin_id, '提醒后保留内容', NOW(3)
  FROM `posts` p
  WHERE p.`title` = '联调帖-02-求代取资料'
    AND NOT EXISTS (
      SELECT 1 FROM `reports` r
      WHERE r.`reporter_id` = v_alice_id
        AND r.`target_type` = 'POST'
        AND r.`target_id` = p.`id`
        AND r.`reason_code` = 'SPAM'
    );

  INSERT INTO `admin_operation_logs` (`admin_user_id`, `operation_type`, `target_type`, `target_id`, `detail`)
  SELECT v_admin_id, 'REPORT_REVIEW', 'TASK', v_t10, '已受理任务争议，等待补充证据'
  WHERE NOT EXISTS (
    SELECT 1 FROM `admin_operation_logs`
    WHERE `admin_user_id` = v_admin_id
      AND `operation_type` = 'REPORT_REVIEW'
      AND `target_type` = 'TASK'
      AND `target_id` = v_t10
  );

  INSERT INTO `admin_operation_logs` (`admin_user_id`, `operation_type`, `target_type`, `target_id`, `detail`)
  SELECT
    v_admin_id, 'REPORT_REVIEW', 'POST', p.`id`, '判定非恶意，提醒用户减少重复发帖'
  FROM `posts` p
  WHERE p.`title` = '联调帖-02-求代取资料'
    AND NOT EXISTS (
      SELECT 1 FROM `admin_operation_logs` l
      WHERE l.`admin_user_id` = v_admin_id
        AND l.`operation_type` = 'REPORT_REVIEW'
        AND l.`target_type` = 'POST'
        AND l.`target_id` = p.`id`
    );

  -- 10) 标记已完成，避免重复造数
  INSERT INTO `system_configs` (`config_key`, `config_value`, `description`)
  VALUES (
    'seed.mock_data_v0_1_applied',
    JSON_OBJECT('applied_at', DATE_FORMAT(NOW(3), '%Y-%m-%d %H:%i:%s.%f')),
    '联调数据 v0.1 已导入'
  );
END $$

CALL `sp_seed_mock_data_v0_1` () $$
DROP PROCEDURE IF EXISTS `sp_seed_mock_data_v0_1` $$

DELIMITER ;
