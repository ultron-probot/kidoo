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

# =================== MAIN YOUTUBE CLASS =================== #
class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        # ... existing init code

    # ------------------ Add this method ------------------
    async def url(self, message):
        """Extract URL from message or reply"""
        if message.reply_to_message:
            msg = message.reply_to_message
        else:
            msg = message

        text = msg.text or msg.caption
        if not text:
            return None

        # Extract first YouTube link in the message
        match = re.search(r"(https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w-]+)", text)
        if match:
        return match.group(0)
        return None
                 video = data["result"][0]
                 title = video["title"]
                 duration = video.get("duration", "0:00")
                 thumbnail = video["thumbnails"][0]["url"]
                 video_id = video["id"]
                 url = f"https://www.youtube.com/watch?v={video_id}"

            duration_sec = time_to_seconds(duration)
            return {
                "title": title,
                "duration": duration_sec,
                "thumbnail": thumbnail,
                "url": url,
            }
        except Exception as e:
            LOGGER.error(f"Search Error: {e}")
            return None

    async def download_audio(self, url: str, title: str):
        """🎵 Download YouTube Audio"""
        try:
            file_path = f"downloads/{title}.mp3"
            os.makedirs("downloads", exist_ok=True)

            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": file_path,
                "quiet": True,
                "nocheckcertificate": True,
                "cookiefile": cookie_txt_file(),
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            return file_path if os.path.exists(file_path) else None

        except Exception as e:
            LOGGER.error(f"Audio Download Error: {e}")
            return None

    async def download_video(self, url: str, title: str):
        """🎬 Download YouTube Video"""
        try:
            file_path = f"downloads/{title}.mp4"
            os.makedirs("downloads", exist_ok=True)

            ydl_opts = {
                "format": "best[ext=mp4]/best",
                "outtmpl": file_path,
                "quiet": True,
                "nocheckcertificate": True,
                "cookiefile": cookie_txt_file(),
                "merge_output_format": "mp4",
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            return file_path if os.path.exists(file_path) else None

        except Exception as e:
            LOGGER.error(f"Video Download Error: {e}")
            return None

    async def process_request(self, query: str, stream_type: str, caption: str, message: Message):
        """🚀 Main handler — search, check cache, download and return file"""
        info = await self.search(query)
        if not info:
            await message.reply_text("❌ Song not found on YouTube.")
            return None

        title = re.sub(r'[\\/*?:"<>|]', "", info["title"])[:60]
        url = info["url"]
        duration = info["duration"]

        # ✅ पहले cache check करो
        from cache_system import play_request, upload_to_cache_group

        cached_file = await play_request(query, stream_type, caption, title, duration)
        if cached_file:
            await message.reply_text("✅ Played from Cache Database 🎵")
            return cached_file

        # 🔽 अगर cache में नहीं है तो download करो
        if stream_type == "audio":
            path = await self.download_audio(url, title)
        else:
            path = await self.download_video(url, title)

        if not path:
            await message.reply_text("⚠️ Download failed. Try again later.")
            return None

        # 💾 Upload to cache group
        msg = await upload_to_cache_group(query, path, stream_type, caption, title, duration)
        await message.reply_text("🎧 Downloaded & Cached for Future Requests ✅")

        return msg.audio.file_id if stream_type == "audio" else msg.video.file_id
        async def url(self, message):
                  """Backward compatibility for old play.py decorators"""
                  text = message.text or message.caption
        if not text:
            return None

        # अगर user ने YouTube link दिया है तो वही return करो
        if "youtube.com" in text or "youtu.be" in text:
            return text.split(None, 1)[1] if " " in text else text

        # नहीं तो plain search query return करो
        return text.split(None, 1)[1] if " " in text else text
        
