import telebot
import requests
from telebot import types
import re

# =========================================
# BOT TOKEN
# =========================================
BOT_TOKEN = "8710999964:AAHV_3swM28F3FDEdL4ERQEfcI-sDGUBY6I"
bot = telebot.TeleBot(BOT_TOKEN)

# =========================================
# SESSION STORE
# =========================================
sessions = {}

# =========================================
# GET ACCESS TOKEN
# =========================================
def get_access_token(refresh_token, client_id):

    url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"

    data = {
        "client_id": client_id,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "scope": "offline_access Mail.Read"
    }

    try:
        r = requests.post(url, data=data, timeout=20)

        if r.status_code == 200:
            return r.json().get("access_token")

        return None

    except:
        return None


# =========================================
# GET MAILS
# =========================================
def get_recent_mails(access_token):

    url = "https://graph.microsoft.com/v1.0/me/messages?$top=5&$orderby=receivedDateTime desc"

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    try:
        r = requests.get(url, headers=headers, timeout=20)

        if r.status_code == 200:
            return r.json().get("value", [])

        return []

    except:
        return []


# =========================================
# BUILD OUTPUT (OTP MONOSPACE)
# =========================================
def build_output(email, mails):

    output = f"📧 EMAIL: {email}\n\n"

    for i, mail in enumerate(mails, start=1):

        subject = mail.get("subject", "No Subject")

        sender = "Unknown"
        try:
            sender = mail["from"]["emailAddress"]["address"]
        except:
            pass

        received = mail.get("receivedDateTime", "Unknown")

        # OTP extract (4–8 digits)
        otp_match = re.findall(r"\b\d{4,8}\b", subject)
        otp = otp_match[0] if otp_match else None

        output += (
            f"━━━━━━━━━━━━━━\n"
            f"[{i}] SUBJECT: {subject}\n"
            f"FROM: {sender}\n"
            f"TIME: {received}\n"
        )

        # 🔥 MONOSPACE OTP (click to copy)
        if otp:
            output += f"🔐 OTP: <code>{otp}</code>\n"

        output += "\n"

    return output[:4000]


# =========================================
# START COMMAND
# =========================================
@bot.message_handler(commands=["start"])
def start(message):

    bot.reply_to(
        message,
        "Send account in this format:\n\nemail|pass|refresh_token|client_id"
    )


# =========================================
# HANDLE ACCOUNT
# =========================================
@bot.message_handler(func=lambda m: True)
def check_account(message):

    try:
        email, password, refresh_token, client_id = message.text.strip().split("|", 3)

    except:
        bot.reply_to(
            message,
            "Wrong format!\n\nUse:\nemail|pass|refresh_token|client_id"
        )
        return

    msg = bot.reply_to(message, f"Checking {email}...")

    access_token = get_access_token(refresh_token, client_id)

    if not access_token:
        bot.edit_message_text(
            "Token Failed!",
            chat_id=message.chat.id,
            message_id=msg.message_id
        )
        return

    mails = get_recent_mails(access_token)

    if not mails:
        bot.edit_message_text(
            "No mails found!",
            chat_id=message.chat.id,
            message_id=msg.message_id
        )
        return

    output = build_output(email, mails)

    # save session
    sessions[msg.message_id] = {
        "email": email,
        "refresh_token": refresh_token,
        "client_id": client_id
    }

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh:{msg.message_id}")
    )

    bot.edit_message_text(
        output,
        chat_id=message.chat.id,
        message_id=msg.message_id,
        reply_markup=markup,
        parse_mode="HTML"
    )


# =========================================
# REFRESH HANDLER
# =========================================
@bot.callback_query_handler(func=lambda call: call.data.startswith("refresh:"))
def refresh_mails(call):

    msg_id = int(call.data.split(":")[1])

    session = sessions.get(msg_id)

    if not session:
        bot.answer_callback_query(call.id, "Session expired!")
        return

    bot.answer_callback_query(call.id, "Refreshing...")

    access_token = get_access_token(session["refresh_token"], session["client_id"])

    if not access_token:
        bot.edit_message_text(
            "Token refresh failed!",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        return

    mails = get_recent_mails(access_token)

    output = build_output(session["email"], mails)

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh:{msg_id}")
    )

    bot.edit_message_text(
        output,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup,
        parse_mode="HTML"
    )


# =========================================
# RUN BOT
# =========================================
print("BOT RUNNING...")
bot.infinity_polling()
