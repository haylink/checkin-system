# TaskFlow — 签到提醒系统

基于 Flask + SQLite + 多通道通知的签到提醒系统。

支持 Telegram、Server酱（微信）、钉钉机器人 三种推送方式，Web 管理面板管理签到任务。

## 环境要求

- Python 3.8+
- pip

## 快速开始

```bash
# 1. 克隆项目
git clone <repo-url> && cd checkin-system

# 2. 安装依赖
pip install -r requirements.txt

# 3. 设置环境变量
export ADMIN_PASSWORD='your_secure_password'
export TELEGRAM_BOT_TOKEN='your_bot_token'       # 可选
export TELEGRAM_CHAT_ID='your_chat_id'           # 可选
export DATABASE_PATH='/path/to/data.db'          # 可选，默认项目目录

# 4. 启动
python3 app.py
```

访问 http://localhost:8080 即可进入登录页面。

## 环境变量

| 变量 | 说明 | 必填 |
|------|------|------|
| `ADMIN_PASSWORD` | 管理员密码（首次启动初始化用） | ✅ 是 |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | 使用 Telegram 通道时必填 |
| `TELEGRAM_CHAT_ID` | Telegram 聊天 ID | 使用 Telegram 通道时必填 |
| `DATABASE_PATH` | 数据库文件路径 | 默认 data.db（项目目录下） |

## 功能

### Web 管理面板

| 页面 | 路径 | 说明 |
|------|------|------|
| 登录 | `/login` | 密码登录 |
| 任务面板 | `/` | 查看所有任务状态，一键签到，切换单列/双列布局 |
| 后台管理 | `/admin` | 管理任务 / 管理通知通道 / 修改密码 / 设置密保问题 |

### 通知通道

支持三种推送方式，可在后台管理页添加：

| 通道 | 类型值 | 配置项 | 说明 |
|------|--------|--------|------|
| Telegram | `telegram` | Bot Token + Chat ID | 通过 Telegram Bot 发送消息 |
| Server酱 | `serverchan` | SendKey | 通过 [sct.ftqq.com](https://sct.ftqq.com) 推送到微信 |
| 钉钉机器人 | `dingtalk` | Webhook URL | 通过钉钉群聊机器人推送 |

### 定时提醒

```bash
# crontab 每分钟执行一次提醒检查
* * * * * cd /path/to/checkin-system && python3 remind.py >> logs/remind.log 2>&1
```

提醒逻辑：
- **提前提醒**：在到期前指定天数（如 3 天、1 天）发送提醒
- **最后提醒**：到期当天发送提醒
- 可自定义消息模板（支持 `{name}` `{cycle}` `{remaining}` `{due}` `{overdue}` 变量）
- 已发送的提醒有去重机制

### 安全

- 首次启动需通过 `ADMIN_PASSWORD` 环境变量初始化密码
- 密码存储在数据库中，可在后台修改
- 支持设置密保问题，忘记密码可通过网页验证密保重置密码
- 密码修改后自动更新 secret key，使现有 session 失效

### 忘记密码

**网页端：** 在登录页点击「忘记密码」→ 回答密保问题 → 重置密码

**命令行：**
```bash
python3 reset_password.py 新密码
```

### API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/tasks` | 获取任务列表及签到状态 |
| POST | `/api/tasks` | 创建任务 |
| PUT | `/api/tasks/<id>` | 更新任务 |
| DELETE | `/api/tasks/<id>` | 删除任务 |
| POST | `/api/tasks/<id>/checkin` | 签到（可附带备注 `note`） |
| GET | `/api/tasks/<id>/history` | 签到历史 |
| GET | `/api/channels` | 获取通知通道列表 |
| POST | `/api/channels` | 创建通道 |
| PUT | `/api/channels/<id>` | 更新通道 |
| DELETE | `/api/channels/<id>` | 删除通道 |
| POST | `/api/channels/test` | 测试发送通知 |
| GET | `/api/settings` | 获取设置状态 |
| PUT | `/api/settings` | 修改密码 |
| GET | `/api/settings/security` | 获取密保问题 |
| PUT | `/api/settings/security` | 设置密保问题 |
| GET | `/api/reset-password/question` | 获取密保问题（无需登录） |
| POST | `/api/reset-password/check` | 验证密保答案（无需登录） |
| POST | `/api/reset-password/reset` | 重置密码（无需登录） |

## 后台运行

```bash
nohup python3 app.py > logs/app.log 2>&1 &
```

## 项目结构

```
checkin-system/
├── app.py              # Flask Web 应用（前端 + REST API）
├── database.py         # SQLite 数据库层
├── remind.py           # 定时提醒脚本（cron 触发）
├── config.py           # 环境变量配置
├── reset_password.py   # 命令行密码重置工具
├── requirements.txt    # Python 依赖
├── .gitignore
├── LICENSE
└── README.md
```