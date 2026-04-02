"""
Python So powerful

"""
```markdown
# 📘 Telegram Subscription Bot – Complete Documentation

A powerful Telegram bot that gates access to a course (or any resource) behind a channel subscription. Users must join your Telegram channel before receiving the course link. The bot supports multiple courses, admin commands, broadcasting, banning, and persistent storage.

---

## 🚀 Features

- ✅ **Subscription Gate** – Users must join your channel to get the content.
- 📚 **Multi‑Course Support** – Add, remove, and switch courses on the fly (no code changes).
- 👑 **Admin Commands** – Broadcast, ban/unban, view stats, manage courses.
- 💾 **Persistent Storage** – Subscribers, banned users, and courses are saved in JSON files.
- ⏱️ **Rate Limiting** – Prevents abuse of the subscription check.
- 📄 **PDF Hint** – After subscribing, users are told that the PDF version is pinned in the channel.
- 🔁 **Auto‑Restart** – The bot automatically restarts on errors.

---

## 📋 Requirements

- **Python 3.14+** (3.10+ should also work)
- **pip** packages:
  - `pyTelegramBotAPI`
  - `requests`
- A **Telegram Bot Token** from [@BotFather](https://t.me/BotFather)
- A **Telegram Channel** (public or private) that users must join
- The bot must be an **administrator** of that channel (to check membership)
- Your **Telegram User ID** (admin) – get it from [@userinfobot](https://t.me/userinfobot)

Install dependencies:

```bash
pip install pyTelegramBotAPI requests
```

---

## ⚙️ Configuration (Edit in the script)

Open the bot `.py` file and change these variables at the top:

| Variable | Description | Example |
|----------|-------------|---------|
| `TOKEN` | Your bot token from BotFather | `"123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"` |
| `COURSE_LINK` | Fallback course link (used if no courses.json) | `"https://canva.link/..."` |
| `CHANNEL_USERNAME` | Channel username (**without** `@`) | `"EasyCs"` |
| `CHANNEL_LINK` | Invite link for the “Join Channel” button | `"https://t.me/EasyCs_Official"` |
| `ADMIN_ID` | Your numeric Telegram user ID | `7020797610` |

Optional file names (can stay as is):

- `SUBSCRIBERS_FILE = "subscribers.json"`
- `BANNED_FILE = "banned.json"`
- `COURSES_FILE = "courses.json"`

---

## 🧠 How the Bot Works

### 1. Subscription Check
- User sends `/start` or `/course`.
- Bot calls `get_chat_member` to verify if the user is in your channel.
- If **not subscribed** → sends an inline keyboard with a **Join Channel** button and a **Check Subscription** button.
- If **subscribed** → saves the user ID to `subscribers.json` and sends the active course link.

### 2. Callback Handling
- When the user clicks **Check Subscription**, the bot immediately answers the callback (to avoid timeout) and then performs the actual check.
- Rate limiting prevents repeated checks (default: 5 seconds).

### 3. Persistent Storage (JSON files)
- `subscribers.json` – list of user IDs that have successfully subscribed.
- `banned.json` – list of banned user IDs (they cannot use the bot).
- `courses.json` – stores all courses and the active index:
  ```json
  {
    "courses": [
      {"name": "Algebra", "link": "https://canva.link/..."},
      {"name": "Calculus", "link": "https://example.com/calc"}
    ],
    "active_index": 0
  }
  ```

### 4. Course Delivery
- The active course (selected by `/setactive`) is sent to users.
- A note is always added: *“You can also find the PDF version of this course inside our channel (pinned message).”*

### 5. Admin Commands
- All admin commands are restricted to the user ID set in `ADMIN_ID`.
- Admin commands include: status, broadcast, ban, unban, listbans, and **course management**.

---

## 📖 User Commands

| Command | Description |
|---------|-------------|
| `/start` | Get the active course link (after subscribing) |
| `/course` | Same as `/start` |
| `/help` | Show available commands |

---

## 👑 Admin Commands

| Command | Description |
|---------|-------------|
| `/status` | Show bot statistics (subscribers, banned, active course, etc.) |
| `/broadcast <message>` | Send a message to all subscribers |
| `/ban <user_id>` | Ban a user from using the bot |
| `/unban <user_id>` | Unban a user |
| `/listbans` | List all banned user IDs |
| `/getme` | Show bot account info (ID, username, capabilities) |
| `/userinfo <user_id>` | Get Telegram user info |
| `/delwebhook` | Delete any active webhook (force polling mode) |
| `/addcourse Name \| link` | Add a new course (pipe symbol required) |
| `/listcourses` | Show all stored courses with indices and active marker |
| `/setactive <index>` | Set the active course (users will receive this one) |
| `/delcourse <index>` | Delete a course by index |
| `/getcourse` | Show the currently active course |

---

## 🆕 How to Add a New Course (No Coding Required)

As the **admin**, talk to the bot and use these commands:

### Step 1 – Add the course
```
/addcourse Calculus | https://example.com/calculus.pdf
```
The bot will reply: `✅ Course added: Calculus`

### Step 2 – List all courses to see indices
```
/listcourses
```
Output example:
```
✅ 0 – Algebra
     https://canva.link/...
   1 – Calculus
     https://example.com/calculus.pdf
```
The checkmark (✅) indicates the active course.

### Step 3 – Activate the new course (if desired)
```
/setactive 1
```
Now every new subscriber (and existing users who type `/start`) will receive the Calculus course.

### Step 4 – Verify the active course
```
/getcourse
```

### Optional – Remove an old course
```
/delcourse 0
```

---

## 🔧 Running the Bot

```bash
python bot.py
```

The bot will:
- Clear any existing webhook.
- Register command menus.
- Start long-polling.
- Log to `bot.log` and the console.

To stop: `Ctrl+C`

---

## 📁 File Structure (After First Run)

```
your_bot_folder/
├── bot.py                  # Main script
├── subscribers.json        # List of subscribed user IDs
├── banned.json             # List of banned user IDs
├── courses.json            # Course data (name, link, active index)
└── bot.log                 # Log file
```

---

## 🛠️ Making Other Changes (Code Modifications)

| Change | Where to edit |
|--------|----------------|
| Rate limit (default 5s) | `RATE_LIMIT_SECONDS = 5` |
| PDF reminder text | Inside `send_course()` function |
| Welcome / subscribe message | Inside `send_subscribe_prompt()` function |
| Add a new admin command | Create a new function with `@bot.message_handler(commands=["mycmd"])` and call `admin_only(message)` |
| Use a **private channel** (numeric ID) | Replace `CHANNEL_USERNAME` with `CHANNEL_ID = -1001234567890` and modify `is_subscribed()` accordingly |

---

## ❗ Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `Bad Request: chat not found` | Bot not in channel or wrong username | Add bot as admin to the channel; set correct `CHANNEL_USERNAME` (without `@`) |
| `query is too old` | Callback answer took >30 seconds | Already fixed in the final code – answer sent immediately |
| `Forbidden: bot was blocked by the user` | User blocked the bot | Ignore – broadcast continues to others |
| JSON file corrupted | Manual edit or disk error | Delete the offending `.json` file and restart – defaults are recreated |

---

## 📦 Backup & Restore

To move the bot to another server, copy:
- The main `.py` script
- `subscribers.json`
- `banned.json`
- `courses.json`

All data is plain JSON and can be edited manually.

---

## 📄 License

This bot is free to use and modify for your own Telegram channels.

---

## 🙋 Support

For issues, check the logs (`bot.log`) or open an issue on your repository.

**Enjoy your subscription bot! 🎉**
```