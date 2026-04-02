# telebot_subscription_bot.py — Fixed version
import json
import logging
import time
import threading
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, BotCommandScopeDefault, BotCommandScopeChat

# ===== CONFIGURATION =====
TOKEN            = "8708911994:AAHwOV2uj3yclWV0KpkeZVUvCyNMF-Rj0uI"
COURSE_LINK      = "https://canva.link/lsnlj5vu4d7snnz"
# 🔁 IMPORTANT: Replace with your actual channel ID (negative number)
CHANNEL_ID       = -1002427472384   # <-- CHANGE THIS
CHANNEL_INVITE   = "https://t.me/EasyCs_Official"
ADMIN_ID         = 7020797610
SUBSCRIBERS_FILE = "subscribers.json"
BANNED_FILE      = "banned.json"
API_URL          = f"https://api.telegram.org/bot{TOKEN}"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
bot = telebot.TeleBot(TOKEN, parse_mode="HTML", threaded=True)

# ===== DIRECT API HELPER =====
def tg_api(method: str, payload: dict = None) -> dict:
    try:
        resp = requests.post(f"{API_URL}/{method}", json=payload or {}, timeout=15)
        return resp.json()
    except Exception as e:
        logger.error("tg_api error: %s", e)
        return {"ok": False, "description": str(e)}

# ===== JSON STORAGE =====
def _load_json_file(path, default):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def _save_json_file(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def load_subscribers():
    return _load_json_file(SUBSCRIBERS_FILE, {"subscribers": []})

def save_subscribers(data):
    _save_json_file(SUBSCRIBERS_FILE, data)

def add_user_to_json(user_id):
    data = load_subscribers()
    if user_id not in data["subscribers"]:
        data["subscribers"].append(user_id)
        save_subscribers(data)
        return True
    return False

def get_subscriber_count():
    return len(load_subscribers()["subscribers"])

def get_all_subscribers():
    return load_subscribers()["subscribers"]

def load_banned():
    return _load_json_file(BANNED_FILE, {"banned": []})

def save_banned(data):
    _save_json_file(BANNED_FILE, data)

def ban_user(user_id):
    data = load_banned()
    if user_id not in data["banned"]:
        data["banned"].append(user_id)
        save_banned(data)
        return True
    return False

def unban_user(user_id):
    data = load_banned()
    if user_id in data["banned"]:
        data["banned"].remove(user_id)
        save_banned(data)
        return True
    return False

def is_banned(user_id):
    return user_id in load_banned()["banned"]

# ===== RATE LIMITING =====
_last_check = {}
RATE_LIMIT_SECONDS = 5

def is_rate_limited(user_id):
    now = time.time()
    if now - _last_check.get(user_id, 0) < RATE_LIMIT_SECONDS:
        return True
    _last_check[user_id] = now
    return False

# ===== SUBSCRIPTION CHECK (FIXED: uses CHANNEL_ID) =====
def is_subscribed(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ("member", "administrator", "creator")
    except telebot.apihelper.ApiTelegramException as e:
        if "chat not found" in str(e):
            logger.error("Bot not in channel or CHANNEL_ID is wrong. Join the channel and set correct numeric ID.")
        else:
            logger.warning("Subscription check failed for %s: %s", user_id, e)
        return False
    except Exception as e:
        logger.error("Unexpected error in is_subscribed: %s", e)
        return False

# ===== KEYBOARDS =====
def subscribe_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("📢 Join Channel", url=CHANNEL_INVITE),
        InlineKeyboardButton("✅ Check Subscription", callback_data="check_sub"),
    )
    return kb

def already_subscribed_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📘 Open Course", url=COURSE_LINK))
    return kb

def send_course(chat_id, greeting="🎉"):
    bot.send_message(
        chat_id,
        f"{greeting} <b>Here is your Algebra course link:</b>\n\n👉 <a href='{COURSE_LINK}'>Click to open the course</a>",
        reply_markup=already_subscribed_keyboard(),
        disable_web_page_preview=False,
    )

def send_subscribe_prompt(chat_id):
    bot.send_message(
        chat_id,
        "👋 <b>Welcome!</b>\n\nTo receive the free Algebra course you must subscribe to our channel first.\n\n"
        "1️⃣ Click <b>Join Channel</b> below.\n2️⃣ Come back and click <b>Check Subscription</b>.",
        reply_markup=subscribe_keyboard(),
    )

def admin_only(message):
    if ADMIN_ID and message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⛔ Admin only.")
        return False
    return True

def ban_guard(message):
    if is_banned(message.from_user.id):
        bot.send_message(message.chat.id, "🚫 You have been banned.")
        return False
    return True

# ===== COMMANDS =====
@bot.message_handler(commands=["start", "course"])
def cmd_start(message):
    if not ban_guard(message): return
    user_id = message.from_user.id
    if is_subscribed(user_id):
        add_user_to_json(user_id)
        send_course(message.chat.id, greeting="🎉 Welcome back!")
    else:
        send_subscribe_prompt(message.chat.id)

@bot.message_handler(commands=["help"])
def cmd_help(message):
    if not ban_guard(message): return
    bot.send_message(message.chat.id, "ℹ️ <b>Bot Commands</b>\n\n/start — Get your course link\n/course — Same as /start\n/help — Show this message")

@bot.message_handler(commands=["status"])
def cmd_status(message):
    if not admin_only(message): return
    me = bot.get_me()
    bot.send_message(message.chat.id, f"🤖 <b>Bot Status</b>\n\nName: @{me.username}\nBot ID: <code>{me.id}</code>\nChannel ID: <code>{CHANNEL_ID}</code>\nSubscribers: {get_subscriber_count()}\nBanned: {len(load_banned()['banned'])}")

@bot.message_handler(commands=["ban"])
def cmd_ban(message):
    if not admin_only(message): return
    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(message.chat.id, "Usage: /ban <user_id>")
        return
    try:
        target = int(parts[1])
        if target == ADMIN_ID:
            bot.send_message(message.chat.id, "❌ Cannot ban yourself.")
            return
        if ban_user(target):
            bot.send_message(message.chat.id, f"✅ Banned <code>{target}</code>")
        else:
            bot.send_message(message.chat.id, f"ℹ️ Already banned")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid ID.")

@bot.message_handler(commands=["unban"])
def cmd_unban(message):
    if not admin_only(message): return
    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(message.chat.id, "Usage: /unban <user_id>")
        return
    try:
        target = int(parts[1])
        if unban_user(target):
            bot.send_message(message.chat.id, f"✅ Unbanned <code>{target}</code>")
        else:
            bot.send_message(message.chat.id, f"ℹ️ Was not banned")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid ID.")

@bot.message_handler(commands=["broadcast"])
def cmd_broadcast(message):
    if not admin_only(message): return
    text = message.text.partition(" ")[2].strip()
    if not text:
        bot.send_message(message.chat.id, "Usage: /broadcast <message>")
        return
    subs = get_all_subscribers()
    if not subs:
        bot.send_message(message.chat.id, "No subscribers.")
        return
    bot.send_message(message.chat.id, f"Broadcasting to {len(subs)} users...")
    def task():
        sent = 0
        for uid in subs:
            try:
                bot.send_message(uid, f"📢 Announcement\n\n{text}")
                sent += 1
                time.sleep(0.05)
            except Exception as e:
                logger.warning(f"Broadcast fail {uid}: {e}")
        bot.send_message(message.chat.id, f"✅ Sent: {sent}\nFailed: {len(subs)-sent}")
    threading.Thread(target=task, daemon=True).start()

# ===== CALLBACK HANDLER (FIXED: immediate answer) =====
@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def callback_check_sub(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    # Answer immediately to avoid timeout
    try:
        bot.answer_callback_query(call.id, text="⏳ Checking...", show_alert=False)
    except Exception as e:
        logger.warning(f"Callback answer failed (already expired): {e}")

    if is_banned(user_id):
        bot.send_message(chat_id, "🚫 You are banned.")
        return

    if is_rate_limited(user_id):
        bot.send_message(chat_id, f"⏳ Please wait {RATE_LIMIT_SECONDS}s before checking again.")
        return

    if is_subscribed(user_id):
        add_user_to_json(user_id)
        send_course(chat_id, greeting="🎉 Subscription confirmed!")
    else:
        bot.send_message(chat_id, "❌ Not subscribed yet. Please join the channel and try again.", reply_markup=subscribe_keyboard())

@bot.message_handler(func=lambda m: True)
def fallback(message):
    if not ban_guard(message): return
    bot.send_message(message.chat.id, "🤖 Use /start to get your course link.")

# ===== STARTUP =====
def setup_bot():
    tg_api("deleteWebhook", {"drop_pending_updates": True})
    bot.set_my_commands([
        BotCommand("start", "Get course link"),
        BotCommand("help", "Help"),
    ], scope=BotCommandScopeDefault())
    if ADMIN_ID:
        bot.set_my_commands([
            BotCommand("start", "Get course link"),
            BotCommand("status", "Bot stats"),
            BotCommand("broadcast", "Send broadcast"),
            BotCommand("ban", "Ban user"),
            BotCommand("unban", "Unban user"),
        ], scope=BotCommandScopeChat(ADMIN_ID))
    logger.info("Bot ready")

if __name__ == "__main__":
    setup_bot()
    logger.info("Starting polling...")
    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=30)
        except Exception as e:
            logger.error(f"Polling error: {e} — restarting in 10s")
            time.sleep(10)