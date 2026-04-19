-- CampusHelpATW
-- MySQL Schema v0.1
-- 目标：支撑 MVP 闭环（认证、任务、聊天、评价、积分、举报、社区）
-- 兼容：MySQL 8.0+

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE DATABASE IF NOT EXISTS `campus_help_atw`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;

USE `campus_help_atw`;

-- =========================
-- 1) 用户与认证
-- =========================

CREATE TABLE IF NOT EXISTS `users` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `campus_email` VARCHAR(128) NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `nickname` VARCHAR(64) NOT NULL,
  `avatar_url` VARCHAR(512) DEFAULT NULL,
  `school_name` VARCHAR(128) DEFAULT NULL,
  `college_name` VARCHAR(128) DEFAULT NULL,
  `reputation_score` INT NOT NULL DEFAULT 0,
  `help_points_balance` INT NOT NULL DEFAULT 0,
  `honor_points_balance` INT NOT NULL DEFAULT 0,
  `status` VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_users_campus_email` (`campus_email`),
  KEY `idx_users_status_created_at` (`status`, `created_at`),
  CONSTRAINT `chk_users_status` CHECK (`status` IN ('ACTIVE', 'SUSPENDED', 'BANNED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `email_verification_codes` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `campus_email` VARCHAR(128) NOT NULL,
  `code_hash` VARCHAR(255) NOT NULL,
  `expire_at` DATETIME(3) NOT NULL,
  `used_at` DATETIME(3) DEFAULT NULL,
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  KEY `idx_email_codes_email_expire_at` (`campus_email`, `expire_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- =========================
-- 2) 任务主链路
-- =========================

CREATE TABLE IF NOT EXISTS `tasks` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `publisher_id` BIGINT UNSIGNED NOT NULL,
  `acceptor_id` BIGINT UNSIGNED DEFAULT NULL,
  `title` VARCHAR(128) NOT NULL,
  `description` TEXT NOT NULL,
  `category` VARCHAR(32) NOT NULL,
  `location_text` VARCHAR(255) DEFAULT NULL,
  `reward_amount` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  `reward_type` VARCHAR(16) NOT NULL DEFAULT 'NONE',
  `deadline_at` DATETIME(3) NOT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'OPEN',
  `accepted_at` DATETIME(3) DEFAULT NULL,
  `completed_at` DATETIME(3) DEFAULT NULL,
  `canceled_at` DATETIME(3) DEFAULT NULL,
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  KEY `idx_tasks_status_category_created_at` (`status`, `category`, `created_at`),
  KEY `idx_tasks_publisher_created_at` (`publisher_id`, `created_at`),
  KEY `idx_tasks_acceptor_created_at` (`acceptor_id`, `created_at`),
  CONSTRAINT `fk_tasks_publisher` FOREIGN KEY (`publisher_id`) REFERENCES `users` (`id`),
  CONSTRAINT `fk_tasks_acceptor` FOREIGN KEY (`acceptor_id`) REFERENCES `users` (`id`),
  CONSTRAINT `chk_tasks_publisher_not_acceptor` CHECK (`acceptor_id` IS NULL OR `publisher_id` <> `acceptor_id`),
  CONSTRAINT `chk_tasks_reward_amount` CHECK (`reward_amount` >= 0),
  CONSTRAINT `chk_tasks_reward_type` CHECK (`reward_type` IN ('NONE', 'CASH', 'POINTS')),
  CONSTRAINT `chk_tasks_status` CHECK (`status` IN (
    'OPEN', 'ACCEPTED', 'IN_PROGRESS', 'PENDING_CONFIRM', 'DONE', 'CANCELED', 'DISPUTED'
  ))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `task_status_logs` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `task_id` BIGINT UNSIGNED NOT NULL,
  `from_status` VARCHAR(32) DEFAULT NULL,
  `to_status` VARCHAR(32) NOT NULL,
  `operator_user_id` BIGINT UNSIGNED NOT NULL,
  `reason` VARCHAR(255) DEFAULT NULL,
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  KEY `idx_task_status_logs_task_created_at` (`task_id`, `created_at`),
  CONSTRAINT `fk_task_status_logs_task` FOREIGN KEY (`task_id`) REFERENCES `tasks` (`id`),
  CONSTRAINT `fk_task_status_logs_operator` FOREIGN KEY (`operator_user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `chk_task_status_logs_to_status` CHECK (`to_status` IN (
    'OPEN', 'ACCEPTED', 'IN_PROGRESS', 'PENDING_CONFIRM', 'DONE', 'CANCELED', 'DISPUTED'
  ))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `task_reviews` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `task_id` BIGINT UNSIGNED NOT NULL,
  `reviewer_id` BIGINT UNSIGNED NOT NULL,
  `reviewee_id` BIGINT UNSIGNED NOT NULL,
  `rating` TINYINT UNSIGNED NOT NULL,
  `content` VARCHAR(500) DEFAULT NULL,
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_task_reviews_task_reviewer` (`task_id`, `reviewer_id`),
  KEY `idx_task_reviews_reviewee_created_at` (`reviewee_id`, `created_at`),
  CONSTRAINT `fk_task_reviews_task` FOREIGN KEY (`task_id`) REFERENCES `tasks` (`id`),
  CONSTRAINT `fk_task_reviews_reviewer` FOREIGN KEY (`reviewer_id`) REFERENCES `users` (`id`),
  CONSTRAINT `fk_task_reviews_reviewee` FOREIGN KEY (`reviewee_id`) REFERENCES `users` (`id`),
  CONSTRAINT `chk_task_reviews_rating` CHECK (`rating` BETWEEN 1 AND 5),
  CONSTRAINT `chk_task_reviews_reviewer_not_reviewee` CHECK (`reviewer_id` <> `reviewee_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `point_ledger` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT UNSIGNED NOT NULL,
  `point_type` VARCHAR(16) NOT NULL,
  `change_amount` INT NOT NULL,
  `balance_after` INT NOT NULL,
  `biz_type` VARCHAR(32) NOT NULL,
  `biz_id` BIGINT UNSIGNED DEFAULT NULL,
  `remark` VARCHAR(255) DEFAULT NULL,
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  KEY `idx_point_ledger_user_type_created_at` (`user_id`, `point_type`, `created_at`),
  KEY `idx_point_ledger_biz` (`biz_type`, `biz_id`),
  CONSTRAINT `fk_point_ledger_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `chk_point_ledger_point_type` CHECK (`point_type` IN ('HELP', 'HONOR'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- =========================
-- 3) 社区（论坛与关系）
-- =========================

CREATE TABLE IF NOT EXISTS `posts` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `author_id` BIGINT UNSIGNED NOT NULL,
  `title` VARCHAR(128) NOT NULL,
  `content` TEXT NOT NULL,
  `like_count` INT UNSIGNED NOT NULL DEFAULT 0,
  `comment_count` INT UNSIGNED NOT NULL DEFAULT 0,
  `status` VARCHAR(16) NOT NULL DEFAULT 'NORMAL',
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  KEY `idx_posts_author_created_at` (`author_id`, `created_at`),
  KEY `idx_posts_status_created_at` (`status`, `created_at`),
  CONSTRAINT `fk_posts_author` FOREIGN KEY (`author_id`) REFERENCES `users` (`id`),
  CONSTRAINT `chk_posts_status` CHECK (`status` IN ('NORMAL', 'HIDDEN', 'DELETED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `post_comments` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `post_id` BIGINT UNSIGNED NOT NULL,
  `author_id` BIGINT UNSIGNED NOT NULL,
  `content` VARCHAR(1000) NOT NULL,
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  KEY `idx_post_comments_post_created_at` (`post_id`, `created_at`),
  CONSTRAINT `fk_post_comments_post` FOREIGN KEY (`post_id`) REFERENCES `posts` (`id`),
  CONSTRAINT `fk_post_comments_author` FOREIGN KEY (`author_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `post_likes` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `post_id` BIGINT UNSIGNED NOT NULL,
  `user_id` BIGINT UNSIGNED NOT NULL,
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_post_likes_post_user` (`post_id`, `user_id`),
  KEY `idx_post_likes_user_created_at` (`user_id`, `created_at`),
  CONSTRAINT `fk_post_likes_post` FOREIGN KEY (`post_id`) REFERENCES `posts` (`id`),
  CONSTRAINT `fk_post_likes_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- =========================
-- 4) 聊天（任务会话）
-- =========================

CREATE TABLE IF NOT EXISTS `task_chats` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `task_id` BIGINT UNSIGNED NOT NULL,
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_task_chats_task_id` (`task_id`),
  CONSTRAINT `fk_task_chats_task` FOREIGN KEY (`task_id`) REFERENCES `tasks` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `chat_messages` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `chat_id` BIGINT UNSIGNED NOT NULL,
  `sender_id` BIGINT UNSIGNED NOT NULL,
  `message_type` VARCHAR(16) NOT NULL DEFAULT 'TEXT',
  `content` TEXT NOT NULL,
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  KEY `idx_chat_messages_chat_created_at` (`chat_id`, `created_at`),
  CONSTRAINT `fk_chat_messages_chat` FOREIGN KEY (`chat_id`) REFERENCES `task_chats` (`id`),
  CONSTRAINT `fk_chat_messages_sender` FOREIGN KEY (`sender_id`) REFERENCES `users` (`id`),
  CONSTRAINT `chk_chat_messages_message_type` CHECK (`message_type` IN ('TEXT', 'IMAGE', 'SYSTEM'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `task_chat_read_cursors` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `chat_id` BIGINT UNSIGNED NOT NULL,
  `user_id` BIGINT UNSIGNED NOT NULL,
  `last_read_message_id` BIGINT UNSIGNED NOT NULL DEFAULT 0,
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_task_chat_read_cursors_chat_user` (`chat_id`, `user_id`),
  KEY `idx_task_chat_read_cursors_user_updated_at` (`user_id`, `updated_at`),
  CONSTRAINT `fk_task_chat_read_cursors_chat` FOREIGN KEY (`chat_id`) REFERENCES `task_chats` (`id`),
  CONSTRAINT `fk_task_chat_read_cursors_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- =========================
-- 5) 举报与管理操作
-- =========================

CREATE TABLE IF NOT EXISTS `reports` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `reporter_id` BIGINT UNSIGNED NOT NULL,
  `target_type` VARCHAR(32) NOT NULL,
  `target_id` BIGINT UNSIGNED NOT NULL,
  `reason_code` VARCHAR(32) NOT NULL,
  `reason_text` VARCHAR(500) DEFAULT NULL,
  `status` VARCHAR(16) NOT NULL DEFAULT 'PENDING',
  `handler_admin_id` BIGINT UNSIGNED DEFAULT NULL,
  `handle_result` VARCHAR(500) DEFAULT NULL,
  `handled_at` DATETIME(3) DEFAULT NULL,
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  KEY `idx_reports_target` (`target_type`, `target_id`),
  KEY `idx_reports_status_created_at` (`status`, `created_at`),
  KEY `idx_reports_reporter_created_at` (`reporter_id`, `created_at`),
  CONSTRAINT `fk_reports_reporter` FOREIGN KEY (`reporter_id`) REFERENCES `users` (`id`),
  CONSTRAINT `fk_reports_handler_admin` FOREIGN KEY (`handler_admin_id`) REFERENCES `users` (`id`),
  CONSTRAINT `chk_reports_target_type` CHECK (`target_type` IN ('TASK', 'POST', 'CHAT_MESSAGE', 'USER')),
  CONSTRAINT `chk_reports_status` CHECK (`status` IN ('PENDING', 'PROCESSING', 'RESOLVED', 'REJECTED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `admin_operation_logs` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `admin_user_id` BIGINT UNSIGNED NOT NULL,
  `operation_type` VARCHAR(32) NOT NULL,
  `target_type` VARCHAR(32) NOT NULL,
  `target_id` BIGINT UNSIGNED NOT NULL,
  `detail` TEXT DEFAULT NULL,
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  KEY `idx_admin_logs_admin_created_at` (`admin_user_id`, `created_at`),
  KEY `idx_admin_logs_target` (`target_type`, `target_id`),
  CONSTRAINT `fk_admin_logs_admin_user` FOREIGN KEY (`admin_user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;

-- 说明：
-- 1) 任务状态机合法性（如 OPEN->ACCEPTED）建议在应用层强校验，必要时可加触发器兜底。
-- 2) 积分变更请务必在事务中同时更新 users 余额和 point_ledger 流水。
-- 3) 当前 DDL 只提供结构，不包含初始化管理员账号与业务种子数据。
