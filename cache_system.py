import asyncio
import datetime
from pyrogram import Client
from config import MONGO_DB_URI, BOT_TOKEN, API_ID, API_HASH
from pymongo import MongoClient

# ========== CONFIG ==========
CACHE_GROUP_ID = -1001234567890  # 👈 इसे अपने private cache group id से बदलो

# MongoDB Setup
mongo = MongoClient(MONGO_DB_URI)
db = mongo['music_bot']
cache_col = db['cache_data']

# Bot Client
app = Client("CacheSystem", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


async def get_cached_media(query: str, media_type: str):
    """MongoDB cache check"""
    data = cache_col.find_one({"query": query.lower(), "type": media_type})
    if data:
        print(f"✅ Cache hit for {query}")
        return data
    print(f"🕵️ Cache miss for {query}")
    return None


async def save_to_cache(query, media_type, message, caption, title, duration):
    """Save new media to cache (MongoDB + Group)"""
    file_id = message.audio.file_id if media_type == "audio" else message.video.file_id
    data = {
        "query": query.lower(),
        "file_id": file_id,
        "type": media_type,
        "duration": duration,
        "title": title,
        "caption": caption,
        "date": datetime.datetime.utcnow().isoformat()
    }
    cache_col.insert_one(data)
    print(f"🗃️ Saved {query} to MongoDB cache.")


async def upload_to_cache_group(query, path, media_type, caption, title, duration):
    """Upload media to Telegram cache group and store details"""
    if media_type == "audio":
        msg = await app.send_audio(
            chat_id=CACHE_GROUP_ID,
            audio=path,
            caption=caption,
            title=title,
            performer="MusicBot"
        )
    else:
        msg = await app.send_video(
            chat_id=CACHE_GROUP_ID,
            video=path,
            caption=caption
        )

    await save_to_cache(query, media_type, msg, caption, title, duration)
    return msg


async def play_request(query, media_type="audio", caption=None, title=None, duration=None):
    """Main function to check cache, else upload new"""
    cached = await get_cached_media(query, media_type)
    if cached:
        return cached["file_id"]  # Return file_id to play directly from Telegram
    return None  # Not found, download needed
