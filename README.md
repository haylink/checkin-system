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
export ADMIN_PASSWORD='***'
export TELEGRAM_BOT_TOKEN='***'       # Optional
export TELEGRAM_CHAT_ID='your_chat_id'           # Optional

# 4. Start the server
python3 app.py
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

## Deployment on a Server

### Basic Setup (Direct Access via Public IP)

If your server has a public IP, you can access the app directly on port 8080 — no reverse proxy needed.

**1. Choose a directory and clone the project**

Recommended: `/opt/checkin-system`

```bash
mkdir -p /opt/checkin-system
cd /opt/checkin-system
git clone https://github.com/haylink/checkin-system.git .
pip install -r requirements.txt
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

**3. Start the application**

```bash
cd /opt/checkin-system
python3 app.py
```

Access via: `http://<your-server-ip>:8080`

**4. Optional: Run as a systemd service**

To ensure the app starts on boot and restarts on failure:

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
ExecStart=/usr/bin/python3 /opt/checkin-system/app.py
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

**5. Optional: Configure Nginx reverse proxy (for domain access)**

If you want to use a domain name or access on port 80 without specifying 8080:

```bash
sudo apt install nginx   # or: sudo yum install nginx
```

Create a site configuration:

```nginx
# /etc/nginx/sites-available/checkin
server {
    listen 80;
    server_name checkin.example.com;  # Replace with your domain

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and reload:

```bash
sudo ln -s /etc/nginx/sites-available/checkin /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Access via: `http://checkin.example.com`

**6. Configure crontab for reminders**

```bash
crontab -e
* * * * * cd /opt/checkin-system && /usr/bin/python3 remind.py >> logs/remind.log 2>&1
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
export TELEGRAM_BOT_TOKEN='***'       # 可选
export TELEGRAM_CHAT_ID='your_chat_id'           # 可选

# 4. 启动服务
python3 app.py
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

- **网页端**：登录页点击「忘记了密码」→ 回答密保问题 → 重置
- **命令行**：

```bash
python3 reset_password.py 新密码
```

### 后台运行

```bash
nohup python3 app.py > logs/app.log 2>&1 &
```

---

## 服务器部署

### 基础部署（公网 IP 直接访问）

如果你的服务器有公网 IP，应用启动后直接通过 `http://<服务器IP>:8080` 访问即可，无需反向代理。

**1. 选择目录并克隆项目**

推荐路径：`/opt/checkin-system`

```bash
mkdir -p /opt/checkin-system
cd /opt/checkin-system
git clone https://github.com/haylink/checkin-system.git .
pip install -r requirements.txt
```

> 数据库（`data.db`）会在首次启动时自动在项目目录下创建。

**2. 设置环境变量**

将环境变量写入 shell 配置文件（`~/.bashrc` 或 `~/.zshrc`）以持久化：

```bash
# ~/.bashrc
export ADMIN_PASSWORD='your_secure_password'
export TELEGRAM_BOT_TOKEN='***'       # 可选
export TELEGRAM_CHAT_ID='your_chat_id'           # 可选
export DATABASE_PATH='/opt/checkin-system/data.db'
```

重新加载配置：

```bash
source ~/.bashrc
```

**3. 启动应用**

```bash
cd /opt/checkin-system
python3 app.py
```

访问：`http://<服务器IP>:8080`

**4. 可选：配置 systemd 服务**

让应用开机自启、崩溃自动重启：

```bash
sudo nano /etc/systemd/system/checkin-system.service
```

```ini
[Unit]
Description=TaskFlow 签到提醒系统
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/checkin-system
Environment=ADMIN_PASSWORD=your_secure_password
Environment=TELEGRAM_BOT_TOKEN=your_bot_token
Environment=TELEGRAM_CHAT_ID=your_chat_id
ExecStart=/usr/bin/python3 /opt/checkin-system/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

> 将占位值替换为实际凭据。也可使用 `EnvironmentFile` 指向单独的 `.env` 文件。

启用并启动：

```bash
sudo systemctl daemon-reload
sudo systemctl enable checkin-system
sudo systemctl start checkin-system
sudo systemctl status checkin-system
```

**5. 可选：配置 Nginx 反向代理（域名访问）**

如果使用域名访问，或希望通过 80 端口访问：

```bash
sudo apt install nginx   # 或：sudo yum install nginx
```

创建站点配置：

```nginx
# /etc/nginx/sites-available/checkin
server {
    listen 80;
    server_name checkin.example.com;  # 替换为你的域名

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

启用并重启：

```bash
sudo ln -s /etc/nginx/sites-available/checkin /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

访问：`http://checkin.example.com`

**6. 配置定时提醒**

```bash
crontab -e
* * * * * cd /opt/checkin-system && /usr/bin/python3 remind.py >> logs/remind.log 2>&1
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
