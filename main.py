import re import json import asyncio import logging import os from pathlib import Path from aiogram import Bot, Dispatcher, F from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton from aiogram.enums import ParseMode from aiogram.filters import Command from aiogram.client.default import DefaultBotProperties from dotenv import load_dotenv from keep_alive import keep_alive

Load environment variables

load_dotenv()

=== CONFIG ===

BOT_TOKEN = os.getenv("BOT_TOKEN", "") if not BOT_TOKEN: raise ValueError("BOT_TOKEN environment variable is required")

ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip().isdigit()] if not ADMIN_IDS: print("Warning: No ADMIN_IDS configured. Bot will not respond to admin commands.")

LINKS_FILE = Path("links.json")

Setup logging

logging.basicConfig( level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s' ) logger = logging.getLogger(name)

=== STORAGE ===

def load_links(): try: if LINKS_FILE.exists(): with open(LINKS_FILE, "r", encoding="utf-8") as f: data = json.load(f) logger.info(f"Loaded {len(data)} links from {LINKS_FILE}") return data else: logger.info(f"Links file {LINKS_FILE} not found, starting with empty database") return {} except Exception as e: logger.error(f"Error loading links: {e}") return {}

def save_links(links): try: with open(LINKS_FILE, "w", encoding="utf-8") as f: json.dump(links, f, indent=2, ensure_ascii=False) logger.info(f"Saved {len(links)} links to {LINKS_FILE}") except Exception as e: logger.error(f"Error saving links: {e}")

links_db = load_links()

=== BOT SETUP ===

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML)) dp = Dispatcher()

=== HELPERS ===

def is_admin(user_id: int) -> bool: return int(user_id) in ADMIN_IDS

def build_keyboard(urls): buttons = [] for url in urls: label = links_db[url].get("label", "Sign Up Now") buttons.append([InlineKeyboardButton(text=label, url=url)]) return InlineKeyboardMarkup(inline_keyboard=buttons)

def escape_html(text): return text.replace("&", "&amp").replace("<", "<").replace(">", ">") if text else ""

=== COMMAND HANDLERS ===

@dp.message(Command("start")) async def cmd_start(msg: Message): try: me = await bot.get_me() status = f"\U0001F916 <b>{me.first_name}</b> is online.\nUsername: @{me.username}\nID: <code>{me.id}</code>\n" except Exception as e: logger.error(f"Status check failed: {e}") status = "⚠️ Bot is online, but couldn't fetch status."

welcome_text = f"""

{status}

<b>Admin Commands:</b> /addurl [Label] [URL] — Add one referral link
/addurls — Add multiple links (one per line)
/delurl [URL] — Remove a referral link
/delurls — Remove multiple referral links
/listurls — List all saved links
/setbutton [URL] [Text] — Update label text for a URL

<i>Bot auto-detects and formats saved referral links in chat.</i> """ await msg.reply(welcome_text.strip())

@dp.message(Command("addurl")) async def cmd_addurl(msg: Message): if not is_admin(msg.from_user.id): await msg.reply("❌ Only admins can use this command.") return

try:
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 3:
        await msg.reply("Usage: /addurl [Label] [URL]")
        return

    label, url = parts[1], parts[2]
    if not (url.startswith("http://") or url.startswith("https://")):
        await msg.reply("❌ Invalid URL")
        return

    links_db[url] = {"label": label}
    save_links(links_db)
    await msg.reply(f"✅ Saved: <b>{escape_html(label)}</b> → {escape_html(url)}")
except Exception as e:
    logger.error(f"addurl error: {e}")
    await msg.reply("❌ Error adding URL.")

@dp.message(Command("addurls")) async def cmd_addurls(msg: Message): if not is_admin(msg.from_user.id): await msg.reply("❌ Only admins can use this command.") return

try:
    lines = msg.text.splitlines()[1:]
    if not lines:
        await msg.reply("Usage: /addurls\nLabel1 URL1\nLabel2 URL2\n...")
        return

    added, errors = [], []
    for i, line in enumerate(lines, 1):
        parts = line.strip().split(maxsplit=1)
        if len(parts) != 2:
            errors.append(f"Line {i}: Invalid format")
            continue
        label, url = parts
        if not url.startswith("http"):
            errors.append(f"Line {i}: Invalid URL")
            continue
        links_db[url] = {"label": label}
        added.append(f"{escape_html(label)} → {escape_html(url)}")

    if added:
        save_links(links_db)

    response = ""
    if added:
        response += "✅ Added:\n" + "\n".join(added)
    if errors:
        response += "\n\n❌ Errors:\n" + "\n".join(errors)

    await msg.reply(response or "No valid URLs to add.")
except Exception as e:
    logger.error(f"addurls error: {e}")
    await msg.reply("❌ Error adding multiple URLs.")

@dp.message(Command("delurl")) async def cmd_delurl(msg: Message): if not is_admin(msg.from_user.id): await msg.reply("❌ Only admins can use this command.") return

try:
    parts = msg.text.split(maxsplit=1)
    if len(parts) != 2:
        await msg.reply("Usage: /delurl [URL]")
        return

    url = parts[1]
    if url in links_db:
        del links_db[url]
        save_links(links_db)
        await msg.reply(f"❌ Removed {escape_html(url)}")
    else:
        await msg.reply("URL not found.")
except Exception as e:
    logger.error(f"delurl error: {e}")
    await msg.reply("❌ Error deleting URL.")

@dp.message(Command("delurls")) async def cmd_delurls(msg: Message): if not is_admin(msg.from_user.id): await msg.reply("❌ Only admins can use this command.") return

try:
    lines = msg.text.splitlines()[1:]
    removed, not_found = [], []

    for line in lines:
        url = line.strip()
        if not url:
            continue
        if url in links_db:
            del links_db[url]
            removed.append(escape_html(url))
        else:
            not_found.append(escape_html(url))

    if removed:
        save_links(links_db)

    reply = ""
    if removed:
        reply += "❌ Removed:\n" + "\n".join(removed)
    if not_found:
        reply += "\n\n⚠️ Not found:\n" + "\n".join(not_found)

    await msg.reply(reply or "No URLs to remove.")
except Exception as e:
    logger.error(f"delurls

