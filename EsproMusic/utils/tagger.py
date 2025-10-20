""" ESPRO Music Bot - Tagger module File: espro_tagger.py Purpose: Add /tagall functionality to a Pyrogram-based bot.

Features:

/tagall <text> or reply to a message with /tagall to tag all non-bot members in the group

Sends mentions in batches (default 5 per message) and updates a status message with progress

Stop tagging with /tagoff, /cancel, /stoptag

Allow invocation using a natural sentence from admins: e.g. "alltag kero bot <your text here>"

Restrict use to group admins or users in SUDO_USERS


Usage:

1. Put this file in your bot project (e.g., espro_tagger.py).


2. In your main bot file (where you create Client app), register the tagger:

from espro_tagger import register_tagger SUDO_USERS = {123456789}  # optional set of user IDs who can use tagall register_tagger(app, SUDO_USERS=SUDO_USERS)


3. Ensure your bot is admin in the group and has permission to see members.



Notes:

Tagging many users can hit rate limits; this implementation adds a small delay between batches.

If your group is huge, consider increasing delay and/or smaller batch_size.


"""

import asyncio from typing import Set, Optional, Dict, List

from pyrogram import Client, filters from pyrogram.types import Message, User from pyrogram.errors import RPCError

active tasks per chat

_active_taggers: Dict[int, asyncio.Event] = {} _active_locks: Dict[int, asyncio.Lock] = {}

def is_admin_or_sudo(client: Client, chat_id: int, user_id: int, SUDO_USERS: Optional[Set[int]] = None) -> bool: """Return True if user is chat admin or in SUDO_USERS.""" # quick sudo check if SUDO_USERS and user_id in SUDO_USERS: return True try: member = client.get_chat_member(chat_id, user_id) return member.status in ("administrator", "creator") except Exception: return False

def mention(user: User) -> str: name = (user.first_name or "User").replace("@", "") return f"{name}"

async def _gather_members(client: Client, chat_id: int) -> List[User]: """Collect members. Requires bot to be admin to see full list.""" members: List[User] = [] try: async for m in client.iter_chat_members(chat_id): if m.user and not m.user.is_bot: members.append(m.user) except RPCError as e: # fallback: try get_members (may be limited) try: # best-effort single call data = await client.get_chat_members(chat_id) for m in data: if m.user and not m.user.is_bot: members.append(m.user) except Exception: raise return members

async def _send_batch_messages(client: Client, chat_id: int, batches: List[List[User]], base_text: str, status_message: Message, delay: float): total = sum(len(b) for b in batches) done = 0 for batch in batches: # check for cancel stop_event = _active_taggers.get(chat_id) if stop_event and stop_event.is_set(): await status_message.edit_text(status_message.text + "\n\nTagging cancelled by command.") return

mentions = " \n".join(mention(u) for u in batch)
    # message to actually tag these users so they receive notification
    try:
        await client.send_message(chat_id, f"{base_text}\n\n{mentions}")
    except RPCError:
        # try smaller chunk: send one by one
        for u in batch:
            try:
                await client.send_message(chat_id, f"{base_text}\n\n{mention(u)}")
            except RPCError:
                continue

    done += len(batch)
    # update status message
    try:
        await status_message.edit_text(f"{base_text}\n\nTagged: {done}/{total}")
    except RPCError:
        pass

    await asyncio.sleep(delay)

# finished
try:
    await status_message.edit_text(status_message.text + "\n\n✅ Tagging complete.")
except RPCError:
    pass

def register_tagger(app: Client, SUDO_USERS: Optional[Set[int]] = None, batch_size: int = 5, delay: float = 1.0): """Register all handlers on the given Pyrogram Client instance.

Parameters:
- app: your pyrogram Client
- SUDO_USERS: optional set of user IDs allowed to use tagall besides admins
- batch_size: how many users to tag per message
- delay: seconds delay between batches (adjust for large groups)
"""

@app.on_message(filters.command("tagall") & filters.group)
async def cmd_tagall(client: Client, message: Message):
    chat_id = message.chat.id
    from_user = message.from_user
    if not from_user:
        return

    # permission check
    if not is_admin_or_sudo(client, chat_id, from_user.id, SUDO_USERS):
        await message.reply_text("❌ आपको यह कमांड इस्तेमाल करने की अनुमति नहीं है। (Admins/Sudo only)")
        return

    # prevent concurrent taggers in same chat
    if chat_id in _active_locks and _active_locks[chat_id].locked():
        await message.reply_text("⚠️ पहले से एक टैगिंग प्रक्रिया चल रही है। /tagoff से बंद करें।")
        return

    # text after command or reply's text
    base_text = ""
    if len(message.command) > 1:
        base_text = message.text.split(None, 1)[1]
    elif message.reply_to_message and message.reply_to_message.text:
        base_text = message.reply_to_message.text
    else:
        base_text = "@everyone"

    # create stop event and lock
    stop_event = asyncio.Event()
    _active_taggers[chat_id] = stop_event
    lock = _active_locks.setdefault(chat_id, asyncio.Lock())

    async with lock:
        try:
            status_message = await message.reply_text(f"{base_text}\n\nTagged: 0/0\n\nProcess starting...")

            # gather members
            members = await _gather_members(client, chat_id)
            if not members:
                await status_message.edit_text("⚠️ सदस्यों की सूची उपलब्ध नहीं है। सुनिश्चित करें कि बॉट को ग्रुप में एडमिन अनुमति है।")
                _active_taggers.pop(chat_id, None)
                return

            # create batches
            batches = [members[i:i+batch_size] for i in range(0, len(members), batch_size)]

            # update status total
            await status_message.edit_text(f"{base_text}\n\nTagged: 0/{len(members)}\n\nTagging will begin...")

            await _send_batch_messages(client, chat_id, batches, base_text, status_message, delay)

        except Exception as e:
            try:
                await message.reply_text(f"❌ Error during tagging: {e}")
            except Exception:
                pass
        finally:
            _active_taggers.pop(chat_id, None)
            _active_locks.pop(chat_id, None)

# natural-language trigger: "alltag kero bot <text>"
@app.on_message(filters.group & filters.regex(r'(?i)^alltag\s+kero\s+bot\b'))
async def nl_tag_all(client: Client, message: Message):
    # check initiator admin/sudo
    if not message.from_user:
        return
    if not is_admin_or_sudo(client, message.chat.id, message.from_user.id, SUDO_USERS):
        return
    # extract following text
    parts = message.text.split(None, 3)
    # parts[0]=alltag, parts[1]=kero, parts[2]=bot, rest is text
    if len(parts) >= 4:
        # mimic /tagall <text>
        new_msg = Message(
            **{ 'chat': message.chat, 'message_id': message.message_id, 'from_user': message.from_user }
        )
        # hack: call cmd_tagall handler by constructing a fake-like object isn't trivial; instead, call tagging code directly
        # create a status message and perform tagging inline
        # prevent concurrent
        chat_id = message.chat.id
        if chat_id in _active_locks and _active_locks[chat_id].locked():
            await message.reply_text("⚠️ पहले से एक टैगिंग प्रक्रिया चल रही है। /tagoff से बंद करें।")
            return

        base_text = message.text.split(None, 3)[3]
        stop_event = asyncio.Event()
        _active_taggers[chat_id] = stop_event
        lock = _active_locks.setdefault(chat_id, asyncio.Lock())

        async with lock:
            status_message = await message.reply_text(f"{base_text}\n\nTagged: 0/0\n\nProcess starting...")
            try:
                members = await _gather_members(client, chat_id)
                if not members:
                    await status_message.edit_text("⚠️ सदस्यों की सूची उपलब्ध नहीं है। Ensure bot is admin.")
                    _active_taggers.pop(chat_id, None)
                    return
                batches = [members[i:i+batch_size] for i in range(0, len(members), batch_size)]
                await status_message.edit_text(f"{base_text}\n\nTagged: 0/{len(members)}\n\nTagging will begin...")
                await _send_batch_messages(client, chat_id, batches, base_text, status_message, delay)
            except Exception as e:
                await message.reply_text(f"❌ Error during tagging: {e}")
            finally:
                _active_taggers.pop(chat_id, None)
                _active_locks.pop(chat_id, None)

# stop handlers
@app.on_message(filters.command(["tagoff", "cancel", "stoptag"]) & filters.group)
async def stop_tagging(client: Client, message: Message):
    chat_id = message.chat.id
    if chat_id in _active_taggers:
        _active_taggers[chat_id].set()
        await message.reply_text("🛑 Tagging stopped.")
    else:
        await message.reply_text("❌ कोई चलती हुई tagging प्रक्रिया नहीं मिली।")

# friendly help
@app.on_message(filters.command(["help_tag", "taghelp"]) & filters.group)
async def help_tag(client: Client, message: Message):
    await message.reply_text(
        "Tagging Help:\n"
        "/tagall <text> - सभी सदस्यों को टैग करें (5 प्रति संदेश by default)\n"
        "/tagoff|/cancel|/stoptag - टैगिंग रोकें\n"
        "Or write: 'alltag kero bot <your text>' as group admin to trigger tagging."
    )

return app

