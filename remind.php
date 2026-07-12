<?php
/**
 * Cron-triggered reminder script — PHP port of remind.py.
 * Called every minute from crontab:
 *   * * * * * cd /path/to/checkin-system && php remind.php >> logs/remind.log 2>&1
 */

require_once __DIR__ . '/database.php';

init_db();

function send_telegram(string $bot_token, string $chat_id, string $text): bool
{
    $url = "https://api.telegram.org/bot{$bot_token}/sendMessage";
    $payload = json_encode(['chat_id' => $chat_id, 'text' => $text]);
    try {
        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_POST => 1,
            CURLOPT_POSTFIELDS => $payload,
            CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
            CURLOPT_TIMEOUT => 10,
            CURLOPT_RETURNTRANSFER => 1,
        ]);
        $resp = @curl_exec($ch);
        // curl handle auto-released at end of scope
        $result = json_decode($resp, true);
        $ok = !empty($result['ok']);
        if ($ok) {
            echo "[" . date('Y-m-d H:i:s') . "] Telegram message sent to {$chat_id}\n";
        } else {
            echo "[" . date('Y-m-d H:i:s') . "] Telegram error: " . ($result['description'] ?? 'unknown') . "\n";
        }
        return $ok;
    } catch (Exception $e) {
        echo "[" . date('Y-m-d H:i:s') . "] Failed to send Telegram message: {$e->getMessage()}\n";
        return false;
    }
}

function send_serverchan(string $send_key, string $text): bool
{
    $title = str_contains($text, "\n\n")
        ? explode("\n\n", $text, 2)[0]
        : mb_substr($text, 0, 50);
    $url = "https://sctapi.ftqq.com/{$send_key}.send";
    try {
        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_POST => 1,
            CURLOPT_POSTFIELDS => http_build_query(['title' => $title, 'desp' => $text]),
            CURLOPT_HTTPHEADER => ['Content-Type: application/x-www-form-urlencoded'],
            CURLOPT_TIMEOUT => 10,
            CURLOPT_RETURNTRANSFER => 1,
        ]);
        $resp = @curl_exec($ch);
        // curl handle auto-released at end of scope
        $result = json_decode($resp, true);
        $ok = ($result['code'] ?? -1) === 0;
        if ($ok) {
            echo "[" . date('Y-m-d H:i:s') . "] ServerChan message sent\n";
        } else {
            echo "[" . date('Y-m-d H:i:s') . "] ServerChan error: " . ($result['message'] ?? 'unknown') . "\n";
        }
        return $ok;
    } catch (Exception $e) {
        echo "[" . date('Y-m-d H:i:s') . "] Failed to send ServerChan message: {$e->getMessage()}\n";
        return false;
    }
}

function send_dingtalk(string $webhook_url, string $text): bool
{
    $payload = json_encode(['msgtype' => 'text', 'text' => ['content' => $text]]);
    try {
        $ch = curl_init($webhook_url);
        curl_setopt_array($ch, [
            CURLOPT_POST => 1,
            CURLOPT_POSTFIELDS => $payload,
            CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
            CURLOPT_TIMEOUT => 10,
            CURLOPT_RETURNTRANSFER => 1,
        ]);
        $resp = @curl_exec($ch);
        // curl handle auto-released at end of scope
        $result = json_decode($resp, true);
        $ok = ($result['errcode'] ?? -1) === 0;
        if ($ok) {
            echo "[" . date('Y-m-d H:i:s') . "] DingTalk message sent\n";
        } else {
            echo "[" . date('Y-m-d H:i:s') . "] DingTalk error: " . ($result['errmsg'] ?? 'unknown') . "\n";
        }
        return $ok;
    } catch (Exception $e) {
        echo "[" . date('Y-m-d H:i:s') . "] Failed to send DingTalk message: {$e->getMessage()}\n";
        return false;
    }
}

function send_notification(array $channel, string $text): bool
{
    $ctype = $channel['channel_type'];
    $cfg = $channel['config'];
    if ($ctype === 'telegram') {
        return send_telegram($cfg['bot_token'] ?? '', $cfg['chat_id'] ?? '', $text);
    } elseif ($ctype === 'serverchan') {
        return send_serverchan($cfg['send_key'] ?? '', $text);
    } elseif ($ctype === 'dingtalk') {
        return send_dingtalk($cfg['webhook_url'] ?? '', $text);
    } else {
        echo "[" . date('Y-m-d H:i:s') . "] Unknown channel type: {$ctype}\n";
        return false;
    }
}

function check_and_remind(): void
{
    $tasks = get_tasks();
    $channels = array_filter(get_channels(), fn($c) => $c['enabled']);

    if (empty($channels)) {
        echo "[" . date('Y-m-d H:i:s') . "] No enabled notification channels found\n";
    }

    foreach ($tasks as $task) {
        if (!$task['active']) {
            continue;
        }

        $last = get_last_checkin($task['id']);
        if (!$last) {
            echo "[" . date('Y-m-d H:i:s') . "] Task '{$task['name']}': no check-in, skipping\n";
            continue;
        }

        $checkinTime = new DateTime($last['checkin_time']);
        $now = new DateTime();
        $dueDate = clone $checkinTime;
        $dueDate->modify("+{$task['checkin_days']} days");
        $remaining = $dueDate->getTimestamp() - $now->getTimestamp();
        $remaining_days = (int)floor($remaining / 86400);

        if ($remaining <= 0) {
            // Final reminder
            $reminder_type = 'final';
            if (!is_reminder_sent($task['id'], $last['id'], $reminder_type)) {
                $overdue_days = abs($remaining_days);
                $tpl = !empty($task['final_msg_template']) ? $task['final_msg_template'] : FINAL_TEMPLATE;
                $text = str_replace(
                    ['{name}', '{cycle}', '{remaining}', '{due}', '{overdue}'],
                    [$task['name'], $task['checkin_days'], $overdue_days, $dueDate->format('Y-m-d'), $overdue_days],
                    $tpl
                );
                foreach ($channels as $ch) {
                    send_notification($ch, $text);
                }
                mark_reminder_sent($task['id'], $last['id'], $reminder_type);
            } else {
                echo "[" . date('Y-m-d H:i:s') . "] Task '{$task['name']}': final reminder already sent\n";
            }
            continue;
        }

        // Advance reminders
        foreach ($task['reminder_days'] as $day) {
            if ($remaining_days === $day) {
                $reminder_type = "advance_{$day}";
                if (!is_reminder_sent($task['id'], $last['id'], $reminder_type)) {
                    $tpl = !empty($task['advance_msg_template']) ? $task['advance_msg_template'] : ADVANCE_TEMPLATE;
                    $text = str_replace(
                        ['{name}', '{cycle}', '{remaining}', '{due}'],
                        [$task['name'], $task['checkin_days'], $remaining_days, $dueDate->format('Y-m-d')],
                        $tpl
                    );
                    foreach ($channels as $ch) {
                        send_notification($ch, $text);
                    }
                    mark_reminder_sent($task['id'], $last['id'], $reminder_type);
                } else {
                    echo "[" . date('Y-m-d H:i:s') . "] Task '{$task['name']}': reminder {$reminder_type} already sent\n";
                }
                break;
            }
        }

        echo "[" . date('Y-m-d H:i:s') . "] Task '{$task['name']}': due={$dueDate->format('Y-m-d')}, remaining={$remaining_days} days\n";
    }
}

check_and_remind();