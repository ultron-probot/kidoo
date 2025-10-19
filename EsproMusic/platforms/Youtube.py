import asyncio
import os
import random
import re
import glob
import json
import logging
from typing import Union
from youtubesearchpython.__future__ import VideosSearch
import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from EsproMusic.logging import LOGGER
from EsproMusic.utils.database import is_on_off
from EsproMusic.utils.formatters import time_to_seconds

# =================== COOKIE FILE HANDLER =================== #
def cookie_txt_file():
    folder_path = f"{os.getcwd()}/cookies"
    filename = f"{os.getcwd()}/cookies/logs.csv"

    txt_files = glob.glob(os.path.join(folder_path, '*.txt'))
    if not txt_files:
        raise FileNotFoundError("❌ No .txt cookie files found in the /cookies folder.")

    chosen = random.choice(txt_files)
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, 'a') as file:
        file.write(f'✅ Using Cookie File: {chosen}\n')

    return f"cookies/{os.path.basename(chosen)}"

# =================== SHELL COMMAND EXECUTOR =================== #
async def shell_cmd(cmd: str):
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    out, err = await proc.communicate()
    return out.decode() if not err else out.decode() or err.decode()


# =================== FILE SIZE CHECKER =================== #
async def check_file_size(link: str):
    async def get_format_info(url):
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp", "--cookies", cookie_txt_file(), "-J", url,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            LOGGER.error(f"yt-dlp error: {stderr.decode()}")
            return None
        return json.loads(stdout.decode())

    def parse_size(formats):
        total = sum(fmt.get("filesize", 0) for fmt in formats if fmt)
        return total

    info = await get_format_info(link)
    if not info:
        return None

    total_size = parse_size(info.get("formats", []))
    return total_size or None

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.listbase = "https://youtube.com/playlist?list="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    # ✅ Check if valid YouTube URL
    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        return bool(re.search(self.regex, link))

    # ✅ Extract URL from message
    async def url(self, message: Message) -> Union[str, None]:
        messages = [message]
        if message.reply_to_message:
            messages.append(message.reply_to_message)

        for msg in messages:
            entities = msg.entities or msg.caption_entities or []
            for entity in entities:
                if entity.type in [MessageEntityType.URL, MessageEntityType.TEXT_LINK]:
                    text = msg.text or msg.caption or ""
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
                    return text[entity.offset : entity.offset + entity.length]
        return None

    # ✅ Get video details (title, duration, thumbnail)
    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration = result.get("duration") or "0:00"
            thumb = result["thumbnails"][0]["url"].split("?")[0]
            vidid = result["id"]
            duration_sec = int(time_to_seconds(duration)) if duration else 0
        return title, duration, duration_sec, thumb, vidid

    # ✅ Get only title
    async def title(self, link: str, videoid: Union[bool, str] = None):
        title, *_ = await self.details(link, videoid)
        return title

    # ✅ Get only duration
    async def duration(self, link: str, videoid: Union[bool, str] = None):
        _, duration, *_ = await self.details(link, videoid)
        return duration

    # ✅ Get only thumbnail
    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        *_, thumb, _ = await self.details(link, videoid)
        return thumb

    # ✅ Get playable video URL
    async def video(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        link = link.split("&")[0]
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "--cookies", cookie_txt_file(),
            "-g", "-f", "best[height<=?720][width<=?1280]",
            link,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if stdout:
            return 1, stdout.decode().split("\n")[0]
        else:
            return 0, stderr.decode()

    # ✅ Playlist ID Extractor
    async def playlist(self, link, limit, user_id, videoid: Union[bool, str] = None):
        if videoid:
            link = self.listbase + link
        link = link.split("&")[0]
        playlist = await shell_cmd(
            f"yt-dlp -i --get-id --flat-playlist --cookies {cookie_txt_file()} --playlist-end {limit} {link}"
        )
        result = [r for r in playlist.split("\n") if r.strip()]
        return result

    # ✅ Track Info Fetcher
    async def track(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            return {
                "title": result["title"],
                "link": result["link"],
                "vidid": result["id"],
                "duration": result["duration"],
                "thumb": result["thumbnails"][0]["url"].split("?")[0],
            }, result["id"]

    # ✅ Available Formats List
    async def formats(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        ydl_opts = {"quiet": True, "cookiefile": cookie_txt_file()}
        ydl = yt_dlp.YoutubeDL(ydl_opts)
        formats_list = []
        with ydl:
            info = ydl.extract_info(link, download=False)
            for f in info["formats"]:
                if "dash" not in f.get("format", "").lower() and f.get("filesize"):
                    formats_list.append({
                        "format": f["format"],
                        "size": f["filesize"],
                        "id": f["format_id"],
                        "ext": f["ext"],
                        "note": f.get("format_note", ""),
                        "yturl": link,
                    })
        return formats_list, link

    # ✅ Download (Audio / Video / Song)
    async def download(
        self,
        link: str,
        mystic,
        video=False,
        videoid=None,
        songaudio=False,
        songvideo=False,
        format_id=None,
        title=None,
    ):
        if videoid:
            link = self.base + link
        link = link.split("&")[0]
        loop = asyncio.get_running_loop()

        # ---------- INTERNAL DOWNLOADERS ----------
        def audio_dl():
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "cookiefile": cookie_txt_file(),
                "quiet": True,
                "geo_bypass": True,
                "no_warnings": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=True)
                return os.path.join("downloads", f"{info['id']}.{info['ext']}")

        def video_dl():
            ydl_opts = {
                "format": "(bestvideo[height<=720][ext=mp4])+bestaudio[ext=m4a]/best",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "cookiefile": cookie_txt_file(),
                "quiet": True,
                "geo_bypass": True,
                "no_warnings": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=True)
                return os.path.join("downloads", f"{info['id']}.{info['ext']}")

        def song_audio_dl():
            ydl_opts = {
                "format": format_id,
                "outtmpl": f"downloads/{title}.%(ext)s",
                "cookiefile": cookie_txt_file(),
                "quiet": True,
                "geo_bypass": True,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([link])
            return f"downloads/{title}.mp3"

        def song_video_dl():
            ydl_opts = {
                "format": f"{format_id}+140",
                "outtmpl": f"downloads/{title}.mp4",
                "cookiefile": cookie_txt_file(),
                "quiet": True,
                "geo_bypass": True,
                "merge_output_format": "mp4",
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([link])
            return f"downloads/{title}.mp4"

        # ---------- MAIN EXECUTION ----------
        if songvideo:
            fpath = await loop.run_in_executor(None, song_video_dl)
            return fpath, True
        elif songaudio:
            fpath = await loop.run_in_executor(None, song_audio_dl)
            return fpath, True
        elif video:
            if await is_on_off(1):
                fpath = await loop.run_in_executor(None, video_dl)
                return fpath, True
            else:
                file_size = await check_file_size(link)
                if not file_size:
                    LOGGER.warning("⚠️ Could not fetch file size.")
                    return None, False
                if file_size / (1024 * 1024) > 250:
                    LOGGER.warning("❌ File too large (>250MB).")
                    return None, False
                fpath = await loop.run_in_executor(None, video_dl)
                return fpath, True
        else:
            fpath = await loop.run_in_executor(None, audio_dl)
            return fpath, True
