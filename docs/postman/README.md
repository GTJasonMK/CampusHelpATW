# Postman / Apifox 联调说明

## 1. 文件说明
1. `CampusHelpATW_MVP_联调.postman_collection.json`：接口集合。
2. `CampusHelpATW_MVP_联调.postman_environment.json`：本地环境变量模板。

## 2. 导入步骤（Postman）
1. Import 集合文件。
2. Import 环境文件并激活 `CampusHelpATW-Local`。
3. 按顺序执行：
   - `00-登录与令牌/登录-Alice`
   - `00-登录与令牌/登录-Bob`
   - `00-登录与令牌/登录-Admin`
   - `01-任务主链路/任务列表-抓取联调任务ID`
   - `02-聊天与评价积分/获取任务聊天会话`
   - `02-聊天与评价积分/查询我的聊天未读统计`
   - `02-聊天与评价积分/标记聊天已读`
4. 然后执行其他接口进行联调。

## 3. 导入步骤（Apifox）
1. 新建项目 -> 导入 -> Postman Collection v2.1。
2. 选择集合文件 `CampusHelpATW_MVP_联调.postman_collection.json`。
3. 在 Apifox 环境变量中补齐：
   - `baseUrl`
   - `verifyCode`
   - `devPassword`
   - `aliceEmail` / `bobEmail` / `adminEmail`
4. 执行顺序与 Postman 一致。

## 4. 使用注意
1. 集合默认使用 `{{token}}` 作为 Bearer Token。
2. 登录请求会自动把 token 写入集合变量（`aliceToken`/`bobToken`/`adminToken`）。
3. `任务列表-抓取联调任务ID` 会尝试自动提取联调任务ID。
4. 如果你的返回结构与文档不一致，请调整对应请求的 `Tests` 脚本取值路径。
5. 未读相关请求依赖 `chat_id`，请先执行“获取任务聊天会话”。
