import asyncio
import os
import re
import json
import random
from typing import Union

import aiohttp
import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython import VideosSearch

from EsproMusic.utils.formatters import time_to_seconds
from config import API_URL, VIDEO_API_URL, API_KEY


# ================= HELPERS =================

def yt_query(q: str):
    if q.startswith("http"):
        return q
    return f"ytsearch:{q}"


def cookie_txt_file():
    cookie_dir = f"{os.getcwd()}/cookies"
    if not os.path.exists(cookie_dir):
        return None
    files = [f for f in os.listdir(cookie_dir) if f.endswith(".txt")]
    if not files:
        return None
    return os.path.join(cookie_dir, random.choice(files))


async def search_to_link(query: str):
    search = VideosSearch(query, limit=1)
    result = (await search.next()).get("result")
    if not result:
        return None
    return result[0]["link"]


# ================= DOWNLOAD HELPERS =================

async def download_song(link: str):
    # 🔥 SONG NAME → YT LINK
    if not link.startswith("http"):
        link = await search_to_link(link)
        if not link:
            return None

    video_id = link.split("v=")[-1].split("&")[0]
    os.makedirs("downloads", exist_ok=True)

    # Already exists
    for ext in ["mp3", "m4a", "webm"]:
        path = f"downloads/{video_id}.{ext}"
        if os.path.exists(path):
            return path

    # ✅ API FIRST (unchanged behavior)
    api_url = f"{API_URL}/song/{video_id}?api={API_KEY}"
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as r:
            if r.status != 200:
                return None
            data = await r.json()
            dl = data.get("link")
            if not dl:
                return None

        async with session.get(dl) as f:
            path = f"downloads/{video_id}.mp3"
            with open(path, "wb") as w:
                w.write(await f.read())
            return path


async def download_video(link: str):
    if not link.startswith("http"):
        link = await search_to_link(link)
        if not link:
            return None

    video_id = link.split("v=")[-1].split("&")[0]
    os.makedirs("downloads", exist_ok=True)

    for ext in ["mp4", "webm", "mkv"]:
        path = f"downloads/{video_id}.{ext}"
        if os.path.exists(path):
            return path

    api_url = f"{VIDEO_API_URL}/video/{video_id}?api={API_KEY}"
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as r:
            if r.status != 200:
                return None
            data = await r.json()
            dl = data.get("link")
            if not dl:
                return None

        async with session.get(dl) as f:
            path = f"downloads/{video_id}.mp4"
            with open(path, "wb") as w:
                w.write(await f.read())
            return path


# ================= YOUTUBE CLASS =================

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(youtube\.com|youtu\.be)"
        self.listbase = "https://youtube.com/playlist?list="

    async def exists(self, link: str, videoid=False):
        if videoid:
            link = self.base + link
        return bool(re.search(self.regex, link))

    async def url(self, message: Message):
        msgs = [message, message.reply_to_message] if message.reply_to_message else [message]
        for msg in msgs:
            if not msg:
                continue
            ents = msg.entities or msg.caption_entities or []
            for e in ents:
                if e.type in [MessageEntityType.URL, MessageEntityType.TEXT_LINK]:
                    return e.url if hasattr(e, "url") else msg.text[e.offset:e.offset+e.length]
        return None

    async def details(self, link: str, videoid=False):
        if not link.startswith("http"):
            link = await search_to_link(link)
        r = VideosSearch(link, limit=1)
        res = (await r.next())["result"][0]
        dur = res["duration"]
        return (
            res["title"],
            dur,
            int(time_to_seconds(dur)) if dur else 0,
            res["thumbnails"][0]["url"].split("?")[0],
            res["id"],
        )

    async def video(self, link: str, videoid=False):
        file = await download_video(link)
        if file:
            return 1, file

        cookie = cookie_txt_file()
        opts = {"format": "best[height<=720]", "quiet": True}
        if cookie:
            opts["cookiefile"] = cookie

        ydl = yt_dlp.YoutubeDL(opts)
        info = ydl.extract_info(yt_query(link), download=False)
        return 1, info["url"]

    async def playlist(self, link, limit, user_id, videoid=False):
        if not link.startswith("http"):
            return []
        cmd = f"yt-dlp -i --flat-playlist --get-id --playlist-end {limit} {link}"
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        out, _ = await proc.communicate()
        return [i for i in out.decode().split("\n") if i]

    async def track(self, link: str, videoid=False):
        if not link.startswith("http"):
            link = await search_to_link(link)
        r = VideosSearch(link, limit=1)
        res = (await r.next())["result"][0]
        return {
            "title": res["title"],
            "link": res["link"],
            "vidid": res["id"],
            "duration_min": res["duration"],
            "thumb": res["thumbnails"][0]["url"].split("?")[0],
        }, res["id"]

    async def download(self, link: str, mystic, video=False, videoid=False):
        cookie = cookie_txt_file()
        opts = {
            "format": "bestaudio/best" if not video else "bestvideo+bestaudio",
            "outtmpl": "downloads/%(id)s.%(ext)s",
            "quiet": True,
        }
        if cookie:
            opts["cookiefile"] = cookie

        ydl = yt_dlp.YoutubeDL(opts)
        info = ydl.extract_info(yt_query(link), download=True)
        return f"downloads/{info['id']}.{info['ext']}"
