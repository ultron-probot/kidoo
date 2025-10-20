"""
ESPRO Music Bot - Tagger Module
---------------------------------
Purpose: Add /tagall functionality to a Pyrogram-based bot.

Features:
- /tagall <text> → tag all non-bot members in group, 5 per message.
- Stop with /tagoff, /cancel, /stoptag.
- Fancy trigger: "alltag kero bot <text>" or "tag band karo bot".
- Admins + SUDO_USERS only.
"""

import asyncio
from typing import Set, Optional, Dict, List

from pyrogram import Client, filters
from pyrogram.types import Message, User
from pyrogram.errors import RPCError

# Active tagging tasks
_active_taggers: Dict[int, asyncio.Event] = {}
_active_locks: Dict[int, asyncio.Lock] = {}


def is_admin_or_sudo(client: Client, chat_id: int, user_id: int, SUDO_USERS: Optional[Set[int]] = None) -> bool:
    """Return True if user is chat admin or in SUDO_USERS."""
    if SUDO_USERS and user_id in SUDO_USERS:
        return True
    try:
        member = client.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


def mention(user: User) -> str:
    """Generate mention text."""
    name = (user.first_name or "User").replace("@", "")
    return f"[{name}](tg://user?id={user.id})"


async def _gather_members(client: Client, chat_id: int) -> List[User]:
    """Collect group members (excluding bots)."""
    members: List[User] = []
    try:
        async for m in client.get_chat_members(chat_id):
            if m.user and not m.user.is_bot:
                members.append(m.user)
    except Exception:
        pass
    return members


async def _send_batch_messages(client: Client, chat_id: int, batches: List[List[User]], base_text: str, status_message: Message, delay: float):
    """Send messages in batches of 5 users with delay."""
    total = sum(len(b) for b in batches)
    done = 0

    for batch in batches:
        stop_event = _active_taggers.get(chat_id)
        if stop_event and stop_event.is_set():
            await status_message.edit_text(status_message.text + "\n\n🛑 Tagging cancelled by command.")
            return

        mentions = " ".join(mention(u) for u in batch)
        try:
            await client.send_message(chat_id, f"{base_text}\n\n{mentions}", disable_web_page_preview=True)
        except RPCError:
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


def register_tagger(app: Client, SUDO_USERS: Optional[Set[int]] = None, batch_size: int = 5, delay: float = 1.0):
    """Register all tagger handlers."""

    @app.on_message(filters.command("tagall") & filters.group)
    async def cmd_tagall(client: Client, message: Message):
        chat_id = message.chat.id
        from_user = message.from_user
        if not from_user:
            return

        # Check permission
        if not is_admin_or_sudo(client, chat_id, from_user.id, SUDO_USERS):
            await message.reply_text("❌ केवल Admins या Sudo यूज़र्स इस कमांड का उपयोग कर सकते हैं।")
            return

        # Prevent duplicate tagging
        if chat_id in _active_locks and _active_locks[chat_id].locked():
            await message.reply_text("⚠️ पहले से एक टैगिंग प्रक्रिया चल रही है। /tagoff से रोकें।")
            return

        # Message text
        base_text = ""
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
                status_message = await message.reply_text(f"{base_text}\n\n✅ Tagged: 0/0\nStarting...")
                members = await _gather_members(client, chat_id)
                if not members:
                    await status_message.edit_text("⚠️ कोई मेंबर नहीं मिला या बॉट के पास परमिशन नहीं है।")
                    _active_taggers.pop(chat_id, None)
                    return

                batches = [members[i:i + batch_size] for i in range(0, len(members), batch_size)]
                await status_message.edit_text(f"{base_text}\n\nTagged: 0/{len(members)}\n🚀 Tagging started...")

                await _send_batch_messages(client, chat_id, batches, base_text, status_message, delay)

            except Exception as e:
                await message.reply_text(f"❌ Error: {e}")
            finally:
                _active_taggers.pop(chat_id, None)
                _active_locks.pop(chat_id, None)

    # Natural command - "alltag kero bot <text>"
    @app.on_message(filters.group & filters.regex(r'(?i)^alltag\s+kero\s+bot\b'))
    async def fancy_trigger(client: Client, message: Message):
        if not message.from_user:
            return
        if not is_admin_or_sudo(client, message.chat.id, message.from_user.id, SUDO_USERS):
            return
        parts = message.text.split(None, 3)
        if len(parts) >= 4:
            fake_text = message.text.split(None, 3)[3]
            await cmd_tagall(client, message)

    # Stop tagging
    @app.on_message(filters.command(["tagoff", "cancel", "stoptag"]) & filters.group)
    async def stop_tagging(client: Client, message: Message):
        chat_id = message.chat.id
        if chat_id in _active_taggers:
            _active_taggers[chat_id].set()
            await message.reply_text("🛑 Tagging stopped.")
        else:
            await message.reply_text("❌ कोई टैगिंग प्रक्रिया नहीं चल रही है।")

    # Help command
    @app.on_message(filters.command(["help_tag", "taghelp"]) & filters.group)
    async def help_tag(client: Client, message: Message):
        await message.reply_text(
            "🧾 **Tagging Help:**\n"
            "/tagall <text> — सभी को 5-5 के बैच में टैग करें\n"
            "/tagoff | /cancel | /stoptag — टैगिंग रोकें\n"
            "🗣 या लिखें: `alltag kero bot <text>`"
        )

    return app
