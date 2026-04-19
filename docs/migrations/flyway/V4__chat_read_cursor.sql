-- CampusHelpATW
-- Flyway V4: Chat Read Cursor
-- 目标：支持服务端未读统计与已读同步
-- 依赖：先执行 V1__core_schema.sql

SET NAMES utf8mb4;

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
