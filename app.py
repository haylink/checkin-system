import datetime
import hashlib
import json
import logging
from functools import wraps

import requests
from flask import Flask, jsonify, redirect, render_template_string, request, session

import config
import database

app = Flask(__name__)
# Secret key 在 init_settings() 之后设置（见启动块）
logger = logging.getLogger(__name__)


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "未登录"}), 401
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated


def fmt_time(iso):
    if not iso:
        return "-"
    try:
        d = datetime.datetime.fromisoformat(iso)
    except (ValueError, TypeError):
        return "-"
    return d.strftime("%Y-%m-%d %H:%M")


# ── HTML Templates ──────────────────────────────────────────────────────────

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>签到系统</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;500;600&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg-primary:#07070a;--bg-card:rgba(18,18,24,0.75);--border-subtle:rgba(255,255,255,0.06);--accent:#6366f1;--accent-glow:rgba(99,102,241,0.25);--accent-gradient:linear-gradient(135deg,#6366f1 0%,#8b5cf6 100%);--text-primary:#f1f5f9;--text-secondary:#94a3b8;--text-muted:#64748b;--radius-sm:10px;--radius-lg:20px}
body{font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--bg-primary);min-height:100vh;display:flex;align-items:center;justify-content:center;overflow:hidden;color:var(--text-primary)}
body::before{content:'';position:fixed;top:0;left:0;width:100%;height:100%;background:radial-gradient(ellipse 600px 600px at 20% 30%,rgba(99,102,241,0.04) 0%,transparent 70%),radial-gradient(ellipse 500px 500px at 80% 70%,rgba(139,92,246,0.03) 0%,transparent 70%);pointer-events:none;z-index:-1;animation:bgShift 20s ease-in-out infinite alternate}
@keyframes bgShift{0%{transform:translate(0,0) scale(1)}50%{transform:translate(-2%,1%) scale(1.02)}100%{transform:translate(2%,-1%) scale(1.01)}}
.background-pattern{position:fixed;top:0;left:0;width:100%;height:100%;opacity:0.015;background-image:repeating-linear-gradient(45deg,transparent,transparent 2px,rgba(255,255,255,0.08) 2px,rgba(255,255,255,0.08) 4px);z-index:-1}
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:3px}
.auth-card{width:400px;max-width:92vw;background:var(--bg-card);backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);border-radius:var(--radius-lg);border:1px solid var(--border-subtle);padding:40px 36px;box-shadow:0 16px 48px rgba(0,0,0,0.3);position:relative;overflow:hidden}
.auth-card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,0.08),transparent)}
.auth-card h1{text-align:center;font-size:1.8rem;font-weight:200;margin-bottom:8px;background:linear-gradient(135deg,#f8fafc 0%,#94a3b8 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;letter-spacing:-0.02em}
.auth-card .subtitle{text-align:center;color:var(--text-muted);font-size:0.9rem;font-weight:300;margin-bottom:32px}
.form-group{margin-bottom:20px}
.form-group label{display:block;color:var(--text-secondary);margin-bottom:8px;font-size:0.9rem;letter-spacing:0.3px}
.form-group input{width:100%;padding:14px 18px;border:none;border-radius:var(--radius-sm);background:rgba(30,30,38,0.8);color:var(--text-primary);font-size:15px;border:1px solid rgba(255,255,255,0.07);transition:all 0.25s ease}
.form-group input::placeholder{color:var(--text-muted)}
.form-group input:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-glow);background:rgba(36,36,46,0.9)}
.btn{width:100%;background:var(--accent-gradient);color:white;border:none;padding:13px 26px;border-radius:var(--radius-sm);cursor:pointer;font-size:15px;font-weight:500;transition:all 0.25s ease;box-shadow:0 4px 16px var(--accent-glow);position:relative;overflow:hidden;user-select:none}
.btn:hover{transform:translateY(-1px);box-shadow:0 6px 24px var(--accent-glow)}
.btn:active{transform:translateY(0)}
.msg{padding:12px 16px;border-radius:var(--radius-sm);margin-bottom:20px;font-size:0.9rem;display:none;align-items:center;gap:10px;animation:msgIn 0.3s ease;border:1px solid}
@keyframes msgIn{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:translateY(0)}}
.msg.error{display:flex;background:rgba(239,68,68,0.08);color:#ef4444;border-color:rgba(239,68,68,0.15)}
.msg.error::before{content:'✕';width:18px;height:18px;background:#ef4444;color:white;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;flex-shrink:0}
.forgot-link{text-align:center;margin-top:16px}
.forgot-link a{color:var(--text-muted);font-size:0.82rem;text-decoration:none;cursor:pointer;transition:color 0.2s}
.forgot-link a:hover{color:var(--text-secondary)}
.reset-tip{display:none;margin-top:16px;padding:14px 16px;border-radius:var(--radius-sm);background:rgba(30,30,38,0.6);border:1px solid rgba(255,255,255,0.06);font-size:0.82rem;color:var(--text-muted);line-height:1.6;animation:msgIn 0.3s ease}
.reset-tip code{display:block;background:rgba(0,0,0,0.3);padding:8px 12px;border-radius:6px;margin-top:6px;font-size:0.8rem;color:#06b6d4;word-break:break-all;font-family:'SF Mono','Fira Code',monospace}
.footer{text-align:center;margin-top:24px;font-size:0.78rem;color:rgba(255,255,255,0.15)}
</style>
</head>
<body>
<div class="background-pattern"></div>
<div class="auth-card">
<h1>签到系统</h1>
<p class="subtitle">管理您的签到任务</p>
<div id="msg" class="msg">{{msg}}</div>

<!-- 登录表单 -->
<form id="loginForm" method="POST" style="display:block">
<div class="form-group"><label>管理密码</label><input type="password" name="password" placeholder="请输入管理密码" autofocus></div>
<button class="btn" type="submit">登 录</button>
</form>

<!-- 忘记密码步骤 -->
<div id="forgotStep" style="display:none">
<div id="forgotMsg" class="msg" style="margin-bottom:16px"></div>
<div id="stepQ" style="display:block">
<div class="form-group"><label id="securityQuestionLabel">密保问题</label><input id="sq_answer" placeholder="请输入答案" style="font-family:SF Mono,Fira Code,monospace"></div>
<button class="btn" onclick="checkAnswer()" style="margin-bottom:12px">验证答案</button>
<button class="btn" style="background:transparent;border:1px solid rgba(255,255,255,0.12);box-shadow:none;color:var(--text-secondary);font-size:13px;padding:8px" onclick="backToLogin()">返回登录</button>
</div>
<div id="stepP" style="display:none">
<div class="form-group"><label>新密码（至少6位）</label><input type="password" id="np1" placeholder="输入新密码" style="font-family:SF Mono,Fira Code,monospace"></div>
<div class="form-group"><label>确认新密码</label><input type="password" id="np2" placeholder="再次输入" style="font-family:SF Mono,Fira Code,monospace"></div>
<button class="btn" onclick="resetPassword()" style="margin-bottom:12px">重置密码</button>
<button class="btn" style="background:transparent;border:1px solid rgba(255,255,255,0.12);box-shadow:none;color:var(--text-secondary);font-size:13px;padding:8px" onclick="backToLogin()">返回登录</button>
</div>
</div>

<div class="forgot-link"><a onclick="showForgot()">忘记密码？</a></div>
<p class="footer">TaskFlow</p>
</div>

<script>
var _resetToken=null;
function showMsg(el,text,type){el.className='msg '+type;el.innerHTML='<span>'+text+'</span>'}
function backToLogin(){document.getElementById('loginForm').style.display='block';document.getElementById('forgotStep').style.display='none'}
function showForgot(){
  _resetToken=null;
  var f=document.getElementById('forgotStep');
  document.getElementById('loginForm').style.display='none';
  f.style.display='block';
  document.getElementById('stepQ').style.display='block';
  document.getElementById('stepP').style.display='none';
  document.getElementById('forgotMsg').className='msg';
  var msg=document.getElementById('forgotMsg');
  msg.innerHTML='<span>正在加载...</span>';msg.className='msg';
  fetch('/api/reset-password/question').then(r=>r.json()).then(d=>{
    if(d.success&&d.has_question){
      document.getElementById('securityQuestionLabel').textContent='🔐 '+d.question;
      document.getElementById('forgotMsg').className='msg';
    }else{
      document.getElementById('stepQ').style.display='none';
      document.getElementById('stepP').style.display='none';
      showMsg(document.getElementById('forgotMsg'),'未设置密保问题，请联系管理员在后台配置。如需紧急重置，登录服务器执行：<code style="display:block;background:rgba(0,0,0,0.3);padding:6px 10px;border-radius:4px;margin-top:6px;font-size:0.78rem;color:#06b6d4">python3 reset_password.py 新密码</code>','error');
    }
  }).catch(function(){showMsg(document.getElementById('forgotMsg'),'网络错误','error')});
}
function checkAnswer(){
  var ans=document.getElementById('sq_answer').value.trim();
  if(!ans){showMsg(document.getElementById('forgotMsg'),'请输入答案','error');return}
  fetch('/api/reset-password/check',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({answer:ans})})
    .then(r=>r.json()).then(d=>{
      if(d.success){
        _resetToken=d.token;
        document.getElementById('stepQ').style.display='none';
        document.getElementById('stepP').style.display='block';
        document.getElementById('forgotMsg').className='msg';
      }else{
        showMsg(document.getElementById('forgotMsg'),d.error||'答案错误','error');
      }
    }).catch(function(){showMsg(document.getElementById('forgotMsg'),'网络错误','error')});
}
function resetPassword(){
  var p1=document.getElementById('np1').value,p2=document.getElementById('np2').value;
  if(!p1||p1.length<6){showMsg(document.getElementById('forgotMsg'),'密码长度不能少于6位','error');return}
  if(p1!==p2){showMsg(document.getElementById('forgotMsg'),'两次密码不一致','error');return}
  if(!_resetToken){showMsg(document.getElementById('forgotMsg'),'请先验证密保问题','error');return}
  fetch('/api/reset-password/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:p1,token:_resetToken})})
    .then(r=>r.json()).then(d=>{
      if(d.success){
        showMsg(document.getElementById('forgotMsg'),'密码已重置，请使用新密码登录','success');
        setTimeout(function(){
          document.getElementById('np1').value='';document.getElementById('np2').value='';
          document.getElementById('sq_answer').value='';
          backToLogin();
        },2000);
      }else{
        showMsg(document.getElementById('forgotMsg'),d.error||'重置失败','error');
      }
    }).catch(function(){showMsg(document.getElementById('forgotMsg'),'网络错误','error')});
}
</script>
</body>
</html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>任务面板</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;500;600&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg-primary:#07070a;--bg-card:rgba(18,18,24,0.75);--bg-card-hover:rgba(24,24,32,0.85);--border-subtle:rgba(255,255,255,0.06);--border-hover:rgba(255,255,255,0.12);--accent:#6366f1;--accent-glow:rgba(99,102,241,0.25);--accent-gradient:linear-gradient(135deg,#6366f1 0%,#8b5cf6 100%);--success:#10b981;--warning:#f59e0b;--danger:#ef4444;--text-primary:#f1f5f9;--text-secondary:#94a3b8;--text-muted:#64748b;--radius-sm:10px;--radius-md:16px;--radius-lg:20px}
body{font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--bg-primary);min-height:100vh;color:var(--text-primary);overflow-x:hidden}
body::before{content:'';position:fixed;top:0;left:0;width:100%;height:100%;background:radial-gradient(ellipse 600px 600px at 20% 30%,rgba(99,102,241,0.04) 0%,transparent 70%),radial-gradient(ellipse 500px 500px at 80% 70%,rgba(139,92,246,0.03) 0%,transparent 70%);pointer-events:none;z-index:-1;animation:bgShift 20s ease-in-out infinite alternate}
@keyframes bgShift{0%{transform:translate(0,0) scale(1)}50%{transform:translate(-2%,1%) scale(1.02)}100%{transform:translate(2%,-1%) scale(1.01)}}
.background-pattern{position:fixed;top:0;left:0;width:100%;height:100%;opacity:0.015;background-image:repeating-linear-gradient(45deg,transparent,transparent 2px,rgba(255,255,255,0.08) 2px,rgba(255,255,255,0.08) 4px);z-index:-1}
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:3px}
.container{max-width:860px;margin:0 auto;padding:24px 20px 40px;position:relative;z-index:1}
/* Header */
.header-area{text-align:center;margin-bottom:36px;position:relative}
.header-area h1{font-size:2.2rem;font-weight:200;background:linear-gradient(135deg,#f8fafc 0%,#94a3b8 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;letter-spacing:-0.02em;margin-bottom:6px}
.header-area .sub{font-size:0.85rem;color:var(--text-muted);font-weight:300;letter-spacing:2px;text-transform:uppercase}
.header-actions{position:absolute;top:8px;right:0;display:flex;gap:10px;align-items:center}
.header-actions a{color:var(--text-muted);text-decoration:none;font-size:0.85rem;padding:8px 16px;border-radius:var(--radius-sm);border:1px solid var(--border-subtle);transition:all 0.25s ease;background:rgba(18,18,24,0.5)}
.header-actions a:hover{color:var(--text-primary);border-color:var(--border-hover);background:rgba(24,24,32,0.7)}
/* Stats Bar */
.stats-bar{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:28px}
.stat-card{background:rgba(22,22,30,0.6);border-radius:var(--radius-md);padding:20px;border:1px solid rgba(255,255,255,0.05);text-align:center;transition:all 0.3s ease}
.stat-card:hover{transform:translateY(-2px);border-color:rgba(255,255,255,0.1)}
.stat-num{font-size:2rem;font-weight:200;letter-spacing:-0.02em;margin-bottom:4px}
.stat-label{font-size:0.8rem;color:var(--text-muted);font-weight:300;letter-spacing:0.5px}
.stat-card.total .stat-num{color:var(--text-primary)}
.stat-card.active .stat-num{color:var(--success)}
.stat-card.overdue .stat-num{color:var(--danger)}
/* Task Card */
.task-card{background:rgba(22,22,30,0.7);border-radius:var(--radius-md);padding:26px;margin-bottom:16px;border:1px solid rgba(255,255,255,0.06);position:relative;overflow:hidden;transition:all 0.35s cubic-bezier(0.22,1,0.36,1);animation:cardIn 0.4s ease both}
@keyframes cardIn{from{opacity:0;transform:translateY(16px) scale(0.98)}to{opacity:1;transform:translateY(0) scale(1)}}
.task-card::before{content:'';position:absolute;top:0;left:0;width:100%;height:2px;background:var(--accent-gradient);opacity:0.6;transition:opacity 0.3s}
.task-card:hover{transform:translateY(-2px);box-shadow:0 16px 40px rgba(0,0,0,0.4);border-color:rgba(255,255,255,0.1)}
.task-card:hover::before{opacity:1}
.task-header{display:flex;justify-content:space-between;align-items:start;margin-bottom:14px}
.task-name{font-size:1.1rem;font-weight:500;color:var(--text-primary);letter-spacing:-0.01em}
.task-desc{color:var(--text-muted);font-size:0.82rem;margin-top:3px;line-height:1.4}
.task-meta{display:flex;gap:16px;flex-wrap:wrap;font-size:0.85rem;color:var(--text-secondary);margin-bottom:14px}
.task-meta span{display:flex;align-items:center;gap:4px}
/* Status Badges */
.status-badge{display:inline-flex;align-items:center;padding:4px 12px;border-radius:20px;font-size:0.78rem;font-weight:500;border:1px solid;gap:6px;flex-shrink:0}
.status-badge::before{content:'';width:6px;height:6px;border-radius:50%;flex-shrink:0}
.status-ok{background:rgba(16,185,129,0.08);color:var(--success);border-color:rgba(16,185,129,0.18)}
.status-ok::before{background:var(--success);box-shadow:0 0 6px rgba(16,185,129,0.4)}
.status-warn{background:rgba(245,158,11,0.08);color:var(--warning);border-color:rgba(245,158,11,0.2);animation:pulse-warn 2s ease-in-out infinite}
.status-warn::before{background:var(--warning);box-shadow:0 0 6px rgba(245,158,11,0.4)}
.status-overdue{background:rgba(239,68,68,0.08);color:var(--danger);border-color:rgba(239,68,68,0.2);animation:pulse-danger 1.5s ease-in-out infinite}
.status-overdue::before{background:var(--danger);box-shadow:0 0 6px rgba(239,68,68,0.4)}
@keyframes pulse-warn{0%,100%{box-shadow:0 0 0 0 rgba(245,158,11,0)}50%{box-shadow:0 0 0 6px rgba(245,158,11,0.12)}}
@keyframes pulse-danger{0%,100%{box-shadow:0 0 0 0 rgba(239,68,68,0)}50%{box-shadow:0 0 0 8px rgba(239,68,68,0.12)}}
/* Buttons */
.btn{display:inline-flex;align-items:center;justify-content:center;gap:5px;border:none;border-radius:8px;padding:7px 14px;font-size:13px;font-weight:500;cursor:pointer;transition:all 0.25s ease;position:relative;overflow:hidden;color:#fff;user-select:none;text-decoration:none}
.btn-checkin{background:var(--accent-gradient);box-shadow:0 4px 16px var(--accent-glow)}
.btn-checkin:hover{transform:translateY(-1px);box-shadow:0 6px 24px var(--accent-glow)}
.btn-checkin:disabled{opacity:0.5;cursor:not-allowed;transform:none!important;box-shadow:none!important}
.btn-done{background:rgba(16,185,129,0.15);color:var(--success);cursor:default;border:1px solid rgba(16,185,129,0.2)}
.btn-small{padding:6px 12px;font-size:12px;border-radius:8px;background:transparent;border:1px solid var(--border-subtle);color:var(--text-muted);cursor:pointer;transition:all 0.2s}
.btn-small:hover{color:var(--text-primary);border-color:var(--border-hover);background:rgba(255,255,255,0.04)}
.btn-url{display:inline-flex;align-items:center;gap:4px;padding:6px 12px;font-size:12px;border-radius:8px;background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.2);color:#818cf8;cursor:pointer;transition:all 0.25s ease;text-decoration:none;flex-shrink:0}
.btn-url:hover{background:rgba(99,102,241,0.15);border-color:rgba(99,102,241,0.35);color:#a5b4fc;transform:translateY(-1px)}
.note-input{padding:8px 12px;border-radius:8px;background:rgba(30,30,38,0.6);color:var(--text-secondary);font-size:13px;border:1px solid rgba(255,255,255,0.06);transition:all 0.25s ease;font-family:'Inter',sans-serif;width:100%;min-width:0}
.note-input::placeholder{color:var(--text-muted);font-size:12px}
.note-input:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 2px var(--accent-glow);background:rgba(36,36,46,0.8);color:var(--text-primary)}
.task-actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:6px}
.note-row{margin-top:8px}
/* Messages */
.msg{padding:10px 16px;border-radius:var(--radius-sm);margin-top:12px;display:none;font-size:0.88rem;border:1px solid;align-items:center;gap:10px;animation:msgIn 0.3s ease}
@keyframes msgIn{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:translateY(0)}}
.msg.success{display:flex;background:rgba(16,185,129,0.08);color:var(--success);border-color:rgba(16,185,129,0.15)}
.msg.success::before{content:'✓';width:18px;height:18px;background:var(--success);color:white;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;flex-shrink:0}
.msg.error{display:flex;background:rgba(239,68,68,0.08);color:var(--danger);border-color:rgba(239,68,68,0.15)}
.msg.error::before{content:'✕';width:18px;height:18px;background:var(--danger);color:white;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;flex-shrink:0}
/* History */
.history-box{margin-top:12px;display:none;background:rgba(22,22,30,0.5);border-radius:var(--radius-sm);padding:16px;border:1px solid rgba(255,255,255,0.04)}
.history-box table{width:100%;border-collapse:collapse;font-size:0.85rem}
.history-box th,.history-box td{text-align:left;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.05)}
.history-box th{color:var(--text-muted);font-weight:400;font-size:0.8rem}
.history-box td{color:var(--text-secondary)}
/* Empty State */
.empty{text-align:center;padding:60px 20px;color:var(--text-muted)}
.empty-icon{font-size:3rem;margin-bottom:16px;opacity:0.3;display:block}
.empty h3{font-size:1.2rem;font-weight:300;margin-bottom:8px;color:var(--text-secondary)}
.empty p{font-size:0.9rem}
.empty a{color:var(--accent);text-decoration:none}
.empty a:hover{text-decoration:underline}
/* Separator */
.section-sep{display:flex;align-items:center;gap:16px;margin:8px 0 20px;color:var(--text-muted);font-size:0.8rem;font-weight:300;letter-spacing:1px;text-transform:uppercase}
.section-sep::after{content:'';flex:1;height:1px;background:linear-gradient(90deg,var(--border-subtle),transparent)}
.layout-btn{display:inline-flex;align-items:center;gap:4px;padding:4px 10px;font-size:11px;border-radius:6px;background:transparent;border:1px solid var(--border-subtle);color:var(--text-muted);cursor:pointer;transition:all 0.25s ease;text-transform:none;letter-spacing:0}
.layout-btn:hover{color:var(--text-primary);border-color:var(--border-hover);background:rgba(255,255,255,0.04)}
/* Task Grid */
.task-grid{display:grid;gap:16px;transition:grid-template-columns 0.4s cubic-bezier(0.22,1,0.36,1)}
.task-grid.layout-1{grid-template-columns:1fr}
.task-grid.layout-2{grid-template-columns:1fr 1fr}
.task-grid .task-card{margin-bottom:0;animation:cardIn 0.4s ease both;transition:all 0.35s cubic-bezier(0.22,1,0.36,1)}
.task-grid.layout-2 .task-card .task-actions{width:100%}
.task-grid.layout-2 .task-actions{flex-direction:row;gap:6px}
.task-grid.layout-2 .task-card{padding:18px}
.task-grid.layout-2 .task-name{font-size:0.95rem}
.task-grid.layout-2 .task-desc{font-size:0.78rem}
.task-grid.layout-2 .task-header{margin-bottom:10px}
.task-grid.layout-2 .task-meta{font-size:0.78rem;gap:3px 0;margin-bottom:10px;flex-direction:column}
.task-grid.layout-2 .task-meta span{gap:4px}
.task-grid.layout-2 .status-badge{font-size:0.72rem;padding:3px 10px}
/* Stagger animation */
.task-card:nth-child(1){animation-delay:0.02s}
.task-card:nth-child(2){animation-delay:0.06s}
.task-card:nth-child(3){animation-delay:0.10s}
.task-card:nth-child(4){animation-delay:0.14s}
.task-card:nth-child(5){animation-delay:0.18s}
.task-card:nth-child(6){animation-delay:0.22s}
.task-card:nth-child(7){animation-delay:0.26s}
.task-card:nth-child(8){animation-delay:0.30s}
/* Footer */
.footer{text-align:center;margin-top:36px;font-size:0.75rem;color:rgba(255,255,255,0.1);letter-spacing:1px}
/* Responsive */
@media(max-width:768px){.container{padding:16px 12px 32px}.header-area h1{font-size:1.6rem}.header-actions{position:relative;top:auto;right:auto;justify-content:center;margin-top:16px}.stats-bar{grid-template-columns:repeat(3,1fr);gap:10px}.stat-card{padding:14px 10px}.stat-num{font-size:1.5rem}.task-card{padding:20px}.task-grid.layout-2{grid-template-columns:1fr 1fr}}
@media(max-width:480px){.stats-bar{grid-template-columns:1fr;gap:8px}.task-header{flex-direction:column;gap:10px}.task-actions{flex-direction:column}.task-actions .btn,.task-actions .btn-url,.task-actions .btn-small{width:100%}.task-grid.layout-2{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="background-pattern"></div>
<div class="container">
<div class="header-area">
<h1>任务面板</h1>
<p class="sub">TaskFlow &mdash; 智能签到管理</p>
<div class="header-actions">
<a href="/admin">&#9881;&#65039; 管理</a>
<a href="/logout">退出</a>
</div>
</div>

<div id="statsBar" class="stats-bar"></div>
<div class="section-sep">任务列表</div>
<div style="display:flex;justify-content:flex-end;margin-top:-12px;margin-bottom:12px">
<button class="layout-btn" onclick="toggleLayout()" title="切换布局">⊞ 切换</button>
</div>
<div id="taskList"></div>
<p class="footer">TaskFlow</p>
</div>

<script>
var currentLayout=parseInt(localStorage.getItem('taskLayout'))||1;

function toggleLayout(){
  currentLayout=currentLayout===1?2:1;
  localStorage.setItem('taskLayout',currentLayout);
  var grid=document.getElementById('taskGrid');
  if(grid)grid.className='task-grid layout-'+currentLayout;
}

async function loadTasks(){
  const res=await fetch('/api/tasks');
  if(res.status===401){window.location='/login';return}
  const data=await res.json();
  const tasks=data.tasks||[];
  renderStats(tasks);
  const el=document.getElementById('taskList');
  if(tasks.length===0){
    el.innerHTML='<div class="empty"><div class="empty-icon">📋</div><h3>暂无任务</h3><p>去<a href="/admin">后台管理</a>添加签到任务</p></div>';
    return
  }
  el.innerHTML='<div class="task-grid layout-'+currentLayout+'" id="taskGrid">'+tasks.map(t=>renderTask(t)).join('')+'</div>';
}
function renderStats(tasks){
  const total=tasks.length;
  const normal=tasks.filter(t=>t.active&&t.last_checkin&&t.remaining_days>3).length;
  const pending=tasks.filter(t=>t.active&&t.last_checkin&&t.remaining_days>=0&&t.remaining_days<=3).length;
  document.getElementById('statsBar').innerHTML=
    '<div class="stat-card total"><div class="stat-num">'+total+'</div><div class="stat-label">全部任务</div></div>'+
    '<div class="stat-card active"><div class="stat-num">'+normal+'</div><div class="stat-label">正常</div></div>'+
    '<div class="stat-card overdue"><div class="stat-num">'+pending+'</div><div class="stat-label">待签到</div></div>';
}
function renderTask(t){
  const statusCls=t.last_checkin
    ? (t.remaining_days<0?'status-overdue':'status-ok')
    : 'status-warn';
  const statusText=t.last_checkin
    ? (t.remaining_days<0?'已超期 '+Math.abs(t.remaining_days)+' 天':'距签到 '+t.remaining_days+' 天')
    : '待签到';
  const due=t.last_checkin?'下次签到：'+fmtDate(t.due_date):'—';
  const remind=t.last_checkin&&t.next_remind?'下次提醒：'+fmtDate(t.next_remind):'';
  const canCheckin=t.can_checkin;
  const btnClass=canCheckin?'btn btn-checkin':'btn btn-done';
  const btnText=canCheckin?'✅ 签到':'✅ 已签到';
  const btnDisabled=canCheckin?'':'disabled';
  const urlBtn=t.url?'<a class="btn-url" href="'+esc(t.url)+'" target="_blank" rel="noopener">🔗 访问链接</a>':'';
  return `
    <div class="task-card">
      <div class="task-header">
        <div>
          <div class="task-name">${esc(t.name)}</div>
          ${t.description?'<div class="task-desc">'+esc(t.description)+'</div>':''}
        </div>
        <span class="status-badge ${statusCls}">${statusText}</span>
      </div>
      <div class="task-meta">
        <span>📅 周期：${t.checkin_days} 天</span>
        <span>🔔 ${due}</span>
        ${remind?'<span>⏰ '+remind+'</span>':''}
        <span>📝 上次：${t.last_checkin?fmtDate(t.last_checkin):'—'}</span>
      </div>
      <div class="task-actions">
        <button class="${btnClass}" ${btnDisabled} onclick="doCheckin(${t.id},this)">${btnText}</button>
        ${urlBtn}
        <button class="btn-small" onclick="toggleHistory(${t.id},this)">📜 记录</button>
      </div>
      <div class="note-row"><input class="note-input" id="note-${t.id}" placeholder="签到备注（可选）" maxlength="100"></div>
      <div id="msg-${t.id}" class="msg"></div>
      <div class="history-box" id="history-${t.id}"></div>
    </div>`;
}
function esc(s){return String(s).replace(/[&<>"]/g,function(m){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]})}
function fmtDate(iso){if(!iso)return '-';const d=new Date(iso);return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')+' '+String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0')}

async function doCheckin(taskId,btn){
  btn.disabled=true;btn.textContent='⏳';
  const msg=document.getElementById('msg-'+taskId);
  msg.className='msg';
  const note=document.getElementById('note-'+taskId).value.trim();
  try{
    const res=await fetch('/api/tasks/'+taskId+'/checkin',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({note:note})});
    const data=await res.json();
    if(data.success){
      msg.className='msg success';
      msg.textContent='签到成功！';
    }else{
      msg.className='msg error';
      msg.textContent=data.error||'失败';
    }
  }catch(e){
    msg.className='msg error';
    msg.textContent='网络错误';
  }
  setTimeout(()=>{msg.className='msg'},3000);
  loadTasks();
}

async function toggleHistory(taskId,el){
  const box=document.getElementById('history-'+taskId);
  if(box.style.display==='block'){box.style.display='none';return}
  box.style.display='block';
  if(box.innerHTML)return;
  const res=await fetch('/api/tasks/'+taskId+'/history');
  const data=await res.json();
  if(!data.history||data.history.length===0){
    box.innerHTML='<div style="color:var(--text-muted);font-size:13px;padding:8px 0">暂无记录</div>';
    return
  }
  box.innerHTML='<table><thead><tr><th>#</th><th>时间</th><th>备注</th></tr></thead><tbody>'+
    data.history.map(h=>'<tr><td>'+h.id+'</td><td>'+fmtDate(h.checkin_time)+'</td><td>'+(h.note||'')+'</td></tr>').join('')+
    '</tbody></table>';
}
loadTasks();
</script>
</body>
</html>
"""

ADMIN_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>后台管理</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;500;600&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg-primary:#07070a;--bg-card:rgba(18,18,24,0.75);--bg-card-hover:rgba(24,24,32,0.85);--border-subtle:rgba(255,255,255,0.06);--border-hover:rgba(255,255,255,0.12);--accent:#6366f1;--accent-glow:rgba(99,102,241,0.25);--accent-gradient:linear-gradient(135deg,#6366f1 0%,#8b5cf6 100%);--success:#10b981;--warning:#f59e0b;--danger:#ef4444;--text-primary:#f1f5f9;--text-secondary:#94a3b8;--text-muted:#64748b;--radius-sm:10px;--radius-md:16px;--radius-lg:20px}
body{font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--bg-primary);min-height:100vh;color:var(--text-primary);overflow-x:hidden}
body::before{content:'';position:fixed;top:0;left:0;width:100%;height:100%;background:radial-gradient(ellipse 600px 600px at 20% 30%,rgba(99,102,241,0.04) 0%,transparent 70%),radial-gradient(ellipse 500px 500px at 80% 70%,rgba(139,92,246,0.03) 0%,transparent 70%);pointer-events:none;z-index:-1;animation:bgShift 20s ease-in-out infinite alternate}
@keyframes bgShift{0%{transform:translate(0,0) scale(1)}50%{transform:translate(-2%,1%) scale(1.02)}100%{transform:translate(2%,-1%) scale(1.01)}}
.background-pattern{position:fixed;top:0;left:0;width:100%;height:100%;opacity:0.015;background-image:repeating-linear-gradient(45deg,transparent,transparent 2px,rgba(255,255,255,0.08) 2px,rgba(255,255,255,0.08) 4px);z-index:-1}
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:3px}
.container{max-width:960px;margin:0 auto;padding:24px 20px 40px;position:relative;z-index:1}
/* Header */
.header{display:flex;justify-content:space-between;align-items:center;margin-bottom:40px;position:relative}
.header::after{content:'';position:absolute;bottom:-16px;left:50%;transform:translateX(-50%);width:48px;height:2px;background:linear-gradient(90deg,transparent,var(--accent),transparent);border-radius:1px}
.header h1{font-size:2rem;font-weight:200;background:linear-gradient(135deg,#f8fafc 0%,#94a3b8 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;letter-spacing:-0.02em}
.header a{color:var(--text-muted);text-decoration:none;font-size:0.9rem;padding:8px 16px;border-radius:var(--radius-sm);border:1px solid var(--border-subtle);transition:all 0.25s ease;background:rgba(18,18,24,0.5)}
.header a:hover{color:var(--text-primary);border-color:var(--border-hover);background:rgba(24,24,32,0.7)}
/* Glass Card Section */
.glass-card{background:var(--bg-card);backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);border-radius:var(--radius-lg);border:1px solid var(--border-subtle);padding:32px;margin-bottom:24px;box-shadow:0 16px 48px rgba(0,0,0,0.3);position:relative;overflow:hidden;transition:border-color 0.3s ease}
.glass-card:hover{border-color:var(--border-hover)}
.glass-card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,0.08),transparent)}
.section-title{color:var(--text-primary);font-size:1.15rem;font-weight:400;margin-bottom:24px;display:flex;align-items:center;gap:12px}
.section-title::before{content:'';width:3px;height:16px;background:var(--accent-gradient);border-radius:2px}
/* Table */
.table-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:0.88rem;margin-bottom:4px}
th,td{text-align:left;padding:12px 8px;border-bottom:1px solid rgba(255,255,255,0.05)}
th{color:var(--text-muted);font-weight:400;font-size:0.8rem;text-transform:uppercase;letter-spacing:0.5px}
td{color:var(--text-secondary)}
td .task-desc-sm{color:var(--text-muted);font-size:0.8rem;display:block;margin-top:2px}
/* Tags */
.tag{display:inline-flex;align-items:center;padding:2px 10px;border-radius:12px;font-size:0.75rem;font-weight:500;border:1px solid;gap:4px}
.tag-active{background:rgba(16,185,129,0.1);color:var(--success);border-color:rgba(16,185,129,0.2)}
.tag-inactive{background:rgba(100,116,139,0.1);color:var(--text-muted);border-color:rgba(100,116,139,0.15)}
/* Buttons */
.btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;border:none;border-radius:var(--radius-sm);padding:10px 20px;font-size:13px;font-weight:500;cursor:pointer;transition:all 0.25s ease;position:relative;overflow:hidden;color:#fff;user-select:none;text-decoration:none}
.btn-primary{background:var(--accent-gradient);box-shadow:0 4px 16px var(--accent-glow)}
.btn-primary:hover{transform:translateY(-1px);box-shadow:0 6px 24px var(--accent-glow)}
.btn-danger{background:linear-gradient(135deg,#ef4444 0%,#dc2626 100%);box-shadow:0 4px 16px rgba(239,68,68,0.25)}
.btn-danger:hover{transform:translateY(-1px);box-shadow:0 6px 24px rgba(239,68,68,0.35)}
.btn-outline{background:transparent;border:1px solid rgba(255,255,255,0.12);box-shadow:none;color:var(--text-secondary)}
.btn-outline:hover{border-color:rgba(255,255,255,0.25);color:var(--text-primary);transform:translateY(-1px)}
.btn-small{padding:6px 12px;font-size:12px;border-radius:8px}
/* Form Controls */
.form-group{margin-bottom:18px}
.form-group label{display:block;color:var(--text-secondary);margin-bottom:6px;font-size:0.85rem;letter-spacing:0.3px}
.form-group input,.form-group textarea,.form-group select{width:100%;padding:12px 16px;border:none;border-radius:var(--radius-sm);background:rgba(30,30,38,0.8);color:var(--text-primary);font-size:14px;border:1px solid rgba(255,255,255,0.07);transition:all 0.25s ease;font-family:'Inter',sans-serif}
.form-group input:focus,.form-group textarea:focus,.form-group select:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-glow);background:rgba(36,36,46,0.9)}
.form-group textarea{resize:vertical;min-height:50px}
.form-group select option{background:#1a1a22;color:#f1f5f9}
.form-hint{font-size:0.78rem;color:var(--text-muted);margin-top:4px;display:block}
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.form-actions{display:flex;gap:10px;align-items:center;margin-top:8px}
/* Messages */
.msg{padding:10px 16px;border-radius:var(--radius-sm);margin-bottom:16px;display:none;font-size:0.88rem;border:1px solid;align-items:center;gap:10px;animation:msgIn 0.3s ease}
@keyframes msgIn{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:translateY(0)}}
.msg.success{display:flex;background:rgba(16,185,129,0.08);color:var(--success);border-color:rgba(16,185,129,0.15)}
.msg.success::before{content:'✓';width:18px;height:18px;background:var(--success);color:white;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;flex-shrink:0}
.msg.error{display:flex;background:rgba(239,68,68,0.08);color:var(--danger);border-color:rgba(239,68,68,0.15)}
.msg.error::before{content:'✕';width:18px;height:18px;background:var(--danger);color:white;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;flex-shrink:0}
/* Global Toast */
#globalMsg{position:fixed;top:24px;right:24px;z-index:9999;padding:14px 22px;border-radius:var(--radius-sm);font-weight:500;font-size:0.9rem;box-shadow:0 12px 40px rgba(0,0,0,0.4);transform:translateX(calc(100% + 24px));transition:all 0.4s cubic-bezier(0.22,1,0.36,1);border:1px solid rgba(255,255,255,0.08);max-width:380px}
#globalMsg.show{transform:translateX(0)}
#globalMsg.g-success{background:rgba(16,185,129,0.92);backdrop-filter:blur(12px);color:white;display:flex;align-items:center;gap:10px}
#globalMsg.g-error{background:rgba(239,68,68,0.92);backdrop-filter:blur(12px);color:white;display:flex;align-items:center;gap:10px}
/* Modal */
.modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);align-items:center;justify-content:center;z-index:1000;animation:fadeIn 0.2s ease}
@keyframes fadeIn{from{opacity:0}to{opacity:1}}
.modal.active{display:flex}
.modal-body{background:rgba(18,18,24,0.95);backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);border-radius:var(--radius-lg);padding:32px;width:520px;max-width:92vw;max-height:85vh;overflow-y:auto;border:1px solid var(--border-subtle);box-shadow:0 24px 64px rgba(0,0,0,0.5);position:relative}
.modal-body::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,0.08),transparent)}
.modal-body h3{color:var(--text-primary);font-size:1.15rem;font-weight:400;margin-bottom:24px;display:flex;align-items:center;gap:10px}
.modal-body .form-group{margin-bottom:16px}
/* Channel Config Box */
.channel-config{background:rgba(22,22,30,0.6);border-radius:var(--radius-sm);padding:16px;margin-bottom:16px;border:1px solid rgba(255,255,255,0.04)}
.channel-config .form-group{margin-bottom:10px}
.toolbar{margin-bottom:20px;display:flex;gap:12px}
/* Empty */
.empty{color:var(--text-muted);font-size:0.88rem;padding:20px 0;text-align:center}
/* Action buttons in table */
.action-cell{display:flex;gap:6px;flex-wrap:nowrap}
.action-cell .btn{padding:4px 10px;font-size:11px;border-radius:6px}
/* Checkbox */
.checkbox-group{display:flex;align-items:center;gap:8px;margin-bottom:12px}
.checkbox-group input[type="checkbox"]{width:auto;accent-color:var(--accent)}
.checkbox-group label{margin-bottom:0;cursor:pointer}
/* Responsive */
@media(max-width:768px){.container{padding:16px 12px 32px}.header h1{font-size:1.5rem}.glass-card{padding:20px;border-radius:var(--radius-md)}.form-row{grid-template-columns:1fr;gap:0}.modal-body{padding:24px 20px}#globalMsg{top:16px;right:16px;left:16px;max-width:none}.action-cell{flex-direction:column}.toolbar{flex-direction:column}}
</style>
</head>
<body>
<div class="background-pattern"></div>
<div class="container">
<div class="header">
<h1>后台管理</h1>
<div style="display:flex;gap:10px;align-items:center">
<a href="/">← 返回看板</a>
<a href="/logout" style="color:var(--text-muted);text-decoration:none;font-size:0.9rem;padding:8px 16px;border-radius:var(--radius-sm);border:1px solid var(--border-subtle);transition:all 0.25s ease;background:rgba(18,18,24,0.5)">退出</a>
</div>
</div>

<div id="globalMsg"></div>

<!-- Tasks Section -->
<div class="glass-card">
<div class="section-title">任务管理</div>
<div class="toolbar">
<button class="btn btn-primary" onclick="showTaskModal()">+ 新建任务</button>
</div>
<div class="table-wrap">
<table><thead><tr><th>ID</th><th>名称</th><th>周期</th><th>提醒</th><th>状态</th><th>操作</th></tr></thead>
<tbody id="taskTableBody"></tbody></table>
</div>
</div>

<!-- Channels Section -->
<div class="glass-card">
<div class="section-title">通知通道</div>
<div class="toolbar">
<button class="btn btn-primary" onclick="showChannelModal()">+ 添加通道</button>
</div>
<div class="table-wrap">
<table><thead><tr><th>ID</th><th>名称</th><th>类型</th><th>状态</th><th>操作</th></tr></thead>
<tbody id="channelTableBody"></tbody></table>
</div>
</div>

<!-- Settings Section -->
<div class="glass-card">
<div class="section-title">安全设置</div>
<div id="settingsMsg" class="msg" style="margin-bottom:16px"></div>

<div style="margin-bottom:24px">
<div style="color:var(--text-primary);font-size:0.95rem;font-weight:400;margin-bottom:14px">修改密码</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:12px">
<div class="form-group" style="margin-bottom:0">
<label>新密码</label>
<input type="password" id="sf_password" placeholder="至少6位" minlength="6" style="font-family:SF Mono,Fira Code,monospace">
</div>
<div class="form-group" style="margin-bottom:0">
<label>确认密码</label>
<input type="password" id="sf_password2" placeholder="再次输入" style="font-family:SF Mono,Fira Code,monospace">
</div>
</div>
<button class="btn btn-primary" onclick="saveSettings()" style="width:auto">修改密码</button>
</div>

<div style="border-top:1px solid var(--border-subtle);padding-top:20px">
<div style="color:var(--text-primary);font-size:0.95rem;font-weight:400;margin-bottom:14px">密保问题 <span style="color:var(--text-muted);font-size:0.8rem;font-weight:300">（忘记密码时用于验证身份）</span></div>
<div class="form-group" style="margin-bottom:12px">
<label>问题</label>
<input id="sf_question" placeholder="如：我的宠物名字是？" value="">
</div>
<div class="form-group" style="margin-bottom:12px">
<label>答案</label>
<input type="password" id="sf_answer" placeholder="答案不区分大小写" style="font-family:SF Mono,Fira Code,monospace">
</div>
<button class="btn btn-primary" onclick="saveSecurityQA()" style="width:auto">保存密保</button>
</div>

<script>
function saveSettings(){
  const el=document.getElementById('settingsMsg');
  const pw=document.getElementById('sf_password').value;
  const pw2=document.getElementById('sf_password2').value;
  if(!pw){msg(el,'请输入新密码','error');return}
  if(pw!==pw2){msg(el,'两次密码输入不一致','error');return}
  if(pw.length<6){msg(el,'密码长度不能少于6位','error');return}
  fetch('/api/settings',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:pw})})
    .then(r=>r.json())
    .then(d=>{
      if(d.success){
        msg(el,'密码已修改，即将重新登录','success');
        setTimeout(()=>{window.location='/logout'},2000);
      }else{
        msg(el,d.error||'保存失败','error');
      }
    }).catch(()=>{msg(el,'网络错误','error')});
}
function saveSecurityQA(){
  const el=document.getElementById('settingsMsg');
  const q=document.getElementById('sf_question').value.trim();
  const a=document.getElementById('sf_answer').value.trim();
  if(!q||!a){msg(el,'请填写问题和答案','error');return}
  fetch('/api/settings/security',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q,answer:a})})
    .then(r=>r.json())
    .then(d=>{
      if(d.success){msg(el,'密保问题已保存','success')}
      else{msg(el,d.error||'保存失败','error')}
    }).catch(()=>{msg(el,'网络错误','error')});
}
// 加载已有密保
fetch('/api/settings/security').then(r=>r.json()).then(d=>{
  if(d.success&&d.question)document.getElementById('sf_question').value=d.question;
}).catch(function(){});
</script>
</div>
</div>

<!-- Task Modal -->
<div class="modal" id="taskModal"><div class="modal-body">
<h3 id="taskModalTitle">📌 新建任务</h3>
<div id="taskModalMsg" class="msg"></div>
<div class="form-group"><label>任务名称</label><input id="tf_name" placeholder="输入任务名称"></div>
<div class="form-group"><label>描述（可选）</label><textarea id="tf_desc" rows="2" placeholder="任务描述"></textarea></div>
<div class="form-group"><label>链接（可选）</label><input id="tf_url" placeholder="https://example.com" style="font-family:SF Mono,Fira Code,monospace;font-size:13px"></div>
<div class="form-row">
<div class="form-group"><label>签到周期（天）</label><input type="number" id="tf_days" min="1" value="7"></div>
<div class="form-group"><label>提前提醒（逗号分隔）</label><input id="tf_remind" value="3,1" placeholder="例: 3,1"></div>
</div>
<div class="form-group"><label>提前提醒消息模板</label>
<textarea id="tf_advance_template" rows="2" placeholder="📅 【{name}】签到提醒...">📅 【{name}】签到提醒：签到周期是 {cycle} 天，还有 {remaining} 天到期，请尽快签到！</textarea>
<span class="form-hint">可用变量：{name} {cycle} {remaining} {due}</span>
</div>
<div class="form-group"><label>最后提醒消息模板</label>
<textarea id="tf_final_template" rows="2" placeholder="⚠️ 【{name}】签到最后提醒...">⚠️ 【{name}】签到最后提醒：已超期 {overdue} 天，请马上签到！</textarea>
<span class="form-hint">可用变量：{name} {cycle} {remaining} {due}</span>
</div>
<div class="checkbox-group" id="tf_active_group" style="display:none">
<input type="checkbox" id="tf_active" checked><label for="tf_active">启用</label>
</div>
<div class="form-actions">
<button class="btn btn-primary" onclick="saveTask()">保存</button>
<button class="btn btn-outline" onclick="closeModal('taskModal')">取消</button>
</div>
</div></div>

<!-- Channel Modal -->
<div class="modal" id="channelModal"><div class="modal-body">
<h3 id="channelModalTitle">📢 添加通道</h3>
<div id="channelModalMsg" class="msg"></div>
<div class="form-group"><label>名称</label><input id="cf_name" placeholder="通道名称"></div>
<div class="form-group"><label>类型</label><select id="cf_type" onchange="switchChannelType()">
<option value="telegram">Telegram</option>
<option value="serverchan">Server酱（微信）</option>
<option value="dingtalk">钉钉机器人</option>
</select></div>
<!-- Telegram -->
<div class="channel-config" id="cfgTelegram">
<div class="form-group"><label>Bot Token</label><input id="cf_bot_token" placeholder="输入 Bot Token"></div>
<div class="form-group"><label>Chat ID</label><input id="cf_chat_id" placeholder="输入 Chat ID"></div>
</div>
<!-- Server酱 -->
<div class="channel-config" id="cfgServerchan" style="display:none">
<div class="form-group"><label>SendKey</label><input id="cf_send_key" placeholder="输入 Server酱 SendKey"></div>
<div class="form-group"><label>说明</label><div style="font-size:0.8rem;color:var(--text-muted);line-height:1.5">在 sct.ftqq.com 获取 SendKey，消息将通过微信推送</div></div>
</div>
<!-- 钉钉 -->
<div class="channel-config" id="cfgDingtalk" style="display:none">
<div class="form-group"><label>Webhook URL</label><input id="cf_webhook_url" placeholder="https://oapi.dingtalk.com/robot/send?access_token=XXX"></div>
<div class="form-group"><label>说明</label><div style="font-size:0.8rem;color:var(--text-muted);line-height:1.5">在钉钉群聊中添加机器人，获取 Webhook 地址</div></div>
</div>
<div class="checkbox-group" id="cf_active_group" style="display:none">
<input type="checkbox" id="cf_active" checked><label for="cf_active">启用</label>
</div>
<div class="form-actions">
<button class="btn btn-primary" onclick="saveChannel()">保存</button>
<button class="btn btn-outline" onclick="testChannel()">📤 测试发送</button>
<button class="btn btn-outline" onclick="closeModal('channelModal')">取消</button>
</div>
</div></div>

<script>
var editingTaskId=null,editingChannelId=null;

function esc(s){return String(s).replace(/[&<>"]/g,function(m){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]})}
function msg(el,text,type){el.className='msg '+type;el.innerHTML='<span>'+text+'</span>'}
function closeModal(id){document.getElementById(id).classList.remove('active')}

// ── Tasks ──
async function loadTasks(){
  const res=await fetch('/api/tasks');
  const data=await res.json();
  const tbody=document.getElementById('taskTableBody');
  if(!data.tasks||data.tasks.length===0){
    tbody.innerHTML='<tr><td colspan="6" class="empty">暂无任务</td></tr>';return
  }
  tbody.innerHTML=data.tasks.map(t=>'<tr>'+
    '<td style="color:var(--text-muted)">'+t.id+'</td>'+
    '<td>'+esc(t.name)+(t.description?'<span class="task-desc-sm">'+esc(t.description)+'</span>':'')+'</td>'+
    '<td>'+t.checkin_days+' 天</td>'+
    '<td>'+(t.reminder_days||[]).join(', ')+' 天</td>'+
    '<td>'+(t.active?'<span class="tag tag-active">● 启用</span>':'<span class="tag tag-inactive">○ 停用</span>')+'</td>'+
    '<td><div class="action-cell"><button class="btn btn-primary btn-small" onclick="editTask('+t.id+')">编辑</button>'+
    '<button class="btn btn-danger btn-small" onclick="deleteTask('+t.id+')">删除</button></div></td>'+
    '</tr>').join('');
}

function showTaskModal(data){
  editingTaskId=data?data.id:null;
  document.getElementById('taskModalTitle').textContent=data?'✏️ 编辑任务':'📌 新建任务';
  document.getElementById('tf_name').value=data?data.name:'';
  document.getElementById('tf_desc').value=data?data.description:'';
  document.getElementById('tf_url').value=data?data.url||'':'';
  document.getElementById('tf_days').value=data?data.checkin_days:7;
  document.getElementById('tf_remind').value=data?(data.reminder_days||[]).join(','):'3,1';
  document.getElementById('tf_advance_template').value=data&&data.advance_msg_template?data.advance_msg_template:'📅 【{name}】签到提醒：签到周期是 {cycle} 天，还有 {remaining} 天到期，请尽快签到！';
  document.getElementById('tf_final_template').value=data&&data.final_msg_template?data.final_msg_template:'⚠️ 【{name}】签到最后提醒：已超期 {overdue} 天，请马上签到！';
  document.getElementById('tf_active_group').style.display=data?'flex':'none';
  if(data)document.getElementById('tf_active').checked=data.active;
  document.getElementById('taskModalMsg').className='msg';
  document.getElementById('taskModal').classList.add('active');
}
async function editTask(id){
  const res=await fetch('/api/tasks');
  const data=await res.json();
  const t=(data.tasks||[]).find(x=>x.id===id);
  if(t)showTaskModal(t);
}
async function saveTask(){
  const el=document.getElementById('taskModalMsg');
  const name=document.getElementById('tf_name').value.trim();
  if(!name){msg(el,'名称不能为空','error');return}
  const body={
    name:name,
    description:document.getElementById('tf_desc').value.trim(),
    url:document.getElementById('tf_url').value.trim(),
    checkin_days:parseInt(document.getElementById('tf_days').value)||7,
    reminder_days:document.getElementById('tf_remind').value.split(',').map(s=>parseInt(s.trim())).filter(n=>!isNaN(n)),
    advance_msg_template:document.getElementById('tf_advance_template').value.trim(),
    final_msg_template:document.getElementById('tf_final_template').value.trim(),
    active:document.getElementById('tf_active')?document.getElementById('tf_active').checked:true,
  };
  try{
    const url=editingTaskId?'/api/tasks/'+editingTaskId:'/api/tasks';
    const method=editingTaskId?'PUT':'POST';
    const res=await fetch(url,{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const data=await res.json();
    if(data.success){closeModal('taskModal');loadTasks()}
    else msg(el,data.error||'失败','error');
  }catch(e){msg(el,'网络错误','error')}
}
async function deleteTask(id){
  if(!confirm('确认删除任务 #'+id+'？相关签到记录也会一并删除。'))return;
  const res=await fetch('/api/tasks/'+id,{method:'DELETE'});
  const data=await res.json();
  if(data.success)loadTasks();
  else alert('删除失败: '+(data.error||''));
}

// ── Channels ──
async function loadChannels(){
  const res=await fetch('/api/channels');
  const data=await res.json();
  const tbody=document.getElementById('channelTableBody');
  if(!data.channels||data.channels.length===0){
    tbody.innerHTML='<tr><td colspan="5" class="empty">暂无通道</td></tr>';return
  }
  tbody.innerHTML=data.channels.map(c=>'<tr>'+
    '<td style="color:var(--text-muted)">'+c.id+'</td>'+
    '<td>'+esc(c.name)+'</td>'+
    '<td><span class="tag" style="background:rgba(99,102,241,0.1);color:#818cf8;border-color:rgba(99,102,241,0.2)">📨 '+c.channel_type+'</span></td>'+
    '<td>'+(c.enabled?'<span class="tag tag-active">● 启用</span>':'<span class="tag tag-inactive">○ 停用</span>')+'</td>'+
    '<td><div class="action-cell"><button class="btn btn-primary btn-small" onclick="editChannel('+c.id+')">编辑</button>'+
    '<button class="btn btn-danger btn-small" onclick="deleteChannel('+c.id+')">删除</button></div></td>'+
    '</tr>').join('');
}

function switchChannelType(){
  var t=document.getElementById('cf_type').value;
  document.getElementById('cfgTelegram').style.display=t==='telegram'?'block':'none';
  document.getElementById('cfgServerchan').style.display=t==='serverchan'?'block':'none';
  document.getElementById('cfgDingtalk').style.display=t==='dingtalk'?'block':'none';
}
function showChannelModal(data){
  editingChannelId=data?data.id:null;
  document.getElementById('channelModalTitle').textContent=data?'✏️ 编辑通道':'📢 添加通道';
  document.getElementById('cf_name').value=data?data.name:'';
  document.getElementById('cf_type').value=data?data.channel_type:'telegram';
  switchChannelType();
  var cfg=data?data.config:{};
  document.getElementById('cf_bot_token').value=cfg.bot_token||'';
  document.getElementById('cf_chat_id').value=cfg.chat_id||'';
  document.getElementById('cf_send_key').value=cfg.send_key||'';
  document.getElementById('cf_webhook_url').value=cfg.webhook_url||'';
  document.getElementById('cf_active_group').style.display=data?'flex':'none';
  if(data)document.getElementById('cf_active').checked=data.enabled;
  document.getElementById('channelModalMsg').className='msg';
  document.getElementById('channelModal').classList.add('active');
}
async function editChannel(id){
  const res=await fetch('/api/channels');
  const data=await res.json();
  const c=(data.channels||[]).find(x=>x.id===id);
  if(c)showChannelModal(c);
}
function getChannelConfig(){
  var t=document.getElementById('cf_type').value;
  if(t==='telegram') return {bot_token:document.getElementById('cf_bot_token').value.trim(),chat_id:document.getElementById('cf_chat_id').value.trim()};
  if(t==='serverchan') return {send_key:document.getElementById('cf_send_key').value.trim()};
  if(t==='dingtalk') return {webhook_url:document.getElementById('cf_webhook_url').value.trim()};
  return {};
}
async function saveChannel(){
  const el=document.getElementById('channelModalMsg');
  const name=document.getElementById('cf_name').value.trim();
  if(!name){msg(el,'名称不能为空','error');return}
  const body={
    name:name,
    channel_type:document.getElementById('cf_type').value,
    config:getChannelConfig(),
    enabled:document.getElementById('cf_active')?document.getElementById('cf_active').checked:true,
  };
  try{
    const url=editingChannelId?'/api/channels/'+editingChannelId:'/api/channels';
    const method=editingChannelId?'PUT':'POST';
    const res=await fetch(url,{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const data=await res.json();
    if(data.success){closeModal('channelModal');loadChannels();showGMsg('通道已保存')}
    else msg(el,data.error||'失败','error');
  }catch(e){msg(el,'网络错误','error')}
}
async function deleteChannel(id){
  if(!confirm('确认删除通道 #'+id+'？'))return;
  const res=await fetch('/api/channels/'+id,{method:'DELETE'});
  const data=await res.json();
  if(data.success){loadChannels();showGMsg('通道已删除')}
  else alert('删除失败: '+(data.error||''));
}
async function testChannel(){
  const el=document.getElementById('channelModalMsg');
  const body={
    name:document.getElementById('cf_name').value.trim()||'测试',
    channel_type:document.getElementById('cf_type').value,
    config:getChannelConfig(),
  };
  try{
    const res=await fetch('/api/channels/test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const data=await res.json();
    if(data.success)msg(el,'测试消息发送成功！','success');
    else msg(el,data.error||'失败','error');
  }catch(e){msg(el,'网络错误','error')}
}
function showGMsg(text){
  const el=document.getElementById('globalMsg');
  el.className='g-success show';el.innerHTML='<span>'+text+'</span>';
  setTimeout(()=>{el.className=''},3000);
}

loadTasks();loadChannels();
</script>
</body>
</html>
"""

# ── Routes ──────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        pw = request.form.get("password", "")
        if pw == database.get_admin_password():
            session["logged_in"] = True
            return redirect("/")
        return render_template_string(
            LOGIN_HTML.replace("{{msg}}", "密码错误，请重试")
        )
    return render_template_string(LOGIN_HTML.replace("{{msg}}", ""))


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/")
@require_auth
def index():
    return render_template_string(DASHBOARD_HTML)


@app.route("/admin")
@require_auth
def admin():
    return render_template_string(ADMIN_HTML)


# ── API: Tasks ──────────────────────────────────────────────────────────────

@app.route("/api/tasks", methods=["GET"])
@require_auth
def api_tasks_list():
    tasks = database.get_tasks()
    result = []
    for t in tasks:
        last = database.get_last_checkin(t["id"])
        can_checkin = database.can_checkin_task(t["id"]) if last else True
        remaining_days = None
        due_date = None
        next_remind = None
        if last:
            lt = datetime.datetime.fromisoformat(last["checkin_time"])
            due = lt + datetime.timedelta(days=t["checkin_days"])
            due_date = due.isoformat()
            remaining = (due - datetime.datetime.now()).total_seconds()
            remaining_days = int(remaining // 86400)
            if remaining > 0:
                rd = remaining_days
                for d in t["reminder_days"]:
                    if rd <= d:
                        rt = due - datetime.timedelta(days=d)
                        if rt > datetime.datetime.now():
                            next_remind = rt.isoformat()
                        break
                if not next_remind:
                    next_remind = due.isoformat()
        result.append({
            **t,
            "can_checkin": can_checkin,
            "last_checkin": last["checkin_time"] if last else None,
            "remaining_days": remaining_days,
            "due_date": due_date,
            "next_remind": next_remind,
        })
    return jsonify({"success": True, "tasks": result})


@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
@require_auth
def api_task_update(task_id):
    data = request.get_json(force=True)
    if not data:
        return jsonify({"success": False, "error": "无效数据"}), 400
    task = database.get_task(task_id)
    if not task:
        return jsonify({"success": False, "error": "任务不存在"}), 404
    name = data.get("name", task["name"])
    description = data.get("description", task["description"])
    url = data.get("url", task.get("url", ""))
    checkin_days = data.get("checkin_days", task["checkin_days"])
    reminder_days = data.get("reminder_days", task["reminder_days"])
    active = data.get("active", task["active"])
    advance_msg_template = data.get("advance_msg_template", task.get("advance_msg_template", ""))
    final_msg_template = data.get("final_msg_template", task.get("final_msg_template", ""))
    try:
        checkin_days = int(checkin_days)
        if checkin_days < 1:
            raise ValueError
        reminder_days = [int(d) for d in reminder_days]
        if any(d < 1 for d in reminder_days):
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "参数无效"}), 400
    database.update_task(task_id, name, description, checkin_days, reminder_days, active,
                         advance_msg_template, final_msg_template, url)
    return jsonify({"success": True})


@app.route("/api/tasks", methods=["POST"])
@require_auth
def api_task_create():
    data = request.get_json(force=True)
    if not data or not data.get("name", "").strip():
        return jsonify({"success": False, "error": "任务名称不能为空"}), 400
    try:
        checkin_days = int(data.get("checkin_days", 7))
        if checkin_days < 1:
            raise ValueError
        reminder_days = data.get("reminder_days", [3, 1])
        if isinstance(reminder_days, str):
            reminder_days = [int(x) for x in reminder_days.split(",") if x.strip()]
        reminder_days = [int(d) for d in reminder_days]
        if any(d < 1 for d in reminder_days):
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "参数无效"}), 400
    advance_msg_template = data.get("advance_msg_template", "")
    final_msg_template = data.get("final_msg_template", "")
    task_url = data.get("url", "")
    tid = database.add_task(data["name"].strip(), data.get("description", "").strip(),
                            checkin_days, reminder_days,
                            advance_msg_template, final_msg_template, task_url)
    return jsonify({"success": True, "task_id": tid})


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
@require_auth
def api_task_delete(task_id):
    task = database.get_task(task_id)
    if not task:
        return jsonify({"success": False, "error": "任务不存在"}), 404
    database.delete_task(task_id)
    return jsonify({"success": True})


@app.route("/api/tasks/<int:task_id>/checkin", methods=["POST"])
@require_auth
def api_task_checkin(task_id):
    task = database.get_task(task_id)
    if not task:
        return jsonify({"success": False, "error": "任务不存在"}), 404
    data = request.get_json(force=True, silent=True)
    note = (data or {}).get("note", "")
    cid = database.add_checkin(task_id, note=note)
    if cid == 0:
        return jsonify({"success": False, "error": "24小时内只能签到一次"}), 400

    # 签到成功后，向所有启用的通知频道推送提醒
    _send_checkin_notification(task)

    return jsonify({"success": True, "checkin_id": cid})


def _send_checkin_notification(task):
    """签到成功后推送通知到所有启用的频道"""
    channels = [c for c in database.get_channels() if c["enabled"]]
    logger.info("通知频道数量: %d", len(channels))
    if not channels:
        logger.warning("没有启用的通知频道")
        return

    text = (
        f"✅ 签到成功！\n\n"
        f"任务：{task['name']}\n"
        f"周期：{task['checkin_days']} 天\n"
        f"时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"下次签到：{task['checkin_days']} 天后"
    )

    for ch in channels:
        ctype = ch["channel_type"]
        cfg = ch["config"]
        logger.info("发送通知到频道: %s(类型=%s)", ch.get("name"), ctype)
        ok = False
        if ctype == "telegram":
            bot_token = cfg.get("bot_token", "")
            chat_id = cfg.get("chat_id", "")
            if not bot_token or not chat_id:
                logger.warning("Telegram 配置不完整")
                continue
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            try:
                resp = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
                resp.raise_for_status()
                ok = True
            except Exception as e:
                logger.error("Telegram 发送失败: %s", e)
        elif ctype == "serverchan":
            send_key = cfg.get("send_key", "")
            if not send_key:
                logger.warning("ServerChan 配置不完整")
                continue
            title = text.split("\n\n", 1)[0] if "\n\n" in text else text[:50]
            try:
                resp = requests.post(f"https://sctapi.ftqq.com/{send_key}.send", data={"title": title, "desp": text}, timeout=10)
                resp.raise_for_status()
                if resp.json().get("code") == 0:
                    ok = True
            except Exception as e:
                logger.error("ServerChan 发送失败: %s", e)
        elif ctype == "dingtalk":
            webhook_url = cfg.get("webhook_url", "")
            if not webhook_url:
                logger.warning("DingTalk 配置不完整")
                continue
            try:
                resp = requests.post(webhook_url, json={"msgtype": "text", "text": {"content": text}}, timeout=10)
                resp.raise_for_status()
                if resp.json().get("errcode") == 0:
                    ok = True
            except Exception as e:
                logger.error("DingTalk 发送失败: %s", e)
        if ok:
            logger.info("通知发送成功")


@app.route("/api/tasks/<int:task_id>/history", methods=["GET"])
@require_auth
def api_task_history(task_id):
    history = database.get_all_checkins(task_id)
    return jsonify({"success": True, "history": history})


# ── API: Channels ───────────────────────────────────────────────────────────

@app.route("/api/channels", methods=["GET"])
@require_auth
def api_channels_list():
    channels = database.get_channels()
    return jsonify({"success": True, "channels": channels})


@app.route("/api/channels", methods=["POST"])
@require_auth
def api_channel_create():
    data = request.get_json(force=True)
    if not data or not data.get("name", "").strip():
        return jsonify({"success": False, "error": "名称不能为空"}), 400
    ctype = data.get("channel_type", "telegram")
    cfg = data.get("config", {})
    cid = database.add_channel(data["name"].strip(), ctype, cfg)
    return jsonify({"success": True, "channel_id": cid})


@app.route("/api/channels/<int:channel_id>", methods=["PUT"])
@require_auth
def api_channel_update(channel_id):
    data = request.get_json(force=True)
    if not data:
        return jsonify({"success": False, "error": "无效数据"}), 400
    ch = database.get_channel(channel_id)
    if not ch:
        return jsonify({"success": False, "error": "通道不存在"}), 404
    name = data.get("name", ch["name"])
    ctype = data.get("channel_type", ch["channel_type"])
    cfg = data.get("config", ch["config"])
    enabled = data.get("enabled", ch["enabled"])
    database.update_channel(channel_id, name, ctype, cfg, enabled)
    return jsonify({"success": True})


@app.route("/api/channels/<int:channel_id>", methods=["DELETE"])
@require_auth
def api_channel_delete(channel_id):
    ch = database.get_channel(channel_id)
    if not ch:
        return jsonify({"success": False, "error": "通道不存在"}), 404
    database.delete_channel(channel_id)
    return jsonify({"success": True})


@app.route("/api/channels/test", methods=["POST"])
@require_auth
def api_channel_test():
    data = request.get_json(force=True)
    if not data:
        return jsonify({"success": False, "error": "无效数据"}), 400
    ctype = data.get("channel_type", "telegram")
    cfg = data.get("config", {})
    text = "🧪 这是一条测试消息，通知通道配置成功！"
    try:
        if ctype == "telegram":
            bot_token = cfg.get("bot_token", "")
            chat_id = cfg.get("chat_id", "")
            if not bot_token or not chat_id:
                return jsonify({"success": False, "error": "Bot Token 和 Chat ID 不能为空"}), 400
            resp = requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage",
                                json={"chat_id": chat_id, "text": text}, timeout=10)
            resp.raise_for_status()
        elif ctype == "serverchan":
            send_key = cfg.get("send_key", "")
            if not send_key:
                return jsonify({"success": False, "error": "SendKey 不能为空"}), 400
            resp = requests.post(f"https://sctapi.ftqq.com/{send_key}.send",
                                data={"title": "签到提醒系统测试", "desp": text}, timeout=10)
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 0:
                return jsonify({"success": False, "error": result.get("message", "发送失败")}), 400
        elif ctype == "dingtalk":
            webhook_url = cfg.get("webhook_url", "")
            if not webhook_url:
                return jsonify({"success": False, "error": "Webhook URL 不能为空"}), 400
            resp = requests.post(webhook_url, json={"msgtype": "text", "text": {"content": text}}, timeout=10)
            resp.raise_for_status()
            result = resp.json()
            if result.get("errcode") != 0:
                return jsonify({"success": False, "error": result.get("errmsg", "发送失败")}), 400
        else:
            return jsonify({"success": False, "error": "不支持的通道类型"}), 400
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)[:200]}), 400


# ── API: Reset Password ──────────────────────────────────────────────────────

# 临时存储已验证的 session（用于重置密码流程中验证答案后保持状态）
import uuid as _uuid
import time as _time
_reset_tokens: dict[str, float] = {}  # token -> creation_timestamp

# 15 分钟 TTL
_RESET_TOKEN_TTL = 15 * 60


def _cleanup_reset_tokens():
    now = _time.time()
    expired = [
        t for t, ts in _reset_tokens.items()
        if now - ts > _RESET_TOKEN_TTL
    ]
    for t in expired:
        del _reset_tokens[t]


@app.route("/api/reset-password/question", methods=["GET"])
def api_reset_question():
    q = database.get_setting("security_question")
    if q:
        return jsonify({"success": True, "has_question": True, "question": q})
    return jsonify({"success": True, "has_question": False})


@app.route("/api/reset-password/check", methods=["POST"])
def api_reset_check():
    data = request.get_json(force=True)
    if not data:
        return jsonify({"success": False, "error": "无效数据"}), 400
    answer = data.get("answer", "").strip().lower()
    stored = (database.get_setting("security_answer") or "").lower()
    if not stored:
        return jsonify({"success": False, "error": "未设置密保问题"}), 400
    if answer != stored:
        return jsonify({"success": False, "error": "答案错误"}), 400
    _cleanup_reset_tokens()
    token = str(_uuid.uuid4())
    _reset_tokens[token] = _time.time()
    return jsonify({"success": True, "token": token})


@app.route("/api/reset-password/reset", methods=["POST"])
def api_reset_reset():
    data = request.get_json(force=True)
    if not data:
        return jsonify({"success": False, "error": "无效数据"}), 400
    _cleanup_reset_tokens()
    token = data.get("token", "")
    if token not in _reset_tokens:
        return jsonify({"success": False, "error": "请先验证密保问题"}), 403
    new_password = data.get("password", "").strip()
    if not new_password or len(new_password) < 6:
        return jsonify({"success": False, "error": "密码长度不能少于6位"}), 400
    database.set_setting("admin_password", new_password)
    app.secret_key = hashlib.sha256(new_password.encode()).hexdigest()
    _reset_tokens.pop(token, None)
    return jsonify({"success": True, "message": "密码已重置"})


@app.route("/api/settings", methods=["GET", "PUT"])
@require_auth
def api_settings():
    if request.method == "GET":
        return jsonify({
            "success": True,
            "has_password": bool(database.get_admin_password()),
        })
    # PUT: 修改密码
    data = request.get_json(force=True)
    if not data:
        return jsonify({"success": False, "error": "无效数据"}), 400
    new_password = data.get("password", "").strip()
    if not new_password:
        return jsonify({"success": False, "error": "密码不能为空"}), 400
    if len(new_password) < 6:
        return jsonify({"success": False, "error": "密码长度不能少于6位"}), 400
    database.set_setting("admin_password", new_password)
    # 更新 secret_key，使现有 session 失效（安全起见要求重新登录）
    app.secret_key = hashlib.sha256(new_password.encode()).hexdigest()
    return jsonify({"success": True, "message": "密码已修改，请重新登录"})


@app.route("/api/settings/security", methods=["GET", "PUT"])
@require_auth
def api_settings_security():
    if request.method == "GET":
        q = database.get_setting("security_question") or ""
        return jsonify({"success": True, "question": q})
    data = request.get_json(force=True)
    if not data:
        return jsonify({"success": False, "error": "无效数据"}), 400
    question = data.get("question", "").strip()
    answer = data.get("answer", "").strip()
    if not question or not answer:
        return jsonify({"success": False, "error": "问题和答案不能为空"}), 400
    database.set_setting("security_question", question)
    database.set_setting("security_answer", answer)
    return jsonify({"success": True})


if __name__ == "__main__":
    database.init_db()
    database.init_settings()
    # 从数据库读取密码作为 secret_key
    app.secret_key = hashlib.sha256(
        database.get_admin_password().encode()
    ).hexdigest()
    app.run(host="0.0.0.0", port=8080, debug=False)
