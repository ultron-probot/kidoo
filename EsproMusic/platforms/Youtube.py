import asyncio
import os
import re
import yt_dlp
import httpx

from typing import Union
from pyrogram.types import Message
from pyrogram.enums import MessageEntityType
from youtubesearchpython.__future__ import VideosSearch

from EsproMusic.logging import LOGGER  # ✅ your bot’s logging
from EsproMusic.utils.formatters import time_to_seconds  # ✅ for duration parsing


# ✅ Execute shell commands safely
async def shell_cmd(cmd: str) -> str:
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    if err:
        if "unavailable videos are hidden" in (err.decode("utf-8")).lower():
            return out.decode("utf-8")
        return err.decode("utf-8")
    return out.decode("utf-8")


# ✅ Fetch streaming link using third-party API
async def get_stream_url(query: str, video: bool = False) -> str:
    api_base = "http://195.26.255.16:8000"  # your FastAPI endpoint
    api_key = "HlzXk3eTV9Ni6M1_Nm1VHEhHVbxobJ6ingFzW4JBCkU"

    endpoint = "/ytmp4" if video else "/ytmp3"
    api_url = f"{api_base}{endpoint}"

    async with httpx.AsyncClient(timeout=120) as client:
        try:
            response = await client.get(api_url, params={"url": query, "api_key": api_key})
            if response.status_code != 200:
                LOGGER.error(f"API call failed with status {response.status_code}")
                return ""
            data = response.json()
            if data.get("status") and data.get("result"):
                return data["result"]["url"]
            LOGGER.warning("Invalid response format from YouTube API")
            return ""
        except Exception as e:
            LOGGER.error(f"Error calling YouTube API: {e}")
            return ""


class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        return bool(re.search(self.regex, link))

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        for message in messages:
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        return text[entity.offset: entity.offset + entity.length]
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        return None

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        search = VideosSearch(link, limit=1)
        results = (await search.next()).get("result", [])
        if not results:
            return None, None, 0, None, None
        result = results[0]
        title = result["title"]
        duration_min = result.get("duration", "0:00")
        duration_sec = int(time_to_seconds(duration_min))
        thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        vidid = result["id"]
        return title, duration_min, duration_sec, thumbnail, vidid

    async def title(self, link: str, videoid: Union[bool, str] = None):
        title, *_ = await self.details(link, videoid)
        return title

    async def duration(self, link: str, videoid: Union[bool, str] = None):
        _, duration, *_ = await self.details(link, videoid)
        return duration

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        *_, thumb, _ = await self.details(link, videoid)
        return thumb

    async def video(self, link: str, videoid: Union[bool, str] = None):
        """Use 3rd-party API for video stream"""
        if videoid:
            link = self.base + link
        link = link.split("&")[0]
        url = await get_stream_url(link, video=True)
        return (1, url) if url else (0, None)

    async def audio(self, link: str, videoid: Union[bool, str] = None):
        """Use 3rd-party API for audio stream"""
        if videoid:
            link = self.base + link
        link = link.split("&")[0]
        url = await get_stream_url(link, video=False)
        return url

    async def playlist(self, link, limit, user_id, videoid: Union[bool, str] = None):
        if videoid:
            link = self.listbase + link
        if "&" in link:
            link = link.split("&")[0]
        playlist = await shell_cmd(
            f"yt-dlp -i --get-id --flat-playlist --playlist-end {limit} --skip-download {link}"
        )
        result = [x for x in playlist.split("\n") if x.strip()]
        return result

    async def track(self, link: str, videoid: Union[bool, str] = None):
        title, duration_min, _, thumb, vidid = await self.details(link, videoid)
        yturl = self.base + vidid
        track_details = {
            "title": title,
            "link": yturl,
            "vidid": vidid,
            "duration_min": duration_min,
            "thumb": thumb,
        }
        return track_details, vidid

    async def formats(self, link: str, videoid: Union[bool, str] = None):
        """Keep formats check via yt-dlp for UI-based selection"""
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        ydl_opts = {"quiet": True}
        ydl = yt_dlp.YoutubeDL(ydl_opts)
        formats_available = []
        with ydl:
            try:
                r = ydl.extract_info(link, download=False)
                for f in r["formats"]:
                    if "dash" in str(f.get("format", "")).lower():
                        continue
                    if all(k in f for k in ["format", "filesize", "format_id", "ext", "format_note"]):
                        formats_available.append({
                            "format": f["format"],
                            "filesize": f["filesize"],
                            "format_id": f["format_id"],
                            "ext": f["ext"],
                            "format_note": f["format_note"],
                            "yturl": link,
                        })
            except Exception as e:
                LOGGER.error(f"Error fetching formats: {e}")
        return formats_available, link

    async def slider(self, link: str, query_type: int, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        a = VideosSearch(link, limit=10)
        result = (await a.next()).get("result", [])
        if not result:
            return None, None, None, None
        item = result[query_type]
        return (
            item["title"],
            item["duration"],
            item["thumbnails"][0]["url"].split("?")[0],
            item["id"],
        )

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ) -> str:
        """Integrated API download fallback"""
        if videoid:
            link = self.base + link
        link = link.split("&")[0]

        # Use API for fast direct play
        if video and not songvideo:
            url = await get_stream_url(link, True)
            return url, None
        elif not video and not songaudio:
            url = await get_stream_url(link, False)
            return url, None

        # yt-dlp fallback for specific formats
        loop = asyncio.get_running_loop()

        def yt_dl_generic(fmt):
            ydl_opts = {
                "format": fmt,
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "geo_bypass": True,
                "quiet": True,
                "no_warnings": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as x:
                info = x.extract_info(link, download=True)
                return os.path.join("downloads", f"{info['id']}.{info['ext']}")

        if songvideo:
            await loop.run_in_executor(None, lambda: yt_dl_generic(f"{format_id}+140"))
            return f"downloads/{title}.mp4"
        elif songaudio:
            await loop.run_in_executor(None, lambda: yt_dl_generic(format_id))
            return f"downloads/{title}.mp3"
        elif video:
            downloaded = await loop.run_in_executor(None, lambda: yt_dl_generic("best[height<=720]"))
            return downloaded, None
        else:
            downloaded = await loop.run_in_executor(None, lambda: yt_dl_generic("bestaudio"))
            return downloaded, None
