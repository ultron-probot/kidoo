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
from EsproMusic.utils.inline import help_pannel, private_panel, start_panel
from config import BANNED_USERS
from strings import get_string

# 🎉 Emoji list for animation
START_EMOJIS = ["❤️", "🎉", "🔥", "👍", "🎉", "❤️‍🔥", "🥀"]

# 🩵 Sticker ID (replace with your own)
START_STICKER_ID = "CAACAgQAAxkBAAEPdj9o2EvRFqZ01s_xNklm_7B93Vys3wACIBYAAuE4MVPgVvqrgdxUTDYE"


@app.on_message(filters.command(["start"]) & filters.private & ~BANNED_USERS)
@LanguageStart
async def start_pm(client, message: Message, _):
    await add_served_user(message.from_user.id)

    # ────────── Handle /start with args ──────────
    if len(message.text.split()) > 1:
        name = message.text.split(None, 1)[1]
        if name[0:4] == "help":
            keyboard = help_pannel(_)
            return await message.reply_photo(
                photo=config.START_IMG_URL,
                caption=_["help_1"].format(config.SUPPORT_CHAT),
                reply_markup=keyboard,
            )
        if name[0:3] == "sud":
            await sudoers_list(client=client, message=message, _=_)
            if await is_on_off(2):
                return await app.send_message(
                    chat_id=config.LOGGER_ID,
                    text=f"{message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ ᴛᴏ ᴄʜᴇᴄᴋ <b>sᴜᴅᴏʟɪsᴛ</b>.\n\n<b>ᴜsᴇʀ ɪᴅ :</b> <code>{message.from_user.id}</code>\n<b>ᴜsᴇʀɴᴀᴍᴇ :</b> @{message.from_user.username}",
                )
            return
        if name[0:3] == "inf":
            m = await message.reply_text("🔎")
            query = (str(name)).replace("info_", "", 1)
            query = f"https://www.youtube.com/watch?v={query}"
            results = VideosSearch(query, limit=1)
            for result in (await results.next())["result"]:
                title = result["title"]
                duration = result["duration"]
                views = result["viewCount"]["short"]
                thumbnail = result["thumbnails"][0]["url"].split("?")[0]
                channellink = result["channel"]["link"]
                channel = result["channel"]["name"]
                link = result["link"]
                published = result["publishedTime"]
            searched_text = _["start_6"].format(
                title, duration, views, published, channellink, channel, app.mention
            )
            key = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text=_["S_B_8"], url=link),
                        InlineKeyboardButton(text=_["S_B_9"], url=config.SUPPORT_CHAT),
                    ],
                ]
            )
            await m.delete()
            await app.send_photo(
                chat_id=message.chat.id,
                photo=thumbnail,
                caption=searched_text,
                reply_markup=key,
            )
            if await is_on_off(2):
                return await app.send_message(
                    chat_id=config.LOGGER_ID,
                    text=f"{message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ ᴛᴏ ᴄʜᴇᴄᴋ <b>ᴛʀᴀᴄᴋ ɪɴғᴏʀᴍᴀᴛɪᴏɴ</b>.\n\n<b>ᴜsᴇʀ ɪᴅ :</b> <code>{message.from_user.id}</code>\n<b>ᴜsᴇʀɴᴀᴍᴇ :</b> @{message.from_user.username}",
)

# ────────── Normal /start ──────────
    else:
        # 🩵 Sticker first
        sticker_msg = await message.reply_sticker(START_STICKER_ID)
        await asyncio.sleep(2)
        await sticker_msg.delete()

        # 📌 Main start image + caption + buttons
        out = private_panel(_)
        caption_text = _["start_2"].format(message.from_user.mention, app.mention)
        start_msg = await message.reply_photo(
            photo=config.START_IMG_URL,
            caption=caption_text,
            reply_markup=InlineKeyboardMarkup(out),
        )

        # ✨ Emoji animation — caption edit + buttons फिर से pass करना जरूरी!
        for _i in range(3):
            await asyncio.sleep(0.5)
            emoji = random.choice(START_EMOJIS)
            await start_msg.edit_caption(
                f"{caption_text} {emoji}",
                reply_markup=InlineKeyboardMarkup(out),
            )

        # 📢 Logger
        if await is_on_off(2):
            return await app.send_message(
                chat_id=config.LOGGER_ID,
                text=f"{message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ.\n\n<b>ᴜsᴇʀ ɪᴅ :</b> <code>{message.from_user.id}</code>\n<b>ᴜsᴇʀɴᴀᴍᴇ :</b> @{message.from_user.username}",
            )


@app.on_message(filters.command(["start"]) & filters.group & ~BANNED_USERS)
@LanguageStart
async def start_gp(client, message: Message, _):
    out = start_panel(_)
    uptime = int(time.time() - _boot_)
    await message.reply_photo(
        photo=config.START_IMG_URL,
        caption=_["start_1"].format(app.mention, get_readable_time(uptime)),
        reply_markup=InlineKeyboardMarkup(out),
    )
    return await add_served_chat(message.chat.id)


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

                out = start_panel(_)
                await message.reply_photo(
                    photo=config.START_IMG_URL,
                    caption=_["start_3"].format(
                        message.from_user.first_name,
                        app.mention,
                        message.chat.title,
                        app.mention,
                    ),
                    reply_markup=InlineKeyboardMarkup(out),
                )
                await add_served_chat(message.chat.id)
                await message.stop_propagation()
        except Exception as ex:
            print(ex)

# (Ankit Event)
@app.on_message(filters.new_chat_members, group=1)
async def bot_added_log(client, message: Message):
    for member in message.new_chat_members:
        if member.id == app.id:
            chat = message.chat
            adder = message.from_user

            chat_title = chat.title
            chat_id = chat.id
            chat_username = f"https://t.me/{chat.username}" if chat.username else "No Public Link"
            adder_name = adder.mention if adder else "Unknown"
            adder_id = adder.id if adder else "N/A"
            adder_username = f"@{adder.username}" if adder and adder.username else "No Username"

            from pyrogram.enums import ParseMode

text = (
    f"😜 <b>𝐁𝐨𝐭 𝐀𝐝𝐝𝐞𝐝 𝐭𝐨 𝐚 𝐆𝐫𝐨𝐮𝐩</b>\n\n"
    f"❤️‍🔥 <b>ᴄʜᴀᴛ ɴᴀᴍᴇ:</b> {chat_title}\n"
    f"🔥 <b>ᴄʜᴀᴛ ɪᴅ:</b> <code>{chat_id}</code>\n"
    f"✅ <b>ᴄʜᴀᴛ ʟɪɴᴋ:</b> {chat_username}\n\n"
    f"🎉 <b>ᴜsᴇʀ :</b> {adder_name}\n"
    f"😍 <b>ᴜsᴇʀ ɪᴅ :</b> <code>{adder_id}</code>\n"
    f"😘 <b>ᴜsᴇʀ ɴᴀᴍᴇ:</b> {adder_username}\n\n"
    f"🥂 <b>𝐂𝐫𝐞𝐚𝐭𝐨𝐫:-</b> <a href='https://t.me/GonnaAgree'>𝜻 • 𝐊 ᴀ ʀ ᴛ ɪ ᴋ</a>"
)

try:
    await app.send_message(
        chat_id=config.LOGGER_ID,
        text=text,
        parse_mode=ParseMode.HTML,  # ✅ Enum use किया गया
        disable_web_page_preview=True
    )
except Exception as e:
    print(f"Logger Error (bot_added_log): {e}")
#  (Ankit Event)
@app.on_message(filters.left_chat_member, group=1)
async def bot_removed_log(client, message: Message):
    if message.left_chat_member.id == app.id:
        chat = message.chat
        remover = message.from_user

        chat_title = chat.title
        chat_id = chat.id
        chat_username = f"https://t.me/{chat.username}" if chat.username else "No Public Link"
        remover_name = remover.mention if remover else "Unknown"
        remover_id = remover.id if remover else "N/A"
        remover_username = f"@{remover.username}" if remover and remover.username else "No Username"

        from pyrogram.enums import ParseMode

text = (
    f"🥺 <b>𝔹𝕠𝕥 ℝ𝕖𝕞𝕠𝕧𝕖𝕕 𝔽𝕣𝕠𝕞 𝕒 𝔾𝕣𝕠𝕦𝕡</b>\n\n"
    f"❤️‍🔥 <b>ᴄʜᴀᴛ ɴᴀᴍᴇ:</b> {chat_title}\n"
    f"❤️‍🔥 <b>ᴄʜᴀᴛ ɪᴅ:</b> <code>{chat_id}</code>\n"
    f"🔗 <b>ᴄʜᴀᴛ ʟɪɴᴋ:</b> {chat_username}\n\n"
    f"💔 <b>ᴜsᴇʀ:</b> {remover_name}\n"
    f"💔 <b>ᴜsᴇʀ ɪᴅ:</b> <code>{remover_id}</code>\n"
    f"💔 <b>ᴜsᴇʀ ɴᴀᴍᴇ:</b> {remover_username}\n\n"
    f"🥂 <b>𝐂𝐫𝐞𝐚𝐭𝐨𝐫:-</b> <a href='https://t.me/GonnaAgree'>𝜻 • 𝐊 ᴀ ʀ ᴛ ɪ ᴋ</a>"
)

try:
    await app.send_message(
        chat_id=config.LOGGER_ID,
        text=text,
        parse_mode=ParseMode.HTML,  # ✅ Enum इस्तेमाल किया गया
        disable_web_page_preview=True
    )
except Exception as e:
    print(f"Logger Error (bot_removed_log): {e}")








