<?php
/**
 * SQLite database layer — PHP port of database.py.
 * Uses PDO with prepared statements throughout.
 */

require_once __DIR__ . '/config.php';

/** Default advance reminder template */
define('ADVANCE_TEMPLATE', "📅 【{name}】签到提醒：签到周期是 {cycle} 天，还有 {remaining} 天到期，请尽快签到！");

/** Default final reminder template */
define('FINAL_TEMPLATE', "⚠️ 【{name}】签到最后提醒：已超期 {overdue} 天，请马上签到！");

/**
 * Get a PDO connection to the SQLite database (lazy-created singleton per request).
 */
function get_connection(): PDO
{
    static $pdo = null;
    if ($pdo === null) {
        global $DATABASE_PATH;
        $pdo = new PDO('sqlite:' . $DATABASE_PATH, null, null, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        ]);
        $pdo->exec('PRAGMA journal_mode=WAL');
        $pdo->exec('PRAGMA foreign_keys=ON');
    }
    return $pdo;
}

/**
 * Initialize database schema (idempotent — only creates missing tables/columns).
 */
function init_db(): void
{
    global $TELEGRAM_BOT_TOKEN, $TELEGRAM_CHAT_ID;
    $pdo = get_connection();

    $pdo->exec("
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
    ");

    // Add columns that may be missing on older schemas
    foreach (['advance_msg_template', 'final_msg_template', 'url'] as $col) {
        try {
            $pdo->exec("ALTER TABLE tasks ADD COLUMN {$col} TEXT DEFAULT ''");
        } catch (PDOException $e) {
            // Column already exists — ignore
        }
    }

    $pdo->exec("
        CREATE TABLE IF NOT EXISTS checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            checkin_time TEXT NOT NULL,
            note TEXT DEFAULT '',
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        )
    ");

    $pdo->exec("
        CREATE TABLE IF NOT EXISTS sent_reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            checkin_id INTEGER NOT NULL,
            reminder_type TEXT NOT NULL,
            sent_at TEXT NOT NULL,
            UNIQUE(task_id, checkin_id, reminder_type)
        )
    ");

    $pdo->exec("
        CREATE TABLE IF NOT EXISTS notification_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            channel_type TEXT NOT NULL DEFAULT 'telegram',
            config TEXT NOT NULL DEFAULT '{}',
            enabled INTEGER NOT NULL DEFAULT 1
        )
    ");

    // Seed a default Telegram channel from env vars if no channels exist
    $count = $pdo->query("SELECT COUNT(*) FROM notification_channels")->fetchColumn();
    if ($count == 0 && $TELEGRAM_BOT_TOKEN) {
        $defaultConfig = json_encode([
            'bot_token' => $TELEGRAM_BOT_TOKEN,
            'chat_id' => $TELEGRAM_CHAT_ID,
        ]);
        $stmt = $pdo->prepare(
            "INSERT INTO notification_channels (name, channel_type, config, enabled) VALUES (?, ?, ?, 1)"
        );
        $stmt->execute(['默认Telegram', 'telegram', $defaultConfig]);
    }

    init_settings();
}

/**
 * Initialize settings table with defaults from environment variables.
 */
function init_settings(): void
{
    global $ADMIN_PASSWORD;
    $pdo = get_connection();

    $pdo->exec("
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ");

    $defaults = [
        'admin_password' => $ADMIN_PASSWORD,
    ];
    foreach ($defaults as $k => $v) {
        $pdo->prepare(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)"
        )->execute([$k, $v]);
    }
}

/**
 * Get a setting value by key.
 */
function get_setting(string $key): ?string
{
    $pdo = get_connection();
    $stmt = $pdo->prepare("SELECT value FROM settings WHERE key=?");
    $stmt->execute([$key]);
    $r = $stmt->fetchColumn();
    return $r !== false ? $r : null;
}

/**
 * Set (insert or replace) a setting value.
 */
function set_setting(string $key, string $value): void
{
    $pdo = get_connection();
    $pdo->prepare(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)"
    )->execute([$key, $value]);
}

/**
 * Get the admin password from settings.
 */
function get_admin_password(): string
{
    return get_setting('admin_password') ?: '';
}

/**
 * Get all tasks, ordered by id.
 * @return array<int, array>
 */
function get_tasks(): array
{
    $pdo = get_connection();
    $rows = $pdo->query(
        "SELECT id, name, description, url, checkin_days, reminder_days,
                advance_msg_template, final_msg_template, created_at, active
         FROM tasks ORDER BY id ASC"
    )->fetchAll();

    return array_map(function ($r) {
        return [
            'id' => (int)$r['id'],
            'name' => $r['name'],
            'description' => $r['description'] ?? '',
            'url' => $r['url'] ?? '',
            'checkin_days' => (int)$r['checkin_days'],
            'reminder_days' => array_filter(
                array_map('intval', explode(',', $r['reminder_days'] ?: '3,1')),
                fn($n) => $n > 0
            ),
            'advance_msg_template' => $r['advance_msg_template'] ?? '',
            'final_msg_template' => $r['final_msg_template'] ?? '',
            'created_at' => $r['created_at'],
            'active' => (bool)$r['active'],
        ];
    }, $rows);
}

/**
 * Get a single task by id.
 */
function get_task(int $task_id): ?array
{
    $pdo = get_connection();
    $stmt = $pdo->prepare(
        "SELECT id, name, description, url, checkin_days, reminder_days,
                advance_msg_template, final_msg_template, created_at, active
         FROM tasks WHERE id=?"
    );
    $stmt->execute([$task_id]);
    $r = $stmt->fetch();
    if (!$r) {
        return null;
    }
    return [
        'id' => (int)$r['id'],
        'name' => $r['name'],
        'description' => $r['description'] ?? '',
        'url' => $r['url'] ?? '',
        'checkin_days' => (int)$r['checkin_days'],
        'reminder_days' => array_filter(
            array_map('intval', explode(',', $r['reminder_days'] ?: '3,1')),
            fn($n) => $n > 0
        ),
        'advance_msg_template' => $r['advance_msg_template'] ?? '',
        'final_msg_template' => $r['final_msg_template'] ?? '',
        'created_at' => $r['created_at'],
        'active' => (bool)$r['active'],
    ];
}

/**
 * Add a new task. Returns the new task id.
 */
function add_task(
    string $name,
    string $description,
    int $checkin_days,
    array $reminder_days,
    string $advance_msg_template = '',
    string $final_msg_template = '',
    string $url = ''
): int {
    $pdo = get_connection();
    $now = date('Y-m-d\TH:i:s');
    $reminder_str = implode(',', $reminder_days);
    $stmt = $pdo->prepare(
        "INSERT INTO tasks (name, description, url, checkin_days, reminder_days,
                advance_msg_template, final_msg_template, created_at, active)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)"
    );
    $stmt->execute([$name, $description, $url, $checkin_days, $reminder_str,
        $advance_msg_template, $final_msg_template, $now]);
    return (int)$pdo->lastInsertId();
}

/**
 * Update an existing task.
 */
function update_task(
    int $task_id,
    string $name,
    string $description,
    int $checkin_days,
    array $reminder_days,
    bool $active,
    string $advance_msg_template = '',
    string $final_msg_template = '',
    string $url = ''
): void {
    $pdo = get_connection();
    $reminder_str = implode(',', $reminder_days);
    $stmt = $pdo->prepare(
        "UPDATE tasks SET name=?, description=?, url=?, checkin_days=?, reminder_days=?,
                advance_msg_template=?, final_msg_template=?, active=?
         WHERE id=?"
    );
    $stmt->execute([
        $name, $description, $url, $checkin_days, $reminder_str,
        $advance_msg_template, $final_msg_template, $active ? 1 : 0, $task_id,
    ]);
}

/**
 * Delete a task and all its checkins and sent reminders.
 */
function delete_task(int $task_id): void
{
    $pdo = get_connection();
    $pdo->prepare("DELETE FROM checkins WHERE task_id=?")->execute([$task_id]);
    $pdo->prepare("DELETE FROM sent_reminders WHERE task_id=?")->execute([$task_id]);
    $pdo->prepare("DELETE FROM tasks WHERE id=?")->execute([$task_id]);
}

/**
 * Insert a checkin only if the last one for this task was >= 86400s ago.
 * Returns checkin_id on success, 0 if cooldown still active.
 */
function add_checkin(int $task_id, string $note = ''): int
{
    $pdo = get_connection();
    $now = date('Y-m-d\TH:i:s');

    // Atomic guard: read last checkin and reject if still in cooldown
    $stmt = $pdo->prepare(
        "SELECT checkin_time FROM checkins WHERE task_id=? ORDER BY id DESC LIMIT 1"
    );
    $stmt->execute([$task_id]);
    $last = $stmt->fetchColumn();

    if ($last !== false) {
        try {
            $lastTs = new DateTime($last);
            $diff = (new DateTime())->getTimestamp() - $lastTs->getTimestamp();
            if ($diff < 86400) {
                return 0;
            }
        } catch (Exception $e) {
            return 0; // corrupt data → treat as locked
        }
    }

    $stmt = $pdo->prepare(
        "INSERT INTO checkins (task_id, checkin_time, note) VALUES (?, ?, ?)"
    );
    $stmt->execute([$task_id, $now, $note]);
    $checkin_id = (int)$pdo->lastInsertId();

    return $checkin_id;
}

/**
 * Get the last checkin for a task, or null.
 */
function get_last_checkin(int $task_id): ?array
{
    $pdo = get_connection();
    $stmt = $pdo->prepare(
        "SELECT id, checkin_time, note FROM checkins WHERE task_id=? ORDER BY id DESC LIMIT 1"
    );
    $stmt->execute([$task_id]);
    $r = $stmt->fetch();
    if (!$r) {
        return null;
    }
    return [
        'id' => (int)$r['id'],
        'checkin_time' => $r['checkin_time'],
        'note' => $r['note'] ?? '',
    ];
}

/**
 * Get all checkins for a task (most recent first).
 * @return array<int, array>
 */
function get_all_checkins(int $task_id, int $limit = 50): array
{
    $pdo = get_connection();
    $stmt = $pdo->prepare(
        "SELECT id, checkin_time, note FROM checkins WHERE task_id=? ORDER BY id DESC LIMIT ?"
    );
    $stmt->execute([$task_id, $limit]);
    return array_map(function ($r) {
        return [
            'id' => (int)$r['id'],
            'checkin_time' => $r['checkin_time'],
            'note' => $r['note'] ?? '',
        ];
    }, $stmt->fetchAll());
}

/**
 * Check if the task can be checked in (no checkin in last 24h).
 */
function can_checkin_task(int $task_id): bool
{
    $pdo = get_connection();
    $stmt = $pdo->prepare(
        "SELECT checkin_time FROM checkins WHERE task_id=? ORDER BY id DESC LIMIT 1"
    );
    $stmt->execute([$task_id]);
    $last = $stmt->fetchColumn();
    if ($last === false) {
        return true;
    }
    try {
        $lastTs = new DateTime($last);
        $diff = (new DateTime())->getTimestamp() - $lastTs->getTimestamp();
        return $diff >= 86400;
    } catch (Exception $e) {
        return true; // corrupt data → allow checkin
    }
}

/**
 * Check if a reminder has already been sent for this checkin.
 */
function is_reminder_sent(int $task_id, int $checkin_id, string $reminder_type): bool
{
    $pdo = get_connection();
    $stmt = $pdo->prepare(
        "SELECT COUNT(*) FROM sent_reminders WHERE task_id=? AND checkin_id=? AND reminder_type=?"
    );
    $stmt->execute([$task_id, $checkin_id, $reminder_type]);
    return $stmt->fetchColumn() > 0;
}

/**
 * Mark a reminder as sent (dedup).
 */
function mark_reminder_sent(int $task_id, int $checkin_id, string $reminder_type): void
{
    $pdo = get_connection();
    $now = date('Y-m-d\TH:i:s');
    try {
        $stmt = $pdo->prepare(
            "INSERT INTO sent_reminders (task_id, checkin_id, reminder_type, sent_at)
             VALUES (?, ?, ?, ?)"
        );
        $stmt->execute([$task_id, $checkin_id, $reminder_type, $now]);
    } catch (PDOException $e) {
        // UNIQUE constraint — already sent, ignore
    }
}

/**
 * Get all notification channels.
 * @return array<int, array>
 */
function get_channels(): array
{
    $pdo = get_connection();
    $rows = $pdo->query(
        "SELECT id, name, channel_type, config, enabled FROM notification_channels ORDER BY id ASC"
    )->fetchAll();
    return array_map(function ($r) {
        return [
            'id' => (int)$r['id'],
            'name' => $r['name'],
            'channel_type' => $r['channel_type'],
            'config' => json_decode($r['config'], true) ?: [],
            'enabled' => (bool)$r['enabled'],
        ];
    }, $rows);
}

/**
 * Get a single notification channel by id.
 */
function get_channel(int $channel_id): ?array
{
    $pdo = get_connection();
    $stmt = $pdo->prepare(
        "SELECT id, name, channel_type, config, enabled FROM notification_channels WHERE id=?"
    );
    $stmt->execute([$channel_id]);
    $r = $stmt->fetch();
    if (!$r) {
        return null;
    }
    return [
        'id' => (int)$r['id'],
        'name' => $r['name'],
        'channel_type' => $r['channel_type'],
        'config' => json_decode($r['config'], true) ?: [],
        'enabled' => (bool)$r['enabled'],
    ];
}

/**
 * Add a new notification channel. Returns the new channel id.
 */
function add_channel(string $name, string $channel_type, array $config_dict): int
{
    $pdo = get_connection();
    $stmt = $pdo->prepare(
        "INSERT INTO notification_channels (name, channel_type, config, enabled) VALUES (?, ?, ?, 1)"
    );
    $stmt->execute([$name, $channel_type, json_encode($config_dict)]);
    return (int)$pdo->lastInsertId();
}

/**
 * Update an existing notification channel.
 */
function update_channel(int $channel_id, string $name, string $channel_type, array $config_dict, bool $enabled): void
{
    $pdo = get_connection();
    $stmt = $pdo->prepare(
        "UPDATE notification_channels SET name=?, channel_type=?, config=?, enabled=? WHERE id=?"
    );
    $stmt->execute([$name, $channel_type, json_encode($config_dict), $enabled ? 1 : 0, $channel_id]);
}

/**
 * Delete a notification channel.
 */
function delete_channel(int $channel_id): void
{
    $pdo = get_connection();
    $pdo->prepare("DELETE FROM notification_channels WHERE id=?")->execute([$channel_id]);
}

/**
 * Helper: format an ISO datetime string for display (same as fmt_time in original).
 */
function fmt_time(?string $iso): string
{
    if (!$iso) {
        return '-';
    }
    try {
        $d = new DateTime($iso);
        return $d->format('Y-m-d H:i');
    } catch (Exception $e) {
        return '-';
    }
}