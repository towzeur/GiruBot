from re import S
from urllib.request import Request
import discord
import asyncio
from discord.channel import VoiceChannel
import youtube_dl
from enum import Enum
from pprint import pprint
from dataclasses import dataclass

import text_en as TEXT

# from music_data_extractor import MusicFileWrapper
from utils import convert_to_youtube_time_format, Markdown


# Fuck your useless bugreports message that gets two link embeds and confuses users
youtube_dl.utils.bug_reports_message = lambda: ""


from functools import wraps


def my_decorator(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        print("@", f.__name__)
        return f(*args, **kwargs)

    return wrapper


# ------------------------------------------------------------------------------

YDL_OPTIONS = {
    "verbose": False,
    "format": "bestaudio/best",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",  # bind to ipv4 since ipv6 addresses cause issues sometimes
    "usenetrc": True,
}


ytdl_before_args = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"


DEFAULT_VOLUME = 0.5

# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------


class GiruCommand(Enum):
    PLAY = 1
    SKIP = 2
    STOP = 3
    PAUSE = 4
    RESUME = 5
    # ENDED = 6


class GiruState(Enum):
    UNKNOWN = 1
    IDLE = 2
    PLAYING = 3
    PAUSED = 4


class GiruMusic:
    def __init__(self, client):
        self.client = client

        self.q = asyncio.Queue()
        self.open, self.close = [], []
        self.state = GiruState.IDLE

        self.loop_on = False
        self.voice = None

        # audio = discord.FFmpegPCMAudio(
        #        new_source, executable="ffmpeg.exe", **ffmpeg_options
        # )
        # player = discord.PCMVolumeTransformer(audio, volume=DEFAULT_VOLUME)
        # self.voice.play(player, after=play_after_callback)

    async def ensure_voice(self, channel):
        if self.voice is None:
            self.voice = await channel.connect()
        if self.voice.channel.id != channel.id:
            await self.voice.move_to(channel)

    async def put(self, e):
        await self.q.put(e)

    async def run(self):
        try:
            while True:
                tmp = await self.q.get()
                if type(tmp) == tuple:
                    handler, args = tmp[0], tmp[1:]
                    await handler(*args)
                else:
                    await tmp()
        except Exception as e:  #  asyncio.CancelledError
            print("[run] Exception", e)
        finally:
            print("[run] finally")

    @my_decorator
    def _play_after(self, e):
        print(e)
        self.state = GiruState.IDLE

        if not self.loop_on:
            req_ok = self.open.pop(0)
            self.close.append(req_ok)

        coro = self.put(self._consume)
        fut = asyncio.run_coroutine_threadsafe(coro, self.client.loop)
        # client.loop)
        try:
            fut.result()
        except:
            pass

    @my_decorator
    async def _join(self, channel):
        await self.ensure_voice(channel)

    @my_decorator
    async def _disconnect(self):
        if self.voice:
            await self.voice.disconnect()

    @my_decorator
    async def _play_now(self, req):
        await self._join(req.message.author.voice.channel)
        audio = discord.FFmpegPCMAudio(req.url, executable="ffmpeg.exe")
        player = discord.PCMVolumeTransformer(audio, volume=DEFAULT_VOLUME)
        self.voice.play(player, after=self._play_after)

    @my_decorator
    async def _consume(self):
        if not self.open:
            print("DEBUG", "nothing to consume")
        req = self.open[0]
        if self.state is GiruState.IDLE:
            self.state = GiruState.PLAYING
            await self._play_now(req)
        elif self.state is GiruState.PLAYING:
            pass
        elif self.state is GiruState.PAUSED:
            pass

    @my_decorator
    async def play(self, req):
        self.open.append(req)
        await self.put(self._consume)

    def skip(self):
        pass

    def stop(self):
        pass

    def pause(self):
        pass

    def resume(self):
        pass

    def loop(self):
        self.loop_on = not self.loop_on
        return self.loop_on


# ------------------------------------------------------------------------------


@dataclass
class Request:
    """Class for keeping track of an item in inventory."""

    message: discord.Message
    query: str
    title: str
    url: str
    duration: float

    @classmethod
    def from_youtube(cls, query, message):
        with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(query, download=False)
        if "entries" in info:  # playlist
            info = info["entries"][0]
        return cls(message, query, info["title"], info["url"], info["duration"])

    @property
    def embed_queued(self):
        embed = discord.Embed(
            title="Added to queue",
            description=Markdown.bold(self.title),
            color=0x00AFF4,
        )
        # embed.set_image(*, query)
        embed.add_field(
            name=Markdown.bold("Channel"),
            value=str(self.message.author.voice.channel),
            inline=True,
        )
        embed.add_field(
            name=Markdown.bold("Song Duration"),
            value=convert_to_youtube_time_format(self.req.duration),
            inline=True,
        )
        embed.add_field(
            name=Markdown.bold("Estimated time until playing"),
            value="???",
            inline=False,
        )
        embed.add_field(
            name=Markdown.bold("Position in queue"),
            value=str(self.queue.qsize()),
            inline=True,
        )
        return embed


# ------------------------------------------------------------------------------


class GiruMusicBot:
    def __init__(self, client, server_id):
        self.client = client
        self.server_id = server_id

        self.girumusic = GiruMusic(self.client)
        self.client.loop.create_task(self.girumusic.run())

    ########################
    @staticmethod
    async def play_handler(self, message, query):
        # user have to be in a voice channel
        if message.author.voice is None:
            return await message.channel.send(TEXT.error_user_not_in_channel)

        # searching for the given query
        await message.channel.send(TEXT.notif_loop_searching.format(query))
        req = Request.from_youtube(query, message)
        print(req)
        if req is None:
            return await message.channel.send(TEXT.error_no_matches)

        # play the song
        await self.girumusic.put((self.girumusic.play, req))

        if self.girumusic.voice.is_playing():
            # if the queue isn't empty
            return await message.channel.send(embed=req.embed_queued)
        else:
            # now playing
            return await message.channel.send(TEXT.notif_playing_now.format(req.info))

    async def join_handler(self, message):
        if message.author.voice is None:
            return await message.channel.send(TEXT.error_user_not_in_channel)
        await self.girumusic._join(message.author.voice.channel)
        await message.channel.send(
            TEXT.notif_joined.format(message.author.voice.channel)
        )

    async def disconnect_handler(self, message):
        if self.girumusic.voice is None:
            return await message.channel.send(TEXT.error_no_voice_channel)
        await self.girumusic._disconnect()
        await message.channel.send(TEXT.notif_disconnected)

    async def pause_handler(self, message):
        if self.voice is None:
            await message.channel.send(TEXT.error_no_voice_channel)

        if not self.voice.is_paused():
            self.voice.pause()
            self.event.set()
            return await message.channel.send(TEXT.notif_paused)

        return await message.channel.send(TEXT.error_already_paused)

    async def resume_handler(self, message):
        if self.voice is None:
            return await message.channel.send(TEXT.error_no_voice_channel)

        if self.voice.is_paused():
            self.voice.resume()
            self.event.set()
            return await message.channel.send(TEXT.notif_resumed)

        return await message.channel.send(TEXT.error_not_paused)

    async def skip_handler(self, message):
        if self.voice is None:
            return await message.channel.send(TEXT.error_no_voice_channel)

        if self.voice.is_playing():
            self.voice.source = None
            self.event.set()
            return await message.channel.send(TEXT.notif_skipped)

        return await message.channel.send(TEXT.error_nothing_playing)

    async def loop_handler(self, message):
        if self.girumusic.loop():
            return await message.channel.send(TEXT.notif_loop_enabled)
        return await message.channel.send(TEXT.notif_loop_disabled)

