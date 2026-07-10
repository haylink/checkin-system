# TaskFlow — Check-in Reminder System

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/framework-Flask-green.svg)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.io/github/license/haylink/checkin-system)](./LICENSE)

A lightweight check-in reminder system built with Flask + SQLite, featuring multi-channel notifications via Telegram, ServerChan (WeChat), and DingTalk webhook.

## Features

- **Web Dashboard** — Manage check-in tasks, one-click sign-in, responsive layout
- **Multi-Channel Notifications** — Telegram, ServerChan (WeChat), DingTalk
- **Flexible Reminder Rules** — Custom advance reminders, deadline alerts, message templates
- **Password Management** — Admin password, security question, web-based recovery
- **REST API** — Full CRUD for tasks and notification channels

---

## Quick Start

### Prerequisites

- Python 3.8+
- pip

### Installation

```bash
# 1. Clone the project
git clone https://github.com/haylink/checkin-system.git && cd checkin-system

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
export ADMIN_PASSWORD='your_secure_password'
export TELEGRAM_BOT_TOKEN='your_bot_token'      # Optional
export TELEGRAM_CHAT_ID='your_chat_id'           # Optional

# 4. Start the server
python3 app.py
```

Visit http://localhost:8080 to access the login page.

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ADMIN_PASSWORD` | Admin password (used on first launch) | Yes |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | When using Telegram channel |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID | When using Telegram channel |
| `DATABASE_PATH` | Database file path | Optional, defaults to `data.db` |

### Notification Channels

Three push methods are supported, configurable from the admin panel:

| Channel | Type Value | Config | Description |
|---------|-----------|--------|-------------|
| Telegram | `telegram` | Bot Token + Chat ID | Push via Telegram Bot API |
| ServerChan | `serverchan` | SendKey | Push to WeChat via [sct.ftqq.com](https://sct.ftqq.com) |
| DingTalk | `dingtalk` | Webhook URL | Push to DingTalk group chat |

### Scheduled Reminders

Run via cron (check every minute):

```bash
crontab -e
* * * * * cd /path/to/checkin-system && python3 remind.py >> logs/remind.log 2>&1
```

Reminder logic:
- **Advance reminders** — sent N days before the due date (e.g., 3 days, 1 day)
- **Final reminder** — sent on the due date
- **Custom templates** — support `{name}`, `{cycle}`, `{remaining}`, `{due}`, `{overdue}` variables
- **Deduplication** — each reminder type is sent only once per check-in

### Security

- First launch requires `ADMIN_PASSWORD` environment variable
- Password stored in database, modifiable from the admin panel
- Security question support for password recovery
- Password change invalidates existing sessions automatically

### Password Recovery

- **Web UI**: Click "Forgot Password" on login page → answer security question → reset
- **Command line**:

```bash
python3 reset_password.py new_password
```

### Running in Background

```bash
nohup python3 app.py > logs/app.log 2>&1 &
```

---

## 中文说明

TaskFlow 是一个轻量级签到提醒系统，基于 Flask + SQLite 构建，支持 Telegram、Server酱（微信）、钉钉机器人三种推送方式。

### 功能特性

- **Web 看板** — 管理签到任务、一键签到、响应式布局
- **多通道通知** — Telegram、Server酱（微信）、钉钉 Webhook
- **灵活提醒规则** — 自定义提前提醒、截止提醒、消息模板
- **密码管理** — 管理员密码、密保问题、网页端密码找回
- **REST API** — 任务和通知通道的完整 CRUD

### 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/haylink/checkin-system.git && cd checkin-system

# 2. 安装依赖
pip install -r requirements.txt

# 3. 设置环境变量
export ADMIN_PASSWORD='your_secure_password'
export TELEGRAM_BOT_TOKEN='your_bot_token'      # 可选
export TELEGRAM_CHAT_ID='your_chat_id'           # 可选

# 4. 启动服务
python3 app.py
```

访问 http://localhost:8080 进入登录页面。

### 环境变量

| 变量 | 说明 | 必填 |
|------|------|------|
| `ADMIN_PASSWORD` | 管理员密码（首次启动初始化用） | ✅ 是 |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | 使用 Telegram 通道时必填 |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID | 使用 Telegram 通道时必填 |
| `DATABASE_PATH` | 数据库文件路径 | 可选，默认 `data.db` |

### 通知通道

三种推送方式，可在后台管理页添加：

| 通道 | 类型值 | 配置项 | 说明 |
|------|--------|--------|------|
| Telegram | `telegram` | Bot Token + Chat ID | Telegram Bot API 推送 |
| Server酱 | `serverchan` | SendKey | 通过 [sct.ftqq.com](https://sct.ftqq.com) 推送到微信 |
| 钉钉机器人 | `dingtalk` | Webhook URL | 钉钉群聊机器人推送 |

### 定时提醒

通过 crontab 每分钟检查一次：

```bash
crontab -e
* * * * * cd /path/to/checkin-system && python3 remind.py >> logs/remind.log 2>&1
```

提醒逻辑：
- **提前提醒** — 到期前指定天数（如 3 天、1 天）发送
- **最后提醒** — 到期当天发送
- **自定义模板** — 支持 `{name}` `{cycle}` `{remaining}` `{due}` `{overdue}` 变量
- **去重机制** — 每种提醒类型每次签到只发送一次

### 安全

- 首次启动需通过 `ADMIN_PASSWORD` 环境变量初始化
- 密码存储在数据库中，可在后台修改
- 支持密保问题，忘记可通过网页验证重置
- 密码修改后自动使现有 session 失效

### 忘记密码

- **网页端**：登录页点击「忘记密码」→ 回答密保问题 → 重置
- **命令行**：

```bash
python3 reset_password.py 新密码
```

### 后台运行

```bash
nohup python3 app.py > logs/app.log 2>&1 &
```

---

## Project Structure

```
checkin-system/
├── app.py              # Flask Web application (frontend + REST API)
├── database.py         # SQLite database layer
├── remind.py           # Scheduled reminder script (cron triggered)
├── config.py           # Environment variable configuration
├── reset_password.py   # CLI password reset tool
├── requirements.txt    # Python dependencies
├── .gitignore
├── LICENSE
└── README.md
```

---

## License

This project is licensed under the [MIT License](./LICENSE).
