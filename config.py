import os

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
if not ADMIN_PASSWORD:
    raise RuntimeError(
        "❌ ADMIN_PASSWORD 环境变量未设置，无法启动。\n"
        "   export ADMIN_PASSWORD='***'"
    )

# Telegram 通道 — 可选，仅在使用 Telegram 通知时需要
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
try:
    _tid = os.environ.get("TELEGRAM_CHAT_ID", "0")
    TELEGRAM_CHAT_ID = int(_tid) if _tid.strip() else 0
except (ValueError, TypeError):
    TELEGRAM_CHAT_ID = 0

DATABASE_PATH = os.environ.get(
    "DATABASE_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.db")
)
