# Flyway 迁移说明（MySQL）

## 1. 文件顺序
1. `V1__core_schema.sql`：核心业务表结构。
2. `V2__seed_data.sql`：初始化分类、默认配置、管理员与演示数据。
3. `V3__guards_and_procedures.sql`：状态流转守卫触发器与事务过程。
4. `V4__chat_read_cursor.sql`：聊天已读游标表，支持服务端未读统计。

说明：
联调样例数据不放在 Flyway 主迁移链，避免误入生产环境。
需要联调数据时，请手工执行 `docs/sql/mysql_mock_data_v0.1.sql`。

## 2. 前置要求
1. MySQL 8.0+。
2. 已手动创建目标数据库（例如 `campus_help_atw`）。
3. Flyway 已配置 `url/user/password`，并指向上述数据库。

## 3. 本地执行示例

```bash
flyway \
  -url=jdbc:mysql://127.0.0.1:3306/campus_help_atw \
  -user=root \
  -password=your_password \
  -locations=filesystem:docs/migrations/flyway \
  migrate
```

## 4. 回滚建议
当前脚本未提供自动 down migration。
建议在测试环境使用库级快照或临时库做回滚演练。

## 5. 注意事项
1. 演示账号仅用于本地环境，生产环境请替换密码哈希与邮箱。
2. 任务状态流转规则由触发器兜底，业务层仍应保持同等校验。
3. 积分相关写操作建议统一调用 `sp_add_points`，避免余额与流水不一致。
