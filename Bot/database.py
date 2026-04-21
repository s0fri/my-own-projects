"""
database.py — Persistent JSON storage layer
Handles: subscribers, courses, messages, banned users
"""

import json
import os
from datetime import datetime

# ── File paths ──────────────────────────────────────────────────────────────
SUBSCRIBERS_FILE = "subscribers.json"
COURSES_FILE     = "courses.json"
MESSAGES_FILE    = "messages.json"
BANNED_FILE      = "banned.json"


# ── Internal helpers ────────────────────────────────────────────────────────
def _load(path: str, default):
    """Load JSON file safely; return default on missing / corrupt file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _save(path: str, data) -> None:
    """Atomically write JSON to file."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


# ── Subscribers ─────────────────────────────────────────────────────────────
def add_subscriber(user_id: int, username: str = None, first_name: str = None) -> bool:
    """
    Register a user. Returns True if new, False if already exists.
    Always updates username/first_name if they changed.
    Data is NEVER auto-deleted.
    """
    data = _load(SUBSCRIBERS_FILE, {"subscribers": {}})
    uid  = str(user_id)
    now  = datetime.now().isoformat()

    if uid not in data["subscribers"]:
        data["subscribers"][uid] = {
            "user_id":    user_id,
            "username":   username   or "",
            "first_name": first_name or "",
            "joined":     now,
            "last_seen":  now,
        }
        _save(SUBSCRIBERS_FILE, data)
        return True

    # Update mutable fields
    changed = False
    rec = data["subscribers"][uid]
    if username   and rec.get("username")   != username:   rec["username"]   = username;   changed = True
    if first_name and rec.get("first_name") != first_name: rec["first_name"] = first_name; changed = True
    rec["last_seen"] = now
    if changed:
        _save(SUBSCRIBERS_FILE, data)
    return False


def get_all_subscribers() -> list:
    return list(_load(SUBSCRIBERS_FILE, {"subscribers": {}})["subscribers"].values())


def get_subscriber_count() -> int:
    return len(_load(SUBSCRIBERS_FILE, {"subscribers": {}})["subscribers"])


def get_subscriber(user_id: int) -> dict | None:
    return _load(SUBSCRIBERS_FILE, {"subscribers": {}})["subscribers"].get(str(user_id))


# ── Courses ─────────────────────────────────────────────────────────────────
def _next_course_id(courses: list) -> int:
    if not courses:
        return 1
    return max(c["id"] for c in courses) + 1


def add_course(title: str, link: str, added_by: int = None) -> int:
    """Add a course. Returns the new course ID."""
    data      = _load(COURSES_FILE, {"courses": []})
    course_id = _next_course_id(data["courses"])
    data["courses"].append({
        "id":       course_id,
        "title":    title.strip(),
        "link":     link.strip(),
        "added_at": datetime.now().isoformat(),
        "added_by": added_by,
    })
    _save(COURSES_FILE, data)
    return course_id


def remove_course(course_id: int) -> bool:
    """Remove course by ID. Returns True if found and removed."""
    data     = _load(COURSES_FILE, {"courses": []})
    original = len(data["courses"])
    data["courses"] = [c for c in data["courses"] if c["id"] != course_id]
    if len(data["courses"]) < original:
        _save(COURSES_FILE, data)
        return True
    return False


def get_all_courses() -> list:
    return _load(COURSES_FILE, {"courses": []})["courses"]


def get_course(course_id: int) -> dict | None:
    for c in get_all_courses():
        if c["id"] == course_id:
            return c
    return None


# ── Messages (contact) ──────────────────────────────────────────────────────
def save_message(from_user_id: int, username: str, text: str) -> int:
    """Save a user contact message. Returns message ID."""
    data   = _load(MESSAGES_FILE, {"messages": []})
    msg_id = (max((m["id"] for m in data["messages"]), default=0)) + 1
    data["messages"].append({
        "id":           msg_id,
        "from_user_id": from_user_id,
        "username":     username or "unknown",
        "text":         text,
        "timestamp":    datetime.now().isoformat(),
        "read":         False,
    })
    _save(MESSAGES_FILE, data)
    return msg_id


def get_all_messages() -> list:
    return _load(MESSAGES_FILE, {"messages": []})["messages"]


def get_unread_messages() -> list:
    return [m for m in get_all_messages() if not m["read"]]


def mark_message_read(msg_id: int) -> None:
    data = _load(MESSAGES_FILE, {"messages": []})
    for msg in data["messages"]:
        if msg["id"] == msg_id:
            msg["read"] = True
    _save(MESSAGES_FILE, data)


def mark_all_read() -> None:
    data = _load(MESSAGES_FILE, {"messages": []})
    for msg in data["messages"]:
        msg["read"] = True
    _save(MESSAGES_FILE, data)


# ── Banned users ─────────────────────────────────────────────────────────────
def ban_user(user_id: int) -> bool:
    data = _load(BANNED_FILE, {"banned": []})
    if user_id not in data["banned"]:
        data["banned"].append(user_id)
        _save(BANNED_FILE, data)
        return True
    return False


def unban_user(user_id: int) -> bool:
    data = _load(BANNED_FILE, {"banned": []})
    if user_id in data["banned"]:
        data["banned"].remove(user_id)
        _save(BANNED_FILE, data)
        return True
    return False


def is_banned(user_id: int) -> bool:
    return user_id in _load(BANNED_FILE, {"banned": []})["banned"]


def get_banned_count() -> int:
    return len(_load(BANNED_FILE, {"banned": []})["banned"])