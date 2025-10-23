# youtube.py (Part 1/2)
import asyncio
import os
import re
import json
import glob
import random
from typing import Union, Optional

import yt_dlp
import aiohttp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch

from EsproMusic.logging import LOGGER
from EsproMusic.platforms._httpx import HttpxClient
from EsproMusic.utils.database import is_on_off
from EsproMusic.utils.formatters import time_to_seconds

from os import getenv

# === Third-Party API defaults (can override via environment or config) ===
API_URL = getenv("API_URL", "https://pytdbotapi.thequickearn.xyz")
API_KEY = getenv("API_KEY", "NxGBNexGenBots2d8c91")

os.makedirs("downloads", exist_ok=True)
os.makedirs("cookies", exist_ok=True)


def cookie_txt_file():
    """Select a random cookie .txt file and log it."""
    folder_path = os.path.join(os.getcwd(), "cookies")
    txt_files = glob.glob(os.path.join(folder_path, "*.txt"))
    if not txt_files:
        raise FileNotFoundError("No .txt cookie files found in ./cookies")
    cookie_path = random.choice(txt_files)
    try:
        with open(os.path.join(folder_path, "logs.csv"), "a") as f:
            f.write(f"Chosen File : {cookie_path}\n")
    except Exception as e:
        LOGGER.warning(f"Cookie log write failed: {e}")
    return cookie_path


async def download_song(link: str) -> Optional[str]:
    """Use 3rd-party API to download a song or audio by video ID or URL."""
    if "v=" in link:
        video_id = link.split("v=")[-1].split("&")[0]
    elif "youtu.be/" in link:
        video_id = link.split("youtu.be/")[-1].split("?")[0]
    else:
        video_id = link

    download_folder = "downloads"
    os.makedirs(download_folder, exist_ok=True)

    for ext in ("mp3", "m4a", "webm", "mp4"):
        candidate = os.path.join(download_folder, f"{video_id}.{ext}")
        if os.path.exists(candidate):
            return candidate

    song_url = f"{API_URL}/song/{video_id}?api={API_KEY}"

    async with aiohttp.ClientSession() as session:
        download_url = None
        file_format = "mp3"
        for attempt in range(10):
            try:
                async with session.get(song_url, timeout=30) as resp:
                    if resp.status != 200:
                        await asyncio.sleep(2)
                        continue
                    data = await resp.json()
                status = (data.get("status") or "").lower()
                if status == "done":
                    download_url = data.get("link")
                    file_format = (data.get("format") or "mp3").lower()
                    break
                elif status == "downloading":
                    await asyncio.sleep(4)
                    continue
                else:
                    LOGGER.error(f"API error: {data}")
                    return None
            except Exception as e:
                LOGGER.warning(f"Attempt {attempt+1} failed: {e}")
                await asyncio.sleep(2)

        if not download_url:
            LOGGER.error("Download URL not received from 3rd-party API.")
            return None

        file_name = f"{video_id}.{file_format}"
        file_path = os.path.join(download_folder, file_name)

        try:
            async with session.get(download_url, timeout=60) as file_resp:
                if file_resp.status != 200:
                    LOGGER.error(f"Download failed: {file_resp.status}")
                    return None
                with open(file_path, "wb") as fd:
                    while True:
                        chunk = await file_resp.content.read(8192)
                        if not chunk:
                            break
                        fd.write(chunk)
            return file_path
        except Exception as e:
            LOGGER.error(f"Saving song failed: {e}")
            return None


async def check_file_size(link):
    """Probe total file size using yt-dlp."""
    async def get_format_info(link):
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "--cookies", cookie_txt_file(),
            "-J",
            link,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            return None
        try:
            return json.loads(stdout.decode())
        except Exception:
            return None

    def parse_size(formats):
        total_size = 0
        for fmt in formats:
            if isinstance(fmt.get("filesize"), (int, float)):
                total_size += fmt["filesize"]
        return total_size

    info = await get_format_info(link)
    if not info:
        return None
    return parse_size(info.get("formats", []))


async def shell_cmd(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    out, err = await proc.communicate()
    return out.decode() if not err else (out.decode() or err.decode())
    # youtube.py (Part 2/2)

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.listbase = "https://youtube.com/playlist?list="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        return bool(re.search(self.regex, link))

    async def url(self, message_1):
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        for message in messages:
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        return text[entity.offset: entity.offset + entity.length]
            if message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        return None

    async def details(self, link, videoid=None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            vidid = result["id"]
            duration_sec = 0 if str(duration_min) == "None" else int(time_to_seconds(duration_min))
        return title, duration_min, duration_sec, thumbnail, vidid

    async def video(self, link, videoid=None):
        if videoid:
            link = self.base + link
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "--cookies", cookie_txt_file(),
            "-g", "-f", "best[height<=?720][width<=?1280]",
            f"{link}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if stdout:
            return 1, stdout.decode().split("\n")[0]
        return 0, stderr.decode()

    async def download(
        self, link, mystic, video=False, videoid=None,
        songaudio=False, songvideo=False, format_id=None, title=None
    ):
        loop = asyncio.get_running_loop()

        def audio_dl():
            ydl_optssx = {
                "format": "bestaudio/best",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "cookiefile": cookie_txt_file(),
                "no_warnings": True,
            }
            x = yt_dlp.YoutubeDL(ydl_optssx)
            info = x.extract_info(link, False)
            xyz = f"downloads/{info['id']}.{info['ext']}"
            if not os.path.exists(xyz):
                x.download([link])
            return xyz

        def video_dl():
            ydl_optssx = {
                "format": "(bestvideo[height<=?720][width<=?1280][ext=mp4])+(bestaudio[ext=m4a])",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "cookiefile": cookie_txt_file(),
                "no_warnings": True,
            }
            x = yt_dlp.YoutubeDL(ydl_optssx)
            info = x.extract_info(link, False)
            xyz = f"downloads/{info['id']}.{info['ext']}"
            if not os.path.exists(xyz):
                x.download([link])
            return xyz

        # === SONGVIDEO (API + fallback) ===
        if songvideo:
            downloaded = await download_song(link)
            if downloaded:
                return downloaded, True
            await loop.run_in_executor(None, video_dl)
            return None, False

        # === SONGAUDIO (API + fallback) ===
        if songaudio:
            downloaded = await download_song(link)
            if downloaded:
                return downloaded, True
            await loop.run_in_executor(None, audio_dl)
            return None, False

        # === NORMAL VIDEO ===
        if video:
            if await is_on_off(1):
                direct = True
                file_path = await loop.run_in_executor(None, video_dl)
            else:
                proc = await asyncio.create_subprocess_exec(
                    "yt-dlp",
                    "--cookies", cookie_txt_file(),
                    "-g",
                    "-f", "best[height<=?720][width<=?1280]",
                    f"{link}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                if stdout:
                    file_path = stdout.decode().split("\n")[0]
                    direct = False
                else:
                    file_path = await loop.run_in_executor(None, video_dl)
                    direct = True
            return file_path, direct

        # === DEFAULT AUDIO ===
        downloaded = await download_song(link)
        if downloaded:
            return downloaded, True
        file_path = await loop.run_in_executor(None, audio_dl)
        return file_path, True
    
