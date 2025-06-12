import re
import json
import asyncio
import logging
import os
from pathlib import Path
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
from keep_alive import keep_alive

# Load environment variables
load_dotenv()

# === CONFIG ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip().isdigit()]
if not ADMIN_IDS:
    print("Warning: No ADMIN_IDS configured. Bot will not respond to admin commands.")

LINKS_FILE = Path("links.json")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# === STORAGE ===
def load_links():
    """Load referral links from JSON file"""
    try:
        if LINKS_FILE.exists():
            with open(LINKS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                logger.info(f"Loaded {len(data)} links from {LINKS_FILE}")
                return data
        else:
            logger.info(f"Links file {LINKS_FILE} not found, starting with empty database")
            return {}
    except Exception as e:
        logger.error(f"Error loading links from {LINKS_FILE}: {e}")
        return {}

def save_links(links):
    """Save referral links to JSON file"""
    try:
        with open(LINKS_FILE, "w", encoding="utf-8") as f:
            json.dump(links, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(links)} links to {LINKS_FILE}")
    except Exception as e:
        logger.error(f"Error saving links to {LINKS_FILE}: {e}")

# Initialize links database
links_db = load_links()

# === BOT SETUP ===
bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# === HELPERS ===
def build_keyboard(urls):
    """Build inline keyboard with referral links"""
    buttons = []
    for url in urls:
        label = links_db[url].get("label", "Sign Up Now")
        buttons.append([InlineKeyboardButton(text=label, url=url)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def escape_html(text):
    """Escape HTML special characters"""
    if not text:
        return ""
    return text.replace("&", "&amp").replace("<", "&lt;").replace(">", "&gt;")

def is_admin(user_id):
    """Check if user is admin"""
    return user_id in ADMIN_IDS

# === COMMAND HANDLERS ===
@dp.message(Command("start"))
async def cmd_start(msg: Message):
    """Start command handler"""
    welcome_text = """
🤖 <b>Referral Link Bot</b>

This bot automatically formats messages containing saved referral links with inline buttons.

<b>Admin Commands:</b>
/addurl [Label] [URL] - Add a single referral link
/addurls - Add multiple links (one per line: Label URL)
/delurl [URL] - Remove a referral link
/delurls - Remove multiple URLs (one per line)
/listurls - List all saved links
/setbutton [URL] [Button Text] - Update button text for a URL

<b>How it works:</b>
When you post a message containing any saved referral URL, the bot will automatically format it with inline buttons and extract any referral codes.
"""
    await msg.reply(welcome_text)

@dp.message(Command("addurl"))
async def cmd_addurl(msg: Message):
    """Add a single referral URL"""
    if not is_admin(msg.from_user.id):
        await msg.reply("❌ Only admins can use this command.")
        return
    
    try:
        parts = msg.text.split(maxsplit=2)
        if len(parts) < 3:
            await msg.reply("Usage: /addurl [Label] [URL]\n\nExample: /addurl \"Sign Up\" https://example.com/ref123")
            return
        
        label, url = parts[1], parts[2]
        
        # Basic URL validation
        if not (url.startswith("http://") or url.startswith("https://")):
            await msg.reply("❌ Invalid URL. Must start with http:// or https://")
            return
        
        links_db[url] = {"label": label}
        save_links(links_db)
        await msg.reply(f"✅ Saved: <b>{escape_html(label)}</b> → {escape_html(url)}")
        logger.info(f"Admin {msg.from_user.id} added URL: {label} -> {url}")
        
    except Exception as e:
        logger.error(f"Error in addurl command: {e}")
        await msg.reply("❌ Error adding URL. Please try again.")

@dp.message(Command("addurls"))
async def cmd_addurls(msg: Message):
    """Add multiple referral URLs"""
    if not is_admin(msg.from_user.id):
        await msg.reply("❌ Only admins can use this command.")
        return
    
    try:
        lines = msg.text.splitlines()[1:]  # Skip the command line
        if not lines:
            await msg.reply("Usage: /addurls\nLabel1 URL1\nLabel2 URL2\n...")
            return
        
        added = []
        errors = []
        
        for line_num, line in enumerate(lines, 1):
            parts = line.strip().split(maxsplit=1)
            if len(parts) != 2:
                errors.append(f"Line {line_num}: Invalid format")
                continue
            
            label, url = parts
            if not (url.startswith("http://") or url.startswith("https://")):
                errors.append(f"Line {line_num}: Invalid URL")
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
        logger.info(f"Admin {msg.from_user.id} added {len(added)} URLs")
        
    except Exception as e:
        logger.error(f"Error in addurls command: {e}")
        await msg.reply("❌ Error adding URLs. Please try again.")

@dp.message(Command("delurl"))
async def cmd_delurl(msg: Message):
    """Delete a single referral URL"""
    if not is_admin(msg.from_user.id):
        await msg.reply("❌ Only admins can use this command.")
        return
    
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
            logger.info(f"Admin {msg.from_user.id} removed URL: {url}")
        else:
            await msg.reply("URL not found in database")
            
    except Exception as e:
        logger.error(f"Error in delurl command: {e}")
        await msg.reply("❌ Error removing URL. Please try again.")

@dp.message(Command("delurls"))
async def cmd_delurls(msg: Message):
    """Delete multiple referral URLs"""
    if not is_admin(msg.from_user.id):
        await msg.reply("❌ Only admins can use this command.")
        return
    
    try:
        lines = msg.text.splitlines()[1:]  # Skip the command line
        if not lines:
            await msg.reply("Usage: /delurls\nURL1\nURL2\n...")
            return
        
        removed = []
        not_found = []
        
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
        
        response = ""
        if removed:
            response += "❌ Removed:\n" + "\n".join(removed)
        if not_found:
            response += "\n\n⚠️ Not found:\n" + "\n".join(not_found)
        
        await msg.reply(response or "No URLs to remove.")
        logger.info(f"Admin {msg.from_user.id} removed {len(removed)} URLs")
        
    except Exception as e:
        logger.error(f"Error in delurls command: {e}")
        await msg.reply("❌ Error removing URLs. Please try again.")

@dp.message(Command("listurls"))
async def cmd_listurls(msg: Message):
    """List all saved referral URLs"""
    if not is_admin(msg.from_user.id):
        await msg.reply("❌ Only admins can use this command.")
        return
    
    try:
        if not links_db:
            await msg.reply("No links saved yet.")
            return
        
        text = f"<b>Saved Links ({len(links_db)}):</b>\n\n"
        for i, (url, data) in enumerate(links_db.items(), 1):
            label = data.get('label', 'No Label')
            text += f"{i}. {escape_html(label)} → {escape_html(url)}\n"
        
        # Split long messages if needed
        if len(text) > 4000:
            chunks = []
            current_chunk = f"<b>Saved Links ({len(links_db)}):</b>\n\n"
            
            for i, (url, data) in enumerate(links_db.items(), 1):
                label = data.get('label', 'No Label')
                line = f"{i}. {escape_html(label)} → {escape_html(url)}\n"
                
                if len(current_chunk + line) > 4000:
                    chunks.append(current_chunk)
                    current_chunk = line
                else:
                    current_chunk += line
            
            if current_chunk:
                chunks.append(current_chunk)
            
            for chunk in chunks:
                await msg.reply(chunk)
        else:
            await msg.reply(text)
            
    except Exception as e:
        logger.error(f"Error in listurls command: {e}")
        await msg.reply("❌ Error listing URLs. Please try again.")

@dp.message(Command("setbutton"))
async def cmd_setbutton(msg: Message):
    """Update button text for a URL"""
    if not is_admin(msg.from_user.id):
        await msg.reply("❌ Only admins can use this command.")
        return
    
    try:
        parts = msg.text.split(maxsplit=2)
        if len(parts) < 3:
            await msg.reply("Usage: /setbutton [URL] [Button Text]")
            return
        
        url, label = parts[1], parts[2]
        if url not in links_db:
            await msg.reply("URL not found in database")
            return
        
        links_db[url]["label"] = label
        save_links(links_db)
        await msg.reply(f"🔁 Updated label for {escape_html(url)} to: <b>{escape_html(label)}</b>")
        logger.info(f"Admin {msg.from_user.id} updated button for {url}")
        
    except Exception as e:
        logger.error(f"Error in setbutton command: {e}")
        await msg.reply("❌ Error updating button. Please try again.")

# === AUTO FORMAT HANDLER ===
@dp.message()
async def auto_edit(msg: Message):
    """Auto-format messages containing referral links"""
    try:
        text = msg.text or ""
        if not text or not links_db:
            return
        
        # Find URLs that are in our database
        found_urls = [url for url in links_db if url in text]
        if not found_urls:
            return
        
        logger.info(f"Found {len(found_urls)} referral URLs in message from user {msg.from_user.id}")
        
        # Extract referral code if present
        code_match = re.search(r'(code[:\s]*)([A-Za-z0-9@_-]+)', text, re.IGNORECASE)
        code_text = f"<b>Code:</b> {escape_html(code_match.group(2))}\n\n" if code_match else ""
        
        # Get the first line as title
        first_line = text.splitlines()[0] if text.splitlines() else "Referral Links"
        
        # Build new message
        new_text = f"<b>{escape_html(first_line)}</b>\n\n{code_text}<b>Links below:</b>"
        
        # Build keyboard with found URLs
        keyboard = build_keyboard(found_urls)
        
        # Try to edit the message
        try:
            await bot.edit_message_text(
                chat_id=msg.chat.id,
                message_id=msg.message_id,
                text=new_text,
                reply_markup=keyboard
            )
            logger.info(f"Successfully edited message {msg.message_id}")
        except Exception as e:
            logger.warning(f"Edit failed for message {msg.message_id}: {e}")
            # If edit fails, we could optionally send a new message
            # await msg.reply(new_text, reply_markup=keyboard)
            
    except Exception as e:
        logger.error(f"Error in auto_edit handler: {e}")

# === ERROR HANDLER ===
async def on_startup():
    """Bot startup handler"""
    logger.info("Bot is starting up...")
    logger.info(f"Bot token configured: {'Yes' if BOT_TOKEN else 'No'}")
    logger.info(f"Admin IDs: {ADMIN_IDS}")
    logger.info(f"Links database loaded with {len(links_db)} entries")
    
    # Delete webhook if it exists to allow polling
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook deleted successfully")
    except Exception as e:
        logger.warning(f"Could not delete webhook: {e}")

async def on_shutdown():
    """Bot shutdown handler"""
    logger.info("Bot is shutting down...")
    await bot.session.close()

# === MAIN ===
async def main():
    """Main bot function with error handling and auto-restart"""
    retry_count = 0
    max_retries = 5
    
    while retry_count < max_retries:
        try:
            logger.info(f"Starting bot (attempt {retry_count + 1}/{max_retries})")
            await on_startup()
            
            # Start polling
            await dp.start_polling(bot, skip_updates=True)
            
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            break
        except Exception as e:
            retry_count += 1
            logger.error(f"Bot crashed with error: {e}")
            
            if retry_count < max_retries:
                wait_time = min(60, 2 ** retry_count)  # Exponential backoff
                logger.info(f"Restarting in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                logger.error("Max retries reached. Bot will not restart automatically.")
                break
        finally:
            await on_shutdown()

if __name__ == "__main__":
    # Start keep-alive server for Replit
    keep_alive()
    
    # Run the bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
