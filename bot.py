#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import telebot, instaloader, time, os, pyotp, threading, sys
from telebot import types, apihelper
from concurrent.futures import ThreadPoolExecutor

apihelper.ENABLE_MIDDLEWARE = True

# ================= TOKEN =================
def get_bot_token():
    if len(sys.argv) > 1:
        return sys.argv[1]
    else:
        print("🔐 Enter your bot token:")
        token = input("➜ ").strip()
        if not token:
            print("❌ Token is required!")
            sys.exit(1)
        return token

BOT_TOKEN = os.getenv("8710999964:AAEVHzSVrkpljKqCE-XHOk_Sa__Xk8idx2k")

# ================= BOT =================
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

UA = 'Mozilla/5.0'
user_sessions = {}

# ================= BUTTON =================
def get_start_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🚀 START"))
    return markup

def get_cancel_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("❌ CANCEL"))
    return markup

# ================= LOGIN =================
def login_worker(chat_id, u, p, k):
    if chat_id not in user_sessions:
        return

    L = instaloader.Instaloader(quiet=True, max_connection_attempts=1)
    L.context._session.headers.update({'User-Agent': UA})

    try:
        L.login(u, p)
        save_success(chat_id, L, u, p)
    except:
        try:
            totp = pyotp.TOTP(k.replace(" ", ""))
            L.two_factor_login(totp.now())
            save_success(chat_id, L, u, p)
        except:
            if chat_id in user_sessions:
                user_sessions[chat_id]['failed'] += 1
                bot.send_message(chat_id, f"❌ *FAILED:* `{u}`")

def save_success(chat_id, L, u, p):
    if chat_id in user_sessions:
        cookies = L.context._session.cookies.get_dict()
        ck_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])

        user_sessions[chat_id]['results'].append(f"{u}|{p}|{ck_str}")
        user_sessions[chat_id]['success'] += 1

        bot.send_message(chat_id, f"✅ *SUCCESS:* `{u}`")

# ================= HANDLERS =================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    text = """
🔥 *MãF! COOKIES BOT*

━━━━━━━━━━━━━━━
🚀 Fast Extract System
🔐 Secure Login Engine
━━━━━━━━━━━━━━━

Click START to begin 👇
"""
    bot.send_message(message.chat.id, text, reply_markup=get_start_markup())

@bot.message_handler(func=lambda m: m.text == "❌ CANCEL")
def cancel_work(message):
    chat_id = message.chat.id

    user_sessions.pop(chat_id, None)
    bot.clear_step_handler_by_chat_id(chat_id)

    bot.send_message(
        chat_id,
        "🚫 *Process Cancelled!*",
        reply_markup=get_start_markup()
    )

@bot.message_handler(func=lambda m: m.text == "🚀 START")
def step1(message):
    msg = bot.send_message(
        message.chat.id,
        "📥 *Send usernames (line by line):*",
        reply_markup=get_cancel_markup()
    )
    bot.register_next_step_handler(msg, step2)

def step2(message):
    if message.text == "❌ CANCEL":
        cancel_work(message)
        return

    chat_id = message.chat.id
    usernames = [u.strip() for u in message.text.splitlines() if u.strip()]

    user_sessions[chat_id] = {
        'u_list': usernames,
        'results': [],
        'success': 0,
        'failed': 0
    }

    msg = bot.send_message(
        chat_id,
        "🔑 *Enter password:*",
        reply_markup=get_cancel_markup()
    )
    bot.register_next_step_handler(msg, step3)

def step3(message):
    if message.text == "❌ CANCEL":
        cancel_work(message)
        return

    chat_id = message.chat.id
    user_sessions[chat_id]['common_pass'] = message.text.strip()

    msg = bot.send_message(
        chat_id,
        "🔐 *Send 2FA keys (line by line):*",
        reply_markup=get_cancel_markup()
    )
    bot.register_next_step_handler(msg, final_step)

def final_step(message):
    if message.text == "❌ CANCEL":
        cancel_work(message)
        return

    chat_id = message.chat.id

    keys = [k.strip() for k in message.text.splitlines() if k.strip()]
    u_list = user_sessions[chat_id]['u_list']
    p = user_sessions[chat_id]['common_pass']

    if len(u_list) != len(keys):
        bot.send_message(chat_id, "❌ *Mismatch in usernames & keys!*")
        return

    bot.send_message(chat_id, f"⚡ *Processing {len(u_list)} accounts...*")

    executor = ThreadPoolExecutor(max_workers=100)

    for i in range(len(u_list)):
        executor.submit(login_worker, chat_id, u_list[i], p, keys[i])

    def finalize():
        executor.shutdown(wait=True)

        if chat_id not in user_sessions:
            return

        data = user_sessions[chat_id]
        success_count = data['success']
        failed_count = data['failed']
        total = len(data['u_list'])

        summary = f"""
📊 *RESULT SUMMARY*

━━━━━━━━━━━━━━━
✅ SUCCESS : `{success_count}`
❌ FAILED  : `{failed_count}`
📦 TOTAL   : `{total}`
━━━━━━━━━━━━━━━
"""
        bot.send_message(chat_id, summary, reply_markup=get_start_markup())

        if data['results']:
            fname = f"result_{chat_id}.txt"

            with open(fname, "w") as f:
                f.write("\n".join(data['results']))

            with open(fname, "rb") as d:
                bot.send_document(chat_id, d)

            os.remove(fname)

    threading.Thread(target=finalize).start()

# ================= RUN =================
if __name__ == "__main__":
    print("🚀 Bot Running...")
    bot.infinity_polling()
