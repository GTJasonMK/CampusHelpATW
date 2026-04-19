-- CampusHelpATW
-- Flyway V2: Seed Data
-- 目标：初始化管理员、基础任务分类、默认系统配置、演示账号
-- 依赖：先执行 V1__core_schema.sql

SET NAMES utf8mb4;

-- =========================
-- 1) 配置表（MVP 扩展）
-- =========================

CREATE TABLE IF NOT EXISTS `task_categories` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `code` VARCHAR(32) NOT NULL,
  `name` VARCHAR(64) NOT NULL,
  `sort_order` INT NOT NULL DEFAULT 0,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_task_categories_code` (`code`),
  KEY `idx_task_categories_active_sort` (`is_active`, `sort_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `system_configs` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `config_key` VARCHAR(128) NOT NULL,
  `config_value` JSON NOT NULL,
  `description` VARCHAR(255) DEFAULT NULL,
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_system_configs_key` (`config_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `admin_roles` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `role_code` VARCHAR(32) NOT NULL,
  `role_name` VARCHAR(64) NOT NULL,
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_admin_roles_code` (`role_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `admin_user_roles` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT UNSIGNED NOT NULL,
  `role_id` BIGINT UNSIGNED NOT NULL,
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_admin_user_roles_user_role` (`user_id`, `role_id`),
  KEY `idx_admin_user_roles_role` (`role_id`),
  CONSTRAINT `fk_admin_user_roles_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `fk_admin_user_roles_role` FOREIGN KEY (`role_id`) REFERENCES `admin_roles` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- =========================
-- 2) 基础任务分类
-- =========================

INSERT INTO `task_categories` (`code`, `name`, `sort_order`, `is_active`)
VALUES
  ('ERRAND', '跑腿代办', 10, 1),
  ('STUDY', '学习辅导', 20, 1),
  ('LIFE', '生活互助', 30, 1),
  ('DOC', '资料代取', 40, 1),
  ('OTHER', '其他', 99, 1)
ON DUPLICATE KEY UPDATE
  `name` = VALUES(`name`),
  `sort_order` = VALUES(`sort_order`),
  `is_active` = VALUES(`is_active`);

-- =========================
-- 3) 默认系统配置
-- =========================

INSERT INTO `system_configs` (`config_key`, `config_value`, `description`)
VALUES
  (
    'points.publish_cost',
    JSON_OBJECT('help_points', 1),
    '发布任务消耗的帮助点'
  ),
  (
    'points.task_complete_reward',
    JSON_OBJECT('help_points', 3, 'honor_points', 2),
    '任务完成后帮助者奖励'
  ),
  (
    'points.publisher_confirm_reward',
    JSON_OBJECT('honor_points', 1),
    '发布者按时确认完成奖励'
  ),
  (
    'risk.daily_task_publish_limit',
    JSON_OBJECT('count', 5),
    '单用户日发任务上限'
  ),
  (
    'risk.daily_post_limit',
    JSON_OBJECT('count', 20),
    '单用户日发帖上限'
  )
ON DUPLICATE KEY UPDATE
  `config_value` = VALUES(`config_value`),
  `description` = VALUES(`description`);

-- =========================
-- 4) 管理员与演示账号
-- =========================
-- 默认明文密码（仅本地开发）：ChangeMe123!
-- 对应 bcrypt hash（示例，请上线前替换）

INSERT INTO `users` (
  `campus_email`, `password_hash`, `nickname`, `school_name`, `college_name`,
  `reputation_score`, `help_points_balance`, `honor_points_balance`, `status`
)
VALUES
  (
    'admin@campus.local',
    '$2b$12$8f2FG8rN5m8nU9x9C2hI3eX7xVd8xg4wIgjlUi1xjtcgYjNAn8HzS',
    '系统管理员',
    'CampusHelpATW',
    '平台运营',
    100,
    1000,
    1000,
    'ACTIVE'
  ),
  (
    'alice@campus.local',
    '$2b$12$8f2FG8rN5m8nU9x9C2hI3eX7xVd8xg4wIgjlUi1xjtcgYjNAn8HzS',
    'Alice',
    'CampusHelpATW',
    '计算机学院',
    10,
    20,
    5,
    'ACTIVE'
  ),
  (
    'bob@campus.local',
    '$2b$12$8f2FG8rN5m8nU9x9C2hI3eX7xVd8xg4wIgjlUi1xjtcgYjNAn8HzS',
    'Bob',
    'CampusHelpATW',
    '信息工程学院',
    8,
    15,
    4,
    'ACTIVE'
  )
ON DUPLICATE KEY UPDATE
  `nickname` = VALUES(`nickname`),
  `school_name` = VALUES(`school_name`),
  `college_name` = VALUES(`college_name`),
  `status` = VALUES(`status`);

INSERT INTO `admin_roles` (`role_code`, `role_name`)
VALUES
  ('SUPER_ADMIN', '超级管理员'),
  ('CONTENT_MODERATOR', '内容审核员')
ON DUPLICATE KEY UPDATE
  `role_name` = VALUES(`role_name`);

SET @seed_admin_user_id := (
  SELECT `id` FROM `users` WHERE `campus_email` = 'admin@campus.local' LIMIT 1
);
SET @seed_super_admin_role_id := (
  SELECT `id` FROM `admin_roles` WHERE `role_code` = 'SUPER_ADMIN' LIMIT 1
);

INSERT INTO `admin_user_roles` (`user_id`, `role_id`)
VALUES (@seed_admin_user_id, @seed_super_admin_role_id)
ON DUPLICATE KEY UPDATE
  `updated_at` = CURRENT_TIMESTAMP(3);

-- =========================
-- 5) 演示任务与积分流水（可删）
-- =========================

SET @seed_alice_id := (
  SELECT `id` FROM `users` WHERE `campus_email` = 'alice@campus.local' LIMIT 1
);
SET @seed_bob_id := (
  SELECT `id` FROM `users` WHERE `campus_email` = 'bob@campus.local' LIMIT 1
);

INSERT INTO `tasks` (
  `publisher_id`, `acceptor_id`, `title`, `description`, `category`, `location_text`,
  `reward_amount`, `reward_type`, `deadline_at`, `status`, `accepted_at`, `completed_at`
)
SELECT
  @seed_alice_id, @seed_bob_id, '代取快递', '请今晚 8 点前帮忙代取东区快递',
  'ERRAND', '东区菜鸟驿站', 5.00, 'CASH',
  DATE_ADD(NOW(3), INTERVAL 1 DAY), 'DONE', NOW(3), NOW(3)
WHERE NOT EXISTS (
  SELECT 1 FROM `tasks`
  WHERE `publisher_id` = @seed_alice_id
    AND `acceptor_id` = @seed_bob_id
    AND `title` = '代取快递'
    AND `status` = 'DONE'
);
