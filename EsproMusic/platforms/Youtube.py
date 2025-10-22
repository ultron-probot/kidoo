import asyncio
import os
import random
import re
import json
import glob
from typing import Union

import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch

from EsproMusic.utils.database import is_on_off
from EsproMusic.utils.formatters import time_to_seconds

# ---------------------------
# COOKIE SYSTEM
# ---------------------------

def cookie_txt_file():
    folder_path = f"{os.getcwd()}/cookies"
    filename = f"{os.getcwd()}/cookies/logs.csv"
    txt_files = glob.glob(os.path.join(folder_path, '*.txt'))
    if not txt_files:
        raise FileNotFoundError("❌ No .txt cookies file found in /cookies/")
    cookie_txt_file = random.choice(txt_files)
    with open(filename, 'a') as file:
        file.write(f'Chosen Cookie File : {cookie_txt_file}\n')
    return f"cookies/{os.path.basename(cookie_txt_file)}"


# ---------------------------
# ASYNC COMMAND RUNNER
# ---------------------------

async def shell_cmd(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    return out.decode() if out else err.decode()


# ---------------------------
# YOUTUBE HANDLER CLASS
# ---------------------------

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.listbase = "https://youtube.com/playlist?list="

    async def exists(self, link: str):
        return bool(re.search(self.regex, link))

    async def url(self, message: Message) -> Union[str, None]:
        text = ""
        if message.entities:
            for e in message.entities:
                if e.type == MessageEntityType.URL:
                    text = message.text or message.caption
                    return text[e.offset:e.offset + e.length]
        elif message.caption_entities:
            for e in message.caption_entities:
                if e.type == MessageEntityType.TEXT_LINK:
                    return e.url
        return None

    async def details(self, link: str):
        results = VideosSearch(link, limit=1)
        data = (await results.next())["result"][0]
        return (
            data["title"],
            data["duration"],
            int(time_to_seconds(data["duration"])) if data["duration"] else 0,
            data["thumbnails"][0]["url"].split("?")[0],
            data["id"],
        )

    # ---------------------------
    # MAIN VIDEO FETCHER
    # ---------------------------
    async def video(self, link: str):
        # 1️⃣ Try normal yt-dlp first
        for client in ["web", "android", "web_remix"]:
            proc = await asyncio.create_subprocess_exec(
                "yt-dlp",
                "--cookies", cookie_txt_file(),
                "--extractor-args", f"youtube:player_client={client}",
                "-g",
                "-f", "best[height<=?720][width<=?1280]",
                f"{link}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if stdout and "http" in stdout.decode():
                return 1, stdout.decode().split("\n")[0]
        return 0, stderr.decode() if stderr else "403 Forbidden or no format found."

    # ---------------------------
    # PLAYLIST PARSER
    # ---------------------------
    async def playlist(self, link, limit):
        cmd = (
            f'yt-dlp -i --get-id --flat-playlist '
            f'--cookies {cookie_txt_file()} '
            f'--extractor-args "youtube:player_client=android" '
            f'--playlist-end {limit} --skip-download {link}'
        )
        result = await shell_cmd(cmd)
        ids = [x for x in result.split("\n") if x.strip()]
        return ids

    # ---------------------------
    # DOWNLOADERS
    # ---------------------------
    async def download(self, link: str, video=False, songaudio=False, songvideo=False, title=None, format_id=None):
        loop = asyncio.get_running_loop()

        def get_opts(fmt):
            return {
                "format": fmt,
                "outtmpl": f"downloads/{title or '%(id)s'}.%(ext)s",
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "cookiefile": cookie_txt_file(),
                "no_warnings": True,
                "extractor_args": {"youtube": {"player_client": ["android"]}},
                "prefer_ffmpeg": True,
                "merge_output_format": "mp4",
            }

        def run_dl(opts):
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(link, download=True)
                return os.path.join("downloads", f"{info['id']}.{info['ext']}")

        if songvideo:
            return await loop.run_in_executor(None, lambda: run_dl(get_opts(f"{format_id}+140")))
        elif songaudio:
            opts = get_opts(format_id)
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
            return await loop.run_in_executor(None, lambda: run_dl(opts))
        elif video:
            if await is_on_off(1):
                return await loop.run_in_executor(None, lambda: run_dl(get_opts("(bestvideo+bestaudio)[height<=720]")))
            else:
                success, result = await self.video(link)
                if success:
                    return result, False
                return None, True
        else:
            return await loop.run_in_executor(None, lambda: run_dl(get_opts("bestaudio/best"))), True
