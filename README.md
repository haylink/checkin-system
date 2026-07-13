# TaskFlow — Check-in Reminder System

[![PHP 8.0+](https://img.shields.io/badge/php-8.0+-blue.svg)](https://www.php.net/)
[![SQLite](https://img.shields.io/badge/database-SQLite-green.svg)](https://www.sqlite.org/)
[![License: MIT](https://img.shields.io/github/license/haylink/checkin-system)](./LICENSE)

A lightweight check-in reminder system built with PHP + SQLite, featuring multi-channel notifications via Telegram, ServerChan (WeChat), and DingTalk webhook.

## Features

- **Web Dashboard** — Manage check-in tasks, one-click sign-in, responsive layout
- **Multi-Channel Notifications** — Telegram, ServerChan (WeChat), DingTalk
- **Flexible Reminder Rules** — Custom advance reminders, deadline alerts, message templates
- **Password Management** — Admin password, security question, web-based recovery
- **REST API** — Full CRUD for tasks and notification channels

---

## Quick Start

### Prerequisites

- PHP 8.0+ (with SQLite and JSON extensions — typically built-in)
- A web server (Apache/Nginx with PHP-FPM, or use the built-in server for development)

### Installation

```bash
# 1. Clone the project
git clone https://github.com/haylink/checkin-system.git && cd checkin-system

# 2. Set environment variables
export ADMIN_PASSWORD='***'
export TELEGRAM_BOT_TOKEN='***'       # Optional
export TELEGRAM_CHAT_ID='your_chat_id'           # Optional

# 3. Start the server (development)
php -S 0.0.0.0:8080 -t .
```

Visit http://localhost:8080 to access the login page.

> **Note:** The database (`data.db`) is created automatically on first startup — no manual setup required.

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
* * * * * cd /path/to/checkin-system && php remind.php >> logs/remind.log 2>&1
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
php reset_password.php new_password
```

### Running in Background

```bash
nohup php -S 0.0.0.0:8080 -t /path/to/checkin-system > logs/app.log 2>&1 &
```

---

## Deployment on a Server

### Production Setup (Apache/Nginx + PHP-FPM)

For production, use Apache or Nginx with PHP-FPM instead of the built-in server. The entry point is `index.php` — configure your web server to route all requests to it.

**1. Choose a directory and clone the project**

Recommended: `/opt/checkin-system`

```bash
mkdir -p /opt/checkin-system
cd /opt/checkin-system
git clone https://github.com/haylink/checkin-system.git .
```

> The database (`data.db`) is automatically created in this directory on first startup.

**2. Set environment variables**

For persistent settings, add them to your shell profile (`~/.bashrc` or `~/.zshrc`):

```bash
# ~/.bashrc
export ADMIN_PASSWORD='***'
export TELEGRAM_BOT_TOKEN='***'       # Optional
export TELEGRAM_CHAT_ID='your_chat_id'           # Optional
export DATABASE_PATH='/opt/checkin-system/data.db'
```

Then reload the profile:

```bash
source ~/.bashrc
```

**3. Nginx configuration**

```nginx
server {
    listen 80;
    server_name checkin.example.com;
    root /opt/checkin-system;

    index index.php;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        fastcgi_pass unix:/var/run/php/php8.x-fpm.sock;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }
}
```

**4. Optional: Run as a systemd service**

```bash
sudo nano /etc/systemd/system/checkin-system.service
```

```ini
[Unit]
Description=TaskFlow Check-in Reminder System
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/checkin-system
Environment=ADMIN_PASSWORD=***
Environment=TELEGRAM_BOT_TOKEN=***
Environment=TELEGRAM_CHAT_ID=your_chat_id
ExecStart=/usr/bin/php -S 0.0.0.0:8080 -t /opt/checkin-system
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

> Replace the placeholder values with your actual credentials. You can also use `EnvironmentFile` to point to a separate `.env` file instead.

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable checkin-system
sudo systemctl start checkin-system
sudo systemctl status checkin-system
```

**5. Configure crontab for reminders**

```bash
crontab -e
* * * * * cd /opt/checkin-system && php remind.php >> logs/remind.log 2>&1
```

---

## 中文说明

TaskFlow 是一个轻量级签到提醒系统，基于 PHP + SQLite 构建，支持 Telegram、Server酱（微信）、钉钉机器人三种推送方式。

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

# 2. 设置环境变量
export ADMIN_PASSWORD='your_secure_password'
export TELEGRAM_BOT_TOKEN='***'       # 可选
export TELEGRAM_CHAT_ID='your_chat_id'           # 可选

# 3. 启动服务（开发模式）
php -S 0.0.0.0:8080 -t .
```

访问 http://localhost:8080 进入登录页面。

> **注意：** 数据库（`data.db`）会在首次启动时自动创建，无需手动操作。

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
* * * * * cd /path/to/checkin-system && php remind.php >> logs/remind.log 2>&1
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

- **网页端**：登录页点击「忘记了密码」→ 回答密保问题 → 重置
- **命令行**：

```bash
php reset_password.php 新密码
```

### 后台运行

```bash
nohup php -S 0.0.0.0:8080 -t /path/to/checkin-system > logs/app.log 2>&1 &
```

---

## Project Structure

```
checkin-system/
├── index.php              # PHP Web application entry point (routing + REST API)
├── database.php           # SQLite database layer
├── remind.php             # Scheduled reminder script (cron triggered)
├── config.php             # Environment variable configuration
├── reset_password.php     # CLI password reset tool
├── templates/
│   ├── login.html         # Login page template
│   ├── dashboard.html     # Dashboard page template
│   └── admin.html         # Admin panel page template
├── data.db                # SQLite database
├── LICENSE
└── README.md
```

---

## License

This project is licensed under the [MIT License](./LICENSE).

<img width="996" height="643" alt="login" src="https://github.com/user-attachments/assets/4dab5fac-a814-4577-acaa-218b06936d1a" />
<img width="1027" height="1300" alt="admin" src="https://github.com/user-attachments/assets/73c1f5a8-e7f9-4b57-8539-116696ef00bb" />
