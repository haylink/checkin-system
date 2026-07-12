<?php
/**
 * Configuration for checkin-system (PHP port).
 * Reads environment variables with the same defaults as the original config.py.
 */

$ADMIN_PASSWORD = getenv('ADMIN_PASSWORD') ?: '';
if (!$ADMIN_PASSWORD) {
    throw new RuntimeException(
        "❌ ADMIN_PASSWORD environment variable not set.\n" .
        "   export ADMIN_PASSWORD='***'\n"
    );
}

$TELEGRAM_BOT_TOKEN = getenv('TELEGRAM_BOT_TOKEN') ?: '';
$TELEGRAM_CHAT_ID = getenv('TELEGRAM_CHAT_ID') ?: '0';
// Preserve original type behavior — int when valid, 0 otherwise
$TELEGRAM_CHAT_ID = ctype_digit(ltrim($TELEGRAM_CHAT_ID, '-')) ? (int)$TELEGRAM_CHAT_ID : 0;

$DATABASE_PATH = getenv('DATABASE_PATH') ?: __DIR__ . '/data.db';