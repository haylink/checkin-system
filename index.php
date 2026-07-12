<?php
/**
 * Main entry point for the checkin-system (PHP port of app.py).
 * No web server rewrite rules needed. All routing uses query parameters:
 *
 *   https://momy.eu.cc/            → dashboard (home)
 *   https://momy.eu.cc/index.php   → dashboard
 *   https://momy.eu.cc/?p=login    → login page
 *   https://momy.eu.cc/?p=admin    → admin page
 *   https://momy.eu.cc/?p=init     → first-time init page
 *   https://momy.eu.cc/?p=logout   → logout
 *   https://momy.eu.cc/?a=api/tasks          → API (GET/POST/PUT/DELETE)
 *   https://momy.eu.cc/?a=api/notify-test    → test notification
 *
 * Just upload index.php + config.php + database.php + remind.php + reset_password.php
 * + templates/ to public_html/. No .htaccess, no Nginx rewrite, no .env file.
 */

// ── Bootstrap ─────────────────────────────────────────────────────────────────

session_name('TASKFLOW');
session_start();

require_once __DIR__ . '/database.php';

// Initialize database schema on every request (idempotent)
init_db();

// ── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Send a JSON response with the given status code.
 */
function json_response(array $data, int $status = 200): void
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
    exit;
}

/**
 * Send a redirect response.
 * Uses ?p= query parameters so no web server rewrite rules are needed.
 */
function redirect(string $page = 'login'): void
{
    // Accept page name (e.g. 'login', 'admin', 'init') or '?a=api/xxx'
    if ($page === '/') {
        $url = '?';
    } elseif (str_starts_with($page, '/')) {
        $p = ltrim($page, '/');
        $url = '?p=' . $p;
    } else {
        $url = '?p=' . $page;
    }
    header("Location: " . $url);
    exit;
}

/**
 * Render an HTML template.
 */
function render_template(string $filepath, string $msg = ''): void
{
    header('Content-Type: text/html; charset=utf-8');
    $html = file_get_contents($filepath);
    if ($html === false) {
        http_response_code(500);
        echo '<h1>500 Internal Server Error</h1><p>Template not found: ' . htmlspecialchars($filepath) . '</p>';
        exit;
    }
    // Replace placeholder message in login template
    echo str_replace('__MSG__', htmlspecialchars($msg), $html);
    exit;
}

/**
 * Auth guard: redirect to login if not authenticated.
 * If no admin password exists yet, redirect to init page instead.
 * For API routes, returns 401 JSON instead.
 */
function require_auth(bool $is_api = false): void
{
    if (empty($_SESSION['logged_in'])) {
        if ($is_api) {
            json_response(['success' => false, 'error' => '未登录'], 401);
        }
        // If no admin password has been set, redirect to init page
        if (!get_admin_password()) {
            redirect('init');
        }
        redirect('login');
    }
}

/**
 * Read JSON body from POST/PUT request.
 */
function json_body(): ?array
{
    $raw = file_get_contents('php://input');
    if (!$raw) {
        return null;
    }
    $data = json_decode($raw, true);
    return is_array($data) ? $data : null;
}

/**
 * Send notification via all enabled channels after a checkin.
 */
function send_checkin_notification(array $task): void
{
    $channels = array_filter(get_channels(), fn($c) => $c['enabled']);
    if (empty($channels)) {
        return;
    }

    $text = "✅ 签到成功！\n\n"
          . "任务：{$task['name']}\n"
          . "周期：{$task['checkin_days']} 天\n"
          . "时间：" . date('Y-m-d H:i') . "\n\n"
          . "下次签到：{$task['checkin_days']} 天后";

    foreach ($channels as $ch) {
        $ctype = $ch['channel_type'];
        $cfg = $ch['config'];
        if ($ctype === 'telegram') {
            $botToken = $cfg['bot_token'] ?? '';
            $chatId = $cfg['chat_id'] ?? '';
            if (!$botToken || !$chatId) continue;
            http_post_json(
                "https://api.telegram.org/bot{$botToken}/sendMessage",
                ['chat_id' => $chatId, 'text' => $text]
            );
        } elseif ($ctype === 'serverchan') {
            $sendKey = $cfg['send_key'] ?? '';
            if (!$sendKey) continue;
            $title = str_contains($text, "\n\n")
                ? explode("\n\n", $text, 2)[0]
                : mb_substr($text, 0, 50);
            http_post_form(
                "https://sctapi.ftqq.com/{$sendKey}.send",
                ['title' => $title, 'desp' => $text]
            );
        } elseif ($ctype === 'dingtalk') {
            $webhookUrl = $cfg['webhook_url'] ?? '';
            if (!$webhookUrl) continue;
            http_post_json($webhookUrl, [
                'msgtype' => 'text',
                'text' => ['content' => $text],
            ]);
        }
    }
}

/**
 * Helper: HTTP POST with JSON body using curl (fire-and-forget).
 */
function http_post_json(string $url, array $data): void
{
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_POST => 1,
        CURLOPT_POSTFIELDS => json_encode($data),
        CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
        CURLOPT_TIMEOUT => 10,
        CURLOPT_RETURNTRANSFER => 1,
    ]);
    @curl_exec($ch);
    // curl handle auto-released at end of scope
}

/**
 * Helper: HTTP POST with form-urlencoded body using curl (fire-and-forget).
 */
function http_post_form(string $url, array $data): void
{
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_POST => 1,
        CURLOPT_POSTFIELDS => http_build_query($data),
        CURLOPT_HTTPHEADER => ['Content-Type: application/x-www-form-urlencoded'],
        CURLOPT_TIMEOUT => 10,
        CURLOPT_RETURNTRANSFER => 1,
    ]);
    @curl_exec($ch);
    // curl handle auto-released at end of scope
}

// ── Route Parsing ────────────────────────────────────────────────────────────
// Uses query parameters — no web server rewrite rules needed.
// ?p=login  ?p=admin  ?p=init  ?p=logout  → HTML pages
// ?a=api/xxx                                    → API endpoints
// neither ?p nor ?a                             → dashboard (home)

$method = $_SERVER['REQUEST_METHOD'];
$p     = trim($_GET['p'] ?? '');   // page: login, admin, init, logout
$a     = trim($_GET['a'] ?? '');   // action: api/xxx

// Legacy compatibility: if REQUEST_URI contains a path like /login or /api/xxx,
// map it to the equivalent query parameter so existing bookmarks still work.
if ($p === '' && $a === '') {
    $path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
    $path = $path !== '/' ? rtrim($path, '/') : $path;
    if (str_starts_with($path, '/api/')) {
        $a = substr($path, 5);
    } else {
        $p = ltrim($path, '/');
    }
}

// ── Routes (no auth required) ─────────────────────────────────────────────────

// LOGIN
if ($p === 'login') {
    // If no admin password exists yet, redirect to init page
    if (!get_admin_password()) {
        redirect('init');
    }
    if ($method === 'POST') {
        $pw = $_POST['password'] ?? '';
        if ($pw === get_admin_password()) {
            $_SESSION['logged_in'] = true;
            redirect('');
        }
        render_template(__DIR__ . '/templates/login.html', '密码错误，请重试');
    }
    render_template(__DIR__ . '/templates/login.html');
}

// LOGOUT
if ($p === 'logout') {
    session_destroy();
    redirect('login');
}

// ── Reset Password API (no auth required) ─────────────────────────────────────
// Tokens stored in session as associative array: token_hash => timestamp

define('RESET_TOKEN_TTL', 15 * 60);

function cleanup_reset_tokens(): void
{
    if (empty($_SESSION['_reset_tokens'])) {
        $_SESSION['_reset_tokens'] = [];
        return;
    }
    $now = time();
    foreach ($_SESSION['_reset_tokens'] as $token => $ts) {
        if ($now - $ts > RESET_TOKEN_TTL) {
            unset($_SESSION['_reset_tokens'][$token]);
        }
    }
}

if ($a === 'api/reset-password/question' && $method === 'GET') {
    $q = get_setting('security_question');
    if ($q) {
        json_response(['success' => true, 'has_question' => true, 'question' => $q]);
    }
    json_response(['success' => true, 'has_question' => false]);
}

if ($a === 'api/reset-password/check' && $method === 'POST') {
    $data = json_body();
    if (!$data) {
        json_response(['success' => false, 'error' => '无效数据'], 400);
    }
    $answer = strtolower(trim($data['answer'] ?? ''));
    $stored = strtolower(trim(get_setting('security_answer') ?? ''));
    if (!$stored) {
        json_response(['success' => false, 'error' => '未设置密保问题'], 400);
    }
    if ($answer !== $stored) {
        json_response(['success' => false, 'error' => '答案错误'], 400);
    }
    cleanup_reset_tokens();
    $token = bin2hex(random_bytes(16));
    $_SESSION['_reset_tokens'][$token] = time();
    json_response(['success' => true, 'token' => $token]);
}

if ($a === 'api/reset-password/reset' && $method === 'POST') {
    $data = json_body();
    if (!$data) {
        json_response(['success' => false, 'error' => '无效数据'], 400);
    }
    cleanup_reset_tokens();
    $token = $data['token'] ?? '';
    if (!isset($_SESSION['_reset_tokens'][$token])) {
        json_response(['success' => false, 'error' => '请先验证密保问题'], 403);
    }
    $newPassword = trim($data['password'] ?? '');
    if (!$newPassword || strlen($newPassword) < 6) {
        json_response(['success' => false, 'error' => '密码长度不能少于6位'], 400);
    }
    set_setting('admin_password', $newPassword);
    unset($_SESSION['_reset_tokens'][$token]);
    json_response(['success' => true, 'message' => '密码已重置']);
}

// ── Init: First-time admin password setup ──────────────────────────────────────
// These routes are public — no auth required because no admin password exists yet.

if ($a === 'api/init' && $method === 'POST') {
    $data = json_body();
    if (!$data) {
        json_response(['success' => false, 'error' => '无效数据'], 400);
    }
    $password = trim($data['password'] ?? '');
    if (!$password || strlen($password) < 6) {
        json_response(['success' => false, 'error' => '密码长度不能少于6位'], 400);
    }
    // If a password already exists, reject
    if (get_admin_password()) {
        json_response(['success' => false, 'error' => '管理员密码已存在'], 400);
    }
    set_setting('admin_password', $password);
    json_response(['success' => true]);
}

if ($p === 'init') {
    // If a password already exists, redirect to login instead
    if (get_admin_password()) {
        redirect('login');
    }
    render_template(__DIR__ . '/templates/init.html');
}

// ── All remaining routes require auth ─────────────────────────────────────────
// (DASHBOARD, ADMIN, API)
require_auth(str_starts_with($a, 'api/'));

// ── HTML Pages ────────────────────────────────────────────────────────────────

if ($p === '' && $a === '') {
    render_template(__DIR__ . '/templates/dashboard.html');
}

if ($p === 'admin') {
    render_template(__DIR__ . '/templates/admin.html');
}

// ── API: Tasks ────────────────────────────────────────────────────────────────

if ($a === 'api/tasks' && $method === 'GET') {
    $tasks = get_tasks();
    $result = [];
    foreach ($tasks as $t) {
        $last = get_last_checkin($t['id']);
        $can_checkin = $last ? can_checkin_task($t['id']) : true;
        $remaining_days = null;
        $due_date = null;
        $next_remind = null;
        if ($last) {
            $lastTs = new DateTime($last['checkin_time']);
            $due = clone $lastTs;
            $due->modify("+{$t['checkin_days']} days");
            $due_date = $due->format('Y-m-d\TH:i:s');
            $now = new DateTime();
            $remaining = $due->getTimestamp() - $now->getTimestamp();
            $remaining_days = (int)floor($remaining / 86400);

            if ($remaining > 0) {
                $rd = $remaining_days;
                foreach ($t['reminder_days'] as $d) {
                    if ($rd <= $d) {
                        $rt = clone $due;
                        $rt->modify("-{$d} days");
                        if ($rt > $now) {
                            $next_remind = $rt->format('Y-m-d\TH:i:s');
                        }
                        break;
                    }
                }
                if (!$next_remind) {
                    $next_remind = $due_date;
                }
            }
        }
        $result[] = array_merge($t, [
            'can_checkin' => $can_checkin,
            'last_checkin' => $last ? $last['checkin_time'] : null,
            'remaining_days' => $remaining_days,
            'due_date' => $due_date,
            'next_remind' => $next_remind,
        ]);
    }
    json_response(['success' => true, 'tasks' => $result]);
}

if ($a === 'api/tasks' && $method === 'POST') {
    $data = json_body();
    if (!$data || empty(trim($data['name'] ?? ''))) {
        json_response(['success' => false, 'error' => '任务名称不能为空'], 400);
    }
    try {
        $checkin_days = (int)($data['checkin_days'] ?? 7);
        if ($checkin_days < 1) throw new ValueError();
        $reminder_days = $data['reminder_days'] ?? [3, 1];
        if (is_string($reminder_days)) {
            $reminder_days = array_filter(array_map('intval', explode(',', $reminder_days)), fn($n) => $n > 0);
        }
        $reminder_days = array_map('intval', $reminder_days);
        if (!empty($reminder_days) && min($reminder_days) < 1) throw new ValueError();
    } catch (ValueError|TypeError $e) {
        json_response(['success' => false, 'error' => '参数无效'], 400);
    }
    $advance_msg_template = $data['advance_msg_template'] ?? '';
    $final_msg_template = $data['final_msg_template'] ?? '';
    $task_url = $data['url'] ?? '';
    $tid = add_task(
        trim($data['name']),
        trim($data['description'] ?? ''),
        $checkin_days,
        $reminder_days,
        $advance_msg_template,
        $final_msg_template,
        $task_url
    );
    json_response(['success' => true, 'task_id' => $tid]);
}

// ── /api/tasks/<id> (PUT / DELETE) ─────────────────────────────────────────────

// Match /api/tasks/<id>
if (preg_match('#^api/tasks/(\\d+)$#', $a, $m) === 1) {
    $task_id = (int)$m[1];

    if ($method === 'PUT') {
        $data = json_body();
        if (!$data) {
            json_response(['success' => false, 'error' => '无效数据'], 400);
        }
        $task = get_task($task_id);
        if (!$task) {
            json_response(['success' => false, 'error' => '任务不存在'], 404);
        }
        $name = $data['name'] ?? $task['name'];
        $description = $data['description'] ?? $task['description'];
        $url = $data['url'] ?? $task['url'];
        $checkin_days = $data['checkin_days'] ?? $task['checkin_days'];
        $reminder_days = $data['reminder_days'] ?? $task['reminder_days'];
        $active = $data['active'] ?? $task['active'];
        $advance_msg_template = $data['advance_msg_template'] ?? $task['advance_msg_template'];
        $final_msg_template = $data['final_msg_template'] ?? $task['final_msg_template'];
        try {
            $checkin_days = (int)$checkin_days;
            if ($checkin_days < 1) throw new ValueError();
            if (is_string($reminder_days)) {
                $reminder_days = array_filter(array_map('intval', explode(',', $reminder_days)), fn($n) => $n > 0);
            }
            $reminder_days = array_map('intval', $reminder_days);
            if (!empty($reminder_days) && min($reminder_days) < 1) throw new ValueError();
        } catch (ValueError|TypeError $e) {
            json_response(['success' => false, 'error' => '参数无效'], 400);
        }
        update_task($task_id, $name, $description, $checkin_days, $reminder_days,
            $active, $advance_msg_template, $final_msg_template, $url);
        json_response(['success' => true]);
    }

    if ($method === 'DELETE') {
        $task = get_task($task_id);
        if (!$task) {
            json_response(['success' => false, 'error' => '任务不存在'], 404);
        }
        delete_task($task_id);
        json_response(['success' => true]);
    }
}

// ── /api/tasks/<id>/checkin ──────────────────────────────────────────────────

if (preg_match('#^api/tasks/(\\d+)/checkin$#', $a, $m) === 1 && $method === 'POST') {
    $task_id = (int)$m[1];
    $task = get_task($task_id);
    if (!$task) {
        json_response(['success' => false, 'error' => '任务不存在'], 404);
    }
    $data = json_body();
    $note = ($data ?? [])['note'] ?? '';
    $cid = add_checkin($task_id, $note);
    if ($cid === 0) {
        json_response(['success' => false, 'error' => '24小时内只能签到一次'], 400);
    }

    // Send notifications to all enabled channels
    send_checkin_notification($task);

    json_response(['success' => true, 'checkin_id' => $cid]);
}

// ── /api/tasks/<id>/history ──────────────────────────────────────────────────

if (preg_match('#^api/tasks/(\\d+)/history$#', $a, $m) === 1 && $method === 'GET') {
    $task_id = (int)$m[1];
    $history = get_all_checkins($task_id);
    json_response(['success' => true, 'history' => $history]);
}

// ── API: Channels ─────────────────────────────────────────────────────────────

if ($a === 'api/channels' && $method === 'GET') {
    json_response(['success' => true, 'channels' => get_channels()]);
}

if ($a === 'api/channels' && $method === 'POST') {
    $data = json_body();
    if (!$data || empty(trim($data['name'] ?? ''))) {
        json_response(['success' => false, 'error' => '名称不能为空'], 400);
    }
    $ctype = $data['channel_type'] ?? 'telegram';
    $cfg = $data['config'] ?? [];
    $cid = add_channel(trim($data['name']), $ctype, $cfg);
    json_response(['success' => true, 'channel_id' => $cid]);
}

// ── /api/channels/<id> (PUT / DELETE) ─────────────────────────────────────────

if (preg_match('#^api/channels/(\\d+)$#', $a, $m) === 1) {
    $channel_id = (int)$m[1];

    if ($method === 'PUT') {
        $data = json_body();
        if (!$data) {
            json_response(['success' => false, 'error' => '无效数据'], 400);
        }
        $ch = get_channel($channel_id);
        if (!$ch) {
            json_response(['success' => false, 'error' => '通道不存在'], 404);
        }
        $name = $data['name'] ?? $ch['name'];
        $ctype = $data['channel_type'] ?? $ch['channel_type'];
        $cfg = $data['config'] ?? $ch['config'];
        $enabled = $data['enabled'] ?? $ch['enabled'];
        update_channel($channel_id, $name, $ctype, $cfg, $enabled);
        json_response(['success' => true]);
    }

    if ($method === 'DELETE') {
        $ch = get_channel($channel_id);
        if (!$ch) {
            json_response(['success' => false, 'error' => '通道不存在'], 404);
        }
        delete_channel($channel_id);
        json_response(['success' => true]);
    }
}

// ── /api/channels/test ────────────────────────────────────────────────────────

if ($a === 'api/channels/test' && $method === 'POST') {
    $data = json_body();
    if (!$data) {
        json_response(['success' => false, 'error' => '无效数据'], 400);
    }
    $ctype = $data['channel_type'] ?? 'telegram';
    $cfg = $data['config'] ?? [];
    $text = '🧪 这是一条测试消息，通知通道配置成功！';

    try {
        if ($ctype === 'telegram') {
            $botToken = $cfg['bot_token'] ?? '';
            $chatId = $cfg['chat_id'] ?? '';
            if (!$botToken || !$chatId) {
                json_response(['success' => false, 'error' => 'Bot Token 和 Chat ID 不能为空'], 400);
            }
            $ch = curl_init("https://api.telegram.org/bot{$botToken}/sendMessage");
            curl_setopt_array($ch, [
                CURLOPT_POST => 1,
                CURLOPT_POSTFIELDS => json_encode(['chat_id' => $chatId, 'text' => $text]),
                CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
                CURLOPT_TIMEOUT => 10,
                CURLOPT_RETURNTRANSFER => 1,
            ]);
            $resp = curl_exec($ch);
            // curl handle auto-released at end of scope
            $result = json_decode($resp, true);
            if (empty($result['ok'])) {
                json_response(['success' => false, 'error' => $result['description'] ?? '发送失败'], 400);
            }
        } elseif ($ctype === 'serverchan') {
            $sendKey = $cfg['send_key'] ?? '';
            if (!$sendKey) {
                json_response(['success' => false, 'error' => 'SendKey 不能为空'], 400);
            }
            $ch = curl_init("https://sctapi.ftqq.com/{$sendKey}.send");
            curl_setopt_array($ch, [
                CURLOPT_POST => 1,
                CURLOPT_POSTFIELDS => http_build_query(['title' => '签到提醒系统测试', 'desp' => $text]),
                CURLOPT_HTTPHEADER => ['Content-Type: application/x-www-form-urlencoded'],
                CURLOPT_TIMEOUT => 10,
                CURLOPT_RETURNTRANSFER => 1,
            ]);
            $resp = curl_exec($ch);
            // curl handle auto-released at end of scope
            $result = json_decode($resp, true);
            if (($result['code'] ?? -1) !== 0) {
                json_response(['success' => false, 'error' => $result['message'] ?? '发送失败'], 400);
            }
        } elseif ($ctype === 'dingtalk') {
            $webhookUrl = $cfg['webhook_url'] ?? '';
            if (!$webhookUrl) {
                json_response(['success' => false, 'error' => 'Webhook URL 不能为空'], 400);
            }
            $ch = curl_init($webhookUrl);
            curl_setopt_array($ch, [
                CURLOPT_POST => 1,
                CURLOPT_POSTFIELDS => json_encode(['msgtype' => 'text', 'text' => ['content' => $text]]),
                CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
                CURLOPT_TIMEOUT => 10,
                CURLOPT_RETURNTRANSFER => 1,
            ]);
            $resp = curl_exec($ch);
            // curl handle auto-released at end of scope
            $result = json_decode($resp, true);
            if (($result['errcode'] ?? -1) !== 0) {
                json_response(['success' => false, 'error' => $result['errmsg'] ?? '发送失败'], 400);
            }
        } else {
            json_response(['success' => false, 'error' => '不支持的通道类型'], 400);
        }
        json_response(['success' => true]);
    } catch (Exception $e) {
        json_response(['success' => false, 'error' => mb_substr($e->getMessage(), 0, 200)], 400);
    }
}

// ── API: Settings ─────────────────────────────────────────────────────────────

if ($a === 'api/settings') {
    if ($method === 'GET') {
        json_response([
            'success' => true,
            'has_password' => (bool)get_admin_password(),
        ]);
    }
    if ($method === 'PUT') {
        $data = json_body();
        if (!$data) {
            json_response(['success' => false, 'error' => '无效数据'], 400);
        }
        $newPassword = trim($data['password'] ?? '');
        if (!$newPassword) {
            json_response(['success' => false, 'error' => '密码不能为空'], 400);
        }
        if (strlen($newPassword) < 6) {
            json_response(['success' => false, 'error' => '密码长度不能少于6位'], 400);
        }
        set_setting('admin_password', $newPassword);
        // Rotate secret_key to invalidate existing sessions
        json_response(['success' => true, 'message' => '密码已修改，请重新登录']);
    }
}

if ($a === 'api/settings/security') {
    if ($method === 'GET') {
        $q = get_setting('security_question') ?: '';
        json_response(['success' => true, 'question' => $q]);
    }
    if ($method === 'PUT') {
        $data = json_body();
        if (!$data) {
            json_response(['success' => false, 'error' => '无效数据'], 400);
        }
        $question = trim($data['question'] ?? '');
        $answer = trim($data['answer'] ?? '');
        if (!$question || !$answer) {
            json_response(['success' => false, 'error' => '问题和答案不能为空'], 400);
        }
        set_setting('security_question', $question);
        set_setting('security_answer', $answer);
        json_response(['success' => true]);
    }
}

// ── 404 Fallback ──────────────────────────────────────────────────────────────

json_response(['success' => false, 'error' => 'Not Found'], 404);