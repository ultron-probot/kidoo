import asyncio
import os
import re
import random
from typing import Union

import aiohttp
import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython import VideosSearch

from EsproMusic.utils.formatters import time_to_seconds
from config import API_URL, VIDEO_API_URL, API_KEY


# ================= BASIC HELPERS =================

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
    res = (await search.next()).get("result")
    if not res:
        return None
    return res[0]["link"]


def extract_video_id(link: str):
    if "v=" in link:
        return link.split("v=")[-1].split("&")[0]
    return link.rsplit("/", 1)[-1]


# ================= API STREAMING =================

async def api_song_stream(link: str):
    if not link.startswith("http"):
        link = await search_to_link(link)
        if not link:
            return None

    vid = extract_video_id(link)
    api = f"{API_URL}/song/{vid}?api={API_KEY}"

    async with aiohttp.ClientSession() as session:
        async with session.get(api) as r:
            if r.status != 200:
                return None
            data = await r.json()
            return data.get("link")  # STREAM URL


async def api_video_stream(link: str):
    if not link.startswith("http"):
        link = await search_to_link(link)
        if not link:
            return None

    vid = extract_video_id(link)
    api = f"{VIDEO_API_URL}/video/{vid}?api={API_KEY}"

    async with aiohttp.ClientSession() as session:
        async with session.get(api) as r:
            if r.status != 200:
                return None
            data = await r.json()
            return data.get("link")


# ================= YTDLP FALLBACK =================

def ytdlp_stream(link: str, video=False):
    cookie = cookie_txt_file()
    opts = {
        "format": "bestvideo+bestaudio" if video else "bestaudio/best",
        "quiet": True,
        "no_warnings": True,
    }
    if cookie:
        opts["cookiefile"] = cookie

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(yt_query(link), download=False)
        return info.get("url")


# ================= YOUTUBE API CLASS =================

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
        # 🔥 API FIRST
        stream = await api_video_stream(link)
        if stream:
            return 1, stream

        # 🔁 FALLBACK
        return 1, ytdlp_stream(link, video=True)

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

    async def playlist(self, link, limit, user_id, videoid=False):
        if not link.startswith("http"):
            return []
        cmd = f"yt-dlp -i --flat-playlist --get-id --playlist-end {limit} {link}"
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, _ = await proc.communicate()
        return [i for i in out.decode().split("\n") if i]

    async def download(self, link: str, mystic, video=False, videoid=False):
        # 🔥 API STREAM FIRST
        stream = await (api_video_stream(link) if video else api_song_stream(link))
        if stream:
            return stream

        # 🔁 FALLBACK
        return ytdlp_stream(link, video=video)
