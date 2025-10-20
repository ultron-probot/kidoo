import asyncio
import importlib
from pyrogram import idle
from pytgcalls.exceptions import NoActiveGroupCall

import config
from EsproMusic import LOGGER, app, userbot
from EsproMusic.core.call import Loy
from EsproMusic.misc import sudo
from EsproMusic.plugins import ALL_MODULES
from EsproMusic.utils.database import get_banned_users, get_gbanned
from EsproMusic.modules.tagger import register_tagger  # ✅ Tagger import
from config import BANNED_USERS


async def init():
    # 🔹 Check assistant clients
    if not any([config.STRING1, config.STRING2, config.STRING3, config.STRING4, config.STRING5]):
        LOGGER(__name__).error("Assistant client variables not defined, exiting...")
        exit()

    await sudo()

    # 🔹 Load banned users
    try:
        for user_id in await get_gbanned():
            BANNED_USERS.add(user_id)
        for user_id in await get_banned_users():
            BANNED_USERS.add(user_id)
    except Exception as e:
        LOGGER("EsproMusic").warning(f"Error while fetching banned users: {e}")

    # 🔹 Start Pyrogram app
    await app.start()

    # 🔹 Register Tagger feature (without SUDO_USERS)
    register_tagger(app)

    # 🔹 Import all plugin modules safely
    for all_module in ALL_MODULES:
        if not all_module.strip():
            continue
        try:
            importlib.import_module(f"EsproMusic.plugins.{all_module}")
        except Exception as e:
            LOGGER("EsproMusic.plugins").warning(f"Failed to import {all_module}: {e}")
    LOGGER("EsproMusic.plugins").info("✅ Successfully Imported Modules...")

    # 🔹 Start userbot and main call client
    await userbot.start()
    await Loy.start()

    # 🔹 Stream test audio/video
    try:
        await Loy.stream_call("https://te.legra.ph/file/29f784eb49d230ab62e9e.mp4")
    except NoActiveGroupCall:
        LOGGER("EsproMusic").error("Please turn on the videochat of your log group/channel.\n\nStopping Bot...")
        exit()
    except Exception as e:
        LOGGER("EsproMusic").warning(f"Error during call stream: {e}")

    # 🔹 Start decorators and idle mode
    await Loy.decorators()
    LOGGER("EsproMusic").info("✅ EsproMusicBot Started Successfully with Tagger System\nSupport: @EsproSupport")

    await idle()
    await app.stop()
    await userbot.stop()
    LOGGER("EsproMusic").info("Stopping Espro Music Bot...")


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(init())
