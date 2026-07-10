import datetime
import json
import logging
import sys

import requests

import config
import database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def send_telegram(bot_token, chat_id, text):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("Telegram message sent to %s", chat_id)
        return True
    except Exception as e:
        logger.error("Failed to send Telegram message to %s: %s", chat_id, e)
        return False


def send_serverchan(send_key, text):
    """Server酱 微信推送"""
    title = text.split("\n\n", 1)[0] if "\n\n" in text else text[:50]
    url = f"https://sctapi.ftqq.com/{send_key}.send"
    payload = {"title": title, "desp": text}
    try:
        resp = requests.post(url, data=payload, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") == 0:
            logger.info("ServerChan message sent")
            return True
        logger.error("ServerChan error: %s", result.get("message", "unknown"))
        return False
    except Exception as e:
        logger.error("Failed to send ServerChan message: %s", e)
        return False


def send_dingtalk(webhook_url, text):
    """钉钉机器人 Webhook 推送"""
    payload = {"msgtype": "text", "text": {"content": text}}
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        if result.get("errcode") == 0:
            logger.info("DingTalk message sent")
            return True
        logger.error("DingTalk error: %s", result.get("errmsg", "unknown"))
        return False
    except Exception as e:
        logger.error("Failed to send DingTalk message: %s", e)
        return False


def send_notification(channel, text):
    ctype = channel["channel_type"]
    cfg = channel["config"]
    if ctype == "telegram":
        return send_telegram(cfg.get("bot_token", ""), cfg.get("chat_id", ""), text)
    elif ctype == "serverchan":
        return send_serverchan(cfg.get("send_key", ""), text)
    elif ctype == "dingtalk":
        return send_dingtalk(cfg.get("webhook_url", ""), text)
    else:
        logger.warning("Unknown channel type: %s", ctype)
        return False


def check_and_remind():
    tasks = database.get_tasks()
    channels = [c for c in database.get_channels() if c["enabled"]]

    if not channels:
        logger.warning("No enabled notification channels found")

    for task in tasks:
        if not task["active"]:
            continue

        last = database.get_last_checkin(task["id"])
        if not last:
            logger.info("Task '%s': no check-in, skipping", task["name"])
            continue

        checkin_time = datetime.datetime.fromisoformat(last["checkin_time"])
        now = datetime.datetime.now()
        due_date = checkin_time + datetime.timedelta(days=task["checkin_days"])
        remaining = (due_date - now).total_seconds()
        remaining_days = int(remaining // 86400)

        if remaining <= 0:
            reminder_type = "final"
            if not database.is_reminder_sent(task["id"], last["id"], reminder_type):
                overdue_days = abs(remaining_days)
                tpl = task.get("final_msg_template") or database.FINAL_TEMPLATE
                text = tpl.replace("{name}", task["name"])\
                          .replace("{cycle}", str(task["checkin_days"]))\
                          .replace("{remaining}", str(overdue_days))\
                          .replace("{due}", due_date.strftime("%Y-%m-%d"))\
                          .replace("{overdue}", str(overdue_days))
                for ch in channels:
                    send_notification(ch, text)
                database.mark_reminder_sent(task["id"], last["id"], reminder_type)
            else:
                logger.info("Task '%s': final reminder already sent", task["name"])
            continue

        for day in task["reminder_days"]:
            if remaining_days == day:
                reminder_type = f"advance_{day}"
                if not database.is_reminder_sent(task["id"], last["id"], reminder_type):
                    tpl = task.get("advance_msg_template") or database.ADVANCE_TEMPLATE
                    text = tpl.replace("{name}", task["name"])\
                              .replace("{cycle}", str(task["checkin_days"]))\
                              .replace("{remaining}", str(remaining_days))\
                              .replace("{due}", due_date.strftime("%Y-%m-%d"))
                    for ch in channels:
                        send_notification(ch, text)
                    database.mark_reminder_sent(task["id"], last["id"], reminder_type)
                else:
                    logger.info("Task '%s': reminder %s already sent", task["name"], reminder_type)
                break

        logger.info(
            "Task '%s': due=%s, remaining=%d days",
            task["name"], due_date.date(), remaining_days,
        )


if __name__ == "__main__":
    database.init_db()
    check_and_remind()
