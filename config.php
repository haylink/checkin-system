<?php
/**
 * Configuration for checkin-system (PHP port).
 * Reads environment variables with the same defaults as the original config.py.
 */
// ── Auto-load .env file (optional) ────────────────────────────────────────────
function load_dotenv(): void
{
    // Only look for .env in the same directory — no parent directory,
    // no open_basedir issues, no unnecessary file access.
    $path = __DIR__ . '/.env';
    if (!is_readable($path)) return;
    foreach (file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
        $line = trim($line);
        if ($line === '' || $line[0] === '#') continue;
        $pos = strpos($line, '=');
        if ($pos === false) continue;
        $key = trim(substr($line, 0, $pos));
        $val = trim(substr($line, $pos + 1));
        if (strlen($val) >= 2 && (($val[0] === "'" && $val[-1] === "'") || ($val[0] === '"' && $val[-1] === '"'))) {
            $val = substr($val, 1, -1);
        }
        if (empty(getenv($key))) {
            putenv("{$key}={$val}");
            $_ENV[$key] = $val;
            $_SERVER[$key] = $val;
        }
    }
}
load_dotenv();

// ── Configuration ──────────────────────────────────────────────────────────────
// ADMIN_PASSWORD is optional. It is NOT required at startup.
// On first visit, if no admin password exists in the DB, users are redirected
// to the init page to set one via the web UI.
$ADMIN_PASSWORD = getenv('ADMIN_PASSWORD') ?: '';

$TELEGRAM_BOT_TOKEN = getenv('TELEGRAM_BOT_TOKEN') ?: '';
$TELEGRAM_CHAT_ID = getenv('TELEGRAM_CHAT_ID') ?: '0';
if ($TELEGRAM_CHAT_ID === '0') {
    $TELEGRAM_CHAT_ID = 0;
} elseif (ctype_digit(ltrim((string)$TELEGRAM_CHAT_ID, '-'))) {
    $TELEGRAM_CHAT_ID = (int)$TELEGRAM_CHAT_ID;
} else {
    $TELEGRAM_CHAT_ID = 0;
}
$DATABASE_PATH = getenv('DATABASE_PATH') ?: __DIR__ . '/data.db';