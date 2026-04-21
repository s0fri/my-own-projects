"""
admin.py — Admin-only Telegram command & callback handlers
Registers all /admin commands onto the given bot instance.
"""

import logging
import time
import threading

import telebot
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    BotCommand, BotCommandScopeChat,
)

import database as db

logger = logging.getLogger(__name__)


# ── Guard helpers ────────────────────────────────────────────────────────────
def is_admin(user_id: int, admin_id: int) -> bool:
    return user_id == admin_id


def admin_guard(bot: telebot.TeleBot, message, admin_id: int) -> bool:
    if not is_admin(message.from_user.id, admin_id):
        bot.send_message(message.chat.id, "⛔ Admin only command.")
        return False
    return True


# ── Keyboards ────────────────────────────────────────────────────────────────
def admin_panel_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📚 List Courses",    callback_data="admin_listcourses"),
        InlineKeyboardButton("➕ Add Course",      callback_data="admin_addcourse"),
        InlineKeyboardButton("📊 Stats",           callback_data="admin_stats"),
        InlineKeyboardButton("📩 Messages",        callback_data="admin_messages"),
        InlineKeyboardButton("📢 Broadcast",       callback_data="admin_broadcast"),
    )
    return kb


def course_delete_keyboard(courses: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    for c in courses:
        kb.add(InlineKeyboardButton(
            f"🗑 [{c['id']}] {c['title'][:40]}",
            callback_data=f"del_course_{c['id']}",
        ))
    kb.add(InlineKeyboardButton("❌ Cancel", callback_data="admin_cancel"))
    return kb


def messages_keyboard(messages: list, offset: int = 0, page_size: int = 5) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    page = messages[offset: offset + page_size]
    for m in page:
        status = "🔵" if not m["read"] else "⚪"
        label  = f"{status} #{m['id']} @{m['username'][:15]}"
        kb.add(InlineKeyboardButton(label, callback_data=f"read_msg_{m['id']}"))
    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"msgs_page_{offset - page_size}"))
    if offset + page_size < len(messages):
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"msgs_page_{offset + page_size}"))
    if nav:
        kb.row(*nav)
    kb.add(InlineKeyboardButton("✅ Mark All Read", callback_data="mark_all_read"))
    kb.add(InlineKeyboardButton("🔙 Back",          callback_data="admin_panel"))
    return kb


# ── Registration function ────────────────────────────────────────────────────
def register_admin_handlers(bot: telebot.TeleBot, admin_id: int, user_states: dict) -> None:
    """
    Call this once from bot.py to register all admin handlers.
    `user_states` is a shared dict for multi-step conversation tracking.
    """

    # ── /admin — main panel ──────────────────────────────────────────────────
    @bot.message_handler(commands=["admin"])
    def cmd_admin(message):
        if not admin_guard(bot, message, admin_id): return
        bot.send_message(
            message.chat.id,
            "🛠 <b>Admin Panel</b>\n\nChoose an action below:",
            reply_markup=admin_panel_keyboard(),
        )

    # ── /stats ───────────────────────────────────────────────────────────────
    @bot.message_handler(commands=["stats"])
    def cmd_stats(message):
        if not admin_guard(bot, message, admin_id): return
        _send_stats(bot, message.chat.id)

    # ── /listcourses ─────────────────────────────────────────────────────────
    @bot.message_handler(commands=["listcourses"])
    def cmd_listcourses(message):
        if not admin_guard(bot, message, admin_id): return
        _send_course_list(bot, message.chat.id)

    # ── /addcourse — step 1 ───────────────────────────────────────────────────
    @bot.message_handler(commands=["addcourse"])
    def cmd_addcourse(message):
        if not admin_guard(bot, message, admin_id): return
        user_states[message.from_user.id] = {"state": "awaiting_course_title"}
        bot.send_message(
            message.chat.id,
            "📚 <b>Add New Course</b>\n\nStep 1/2 — Enter the <b>course title</b>:\n\n"
            "<i>Send /cancel to abort.</i>",
        )

    # ── /removecourse ─────────────────────────────────────────────────────────
    @bot.message_handler(commands=["removecourse"])
    def cmd_removecourse(message):
        if not admin_guard(bot, message, admin_id): return
        courses = db.get_all_courses()
        if not courses:
            bot.send_message(message.chat.id, "📭 No courses to remove.")
            return
        bot.send_message(
            message.chat.id,
            "🗑 <b>Remove Course</b>\n\nSelect a course to delete:",
            reply_markup=course_delete_keyboard(courses),
        )

    # ── /broadcast ────────────────────────────────────────────────────────────
    @bot.message_handler(commands=["broadcast"])
    def cmd_broadcast(message):
        if not admin_guard(bot, message, admin_id): return
        text = message.text.partition(" ")[2].strip()
        if not text:
            user_states[message.from_user.id] = {"state": "awaiting_broadcast_text"}
            bot.send_message(
                message.chat.id,
                "📢 <b>Broadcast</b>\n\nType your broadcast message:\n\n<i>Send /cancel to abort.</i>",
            )
            return
        _do_broadcast(bot, message.chat.id, text)

    # ── /messages ─────────────────────────────────────────────────────────────
    @bot.message_handler(commands=["messages"])
    def cmd_messages(message):
        if not admin_guard(bot, message, admin_id): return
        _send_messages_panel(bot, message.chat.id)

    # ── /ban ──────────────────────────────────────────────────────────────────
    @bot.message_handler(commands=["ban"])
    def cmd_ban(message):
        if not admin_guard(bot, message, admin_id): return
        parts = message.text.split()
        if len(parts) < 2:
            bot.send_message(message.chat.id, "Usage: /ban <user_id>"); return
        try:
            target = int(parts[1])
            if target == admin_id:
                bot.send_message(message.chat.id, "❌ Cannot ban yourself."); return
            result = db.ban_user(target)
            bot.send_message(message.chat.id,
                f"✅ Banned <code>{target}</code>" if result else f"ℹ️ <code>{target}</code> already banned")
        except ValueError:
            bot.send_message(message.chat.id, "❌ Invalid user ID.")

    # ── /unban ────────────────────────────────────────────────────────────────
    @bot.message_handler(commands=["unban"])
    def cmd_unban(message):
        if not admin_guard(bot, message, admin_id): return
        parts = message.text.split()
        if len(parts) < 2:
            bot.send_message(message.chat.id, "Usage: /unban <user_id>"); return
        try:
            target = int(parts[1])
            result = db.unban_user(target)
            bot.send_message(message.chat.id,
                f"✅ Unbanned <code>{target}</code>" if result else f"ℹ️ <code>{target}</code> was not banned")
        except ValueError:
            bot.send_message(message.chat.id, "❌ Invalid user ID.")

    # ── /cancel ────────────────────────────────────────────────────────────────
    @bot.message_handler(commands=["cancel"])
    def cmd_cancel(message):
        uid = message.from_user.id
        if uid in user_states:
            user_states.pop(uid)
            bot.send_message(message.chat.id, "❌ Action cancelled.")
        else:
            bot.send_message(message.chat.id, "Nothing to cancel.")

    # ── Admin callbacks ────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith("admin_") or
                                               c.data.startswith("del_course_") or
                                               c.data.startswith("read_msg_") or
                                               c.data.startswith("msgs_page_") or
                                               c.data == "mark_all_read")
    def admin_callbacks(call):
        if not is_admin(call.from_user.id, admin_id):
            bot.answer_callback_query(call.id, "⛔ Not allowed")
            return
        bot.answer_callback_query(call.id)
        data = call.data
        cid  = call.message.chat.id

        if data == "admin_panel":
            bot.send_message(cid, "🛠 <b>Admin Panel</b>", reply_markup=admin_panel_keyboard())

        elif data == "admin_stats":
            _send_stats(bot, cid)

        elif data == "admin_listcourses":
            _send_course_list(bot, cid)

        elif data == "admin_addcourse":
            user_states[call.from_user.id] = {"state": "awaiting_course_title"}
            bot.send_message(cid,
                "📚 <b>Add New Course</b>\n\nStep 1/2 — Enter the <b>course title</b>:\n\n"
                "<i>Send /cancel to abort.</i>")

        elif data == "admin_messages":
            _send_messages_panel(bot, cid)

        elif data == "admin_broadcast":
            user_states[call.from_user.id] = {"state": "awaiting_broadcast_text"}
            bot.send_message(cid,
                "📢 <b>Broadcast</b>\n\nType the message to send to all subscribers:\n\n"
                "<i>Send /cancel to abort.</i>")

        elif data == "admin_cancel":
            # BUG FIX #4 — clear state or admin stays stuck in wizard
            user_states.pop(call.from_user.id, None)
            bot.send_message(cid, "❌ Cancelled.")

        elif data.startswith("del_course_"):
            course_id = int(data.split("_")[-1])
            course    = db.get_course(course_id)
            if db.remove_course(course_id):
                title = course["title"] if course else f"#{course_id}"
                bot.send_message(cid, f"✅ Course <b>{title}</b> removed.")
            else:
                bot.send_message(cid, "❌ Course not found.")

        elif data.startswith("read_msg_"):
            msg_id = int(data.split("_")[-1])
            msgs   = db.get_all_messages()
            msg    = next((m for m in msgs if m["id"] == msg_id), None)
            if not msg:
                bot.send_message(cid, "❌ Message not found."); return
            db.mark_message_read(msg_id)
            ts = msg["timestamp"][:19].replace("T", " ")
            bot.send_message(
                cid,
                f"📨 <b>Message #{msg['id']}</b>\n"
                f"👤 From: @{msg['username']} (<code>{msg['from_user_id']}</code>)\n"
                f"🕐 {ts}\n\n"
                f"{msg['text']}",
            )

        elif data.startswith("msgs_page_"):
            offset = int(data.split("_")[-1])
            msgs   = db.get_all_messages()
            if not msgs:
                bot.send_message(cid, "📭 No messages."); return
            unread = len([m for m in msgs if not m["read"]])
            bot.send_message(
                cid,
                f"📩 <b>Inbox</b> — {len(msgs)} total, <b>{unread} unread</b>\n\nSelect a message:",
                reply_markup=messages_keyboard(msgs, offset),
            )

        elif data == "mark_all_read":
            db.mark_all_read()
            bot.send_message(cid, "✅ All messages marked as read.")


    # ── Set admin commands ─────────────────────────────────────────────────────
    try:
        bot.set_my_commands(
            [
                BotCommand("admin",        "Admin panel"),
                BotCommand("stats",        "Bot statistics"),
                BotCommand("listcourses",  "List all courses"),
                BotCommand("addcourse",    "Add a new course"),
                BotCommand("removecourse", "Remove a course"),
                BotCommand("broadcast",    "Broadcast message"),
                BotCommand("messages",     "View user messages"),
                BotCommand("ban",          "Ban a user"),
                BotCommand("unban",        "Unban a user"),
                BotCommand("cancel",       "Cancel current action"),
            ],
            scope=BotCommandScopeChat(admin_id),
        )
    except Exception as e:
        logger.warning("Could not set admin commands: %s", e)


# ── Private helpers ──────────────────────────────────────────────────────────
def _send_stats(bot: telebot.TeleBot, chat_id: int) -> None:
    subs     = db.get_subscriber_count()
    courses  = len(db.get_all_courses())
    msgs     = db.get_all_messages()
    unread   = len([m for m in msgs if not m["read"]])
    banned   = db.get_banned_count()
    bot.send_message(
        chat_id,
        f"📊 <b>Bot Statistics</b>\n\n"
        f"👥 Subscribers : <b>{subs}</b>\n"
        f"📚 Courses      : <b>{courses}</b>\n"
        f"📩 Messages     : <b>{len(msgs)}</b> total, <b>{unread}</b> unread\n"
        f"🚫 Banned       : <b>{banned}</b>",
    )


def _send_course_list(bot: telebot.TeleBot, chat_id: int) -> None:
    courses = db.get_all_courses()
    if not courses:
        bot.send_message(chat_id, "📭 No courses yet. Use /addcourse to add one.")
        return
    lines = ["📚 <b>All Courses</b>\n"]
    for c in courses:
        added = c["added_at"][:10]
        lines.append(f"<b>[{c['id']}]</b> {c['title']}\n"
                     f"     🔗 <a href='{c['link']}'>Open link</a>  |  📅 {added}")
    bot.send_message(chat_id, "\n\n".join(lines), disable_web_page_preview=True)


def _send_messages_panel(bot: telebot.TeleBot, chat_id: int) -> None:
    msgs   = db.get_all_messages()
    unread = len([m for m in msgs if not m["read"]])
    if not msgs:
        bot.send_message(chat_id, "📭 No contact messages yet.")
        return
    bot.send_message(
        chat_id,
        f"📩 <b>Inbox</b> — {len(msgs)} total, <b>{unread} unread</b>\n\nSelect a message:",
        reply_markup=messages_keyboard(msgs),
    )


def _do_broadcast(bot: telebot.TeleBot, admin_chat: int, text: str) -> None:
    subs = db.get_all_subscribers()
    if not subs:
        bot.send_message(admin_chat, "📭 No subscribers to broadcast to.")
        return
    bot.send_message(admin_chat, f"📢 Broadcasting to <b>{len(subs)}</b> users…")

    def task():
        sent = failed = 0
        for sub in subs:
            try:
                bot.send_message(sub["user_id"],
                    f"📢 <b>Announcement</b>\n\n{text}")
                sent += 1
                time.sleep(0.04)   # stay well under 30 msg/s limit
            except Exception as e:
                failed += 1
                logger.warning("Broadcast fail %s: %s", sub["user_id"], e)
        bot.send_message(admin_chat,
            f"✅ <b>Broadcast complete</b>\n\n"
            f"Delivered : <b>{sent}</b>\n"
            f"Failed    : <b>{failed}</b>")

    threading.Thread(target=task, daemon=True).start()