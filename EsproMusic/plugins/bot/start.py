import time
import asyncio
import random

from pyrogram import filters
from pyrogram.enums import ChatType
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from youtubesearchpython.__future__ import VideosSearch

import config
from EsproMusic import app
from EsproMusic.misc import _boot_
from EsproMusic.plugins.sudo.sudoers import sudoers_list
from EsproMusic.utils.database import (
    add_served_chat,
    add_served_user,
    blacklisted_chats,
    get_lang,
    is_banned_user,
    is_on_off,
)
from EsproMusic.utils.decorators.language import LanguageStart
from EsproMusic.utils.formatters import get_readable_time
from strings import get_string

# 🎉 Emoji list for animation effect
START_EMOJIS = ["❤️", "🎉", "🔥", "👍"]

# 🩵 Sticker ID
START_STICKER_ID = "CAACAgQAAxkBAAEPdj9o2EvRFqZ01s_xNklm_7B93Vys3wACIBYAAuE4MVPgVvqrgdxUTDYE"

# 🔘 Private panel buttons
def private_panel(_):
    buttons = [
        [
            InlineKeyboardButton(
                text=_["S_B_1"], url=f"https://t.me/{app.username}?startgroup=true"
            ),
        ],
        [
            InlineKeyboardButton(text=_["S_B_2"], url=config.SUPPORT_CHAT),
            InlineKeyboardButton(text=_["S_B_3"], url=config.CHANNEL),
        ],
        [
            InlineKeyboardButton(text=_["S_B_4"], callback_data="settings_back_helper"),
        ],
        [
            InlineKeyboardButton(text=_["S_B_5"], user_id=config.OWNER_ID),
        ],
    ]
    return buttons

# ================= PRIVATE START =================
@app.on_message(filters.command(["start"]) & filters.private & ~config.BANNED_USERS)
@LanguageStart
async def start_pm(client, message: Message, _):
    await add_served_user(message.from_user.id)

    # 📝 Start message pehle bhejna (sticker se pehle)
    caption_text = _["start_2"].format(message.from_user.mention, app.mention)
    out = private_panel(_)
    start_msg = await message.reply_photo(
        photo=config.START_IMG_URL,
        caption=caption_text,
        reply_markup=InlineKeyboardMarkup(out),
    )

    # 🎉 Emoji animation under caption
    for _ in range(3):
        await asyncio.sleep(0.5)
        emoji = random.choice(START_EMOJIS)
        await start_msg.edit_caption(f"{caption_text} {emoji}")

    # ✨ Sticker bhejna aur delete karna
    sticker_msg = await message.reply_sticker(START_STICKER_ID)
    await asyncio.sleep(2.5)
    await sticker_msg.delete()

    # 📢 Logger
    if await is_on_off(2):
        await app.send_message(
            chat_id=config.LOGGER_ID,
            text=f"{message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ.\n\n<b>ᴜsᴇʀ ɪᴅ :</b> <code>{message.from_user.id}</code>\n<b>ᴜsᴇʀɴᴀᴍᴇ :</b> @{message.from_user.username}",
        )

# ================= GROUP START =================
@app.on_message(filters.command(["start"]) & filters.group & ~config.BANNED_USERS)
@LanguageStart
async def start_gp(client, message: Message, _):
    uptime = int(time.time() - _boot_)
    buttons = [
        [
            InlineKeyboardButton(
                text=_["S_B_1"], url=f"https://t.me/{app.username}?startgroup=true"
            ),
        ],
        [
            InlineKeyboardButton(text=_["S_B_2"], url=config.SUPPORT_CHAT),
            InlineKeyboardButton(text=_["S_B_3"], url=config.CHANNEL),
        ],
    ]
    await message.reply_photo(
        photo=config.START_IMG_URL,
        caption=_["start_1"].format(app.mention, get_readable_time(uptime)),
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    await add_served_chat(message.chat.id)

# ================= WELCOME NEW MEMBERS =================
@app.on_message(filters.new_chat_members, group=-1)
async def welcome(client, message: Message):
    for member in message.new_chat_members:
        try:
            language = await get_lang(message.chat.id)
            _ = get_string(language)
            if await is_banned_user(member.id):
                try:
                    await message.chat.ban_member(member.id)
                except:
                    pass
            if member.id == app.id:
                if message.chat.type != ChatType.SUPERGROUP:
                    await message.reply_text(_["start_4"])
                    return await app.leave_chat(message.chat.id)
                if message.chat.id in await blacklisted_chats():
                    await message.reply_text(
                        _["start_5"].format(
                            app.mention,
                            f"https://t.me/{app.username}?start=sudolist",
                            config.SUPPORT_CHAT,
                        ),
                        disable_web_page_preview=True,
                    )
                    return await app.leave_chat(message.chat.id)

                buttons = private_panel(_)
                await message.reply_photo(
                    photo=config.START_IMG_URL,
                    caption=_["start_3"].format(
                        message.from_user.first_name,
                        app.mention,
                        message.chat.title,
                        app.mention,
                    ),
                    reply_markup=InlineKeyboardMarkup(buttons),
                )
                await add_served_chat(message.chat.id)
                await message.stop_propagation()
        except Exception as ex:
            print(ex)
