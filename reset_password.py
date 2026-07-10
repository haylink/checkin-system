#!/usr/bin/env python3
"""
密码重置工具
用法: python3 reset_password.py <新密码>

示例: python3 reset_password.py admin123
"""

import sys
import os

# 确保在项目目录下运行
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 临时设置环境变量让 config.py 能加载
os.environ.setdefault("ADMIN_PASSWORD", "dummy_for_init")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "dummy_bot_token")
os.environ.setdefault("TELEGRAM_CHAT_ID", "1")

import database


def main():
    if len(sys.argv) < 2:
        print("❌ 用法: python3 reset_password.py <新密码>")
        print("   示例: python3 reset_password.py admin123")
        sys.exit(1)

    new_password = sys.argv[1].strip()
    if len(new_password) < 6:
        print("❌ 密码长度不能少于6位")
        sys.exit(1)
    if not new_password:
        print("❌ 密码不能为空")
        sys.exit(1)

    database.init_db()
    database.init_settings()
    database.set_setting("admin_password", new_password)
    print(f"✅ 密码已重置为: {new_password}")
    print("   请使用新密码登录")


if __name__ == "__main__":
    main()