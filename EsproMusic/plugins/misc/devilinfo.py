import os
import uuid
import random
import asyncio
from typing import Union, Optional

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from pyrogram import filters, enums
from pyrogram.types import Message
from EsproMusic import app
# ------------------------------------------------------------------------

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
BG_PATH = os.path.join(ASSETS_DIR, "userinfo.png")     # background image
FONT_PATH = os.path.join(ASSETS_DIR, "hiroko.ttf")    # your devil.ttf 
# -------------------------------------------------------------------------

# fallback remote images if user has no profile pic
RANDOM_PHOTOS = [
    "https://telegra.ph/file/1949480f01355b4e87d26.jpg",
    "https://telegra.ph/file/3ef2cc0ad2bc548bafb30.jpg",
    "https://telegra.ph/file/a7d663cd2de689b811729.jpg",
    "https://telegra.ph/file/6f19dc23847f5b005e922.jpg",
    "https://telegra.ph/file/2973150dd62fd27a3a6ba.jpg",
]

# output temp directory (will be created automatically)
TEMP_DIR = os.path.join(os.path.dirname(__file__), "..", "temp_userinfo")
os.makedirs(TEMP_DIR, exist_ok=True)


def _get_font(size: int):
    """Try to load provided TTF; fallback to default PIL font."""
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()


def _make_circular(im: Image.Image) -> Image.Image:
    """Return circular-cropped RGBA image."""
    im = im.convert("RGBA")
    size = im.size
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse([(0, 0), size], fill=255)
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.paste(im, (0, 0), mask)
    return out


def _resize_aspect_fit(max_w: int, max_h: int, image: Image.Image) -> Image.Image:
    """Resize while keeping aspect ratio, fitting inside (max_w, max_h)."""
    img_w, img_h = image.size
    ratio = min(max_w / img_w, max_h / img_h)
    new_size = (int(img_w * ratio), int(img_h * ratio))
    return image.resize(new_size, Image.LANCZOS)


async def _download_profile_photo(file_id: str) -> Optional[str]:
    """Download profile photo via app.download_media and return local path or None."""
    try:
        # unique temp filename
        local_name = os.path.join(TEMP_DIR, f"profile_{uuid.uuid4().hex}.jpg")
        path = await app.download_media(file_id, file_name=local_name)
        return path
    except Exception:
        return None


async def _generate_image_for_user(
    user_id: Union[int, str],
    profile_path: Optional[str] = None,
    bg_path: str = BG_PATH,
    font_path: str = FONT_PATH,
) -> str:
    """
    Compose final userinfo image and return filepath.
    - profile_path: local path to profile pic (optional)
    """
    # unique output name
    out_path = os.path.join(TEMP_DIR, f"userinfo_{user_id}_{uuid.uuid4().hex}.png")

    # Open background
    try:
        bg = Image.open(bg_path).convert("RGBA")
    except Exception:
        # If background missing, create a blank one
        bg = Image.new("RGBA", (1280, 720), (18, 18, 18, 255))

    draw = ImageDraw.Draw(bg)

    # Paste circular profile if provided
    if profile_path and os.path.exists(profile_path):
        try:
            with Image.open(profile_path).convert("RGBA") as p:
                circ = _make_circular(p)
                circ = _resize_aspect_fit(400, 400, circ)
                # position - adjust if your bg is different
                pos_x = 440
                pos_y = 160
                bg.paste(circ, (pos_x, pos_y), circ)
        except Exception:
            pass

    # Draw user id placeholder (you can change coordinates/font sizes)
    try:
        font_large = ImageFont.truetype(font_path, 46)
    except Exception:
        font_large = _get_font(46)
    try:
        font_small = ImageFont.truetype(font_path, 30)
    except Exception:
        font_small = _get_font(30)

    # default positions (these match the template described earlier)
    txt_x = 529
    txt_y = 627
    draw.text((txt_x, txt_y), str(user_id).upper(), font=font_large, fill=(255, 255, 255, 255))

    # Save
    bg.save(out_path)
    return out_path


# ---------------------------
# Random caption templates
# ---------------------------
_INFO_TEMPLATES = [
    """**
❅─────✧❅✦❅✧─────❅
            ✦ ᴜsᴇʀ ɪɴғᴏ ✦

➻ ᴜsᴇʀ ɪᴅ ‣ **`{id}`**
**➻ ғɪʀsᴛ ɴᴀᴍᴇ ‣ **{first}
**➻ ʟᴀsᴛ ɴᴀᴍᴇ ‣ **{last}
**➻ ᴜsᴇʀɴᴀᴍᴇ ‣ **`{username}`
**➻ ᴍᴇɴᴛɪᴏɴ ‣ **{mention}
**➻ ʟᴀsᴛ sᴇᴇɴ ‣ **{status}
**➻ ᴅᴄ ɪᴅ ‣ **{dc}
**➻ ʙɪᴏ ‣ **`{bio}`

**❅─────✧❅✦❅✧─────❅**
""",
    """╔══❀•°❀°•❀══╗
      𝙐𝙎𝙀𝙍 𝙄𝙉𝙁𝙊
╚══❀•°❀°•❀══╝

• 𝐔𝐬𝐞𝐫 𝐈𝐃 » `{id}`
• 𝐅𝐢𝐫𝐬𝐭 𝐍𝐚𝐦𝐞 » {first}
• 𝐋𝐚𝐬𝐭 𝐍𝐚𝐦𝐞 » {last}
• 𝐔𝐬𝐞𝐫𝐧𝐚𝐦𝐞 » `{username}`
• 𝐌𝐞𝐧𝐭𝐢𝐨𝐧 » {mention}
• 𝐋𝐚𝐬𝐭 𝐒𝐞𝐞𝐧 » {status}
• 𝐃𝐂 𝐈𝐃 » {dc}
• 𝐁𝐢𝐨 » `{bio}`

╔══❀•°❀°•❀══╗
""",
    """┌────────────────────┐
       ＵＳＥＲ ＩＮＦＯ
└────────────────────┘

> User ID: `{id}`
> First Name: {first}
> Last Name: {last}
> Username: `{username}`
> Mention: {mention}
> Last Seen: {status}
> DC ID: {dc}
> Bio: `{bio}`

┌────────────────────┐
""",
    """🌸───・✧ ✦ ✧・───🌸
          ᴜsᴇʀ ᴘʀᴏꜰɪʟᴇ
🌸───・✧ ✦ ✧・───🌸

🔹 ɪᴅ: `{id}`
🔹 ꜰɪʀꜱᴛ ɴᴀᴍᴇ: {first}
🔹 ʟᴀꜱᴛ ɴᴀᴍᴇ: {last}
🔹 ᴜsᴇʀɴᴀᴍᴇ: `{username}`
🔹 ᴍᴇɴᴛɪᴏɴ: {mention}
🔹 ʟᴀsᴛ sᴇᴇɴ: {status}
🔹 ᴅᴄ ɪᴅ: {dc}
🔹 ʙɪᴏ: `{bio}`

🌸───・✧ ✦ ✧・───🌸
""",
    """✧･ﾟ: *✧･ﾟ:*  𝐔𝐒𝐄𝐑 𝐈𝐍𝐅𝐎  *:･ﾟ✧*:･ﾟ✧

➤ User ID » `{id}`
➤ First Name » {first}
➤ Last Name » {last}
➤ Username » `{username}`
➤ Mention » {mention}
➤ Last Seen » {status}
➤ DC ID » {dc}
➤ Bio » `{bio}`

✧･ﾟ: *✧･ﾟ:* ✧*:･ﾟ✧*:･ﾟ✧
""",
    """┏━━━━ User Info ━━━━┓

• ID: `{id}`
• First: {first}
• Last: {last}
• Username: `{username}`
• Mention: {mention}
• Last Seen: {status}
• DC ID: {dc}
• Bio: `{bio}`

┗━━━━━━━━━━━━━━━━━━┛
""",
    """✦••┈┈••✦ 𝐔𝐒𝐄𝐑 𝐈𝐍𝐅𝐎 ✦••┈┈••✦

👑 ID: `{id}`
👑 First Name: {first}
👑 Last Name: {last}
👑 Username: `{username}`
👑 Mention: {mention}
👑 Last Seen: {status}
👑 DC ID: {dc}
👑 Bio: `{bio}`

✦••┈┈••✦
"""
]


def get_random_info_caption(
    id: Union[int, str],
    first: str,
    last: str,
    username: str,
    mention: str,
    status: str,
    dc: Union[int, str],
    bio: str,
) -> str:
    """
    Selects random template and formats it with provided fields.
    """
    tpl = random.choice(_INFO_TEMPLATES)
    # sanitize None -> nice default
    first = first or "No first name"
    last = last or "No last name"
    username = username or "No Username"
    mention = mention or f"[{first}](tg://user?id={id})"
    status = status or "Unknown"
    dc = dc or "N/A"
    bio = bio or "No bio set"

    return tpl.format(
        id=str(id),
        first=str(first),
        last=str(last),
        username=str(username),
        mention=str(mention),
        status=str(status),
        dc=str(dc),
        bio=str(bio),
    )


async def _user_status_text(user_id: int) -> str:
    try:
        user = await app.get_users(user_id)
        status = user.status
        if status == enums.UserStatus.RECENTLY:
            return "Recently."
        if status == enums.UserStatus.LAST_WEEK:
            return "Last week."
        if status == enums.UserStatus.LONG_AGO:
            return "Long time ago."
        if status == enums.UserStatus.OFFLINE:
            return "Offline."
        if status == enums.UserStatus.ONLINE:
            return "Online."
    except Exception:
        return "Unknown"


# ---------------- Command Handler ----------------
@app.on_message(filters.command(["info", "userinfo"], prefixes=["/", "!", ".", "#", "@", "?"]))
async def devil_userinfo_handler(_, message: Message):
    """
    Usage:
    - /info  -> shows info about sender
    - /info <id_or_username> -> shows info for that id/username
    - reply to a message and run /info -> shows info about replied user
    """
    target = message.from_user.id

    # argument provided (and not a reply)
    if not message.reply_to_message and len(message.command) >= 2:
        # accept either numeric id or username (t.me/username)
        arg = message.command[1].strip()
        target = arg

    # reply case
    if message.reply_to_message:
        target = message.reply_to_message.from_user.id

    # gather info
    profile_local = None
    generated_img = None
    try:
        # get_chat returns fields like first_name, last_name, username, bio
        user_chat = await app.get_chat(target)
        user = await app.get_users(target)
        uid = user_chat.id
        dc_id = getattr(user_chat, "dc_id", "N/A")
        first_name = user_chat.first_name or "No first name"
        last_name = user_chat.last_name or "No last name"
        username = user_chat.username or "No Username"
        mention = getattr(user, "mention", f"[{first_name}](tg://user?id={uid})")
        bio = getattr(user_chat, "bio", "No bio set")
        status_text = await _user_status_text(uid)

        # if user has a profile photo, download it
        if getattr(user, "photo", None):
            # big_file_id might be under user.photo.big_file_id
            try:
                file_id = user.photo.big_file_id
            except Exception:
                try:
                    file_id = user.photo.file_id
                except Exception:
                    file_id = None
            if file_id:
                profile_local = await _download_profile_photo(file_id)

        # if no local profile, we will use a remote fallback image
        if not profile_local:
            # pick random fallback URL, Pyrogram can send remote URLs directly
            # but our generator needs a local file for circular crop -> download remote fallback
            # try to download one fallback quickly; if fails, we'll skip circular profile
            try:
                # using app.download_media to fetch remote image to local
                fallback_url = random.choice(RANDOM_PHOTOS)
                profile_local = await app.download_media(fallback_url, file_name=os.path.join(TEMP_DIR, f"fallback_{uuid.uuid4().hex}.jpg"))
            except Exception:
                profile_local = None

        # generate composed image (if profile_local exists, it will be used)
        generated_img = await _generate_image_for_user(uid, profile_path=profile_local)

        # send the image (if local). If generation failed, fallback to sending a remote random image + caption
        caption = get_random_info_caption(uid, first_name, last_name, username, mention, status_text, dc_id, bio)
        if generated_img and os.path.exists(generated_img):
            await app.send_photo(message.chat.id, photo=generated_img, caption=caption, reply_to_message_id=message.id)
        else:
            # fallback: send remote photo (first in list) with caption
            await app.send_photo(message.chat.id, photo=random.choice(RANDOM_PHOTOS), caption=caption, reply_to_message_id=message.id)

    except Exception as e:
        # user-friendly error
        try:
            await message.reply_text(f"Error fetching user info: {e}")
        except:
            pass

    finally:
        # cleanup temp files
        try:
            if profile_local and os.path.exists(profile_local):
                os.remove(profile_local)
        except Exception:
            pass
        try:
            if generated_img and os.path.exists(generated_img):
                os.remove(generated_img)
        except Exception:
            pass
