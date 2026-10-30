-- 创建数据库
CREATE DATABASE IF NOT EXISTS agent_center
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_bin;


-- 创建应用信息表
CREATE TABLE  `app_info` (
	`id` BIGINT NOT NULL COMMENT '数据id',
	`app_key` VARCHAR(64) NOT NULL COMMENT '应用key' COLLATE 'utf8mb4_bin',
	`app_secret` VARCHAR(64) NOT NULL COMMENT '应用秘钥' COLLATE 'utf8mb4_bin',
	`name` VARCHAR(32) NULL DEFAULT NULL COMMENT '应用名称' COLLATE 'utf8mb4_bin',
	`create_time` DATETIME NOT NULL DEFAULT (now()) COMMENT '创建时间',
	`update_time` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
	PRIMARY KEY (`id`) USING BTREE,
	INDEX `app_key` (`app_key`) USING BTREE
)
COMMENT='应用信息表'
COLLATE='utf8mb4_bin'
ENGINE=InnoDB
;


-- 插入天机AI业务的数据
INSERT INTO `app_info` (`id`, `app_key`, `app_secret`, `name`, `create_time`, `update_time`) VALUES (7388495056530878465, 'ddd8c127b3c1baa5f2ca7280d287a102', '5ca5087fd74a5afd5cb1cad3016e4980', '天机AI助手', '2025-10-27 16:43:27', '2025-10-27 16:43:34');


-- 创建对话session表
CREATE TABLE `chat_session` (
	`id` BIGINT NOT NULL COMMENT '数据id',
	`session_id` VARCHAR(32) NOT NULL COMMENT '会话id' COLLATE 'utf8mb4_bin',
	`user_id` BIGINT NOT NULL DEFAULT '0' COMMENT '用户id',
	`agent_id` BIGINT NOT NULL COMMENT '智能体id',
	`title` VARCHAR(100) NULL DEFAULT NULL COMMENT '会话标题' COLLATE 'utf8mb4_bin',
	`create_time` DATETIME NOT NULL DEFAULT (now()) COMMENT '创建时间',
	`update_time` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
	PRIMARY KEY (`id`) USING BTREE,
	INDEX `session_id_index` (`session_id`) USING BTREE,
	INDEX `user_id_index` (`user_id`) USING BTREE,
	INDEX `update_time_index` (`update_time`) USING BTREE,
	INDEX `agent_id_index` (`agent_id`) USING BTREE
)
COMMENT='对话session'
COLLATE='utf8mb4_bin'
ENGINE=InnoDB
;
