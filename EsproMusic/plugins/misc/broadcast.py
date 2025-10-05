import asyncio
import time
from datetime import datetime, timedelta

from pyrogram import filters
from pyrogram.enums import ChatMembersFilter
from pyrogram.errors import FloodWait

from EsproMusic import app
from EsproMusic.misc import SUDOERS
from EsproMusic.utils.database import (
    get_active_chats,
    get_authuser_names,
    get_client,
    get_served_chats,
    get_served_users,
)
from EsproMusic.utils.decorators.language import language
from EsproMusic.utils.formatters import alpha_to_int
from config import adminlist, OWNER_ID, MONGO_DB_URI
from motor.motor_asyncio import AsyncIOMotorClient

# 🟡 Permanent Broadcast User ID
PERMANENT_BROADCAST_ID = 6135117014

# 🟡 MongoDB Setup for Premium Users
mongo = AsyncIOMotorClient(MONGO_DB_URI)
premium_db = mongo["EsproMusic"]["PremiumUsers"]

IS_BROADCASTING = False


# ✅ Premium Check
async def is_premium(user_id: int):
    data = await premium_db.find_one({"user_id": user_id})
    if not data:
        return False
    if data["expires_at"] < int(time.time()):
        await premium_db.delete_one({"user_id": user_id})
        return False
    return True


# ✅ Add Premium Helper
async def add_premium_user(user_id: int, days: int):
    expires_at = int(time.time()) + (days * 86400)
    await premium_db.update_one(
        {"user_id": user_id},
        {"$set": {"expires_at": expires_at}},
        upsert=True,
    )


# ✅ Delete Premium Helper
async def delete_premium_user(user_id: int):
    await premium_db.delete_one({"user_id": user_id})


# ✅ List Premium Helper
async def list_premium_users():
    cursor = premium_db.find({})
    result = []
    async for user in cursor:
        remaining = user["expires_at"] - int(time.time())
        if remaining > 0:
            days = remaining // 86400
            result.append((user["user_id"], days))
        else:
            await premium_db.delete_one({"user_id": user["user_id"]})
    return result


# ✅ Broadcast Command
@app.on_message(filters.command("broadcast"))
@language
async def broadcast_handler(client, message, _):
    global IS_BROADCASTING
    user_id = message.from_user.id

    # 🔐 Allow only OWNER, Permanent ID, or Premium users
    if user_id != OWNER_ID and user_id != PERMANENT_BROADCAST_ID and not await is_premium(user_id):
        return await message.reply_text("🥵ʟᴀᴜᴅᴀ ᴄʜᴜsᴇɢᴀ ᴍᴇʀᴀ\nғɪʀ ᴋᴇʀ ᴘʏᴇɢᴀ ʙʀᴏᴀᴅᴄᴀsᴛ 💦")
    if message.reply_to_message:
        x = message.reply_to_message.id
        y = message.chat.id
        query = None
    else:
        if len(message.command) < 2:
            return await message.reply_text(_["broad_2"])
        query = message.text.split(None, 1)[1]

    IS_BROADCASTING = True
    await message.reply_text(_["broad_1"])

    sent = 0
    pin = 0
    schats = await get_served_chats()
    chats = [int(chat["chat_id"]) for chat in schats]

    for i in chats:
        try:
            m = (
                await app.forward_messages(i, y, x)
                if message.reply_to_message
                else await app.send_message(i, text=query)
            )
            if "-pin" in message.text:
                try:
                    await m.pin(disable_notification=True)
                    pin += 1
                except:
                    pass
            elif "-pinloud" in message.text:
                try:
                    await m.pin(disable_notification=False)
                    pin += 1
                except:
                    pass
            sent += 1
            await asyncio.sleep(0.2)
        except FloodWait as fw:
            await asyncio.sleep(fw.value)
        except:
            continue

    try:
        await message.reply_text(_["broad_3"].format(sent, pin))
    except:
        pass

    IS_BROADCASTING = False


# ✅ Add Premium Command
@app.on_message(filters.command("addpremium") & filters.user([OWNER_ID, PERMANENT_BROADCAST_ID]))
async def addpremium_cmd(_, message):
    if len(message.command) < 3:
        return await message.reply_text("➥ʀɪɢʜᴛ ᴡᴀʏ ᴛᴏ ᴜsᴇ ᴄᴏᴍᴍᴀɴᴅ: /addpremium <user_id> <days>")

    try:
        user_id = int(message.command[1])
        days = int(message.command[2])
    except:
        return await message.reply_text("⚠ सही Format में दो: /addpremium 123456789 30")

    await add_premium_user(user_id, days)
    await message.reply_text(f"✅ User `{user_id}` को {days} दिन का Premium दे दिया गया।")


# ✅ Delete Premium Command
@app.on_message(filters.command("delpremium") & filters.user([OWNER_ID, PERMANENT_BROADCAST_ID]))
async def delpremium_cmd(_, message):
    if len(message.command) < 2:
        return await message.reply_text("❌ इस्तेमाल: /delpremium <user_id>")

    try:
        user_id = int(message.command[1])
    except:
        return await message.reply_text("⚠ User ID में सिर्फ नंबर दो।")

    await delete_premium_user(user_id)
    await message.reply_text(f"🗑 User `{user_id}` का Premium हटा दिया गया।")


# ✅ Premium List Command
@app.on_message(filters.command("premiumlist") & filters.user([OWNER_ID, PERMANENT_BROADCAST_ID]))
async def premiumlist_cmd(_, message):
    users = await list_premium_users()
    if not users:
        return await message.reply_text("➥ ᴛʜᴇʀᴇ ᴀʀᴇ ɴᴏ ᴘʀᴇᴍɪᴜᴍ ᴜsᴇʀs ʏᴇᴛ ʙᴀʙʏ🥺")

    text = "⭐ **Premium Users List:**\n\n"
    for uid, days in users:
        text += f"• `{uid}` → {days} \n"

    await message.reply_text(text)


# ✅ Auto Clean Admin List
async def auto_clean():
    while not await asyncio.sleep(10):
        try:
            served_chats = await get_active_chats()
            for chat_id in served_chats:
                if chat_id not in adminlist:
                    adminlist[chat_id] = []
                    async for user in app.get_chat_members(
                        chat_id, filter=ChatMembersFilter.ADMINISTRATORS
                    ):
                        if user.privileges.can_manage_video_chats:
                            adminlist[chat_id].append(user.user.id)
                    authusers = await get_authuser_names(chat_id)
                    for user in authusers:
                        user_id = await alpha_to_int(user)
                        adminlist[chat_id].append(user_id)
        except:
            continue

asyncio.create_task(auto_clean())




