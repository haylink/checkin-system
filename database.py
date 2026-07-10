import sqlite3
import json
import datetime
import config
from config import DATABASE_PATH


ADVANCE_TEMPLATE = "📅 【{name}】签到提醒：签到周期是 {cycle} 天，还有 {remaining} 天到期，请尽快签到！"
FINAL_TEMPLATE = "⚠️ 【{name}】签到最后提醒：已超期 {overdue} 天，请马上签到！"


def get_connection():
    return sqlite3.connect(DATABASE_PATH)


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            url TEXT DEFAULT '',
            checkin_days INTEGER NOT NULL DEFAULT 3,
            reminder_days TEXT NOT NULL DEFAULT '3,1',
            advance_msg_template TEXT DEFAULT '',
            final_msg_template TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        )
    """)

    for col in ["advance_msg_template", "final_msg_template", "url"]:
        try:
            c.execute(f"ALTER TABLE tasks ADD COLUMN {col} TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass

    c.execute("""
        CREATE TABLE IF NOT EXISTS checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            checkin_time TEXT NOT NULL,
            note TEXT DEFAULT '',
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS sent_reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            checkin_id INTEGER NOT NULL,
            reminder_type TEXT NOT NULL,
            sent_at TEXT NOT NULL,
            UNIQUE(task_id, checkin_id, reminder_type)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS notification_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            channel_type TEXT NOT NULL DEFAULT 'telegram',
            config TEXT NOT NULL DEFAULT '{}',
            enabled INTEGER NOT NULL DEFAULT 1
        )
    """)

    c.execute("SELECT COUNT(*) FROM notification_channels")
    if c.fetchone()[0] == 0:
        default_config = json.dumps({
            "bot_token": config.TELEGRAM_BOT_TOKEN,
            "chat_id": config.TELEGRAM_CHAT_ID,
        })
        c.execute(
            "INSERT INTO notification_channels (name, channel_type, config, enabled) VALUES (?, ?, ?, 1)",
            ("默认Telegram", "telegram", default_config),
        )

    conn.commit()
    conn.close()
    init_settings()


def init_settings():
    """初始化设置表，从环境变量读取默认值写入数据库"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    defaults = {
        "admin_password": config.ADMIN_PASSWORD,
    }
    for k, v in defaults.items():
        c.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (k, v),
        )
    conn.commit()
    conn.close()


def get_setting(key):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    r = c.fetchone()
    conn.close()
    return r[0] if r else None


def set_setting(key, value):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, value),
    )
    conn.commit()
    conn.close()


def get_admin_password():
    return get_setting("admin_password") or ""


def get_tasks():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, description, url, checkin_days, reminder_days, "
              "advance_msg_template, final_msg_template, created_at, active "
              "FROM tasks ORDER BY id ASC")
    rows = c.fetchall()
    conn.close()
    return [
        {
            "id": r[0], "name": r[1], "description": r[2], "url": r[3] or "",
            "checkin_days": r[4], "reminder_days": [int(x) for x in (r[5] or "3,1").split(",") if x.strip()],
 "advance_msg_template": r[6] or '', "final_msg_template": r[7] or '',
 "created_at": r[8], "active": bool(r[9]),
 }
 for r in rows
 ]


def get_task(task_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, description, url, checkin_days, reminder_days, "
              "advance_msg_template, final_msg_template, created_at, active "
              "FROM tasks WHERE id=?", (task_id,))
    r = c.fetchone()
    conn.close()
    if not r:
        return None
    return {
        "id": r[0], "name": r[1], "description": r[2], "url": r[3] or "",
        "checkin_days": r[4], "reminder_days": [int(x) for x in (r[5] or "3,1").split(",") if x.strip()],
        "advance_msg_template": r[6] or '', "final_msg_template": r[7] or '',
        "created_at": r[8], "active": bool(r[9]),
    }


def add_task(name, description, checkin_days, reminder_days,
             advance_msg_template="", final_msg_template="", url=""):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.datetime.now().isoformat()
    reminder_str = ",".join(str(d) for d in reminder_days)
    c.execute(
        "INSERT INTO tasks (name, description, url, checkin_days, reminder_days, "
        "advance_msg_template, final_msg_template, created_at, active) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)",
        (name, description, url, checkin_days, reminder_str,
         advance_msg_template, final_msg_template, now),
    )
    task_id = c.lastrowid
    conn.commit()
    conn.close()
    return task_id


def update_task(task_id, name, description, checkin_days, reminder_days, active,
                advance_msg_template="", final_msg_template="", url=""):
    conn = get_connection()
    c = conn.cursor()
    reminder_str = ",".join(str(d) for d in reminder_days)
    c.execute(
        "UPDATE tasks SET name=?, description=?, url=?, checkin_days=?, reminder_days=?, "
        "advance_msg_template=?, final_msg_template=?, active=? WHERE id=?",
        (name, description, url, checkin_days, reminder_str,
         advance_msg_template, final_msg_template, 1 if active else 0, task_id),
    )
    conn.commit()
    conn.close()


def delete_task(task_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM checkins WHERE task_id=?", (task_id,))
    c.execute("DELETE FROM sent_reminders WHERE task_id=?", (task_id,))
    c.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()


def add_checkin(task_id, note=""):
    """Insert a checkin only if the last one for this task was >= 86400s ago.
    Returns checkin_id on success, 0 if cooldown still active."""
    conn = get_connection()
    c = conn.cursor()
    try:
        now = datetime.datetime.now().isoformat()
        # Atomic guard: read last checkin and only INSERT if cooldown expired
        last = c.execute(
            "SELECT checkin_time FROM checkins WHERE task_id=? ORDER BY id DESC LIMIT 1",
            (task_id,),
        ).fetchone()
        if last:
            try:
                last_time = datetime.datetime.fromisoformat(last[0])
            except (ValueError, TypeError):
                conn.close()
                return 0  # corrupt checkin -> treat as locked
            if (datetime.datetime.now() - last_time).total_seconds() < 86400:
                conn.close()
                return 0  # signal: still in cooldown
        c.execute(
            "INSERT INTO checkins (task_id, checkin_time, note) VALUES (?, ?, ?)",
            (task_id, now, note),
        )
        checkin_id = c.lastrowid
        conn.commit()
        conn.close()
        return checkin_id
    except Exception:
        conn.close()
        raise


def get_last_checkin(task_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, checkin_time, note FROM checkins WHERE task_id=? ORDER BY id DESC LIMIT 1",
              (task_id,))
    r = c.fetchone()
    conn.close()
    if r:
        return {"id": r[0], "checkin_time": r[1], "note": r[2]}
    return None


def get_all_checkins(task_id, limit=50):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, checkin_time, note FROM checkins WHERE task_id=? ORDER BY id DESC LIMIT ?",
              (task_id, limit))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "checkin_time": r[1], "note": r[2]} for r in rows]


def can_checkin_task(task_id):
    """Check if the task can be checked in (no checkin in last 24h)."""
    conn = get_connection()
    c = conn.cursor()
    try:
        last = c.execute(
            "SELECT checkin_time FROM checkins WHERE task_id=? ORDER BY id DESC LIMIT 1",
            (task_id,),
        ).fetchone()
        if not last:
            return True
        try:
            last_time = datetime.datetime.fromisoformat(last[0])
        except (ValueError, TypeError):
            return True  # corrupt data -> allow checkin
        now = datetime.datetime.now()
        return (now - last_time).total_seconds() >= 86400
    finally:
        conn.close()


def is_reminder_sent(task_id, checkin_id, reminder_type):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM sent_reminders WHERE task_id=? AND checkin_id=? AND reminder_type=?",
              (task_id, checkin_id, reminder_type))
    count = c.fetchone()[0]
    conn.close()
    return count > 0


def mark_reminder_sent(task_id, checkin_id, reminder_type):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.datetime.now().isoformat()
    try:
        c.execute("INSERT INTO sent_reminders (task_id, checkin_id, reminder_type, sent_at) "
                  "VALUES (?, ?, ?, ?)", (task_id, checkin_id, reminder_type, now))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()


def get_channels():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, channel_type, config, enabled FROM notification_channels ORDER BY id ASC")
    rows = c.fetchall()
    conn.close()
    return [
        {
            "id": r[0], "name": r[1], "channel_type": r[2],
            "config": json.loads(r[3]), "enabled": bool(r[4]),
        }
        for r in rows
    ]


def get_channel(channel_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, channel_type, config, enabled FROM notification_channels WHERE id=?",
              (channel_id,))
    r = c.fetchone()
    conn.close()
    if not r:
        return None
    return {
        "id": r[0], "name": r[1], "channel_type": r[2],
        "config": json.loads(r[3]), "enabled": bool(r[4]),
    }


def add_channel(name, channel_type, config_dict):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO notification_channels (name, channel_type, config, enabled) VALUES (?, ?, ?, 1)",
              (name, channel_type, json.dumps(config_dict)))
    channel_id = c.lastrowid
    conn.commit()
    conn.close()
    return channel_id


def update_channel(channel_id, name, channel_type, config_dict, enabled):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE notification_channels SET name=?, channel_type=?, config=?, enabled=? WHERE id=?",
              (name, channel_type, json.dumps(config_dict), 1 if enabled else 0, channel_id))
    conn.commit()
    conn.close()


def delete_channel(channel_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM notification_channels WHERE id=?", (channel_id,))
    conn.commit()
    conn.close()
