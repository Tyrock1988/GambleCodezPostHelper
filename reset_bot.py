import asyncio
from aiogram import Bot
from dotenv import load_dotenv
import os

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

async def reset():
    bot = Bot(BOT_TOKEN)
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Telegram webhook and update queue cleared.")
    await bot.session.close()

asyncio.run(reset())