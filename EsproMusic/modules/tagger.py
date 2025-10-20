"""
ESPRO Music Bot - Advanced Tagger Module
----------------------------------------
Features:
- Tag all non-bot members in batches with delay
- Skip left/deleted users automatically
- Stop tagging anytime
- Progress updates
- Fancy natural triggers supported
"""

import asyncio
from typing import Dict, List

from pyrogram import Client, filters
from pyrogram.types import Message, User
from pyrogram.errors import RPCError

from config import OWNER_ID

# Active tagging trackers
_active_taggers: Dict[int, asyncio.Event] = {}
_active_locks: Dict[int, asyncio.Lock] = {}

# ------------------ Utility Functions ------------------

async def is_admin_or_owner(client: Client, chat_id: int, user_id: int) -> bool:
    """Check if user is admin or bot owner."""
    if user_id == OWNER_ID:
        return True
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False

def mention(user: User) -> str:
    """Return inline mention string."""
    name = (user.first_name or "User").replace("@", "")
    return f"[{name}](tg://user?id={user.id})"

async def gather_members(client: Client, chat_id: int) -> List[User]:
    """Get non-bot members, skip left/deleted users."""
    members: List[User] = []
    try:
        async for m in client.get_chat_members(chat_id):
            u = m.user
            if u and not u.is_bot:
                members.append(u)
    except Exception:
        pass
    return members

async def send_batches(client: Client, chat_id: int, batches: List[List[User]], base_text: str, status_message: Message, delay: float):
    """Send tagging messages in batches with status updates."""
    total = sum(len(b) for b in batches)
    done = 0

    for batch in batches:
        stop_event = _active_taggers.get(chat_id)
        if stop_event and stop_event.is_set():
            await status_message.edit_text(status_message.text + "\n\n🛑 Tagging cancelled.")
            return

        mentions = " ".join(mention(u) for u in batch)
        try:
            await client.send_message(chat_id, f"{base_text}\n\n{mentions}", disable_web_page_preview=True)
        except RPCError:
            # fallback: one by one if flood
            for u in batch:
                try:
                    await client.send_message(chat_id, f"{base_text}\n\n{mention(u)}", disable_web_page_preview=True)
                except RPCError:
                    continue

        done += len(batch)
        try:
            await status_message.edit_text(f"{base_text}\n\n✅ Tagged: {done}/{total}")
        except RPCError:
            pass

        await asyncio.sleep(delay)

    try:
        await status_message.edit_text(status_message.text + "\n\n✅ Tagging complete.")
    except RPCError:
        pass

# ------------------ Main Registration ------------------

def register_tagger(app: Client, batch_size: int = 5, delay: float = 1.0):
    
    @app.on_message(filters.command("tagall") & filters.group)
    async def cmd_tagall(client: Client, message: Message):
        chat_id = message.chat.id
        user = message.from_user
        if not user:
            return

        if not await is_admin_or_owner(client, chat_id, user.id):
            await message.reply_text("❌ केवल Admins या Bot Owner इस कमांड का उपयोग कर सकते हैं।")
            return

        if chat_id in _active_locks and _active_locks[chat_id].locked():
            await message.reply_text("⚠️ पहले से टैगिंग प्रक्रिया चल रही है। /tagoff से रोकें।")
            return

        # Determine base text
        if len(message.command) > 1:
            base_text = message.text.split(None, 1)[1]
        elif message.reply_to_message and message.reply_to_message.text:
            base_text = message.reply_to_message.text
        else:
            base_text = "@everyone"

        stop_event = asyncio.Event()
        _active_taggers[chat_id] = stop_event
        lock = _active_locks.setdefault(chat_id, asyncio.Lock())

        async with lock:
            try:
                status_message = await message.reply_text(f"{base_text}\n\n✅ Tagged: 0/0\n🚀 Starting tagging...")
                members = await gather_members(client, chat_id)
                if not members:
                    await status_message.edit_text("⚠️ कोई मेंबर नहीं मिला या बॉट के पास परमिशन नहीं है।")
                    _active_taggers.pop(chat_id, None)
                    return

                batches = [members[i:i + batch_size] for i in range(0, len(members), batch_size)]
                await send_batches(client, chat_id, batches, base_text, status_message, delay)

            except Exception as e:
                await message.reply_text(f"❌ Error: {e}")
            finally:
                _active_taggers.pop(chat_id, None)
                _active_locks.pop(chat_id, None)

    # ---------------- Fancy Trigger ----------------
    @app.on_message(filters.group & filters.regex(r'(?i)^alltag\s+kero\s+bot\b'))
    async def fancy_trigger(client: Client, message: Message):
        if not message.from_user:
            return
        if not await is_admin_or_owner(client, message.chat.id, message.from_user.id):
            return
        await cmd_tagall(client, message)

    # ---------------- Stop Tagging ----------------
    @app.on_message(filters.command(["tagoff", "cancel", "stoptag"]) & filters.group)
    async def stop_tagging(client: Client, message: Message):
        chat_id = message.chat.id
        if chat_id in _active_taggers:
            _active_taggers[chat_id].set()
            await message.reply_text("🛑 Tagging stopped.")
        else:
            await message.reply_text("❌ कोई टैगिंग प्रक्रिया नहीं चल रही है।")

    # ---------------- Help ----------------
    @app.on_message(filters.command(["help_tag", "taghelp"]) & filters.group)
    async def help_tag(client: Client, message: Message):
        await message.reply_text(
            "🧾 **Tagging Help:**\n"
            "/tagall <text> — सभी को 5-5 के बैच में टैग करें\n"
            "/tagoff | /cancel | /stoptag — टैगिंग रोकें\n"
            "🗣 Fancy: `alltag kero bot <text>`"
        )

    return app
