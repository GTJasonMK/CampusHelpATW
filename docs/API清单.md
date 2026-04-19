# CampusHelpATW API 清单（MVP 草案）

## 1. 说明
1. 协议：HTTP + JSON（后续可加 WebSocket 用于实时聊天）。
2. 鉴权：`Authorization: Bearer <token>`。
3. 响应格式建议：

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

4. 错误码建议：
- `0` 成功
- `4001` 参数错误
- `4003` 未登录或 token 失效
- `4004` 资源不存在
- `4009` 状态不允许
- `4011` 请求频率超限
- `5000` 服务器错误

## 2. 认证模块

### 2.1 发送邮箱验证码
`POST /api/v1/auth/email/send-code`

请求体：
```json
{
  "campus_email": "user@school.edu"
}
```

### 2.2 校验验证码并注册/登录
`POST /api/v1/auth/email/verify`

请求体：
```json
{
  "campus_email": "user@school.edu",
  "code": "123456",
  "password": "xxx"
}
```

返回：
```json
{
  "token": "jwt-token",
  "user": {
    "id": 1,
    "nickname": "Jason"
  }
}
```

### 2.3 获取当前用户信息
`GET /api/v1/me`

### 2.4 更新个人资料
`PATCH /api/v1/me/profile`

请求体（可选字段）：
```json
{
  "nickname": "新昵称",
  "avatar_url": "https://...",
  "college_name": "计算机学院"
}
```

### 2.5 获取当前用户权限
`GET /api/v1/me/permissions`

返回示例：
```json
{
  "is_admin": true,
  "can_manage_community": true,
  "role_codes": ["CONTENT_MODERATOR"]
}
```

## 3. 任务模块

### 3.1 创建任务
`POST /api/v1/tasks`

请求体：
```json
{
  "title": "代取快递",
  "description": "今晚7点前帮取",
  "category": "ERRAND",
  "location_text": "东区菜鸟驿站",
  "reward_amount": 5,
  "reward_type": "CASH",
  "deadline_at": "2026-03-01T19:00:00+08:00"
}
```

说明：
1. 发任务会扣除帮助点（`TASK_PUBLISH` 流水）。
2. 当帮助点不足时，创建会失败。
3. 发任务接口有基础限流（单位时间内请求上限）。

### 3.2 任务列表
`GET /api/v1/tasks?status=OPEN&category=ERRAND&page=1&page_size=20`

可选参数：
1. `include_unread=true|false`（默认 `true`）  
2. 当 `include_unread=true` 时，列表项会包含 `unread_count` 字段，响应里还会返回 `total_unread`。
3. 列表项附带 `publisher_user` / `acceptor_user` 简要信息（昵称、头像、院校）。

### 3.3 任务详情
`GET /api/v1/tasks/{task_id}`

可选参数：
1. `include_unread=true|false`（默认 `true`）  
2. 当 `include_unread=true` 时，响应里会包含该任务的 `unread_count`。
3. 响应附带 `publisher_user` / `acceptor_user` 简要信息（昵称、头像、院校）。

### 3.4 接单
`POST /api/v1/tasks/{task_id}/accept`

约束：
1. 仅 `OPEN` 状态可接单。
2. 发布者不能接自己的单。

### 3.5 取消任务
`POST /api/v1/tasks/{task_id}/cancel`

请求体：
```json
{
  "reason": "时间冲突"
}
```

约束：
1. `OPEN` 状态仅发布者可取消。
2. `ACCEPTED/IN_PROGRESS` 状态仅任务参与者可取消。

### 3.6 标记进行中
`POST /api/v1/tasks/{task_id}/start`

### 3.7 提交完成
`POST /api/v1/tasks/{task_id}/submit-completion`

### 3.8 确认完成
`POST /api/v1/tasks/{task_id}/confirm-completion`

效果：
1. 任务状态改为 `DONE`。
2. 写入积分流水。

### 3.9 发起申诉
`POST /api/v1/tasks/{task_id}/dispute`

请求体：
```json
{
  "reason": "对方未按约定完成"
}
```

### 3.10 任务状态日志
`GET /api/v1/tasks/{task_id}/status-logs`

## 4. 任务聊天模块

### 4.1 获取任务聊天会话
`GET /api/v1/tasks/{task_id}/chat`

### 4.2 获取聊天消息
`GET /api/v1/chats/{chat_id}/messages?cursor=0&page_size=20`

### 4.3 发送聊天消息
`POST /api/v1/chats/{chat_id}/messages`

请求体：
```json
{
  "message_type": "TEXT",
  "content": "我已经到驿站了"
}
```

### 4.4 查询我的未读统计
`GET /api/v1/me/chats/unread`

返回示例：
```json
{
  "total_unread": 3,
  "items": [
    {
      "task_id": 1001,
      "chat_id": 501,
      "unread_count": 2,
      "latest_message_id": 9001,
      "last_read_message_id": 8998
    }
  ]
}
```

### 4.5 标记会话已读
`POST /api/v1/chats/{chat_id}/read`

请求体（可选）：
```json
{
  "last_read_message_id": 9001
}
```

### 4.6 WebSocket（任务聊天通道）
`GET /api/v1/ws/tasks/{task_id}?token={jwt}`

说明：
1. 用于任务聊天实时收发消息。
2. 支持客户端发送 `{"message_type":"PING"}` 心跳，服务端返回 `pong`。

### 4.7 WebSocket（全局通知通道）
`GET /api/v1/ws/me/notifications?token={jwt}`

说明：
1. 用于跨页面推送未读变化，驱动全局红点/角标更新。
2. 连接建立后服务端会先下发 `unread_snapshot`。
3. 聊天消息创建、会话已读时会下发 `chat_unread` 增量。
4. 任务关键动作（接单、提交完成、确认完成、取消、申诉、仲裁）会下发 `task_event`。

事件示例：
```json
{
  "event": "unread_snapshot",
  "reason": "connect",
  "user_id": 1,
  "total_unread": 3,
  "items": [
    {
      "task_id": 1001,
      "chat_id": 501,
      "unread_count": 2,
      "latest_message_id": 9001,
      "last_read_message_id": 8998
    }
  ],
  "ts": "2026-03-01T10:00:00Z"
}
```

```json
{
  "event": "chat_unread",
  "reason": "message_created",
  "user_id": 1,
  "task_id": 1001,
  "chat_id": 501,
  "unread_count": 3,
  "total_unread": 4,
  "latest_message_id": 9002,
  "last_read_message_id": 8998,
  "ts": "2026-03-01T10:01:00Z"
}
```

```json
{
  "event": "task_event",
  "task_id": 1001,
  "status": "PENDING_CONFIRM",
  "action": "submit_completion",
  "operator_user_id": 2,
  "reason": "已送达",
  "ts": "2026-03-01T10:02:00Z"
}
```

## 5. 评价与积分模块

### 5.1 提交评价
`POST /api/v1/tasks/{task_id}/reviews`

请求体：
```json
{
  "reviewee_id": 2,
  "rating": 5,
  "content": "沟通顺畅，准时完成"
}
```

### 5.2 查询用户公开资料
`GET /api/v1/users/{user_id}`

说明：
1. 返回用户基础公开信息（昵称、头像、院校、积分与信誉）。
2. 返回评价聚合信息：`review_count`、`review_avg_rating`。
3. 返回共同数据聚合：`shared_stats.common_task_count`。

### 5.3 查询用户评价列表
`GET /api/v1/users/{user_id}/reviews?page=1&page_size=20`

可选参数：
1. `rating=1..5`（按星级筛选）。
2. `with_content=true|false`（默认 `false`；`true` 时仅返回有文字内容的评价）。

### 5.4 查询共同任务列表
`GET /api/v1/users/{user_id}/shared/tasks?page=1&page_size=20`

说明：
1. 以“当前登录用户 + 目标用户”为维度，返回双方互为发布者/接单者的任务列表。
2. 可选参数：`status`（`OPEN/ACCEPTED/IN_PROGRESS/PENDING_CONFIRM/DONE/CANCELED/DISPUTED`）。
3. 可选参数：`sort`（`latest/deadline_asc/reward_desc`，默认 `latest`）。

### 5.5 查询积分流水
`GET /api/v1/me/points/ledger?point_type=HELP&page=1&page_size=20`

## 6. 论坛模块

### 6.1 发帖
`POST /api/v1/posts`

请求体：
```json
{
  "title": "求推荐自习室",
  "content": "晚上人少的地方有哪些？"
}
```

说明：
1. 发帖接口有基础限流（单位时间内请求上限）。

### 6.2 帖子列表
`GET /api/v1/posts?page=1&page_size=20&sort=latest`

### 6.3 帖子详情
`GET /api/v1/posts/{post_id}`

### 6.4 评论帖子
`POST /api/v1/posts/{post_id}/comments`

### 6.5 点赞/取消点赞
`POST /api/v1/posts/{post_id}/like`
`DELETE /api/v1/posts/{post_id}/like`

## 7. 举报与治理模块

### 7.1 提交举报
`POST /api/v1/reports`

请求体：
```json
{
  "target_type": "TASK",
  "target_id": 1001,
  "reason_code": "FRAUD",
  "reason_text": "疑似虚假任务"
}
```

### 7.2 查询我的举报
`GET /api/v1/reports/mine?page=1&page_size=20`

## 8. 管理端 API（后台）

### 8.1 举报列表
`GET /api/v1/admin/reports?status=PENDING&page=1&page_size=20`

### 8.2 处理举报
`POST /api/v1/admin/reports/{report_id}/handle`

请求体：
```json
{
  "action": "RESOLVE",
  "result": "下架违规内容并警告用户"
}
```

处理建议：
1. 当 `action=RESOLVE` 且举报目标为 `POST` 时，系统会自动将该帖子状态置为 `HIDDEN`（管理员仍可在帖子管理页恢复）。

### 8.3 任务仲裁
`POST /api/v1/admin/tasks/{task_id}/arbitrate`

请求体：
```json
{
  "decision": "MARK_DONE",
  "reason": "证据显示帮助者已完成"
}
```

### 8.4 分类管理（推荐）
`GET /api/v1/admin/task-categories`
`POST /api/v1/admin/task-categories`
`PATCH /api/v1/admin/task-categories/{category_id}`

说明：
1. 用于维护 `task_categories`，支持前端分类动态配置。
2. `GET` 支持 `is_active/page/page_size`。
3. `POST` 请求体示例：
```json
{
  "code": "ERRAND",
  "name": "跑腿代办",
  "sort_order": 10,
  "is_active": true
}
```
4. `PATCH` 支持部分更新（`code/name/sort_order/is_active`）。

### 8.5 系统配置管理（推荐）
`GET /api/v1/admin/system-configs`
`PUT /api/v1/admin/system-configs/{config_key}`

说明：
1. 用于维护积分规则、限流阈值等配置项。
2. `PUT` 为 upsert（不存在则创建，存在则更新）。
3. `PUT` 请求体示例：
```json
{
  "config_value": { "count": 10 },
  "description": "单用户日发任务上限"
}
```

### 8.6 论坛帖子管理（推荐）
`GET /api/v1/admin/posts`
`PATCH /api/v1/admin/posts/{post_id}/status`

说明：
1. `GET` 支持筛选参数：`status/category/sort/keyword/author_id/page/page_size`。
2. `status` 可选：`NORMAL/HIDDEN/DELETED`。
3. `category` 可选：`HELP/SHARE/RESOURCE/ALERT`。
4. `sort` 可选：`latest/hot`。
5. `PATCH` 请求体示例：
```json
{
  "status": "HIDDEN",
  "reason": "涉及违规内容"
}
```

### 8.7 学校特色样式管理（推荐）
`GET /api/v1/admin/school-branding`
`PUT /api/v1/admin/school-branding`

说明：
1. 该接口用于管理“学校特色层”，不会覆盖系统原生基础样式。
2. `PUT` 请求体格式与 `SystemConfigUpsertRequest` 一致，核心字段在 `config_value` 中。
3. `pattern_type` 支持：`none/dots/grid/diagonal/wave/oil`。
4. 推荐将花纹、贴纸、角标文案放在这里做学校差异化配置。
5. 若希望“系统配色可变但布局不变”，请在 `ui_tokens` 中配置颜色 token。

## 9. API 开发优先级

1. P0 第一批：
- 认证：`send-code`、`verify`、`me`
- 任务：创建、列表、详情、接单、取消、提交完成、确认完成
- 评价：提交评价
- 积分：积分流水查询

2. P0 第二批：
- 聊天：会话、消息拉取、消息发送
- 举报：提交举报
- 管理端：举报处理、任务仲裁

3. P1：
- 论坛增强接口

## 10. 接口测试建议

1. 单元测试：状态机校验、权限校验、积分结算。
2. 集成测试：从创建任务到完成评价全链路。
3. 安全测试：越权访问、重复提交、恶意参数。

## 11. 配置读取接口（前端）

### 11.1 任务分类列表
`GET /api/v1/meta/task-categories`

返回示例：
```json
[
  {
    "id": 1,
    "code": "ERRAND",
    "name": "跑腿代办",
    "sort_order": 10,
    "is_active": true
  },
  {
    "id": 2,
    "code": "STUDY",
    "name": "学习辅导",
    "sort_order": 20,
    "is_active": true
  }
]
```

说明：
1. 该接口默认仅返回 `is_active = true` 的分类。
2. 默认按 `sort_order ASC, id ASC` 排序。

### 11.2 信任等级规则
`GET /api/v1/meta/trust-level-rules`

返回示例：
```json
{
  "config_key": "trust_level_rules",
  "source": "system_config",
  "rules": [
    {
      "key": "pillar",
      "label": "校园支柱",
      "description": "你已形成稳定可信的互助履约记录。",
      "status_class": "status-done",
      "min_reputation": 100,
      "min_honor_points": 120,
      "min_help_points": 0
    }
  ]
}
```

说明：
1. `source` 取值：`default/system_config/system_config_invalid`。
2. 当系统配置格式异常时，会自动回退默认规则。

### 11.3 学校专属样式
`GET /api/v1/meta/school-branding`

返回示例：
```json
{
  "config_key": "school_branding",
  "source": "system_config",
  "defaults": {
    "short_name": "中石大互助",
    "emblem_text": "油",
    "badge_text": "CUP",
    "slogan": "能源报国，互助同行",
    "accent_color": "#005f3c",
    "badge_bg_color": "#e8f5ec",
    "badge_text_color": "#103b2d",
    "pattern_type": "oil",
    "pattern_color": "#0f6a4c",
    "pattern_opacity": 0.18,
    "pattern_size": 22,
    "sticker_text": "石油特色",
    "sticker_bg_color": "#fff3cd",
    "sticker_text_color": "#2d2d2d",
    "ribbon_text": "中国石油大学",
    "ui_tokens": {
      "paper_bg": "#f6fbf7",
      "paper_dot": "#d7e7dc",
      "ink": "#1f2f28",
      "card_bg": "#ffffff",
      "postit_bg": "#e8f5ec",
      "accent_bg": "#0f6a4c",
      "secondary_bg": "#dcece1",
      "secondary_text": "#1f2f28",
      "status_open_bg": "#eef8f0",
      "status_processing_bg": "#dceee3",
      "status_done_bg": "#d6f0df",
      "status_danger_bg": "#ffd9d9",
      "muted_text": "#4f5d56",
      "sub_title_text": "#304238",
      "error_text": "#c43d3d"
    }
  },
  "schools": [
    {
      "school_name": "中国石油大学（华东）",
      "short_name": "中石大华东",
      "emblem_text": "油",
      "badge_text": "CUP-EAST",
      "slogan": "立足能源，服务同学",
      "accent_color": "#006a43",
      "badge_bg_color": "#e8f5ec",
      "badge_text_color": "#103b2d",
      "pattern_type": "diagonal",
      "pattern_color": "#0b7b50",
      "pattern_opacity": 0.2,
      "pattern_size": 20,
      "sticker_text": "华东校区",
      "sticker_bg_color": "#fff1b8",
      "sticker_text_color": "#2d2d2d",
      "ribbon_text": "中国石油大学（华东）"
    }
  ]
}
```

说明：
1. 前端可按 `school_name` 匹配 `schools`，未命中则使用 `defaults`。
2. 建议优先使用 `PUT /api/v1/admin/school-branding` 维护该配置。
3. 所有颜色要求 `#RRGGBB` 格式，非法值会自动回退默认值。
4. 花纹参数中 `pattern_opacity` 取值范围建议 `0.0 - 0.4`，`pattern_size` 建议 `8 - 64`。
5. `ui_tokens` 仅影响颜色体系，不改变页面布局结构。
