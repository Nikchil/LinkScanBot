import time
from datetime import timedelta

from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import ChatAdminRequired
from pyrogram.enums import ChatMembersFilter, ChatMemberStatus

from config import OWNER_ID, LOG_CHANNEL, BOT_NAME
from utils.sudo import is_sudo
from database.core import (
    refresh_memory_cache,
    get_served_users,
    get_served_chats,
    add_served_user,
    add_served_chat,
    set_bio_scan,
    get_bio_scan,
    add_to_whitelist,
    remove_from_whitelist,
    get_all_whitelist,
)

BOT_START_TIME = time.time()
BOT_USERNAME = "BioLinkRemoverBot"

BROADCAST_STATUS = {
    "active": False,
    "sent": 0,
    "failed": 0,
    "total": 0,
    "start_time": 0,
    "users": 0,
    "chats": 0,
    "sent_users": 0,
    "sent_chats": 0,
    "mode": "",
}

def init(app):
    @app.on_message(filters.command("start") & filters.private)
    async def start_command(client, message: Message):
        user = message.from_user
        await add_served_user(user.id)
        
        start_text = (
            f"👋 <b>Hello {user.first_name}!</b>\n\n"
            f"I'm <b>{BOT_NAME}</b>, here to help moderate your groups by scanning bios for unwanted links.\n\n"
            "<b>Main Features:</b>\n"
            "• Auto-detect links in user bios\n"
            "• Customizable warning system\n"
            "• Whitelist trusted users\n\n"
            "Add me to your group and promote me to admin to get started!"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")],
            [InlineKeyboardButton("⚙️ Help", callback_data="help")]
        ])
        
        await message.reply(start_text, reply_markup=keyboard)
        
        if LOG_CHANNEL:
            await client.send_message(
                LOG_CHANNEL,
                f"🆕 <b>New User Started Bot</b>\n"
                f"👤 <a href='tg://user?id={user.id}'>{user.first_name}</a>\n"
                f"🆔 ID: <code>{user.id}</code>\n"
                f"📅 {message.date.strftime('%Y-%m-%d %H:%M')}"
            )

    @app.on_message(filters.command("") & filters.text)
    async def log_all_commands(client, message: Message):
        if not LOG_CHANNEL or not message.from_user:
            return

        user = message.from_user
        user_mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
        origin = "🗣 <b>Group</b>" if message.chat.type in ["group", "supergroup"] else "👤 <b>Private</b>"
        chat_info = f"\n👥 <b>Chat:</b> <code>{message.chat.title}</code>" if message.chat.title else ""

        await client.send_message(
            LOG_CHANNEL,
            f"📥 <b>Command Used</b>\n"
            f"{origin}{chat_info}\n"
            f"👤 <b>User:</b> {user_mention} (`{user.id}`)\n"
            f"💬 <b>Command:</b> <code>{message.text}</code>"
        )

    @app.on_message(filters.command("ping"))
    async def ping(_, message: Message):
        start = time.time()
        sent = await message.reply("🏓 Pinging...")
        end = time.time()
        latency = round((end - start) * 1000)
        uptime = str(timedelta(seconds=int(time.time() - BOT_START_TIME)))

        await refresh_memory_cache()

        await sent.edit_text(
            f"🏓 <b>Bot Status</b>\n"
            f"📶 <b>Ping:</b> <code>{latency}ms</code>\n"
            f"⏱ <b>Uptime:</b> <code>{uptime}</code>\n"
            f"🤖 <b>Bot:</b> @{BOT_USERNAME}"
        )

    @app.on_message(filters.command("refresh"))
    async def refresh_cmd(_, message: Message):
        if not await is_sudo(message.from_user.id):
            return await message.reply("🚫 You are not allowed to do this.")
        
        await refresh_memory_cache()
        await message.reply("🔄 <b>System Synced</b>\nAll data refreshed and up-to-date.")
        
        if LOG_CHANNEL:
            await _.send_message(
                LOG_CHANNEL,
                f"♻️ <b>Memory Cache Refreshed</b>\n"
                f"👤 <a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"
            )

    @app.on_message(filters.command("admincache") & filters.group)
    async def admin_cache_cmd(client, message: Message):
        if not await is_sudo(message.from_user.id):
            return await message.reply("🚫 You are not allowed to do this.")
        
        try:
            members = []
            async for member in client.get_chat_members(message.chat.id, filter=ChatMembersFilter.ADMINISTRATORS):
                members.append(member.user.id)

            await refresh_memory_cache()

            await message.reply(
                f"👥 <b>Admin List Refreshed</b>\n"
                f"Total admins synced: <code>{len(members)}</code>"
            )
            
            if LOG_CHANNEL:
                await client.send_message(
                    LOG_CHANNEL,
                    f"🔁 <b>AdminCache Updated</b>\n"
                    f"👤 By: <a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>\n"
                    f"👥 Group: <code>{message.chat.title}</code>\n"
                    f"👮 Admins Synced: <code>{len(members)}</code>"
                )
        except ChatAdminRequired:
            await message.reply("❌ I need admin rights to view admin list.")

    @app.on_message(filters.command("biolink") & filters.group)
    async def toggle_biolink(_, message: Message):
        user_id = message.from_user.id
        chat_id = message.chat.id

        try:
            member = await _.get_chat_member(chat_id, user_id)
            if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
                return await message.reply("🚫 You must be a group admin to use this.")
        except ChatAdminRequired:
            return await message.reply("❌ I need admin rights to check your status.")

        args = message.text.split(None, 1)
        if len(args) == 1:
            return await message.reply("Usage: /biolink enable | disable")

        choice = args[1].lower().strip()
        if choice == "enable":
            await set_bio_scan(chat_id, True)
            await message.reply("✅ Bio link scanning has been enabled in this group.")
        elif choice == "disable":
            await set_bio_scan(chat_id, False)
            await message.reply("❌ Bio link scanning has been disabled in this group.")
        else:
            await message.reply("Usage: /biolink enable | disable")

    @app.on_message(filters.command("allow") & filters.group)
    async def allow_user(_, message: Message):
        if not await is_sudo(message.from_user.id):
            return await message.reply("🚫 You don't have permission to do this.")

        user = None
        if message.reply_to_message:
            user = message.reply_to_message.from_user
        elif len(message.command) > 1:
            query = message.command[1]
            if query.startswith("@"):
                try:
                    user = await _.get_users(query)
                except:
                    return await message.reply("❌ Could not find that username.")
            else:
                try:
                    user = await _.get_users(int(query))
                except:
                    return await message.reply("❌ Invalid user ID.")
        
        if not user:
            return await message.reply(
                "ℹ️ Reply to a user or provide a username/user ID.\nUsage:\n<code>/allow @username</code>\n<code>/allow 123456789</code>",
                quote=True
            )

        await add_to_whitelist(user.id)
        await message.reply(f"✅ <b>{user.first_name}</b> has been whitelisted from bio scans.")

    @app.on_message(filters.command("remove") & filters.group)
    async def remove_user(_, message: Message):
        if not await is_sudo(message.from_user.id):
            return await message.reply("🚫 You don't have permission to do this.")

        user = None
        if message.reply_to_message:
            user = message.reply_to_message.from_user
        elif len(message.command) > 1:
            query = message.command[1]
            if query.startswith("@"):
                try:
                    user = await _.get_users(query)
                except:
                    return await message.reply("❌ Could not find that username.")
            else:
                try:
                    user = await _.get_users(int(query))
                except:
                    return await message.reply("❌ Invalid user ID.")
        
        if not user:
            return await message.reply(
                "ℹ️ Reply to a user or provide a username/user ID.\nUsage:\n<code>/remove @username</code>\n<code>/remove 123456789</code>",
                quote=True
            )

        await remove_from_whitelist(user.id)
        await message.reply(f"❌ <b>{user.first_name}</b> has been removed from the whitelist.")

    @app.on_message(filters.command("freelist") & filters.group)
    async def list_whitelisted(_, message: Message):
        users = await get_all_whitelist()
        if not users:
            return await message.reply("📝 Whitelist is currently empty.")
        formatted = "\n".join([f"• <code>{uid}</code>" for uid in users])
        await message.reply(f"<b>Whitelisted Users:</b>\n{formatted}")

    @app.on_chat_member_updated()
    async def save_group(_, chat_member):
        await add_served_chat(chat_member.chat.id)

    @app.on_message(filters.private & ~filters.service)
    async def save_user(_, message: Message):
        await add_served_user(message.from_user.id)
        if LOG_CHANNEL:
            await _.send_message(
                LOG_CHANNEL,
                f"👤 <b>New User Started Bot</b>\n"
                f"🆔 ID: <code>{message.from_user.id}</code>\n"
                f"👤 Name: <a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"
            )
