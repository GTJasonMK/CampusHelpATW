# MySQL 脚本执行说明（直接 SQL 方式）

## 1. 执行顺序
1. `mysql_schema_v0.1.sql`：创建核心业务表。
2. `mysql_seed_v0.1.sql`：初始化分类、配置、管理员、演示数据。
3. `mysql_guards_v0.1.sql`：创建状态守卫触发器和存储过程。
4. `mysql_mock_data_v0.1.sql`：生成联调用样例数据（10条任务+聊天+评价+举报）。
5. `mysql_sanity_checks_v0.1.sql`：执行联调验收检查查询。
6. `mysql_mock_data_cleanup_v0.1.sql`：清理联调样例数据（需显式确认）。

## 2. 执行示例

```bash
mysql -u root -p < docs/sql/mysql_schema_v0.1.sql
mysql -u root -p < docs/sql/mysql_seed_v0.1.sql
mysql -u root -p < docs/sql/mysql_guards_v0.1.sql
mysql -u root -p < docs/sql/mysql_mock_data_v0.1.sql
mysql -u root -p < docs/sql/mysql_sanity_checks_v0.1.sql
# 需要回收联调数据时再执行
mysql -u root -p < docs/sql/mysql_mock_data_cleanup_v0.1.sql
```

## 3. 说明
1. 默认数据库名：`campus_help_atw`（已在 schema 脚本中创建）。
2. 演示账号密码哈希仅用于开发环境，生产环境必须替换。
3. 触发器用于兜底状态校验，业务层仍应保持同样的状态机验证。
4. 联调数据脚本默认只生效一次，会写入 `seed.mock_data_v0_1_applied` 配置标记。
5. 清理脚本会删除联调数据，执行前请确认环境不是生产环境。
