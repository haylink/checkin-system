import os

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
if not ADMIN_PASSWORD:
    raise RuntimeError(
        "❌ 必须设置 ADMIN_PASSWORD 环境变量才能启动。\n"
        "   export ADMIN_PASSWORD='your_secure_password'"
    )

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError(
        "❌ 必须设置 TELEGRAM_BOT_TOKEN 环境变量才能启动。\n"
        "   export TELEGRAM_BOT_TOKEN='your_bot_token'"
    )

TELEGRAM_CHAT_ID = int(os.environ.get("TELEGRAM_CHAT_ID", "0"))
if not TELEGRAM_CHAT_ID:
    raise RuntimeError(
        "❌ 必须设置 TELEGRAM_CHAT_ID 环境变量才能启动。\n"
        "   export TELEGRAM_CHAT_ID='your_chat_id'"
    )

DATABASE_PATH = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.db"))
