# BioLinkRemoverBot - All rights reserved
# © Graybots™. All rights reserved.

import time
from datetime import timedelta
from pyrogram import filters
from pyrogram.types import Message
from bot.bot import app
from database.user_language import get_user_language
from utils.language import get_message

# ✅ Motor database client for stats
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL

mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client["BioLinkRemover"]
users_collection = db["users"]
groups_col = db["groups"]

BOT_START_TIME = time.time()

def get_readable_time(seconds: int) -> str:
    return str(timedelta(seconds=int(seconds)))

@app.on_message(filters.command("ping") & ~filters.channel)
async def ping_command(client, message: Message):
    lang = await get_user_language(message.from_user.id)
    reply_temp = get_message(lang, "PING")
    reply_final = get_message(lang, "PING_FINAL")

    start = time.time()
    sent = await message.reply(reply_temp)
    end = time.time()

    ping = round((end - start) * 1000, 3)
    uptime = get_readable_time(time.time() - BOT_START_TIME)

    await sent.edit_text(
        reply_final.format(
            uptime=uptime,
            ping=ping
        )
    )

@app.on_message(filters.command("alive") & ~filters.channel)
async def alive_command(client, message: Message):
    lang = await get_user_language(message.from_user.id)
    reply_temp = get_message(lang, "ALIVE")
    reply_final = get_message(lang, "ALIVE_FINAL")

    start = time.time()
    sent = await message.reply(reply_temp)
    end = time.time()

    ping = round((end - start) * 1000, 3)
    uptime = get_readable_time(time.time() - BOT_START_TIME)

    await sent.edit_text(
        reply_final.format(
            uptime=uptime,
            ping=ping
        )
    )

@app.on_message(filters.command("stats") & ~filters.channel)
async def stats_command(client, message: Message):
    lang = await get_user_language(message.from_user.id)
    stats_text = get_message(lang, "BOT_STATS")

    total_users = await users_collection.count_documents({})
    total_groups = await groups_col.count_documents({})

    await message.reply(
        stats_text.format(users=total_users, groups=total_groups)
    )
