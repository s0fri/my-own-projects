"""
bot.py — Main Telegram bot entry point
Handles: Flask webhook, user flows, multi-step states, contact system
"""

import os
import logging
import time
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

from flask import Flask, request
import telebot
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    BotCommand, BotCommandScopeDefault,
)

import database as db
from admin import register_admin_handlers, _do_broadcast

# ═══════════════════════════════════════════════════════════════════════════
#  CONFIGURATION  — fill in your values here
# ═══════════════════════════════════════════════════════════════════════════
TOKEN        = os.getenv("BOT_TOKEN",  "8708911994:AAHwOV2uj3yclWV0KpkeZVUvCyNMF-Rj0uI")
ADMIN_ID     = int(os.getenv("ADMIN_ID", "7020797610"))          # your Telegram user ID
CHANNEL_ID   = int(os.getenv("CHANNEL_ID", "-1002427472384"))        # negative number e.g. -1002427472384
CHANNEL_INVITE = os.getenv("CHANNEL_INVITE", "https://t.me/EasyCs_Official")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST",  "https://bot-qtnz.onrender.com")

# Email config (optional — leave blank to disable email forwarding)
SMTP_HOST    = os.getenv("SMTP_HOST",   "smtp.gmail.com")
SMTP_PORT    = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER    = os.getenv("SMTP_USER",   "")      # your Gmail address
SMTP_PASS    = os.getenv("SMTP_PASS",   "")      # app password
ADMIN_EMAIL  = os.getenv("ADMIN_EMAIL", "")      # where to forward messages
RATE_LIMIT_SECONDS = 5
# ═══════════════════════════════════════════════════════════════════════════

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(TOKEN, parse_mode="HTML", threaded=True)
app = Flask(__name__)

# Shared state  { user_id: {"state": "...", ...} }
user_states: dict = {}
_last_action: dict = {}


# ── Helpers ──────────────────────────────────────────────────────────────────
def rate_limited(user_id: int) -> bool:
    now = time.time()
    if now - _last_action.get(user_id, 0) < RATE_LIMIT_SECONDS:
        return True
    _last_action[user_id] = now
    return False


def is_subscribed(user_id: int) -> bool:
    if not CHANNEL_ID:
        return True
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ("member", "administrator", "creator")
    except telebot.apihelper.ApiTelegramException as e:
        if "chat not found" in str(e):
            logger.error("Bot not in channel or CHANNEL_ID is wrong.")
        else:
            logger.warning("Subscription check failed for %s: %s", user_id, e)
        return False
    except Exception as e:
        logger.error("Unexpected error in is_subscribed: %s", e)
        return False


def forward_to_email(from_user: str, from_id: int, text: str) -> bool:
    if not all([SMTP_USER, SMTP_PASS, ADMIN_EMAIL]):
        return False
    try:
        body = (
            f"New contact message from Telegram bot\n\n"
            f"From : @{from_user} (ID: {from_id})\n"
            f"Time : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"Message:\n{text}"
        )
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = f"[Bot Message] from @{from_user}"
        msg["From"]    = SMTP_USER
        msg["To"]      = ADMIN_EMAIL
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.sendmail(SMTP_USER, ADMIN_EMAIL, msg.as_string())
        return True
    except Exception as e:
        logger.error("Email forward failed: %s", e)
        return False


# ── Keyboards ────────────────────────────────────────────────────────────────
def main_menu_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📚 Courses", callback_data="menu_courses"),
        InlineKeyboardButton("👤 Profile", callback_data="menu_profile"),
        InlineKeyboardButton("📩 Contact", callback_data="menu_contact"),
        InlineKeyboardButton("ℹ️ Help",    callback_data="menu_help"),
    )
    return kb


def subscribe_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("📢 Join Channel",       url=CHANNEL_INVITE),
        InlineKeyboardButton("✅ Check Subscription", callback_data="check_sub"),
    )
    return kb


def courses_keyboard(courses: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    for c in courses:
        kb.add(InlineKeyboardButton(f"📖 {c['title']}", url=c["link"]))
    kb.add(InlineKeyboardButton("🔙 Back", callback_data="menu_back"))
    return kb


def contact_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("📨 Send me a message", callback_data="contact_send"),
        InlineKeyboardButton("🔙 Back",              callback_data="menu_back"),
    )
    return kb


def back_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 Main Menu", callback_data="menu_back"))
    return kb


# ── Guards ───────────────────────────────────────────────────────────────────
def ban_guard(message) -> bool:
    if db.is_banned(message.from_user.id):
        bot.send_message(message.chat.id, "🚫 You have been banned from this bot.")
        return False
    return True


# BUG FIX #3 — was: register_user(call.message) which passed the BOT's message
# object, registering the bot itself as a subscriber. Now takes a telebot User.
def register_user(user) -> None:
    """Register or update a subscriber. Pass message.from_user or call.from_user."""
    db.add_subscriber(
        user_id    = user.id,
        username   = user.username,
        first_name = user.first_name,
    )


# ── Welcome & menus ───────────────────────────────────────────────────────────
def send_main_menu(chat_id: int, name: str = "there") -> None:
    bot.send_message(
        chat_id,
        f"👋 <b>Hello, {name}!</b>\n\n"
        "Welcome to the <b>EasyCS Bot</b> 🎓\n\n"
        "Use the menu below to navigate:",
        reply_markup=main_menu_keyboard(),
    )


def send_subscribe_prompt(chat_id: int) -> None:
    bot.send_message(
        chat_id,
        "🔒 <b>Channel Required</b>\n\n"
        "To access courses you must subscribe to our channel first.\n\n"
        "1️⃣ Tap <b>Join Channel</b>\n"
        "2️⃣ Come back and tap <b>Check Subscription</b>",
        reply_markup=subscribe_keyboard(),
    )


# ── Commands ──────────────────────────────────────────────────────────────────
@bot.message_handler(commands=["start", "menu"])
def cmd_start(message):
    if not ban_guard(message): return
    register_user(message.from_user)          # fixed: pass from_user, not message
    name = message.from_user.first_name or "there"
    if not is_subscribed(message.from_user.id):
        send_subscribe_prompt(message.chat.id)
        return
    send_main_menu(message.chat.id, name)


@bot.message_handler(commands=["help"])
def cmd_help(message):
    if not ban_guard(message): return
    bot.send_message(
        message.chat.id,
        "ℹ️ <b>Help</b>\n\n"
        "/start — Show main menu\n"
        "/help  — This message\n\n"
        "Use the inline buttons to browse courses, view your profile, or contact us.",
    )


# ── Menu callbacks ────────────────────────────────────────────────────────────
@bot.callback_query_handler(func=lambda c: c.data.startswith("menu_") or c.data == "check_sub")
def menu_callbacks(call):
    uid  = call.from_user.id
    cid  = call.message.chat.id
    data = call.data

    if db.is_banned(uid):
        bot.answer_callback_query(call.id, "🚫 You are banned.")
        return

    bot.answer_callback_query(call.id)

    if data == "check_sub":
        if rate_limited(uid):
            bot.send_message(cid, f"⏳ Please wait {RATE_LIMIT_SECONDS}s before checking again.")
            return
        if is_subscribed(uid):
            register_user(call.from_user)     # fixed: was call.message (the bot's msg)
            name = call.from_user.first_name or "there"
            bot.send_message(cid, "✅ <b>Subscription confirmed!</b>")
            send_main_menu(cid, name)
        else:
            bot.send_message(
                cid,
                "❌ You are not subscribed yet.\nJoin the channel and try again.",
                reply_markup=subscribe_keyboard(),
            )
        return

    if not is_subscribed(uid):
        send_subscribe_prompt(cid)
        return

    if data == "menu_back":
        name = call.from_user.first_name or "there"
        send_main_menu(cid, name)

    elif data == "menu_courses":
        courses = db.get_all_courses()
        if not courses:
            bot.send_message(cid, "📭 <b>No courses available yet.</b>\n\nCheck back soon!",
                             reply_markup=back_keyboard())
        else:
            bot.send_message(
                cid,
                f"📚 <b>Available Courses</b>\n\nWe have <b>{len(courses)}</b> course(s).\n"
                "Tap a title to open:",
                reply_markup=courses_keyboard(courses),
            )

    elif data == "menu_profile":
        u      = call.from_user
        rec    = db.get_subscriber(uid)
        joined = rec["joined"][:10] if rec else "—"
        uname  = f"@{u.username}" if u.username else "<i>no username</i>"
        bot.send_message(
            cid,
            f"👤 <b>Your Profile</b>\n\n"
            f"Name     : {u.first_name or '—'}\n"
            f"Username : {uname}\n"
            f"ID       : <code>{uid}</code>\n"
            f"Joined   : {joined}",
            reply_markup=back_keyboard(),
        )

    elif data == "menu_contact":
        bot.send_message(
            cid,
            "📩 <b>Contact Us</b>\n\n"
            "Have a question or suggestion?\n"
            "Tap the button below to send us a message.",
            reply_markup=contact_keyboard(),
        )

    elif data == "menu_help":
        bot.send_message(
            cid,
            "ℹ️ <b>Help &amp; FAQ</b>\n\n"
            "📚 <b>Courses</b> — Browse all available course links.\n"
            "👤 <b>Profile</b> — See your account details.\n"
            "📩 <b>Contact</b> — Send a message to the admin.\n\n"
            "<b>Commands</b>\n"
            "/start — Open main menu\n"
            "/help  — Show this panel",
            reply_markup=back_keyboard(),
        )


# ── Contact flow ──────────────────────────────────────────────────────────────
@bot.callback_query_handler(func=lambda c: c.data == "contact_send")
def contact_send_callback(call):
    uid = call.from_user.id
    if db.is_banned(uid):
        bot.answer_callback_query(call.id, "🚫 Banned")
        return
    bot.answer_callback_query(call.id)
    user_states[uid] = {"state": "awaiting_contact_message"}
    bot.send_message(
        call.message.chat.id,
        "✏️ <b>Write your message</b>\n\n"
        "Type anything you want to tell us and send it.\n\n"
        "<i>Send /cancel to abort.</i>",
    )


# ── Multi-step text handler ───────────────────────────────────────────────────
# BUG FIX #2 — original lambda: not m.text.startswith("/")
# crashes with AttributeError when m.text is None (photo, sticker, etc.)
# Fixed by checking content_type == 'text' FIRST before accessing m.text
@bot.message_handler(
    func=lambda m: m.content_type == "text"
                   and m.from_user.id in user_states
                   and not m.text.startswith("/")
)
def handle_state_input(message):
    if not ban_guard(message): return
    uid   = message.from_user.id
    state = user_states.get(uid, {})
    s     = state.get("state")
    cid   = message.chat.id

    if s == "awaiting_contact_message":
        text     = message.text.strip()
        username = message.from_user.username or message.from_user.first_name or "unknown"
        msg_id   = db.save_message(uid, username, text)
        try:
            bot.send_message(
                ADMIN_ID,
                f"📨 <b>New Contact Message #{msg_id}</b>\n\n"
                f"From: @{username} (<code>{uid}</code>)\n\n"
                f"{text}",
            )
        except Exception as e:
            logger.warning("Could not forward message to admin: %s", e)
        forward_to_email(username, uid, text)
        user_states.pop(uid, None)
        bot.send_message(cid, "✅ <b>Message sent!</b>\n\nThank you — we'll get back to you shortly.",
                         reply_markup=back_keyboard())

    elif s == "awaiting_course_title":
        title = message.text.strip()
        if len(title) < 2:
            bot.send_message(cid, "⚠️ Title too short. Try again:"); return
        user_states[uid] = {"state": "awaiting_course_link", "title": title}
        bot.send_message(cid,
            f"✅ Title saved: <b>{title}</b>\n\n"
            "Step 2/2 — Now send the <b>course URL</b>:")

    elif s == "awaiting_course_link":
        link = message.text.strip()
        if not link.startswith("http"):
            bot.send_message(cid, "⚠️ Please enter a valid URL (must start with http):"); return
        title     = state["title"]
        course_id = db.add_course(title, link, added_by=uid)
        user_states.pop(uid, None)
        bot.send_message(
            cid,
            f"🎉 <b>Course Added!</b>\n\n"
            f"ID    : <code>{course_id}</code>\n"
            f"Title : {title}\n"
            f"Link  : <a href='{link}'>Open</a>",
        )

    elif s == "awaiting_broadcast_text":
        text = message.text.strip()
        user_states.pop(uid, None)
        _do_broadcast(bot, cid, text)


# ── Fallback — plain function, NOT a decorator
# BUG FIX #1 — the @decorator ran at import time, registering fallback BEFORE
# admin handlers. Since telebot picks the first matching handler in order,
# fallback (func=True) was swallowing every admin command (/admin, /stats, etc.)
# Fix: register it at the END of setup_bot(), after all other handlers.
def fallback(message):
    if not ban_guard(message): return
    bot.send_message(message.chat.id, "🤖 Use /start to open the main menu.")


# ── Bot setup ─────────────────────────────────────────────────────────────────
def setup_bot() -> None:
    bot.remove_webhook()

    # Step 1 — admin handlers (commands + callbacks)
    register_admin_handlers(bot, ADMIN_ID, user_states)

    # Step 2 — public command list
    try:
        bot.set_my_commands(
            [BotCommand("start", "Open main menu"), BotCommand("help", "Help & FAQ")],
            scope=BotCommandScopeDefault(),
        )
    except Exception as e:
        logger.warning("Could not set public commands: %s", e)

    # Step 3 — fallback MUST be last, after all specific handlers
    bot.message_handler(func=lambda m: True)(fallback)

    logger.info("Bot ready ✅")


# ── Flask (webhook mode — used when deployed) ─────────────────────────────────
@app.route("/")
def home():
    return "✅ Bot is running!", 200


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook_route():
    json_str = request.get_data(as_text=True)
    update   = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "", 200


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    setup_bot()
    logger.info("Starting polling — press Ctrl+C to stop")
    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=30)
        except Exception as e:
            logger.error("Polling error: %s — restarting in 5s", e)
            time.sleep(5)