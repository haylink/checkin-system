#!/usr/bin/env php
<?php
/**
 * CLI password reset tool — PHP port of reset_password.py.
 *
 * Usage:
 *   php reset_password.php <new_password>
 *
 * Example:
 *   php reset_password.php admin123
 */

// Ensure we're in the project directory
chdir(__DIR__);

// Set dummy env vars so config.php can load
putenv('ADMIN_PASSWORD=dummy_for_init');
putenv('TELEGRAM_BOT_TOKEN=dummy_bot_token');
putenv('TELEGRAM_CHAT_ID=1');

require_once __DIR__ . '/database.php';

if ($argc < 2) {
    echo "❌ Usage: php reset_password.php <new_password>\n";
    echo "   Example: php reset_password.php admin123\n";
    exit(1);
}

$newPassword = trim($argv[1]);
if (strlen($newPassword) < 6) {
    echo "❌ Password must be at least 6 characters\n";
    exit(1);
}
if (!$newPassword) {
    echo "❌ Password cannot be empty\n";
    exit(1);
}

init_db();
set_setting('admin_password', $newPassword);
echo "✅ Password has been reset to: {$newPassword}\n";
echo "   Please use the new password to log in\n";