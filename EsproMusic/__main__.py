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
from config import BANNED_USERS

# ✅ Tagger module import
from EsproMusic.modules.tagger import register_tagger


async def init():
    # ✅ Check assistant string vars
    if (
        not config.STRING1
        and not config.STRING2
        and not config.STRING3
        and not config.STRING4
        and not config.STRING5
    ):
        LOGGER(__name__).error("Assistant client variables not defined, exiting...")
        exit()

    await sudo()

    # ✅ Fetch banned users
    try:
        users = await get_gbanned()
        for user_id in users:
            BANNED_USERS.add(user_id)

        users = await get_banned_users()
        for user_id in users:
            BANNED_USERS.add(user_id)
    except Exception as e:
        LOGGER("EsproMusic").warning(f"Error while fetching banned users: {e}")

    # ✅ Start main bot
    await app.start()

    # ✅ Register Tagger feature
    register_tagger(app, SUDO_USERS=set())

    # ✅ Load all plugins dynamically
    for all_module in ALL_MODULES:
        importlib.import_module("EsproMusic.plugins." + all_module)
    LOGGER("EsproMusic.plugins").info("Successfully Imported Modules...")

    # ✅ Start userbot and main call client
    await userbot.start()
    await Loy.start()

    # ✅ Test audio stream (used to keep voice chat active)
    try:
        await Loy.stream_call("https://te.legra.ph/file/29f784eb49d230ab62e9e.mp4")
    except NoActiveGroupCall:
        LOGGER("EsproMusic").error(
            "Please turn on the videochat of your log group/channel.\n\nStopping Bot..."
        )
        exit()
    except Exception as e:
        LOGGER("EsproMusic").warning(f"Error during call stream: {e}")

    await Loy.decorators()
    LOGGER("EsproMusic").info(
        "✅ EsproMusic Bot Started Successfully with Tagger System\nSupport: @KomalMusicUpdate"
    )

    # ✅ Keep bot running
    await idle()

    # ✅ Cleanup when stopped
    await app.stop()
    await userbot.stop()
    LOGGER("EsproMusic").info("Stopping Espro Music Bot...")


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(init())
