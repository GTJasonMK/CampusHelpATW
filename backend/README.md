# CampusHelpATW FastAPI 后端骨架

## 1. 目录说明
1. `app/main.py`：应用入口。
2. `app/api/routes/`：路由层（认证、任务、聊天、论坛、举报、管理端）。
3. `app/services.py`：服务层（状态流转、积分结算、业务校验）。
4. `app/repositories/`：数据访问层（统一数据库读写）。
5. `app/domain/`：领域规则（任务状态机）。
6. `app/ws/`：WebSocket 连接管理。
7. `app/db_models.py`：SQLAlchemy 模型（对齐 MySQL 表结构）。
8. `scripts/smoke.sh`：基础接口冒烟脚本。

## 2. 启动步骤
1. 复制环境变量：

```bash
cd backend
cp .env.example .env
```

2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 启动服务：

```bash
uvicorn app.main:app --reload --port 3000
```

### 2.1 SQLite 本机调试（可选）
如果你暂时不想安装 MySQL，可以切到 SQLite 本机模式：

1. 修改 `.env` 中 `DATABASE_URL`：

```bash
DATABASE_URL=sqlite+aiosqlite:///./campus_help_atw.dev.db
```

2. 安装依赖并初始化 SQLite：

```bash
pip install -r requirements.txt
python scripts/init_sqlite_dev.py --reset
```

3. 启动服务：

```bash
uvicorn app.main:app --reload --port 3000
```

4. 本地调试账号（由 `scripts/init_sqlite_dev.py` 写入）：
1. `admin@campus.local`
2. `alice@campus.local`
3. `bob@campus.local`
4. `charlie@campus.local`
5. `diana@campus.local`

默认密码：`ChangeMe123!`

开发环境验证码（`APP_ENV != prod`）：`123456`

5. 最小验证命令（可选）：

```bash
# 健康检查
curl -s http://127.0.0.1:3000/healthz

# 获取开发验证码（响应里会返回 dev_code）
curl -s -X POST http://127.0.0.1:3000/api/v1/auth/email/send-code \
  -H 'Content-Type: application/json' \
  -d '{"campus_email":"alice@campus.local"}'

# 登录换 token（验证码固定 123456）
curl -s -X POST http://127.0.0.1:3000/api/v1/auth/email/verify \
  -H 'Content-Type: application/json' \
  -d '{"campus_email":"alice@campus.local","code":"123456","password":"ChangeMe123!"}'
```

说明：
1. SQLite 模式已兼容任务状态流转与积分变更（使用 Python 事务逻辑替代存储过程）。
2. `backend/scripts/smoke.sh` 主要面向 MySQL 联调数据，SQLite 下不保证全部断言通过。

4. 访问接口文档：
- Swagger UI: `http://127.0.0.1:3000/docs`
- ReDoc: `http://127.0.0.1:3000/redoc`
 - OpenAPI 文件：`docs/openapi/CampusHelpATW.openapi.yaml`

5. WebSocket 聊天地址（任务维度）：
- `ws://127.0.0.1:3000/api/v1/ws/tasks/{task_id}?token={jwt}`

## 3. 与微信小程序对接说明
1. 小程序端通过 `wx.request` 调用本服务 API。
2. 需要配置微信公众平台的 request 合法域名（HTTPS）。
3. 开发阶段可用内网穿透（如 `ngrok`/`frp`）映射本地 3000 端口。

## 4. 与数据库脚本的关系
1. 先执行：
   - `docs/sql/mysql_schema_v0.1.sql`
   - `docs/sql/mysql_seed_v0.1.sql`
   - `docs/sql/mysql_guards_v0.1.sql`
2. 如需联调样例数据，再执行：
   - `docs/sql/mysql_mock_data_v0.1.sql`
   - `docs/sql/mysql_sanity_checks_v0.1.sql`

## 5. 重要约束
1. MySQL 模式下，任务状态变更应走 `sp_task_transition`。
2. MySQL 模式下，积分变更应走 `sp_add_points`。
3. 管理端处理动作应写审计日志。

SQLite 本机调试模式下会自动切到 Python 事务兼容逻辑。

## 6. 单元测试
安装测试依赖：

```bash
pip install -r requirements-dev.txt
```

执行测试（建议限制 60 秒以内）：

```bash
timeout 60s pytest -q
```

## 7. 冒烟脚本

```bash
cd /mnt/e/Code/CampusHelpATW
bash backend/scripts/smoke.sh
```

## 8. 云托管部署（微信）

### 8.1 新增文件
1. `Dockerfile`：生产容器构建文件。
2. `.dockerignore`：镜像构建排除规则。
3. `scripts/start.sh`：容器启动脚本（读取 `PORT`，默认 `3000`）。
4. `.env.cloud.example`：云托管环境变量模板。

### 8.2 本地验证容器（推荐先做）

1. 构建镜像：

```bash
cd backend
docker build -t campushelpatw-backend:latest .
```

2. 使用 MySQL 环境变量运行容器：

```bash
docker run --rm -p 3000:3000 \
  --env-file .env.cloud.example \
  -e DATABASE_URL='mysql+aiomysql://db_user:db_password@127.0.0.1:3306/campus_help_atw' \
  campushelpatw-backend:latest
```

3. 健康检查：

```bash
curl -s http://127.0.0.1:3000/healthz
```

### 8.3 绑定到微信云托管

1. 在微信云托管创建服务，选择“通过 Dockerfile 构建”。
2. 代码目录指向 `backend`（即 `Dockerfile` 所在目录）。
3. 启动命令保持默认（镜像里已通过 `CMD` 启动 `scripts/start.sh`）。
4. 在云托管环境变量里填写 `.env.cloud.example` 对应配置，重点配置：
   - `APP_ENV=prod`
   - `DATABASE_URL=mysql+aiomysql://...`
   - `JWT_SECRET_KEY=<强随机密钥>`
5. 给服务绑定 HTTPS 域名。

### 8.4 小程序配置

1. 把 `miniapp-template/config/index.js` 的 `baseUrl` 改为云托管 HTTPS 域名，例如：
   - `https://api.your-domain.com/api/v1`
2. 微信公众平台配置合法域名：
   - request 合法域名：`https://api.your-domain.com`
   - socket 合法域名：`wss://api.your-domain.com`
3. 若启用了路径前缀，确认与后端 `API_V1_PREFIX` 保持一致（默认 `/api/v1`）。

### 8.5 SQLite 说明

云托管建议使用 MySQL。SQLite 仅用于本机开发调试。
