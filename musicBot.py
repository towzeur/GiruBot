import discord
import asyncio
import youtube_dl
from re import S
from enum import Enum
from pprint import pprint
from dataclasses import dataclass
from functools import partial

from options import (
    YTDL_OPTIONS,
    FFMPEG_BEFORE_OPTIONS,
    FFMPEG_BEFORE_OPTIONS,
    FFMPEG_EXECUTABLE,
    FFMPEG_OPTIONS,
    DEFAULT_VOLUME,
)

from utils import (
    convert_to_youtube_time_format,
    Markdown,
    log_called_function,
)


youtube_dl.utils.bug_reports_message = lambda: ""


# ------------------------------------------------------------------------------


class AudioSourceTracked(discord.AudioSource):
    def __init__(self, source):
        self._source = source
        self.count = 0

    def read(self) -> bytes:
        data = self._source.read()
        if data:
            self.count += 1
        return data

    def is_opus(self) -> bool:
        try:
            return self._source.is_opus()
        except:
            return True

    def cleanup(self):
        self._source.cleanup()

    @property
    def progress(self) -> float:
        # 20ms
        return self.count * 0.02


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
    def __init__(self, event_loop, locale):
        self.event_loop = event_loop
        self.locale = locale

        self.q = asyncio.Queue()
        self.open, self.close = [], []
        self.state = GiruState.IDLE

        self.voice: discord.VoiceClient = None

        self.looped_playback: bool = False
        self.skip_flag: bool = False

    async def ensure_voice(self, channel):
        if self.voice is None:
            self.voice = await channel.connect()
        if self.voice.channel.id != channel.id:
            await self.voice.move_to(channel)

    async def put(self, callback, *args, **kwargs):
        await self.q.put(partial(callback, *args, **kwargs))

    async def run(self):
        try:
            while True:
                callback = await self.q.get()
                await callback()
        except Exception as e:  #  asyncio.CancelledError
            print("[run] Exception", e)
        finally:
            print("[run] finally")

    @log_called_function
    def _play_after(self, e):
        print(e)

        # should the current head (1st position in open list) closed ?
        if self.open and (self.skip_flag or not self.looped_playback):
            print("POGO PIGI")
            self.close.append(self.open.pop(0))

        # ensure to set this flag BEFORE calling consume
        self.state = GiruState.IDLE
        self.skip_flag = False

        # call the callback like that because _play_after can't be defined as
        # a coroutines
        coro = self.put(self._consume)
        fut = asyncio.run_coroutine_threadsafe(coro, self.event_loop)
        try:
            fut.result()
        except:
            pass

    @log_called_function
    async def _join(self, channel):
        await self.ensure_voice(channel)

    @log_called_function
    async def _disconnect(self):
        if self.voice:
            await self.voice.disconnect()

    @log_called_function
    async def _play_now(self, req):
        await self._join(req.message.author.voice.channel)

        audio = discord.FFmpegPCMAudio(
            req.url,
            executable=FFMPEG_EXECUTABLE,
            pipe=False,
            stderr=None,  # subprocess.PIPE
            before_options=FFMPEG_BEFORE_OPTIONS,  # "-nostdin",
            options=FFMPEG_OPTIONS,
        )
        player = discord.PCMVolumeTransformer(audio, volume=DEFAULT_VOLUME)
        player = AudioSourceTracked(player)
        player.read()
        self.voice.play(player, after=self._play_after)

    @log_called_function
    async def _consume(self):
        if self.open and self.state is GiruState.IDLE:
            req = self.open[0]
            self.state = GiruState.PLAYING
            await self._play_now(req)

        else:
            print("DEBUG", "nothing to consume")

    @log_called_function
    async def play(self, req):
        self.open.append(req)
        await self.put(self._consume)

        if self.state is GiruState.IDLE:
            await req.message.channel.send(
                self.locale.notif_playing_now.format(req.title)
            )
        elif self.state is GiruState.PLAYING:
            await req.message.channel.send(
                embed=req.create_embed_queued(
                    estimated=self.estimated, position=len(self.open) - 1
                )
            )

    @log_called_function
    def skip(self):
        # if self.open:
        #    req_skip = self.open.pop(0)
        #    self.close.append(req_skip)
        self.voice.stop()
        self.skip_flag = True

    @log_called_function
    def stop(self):
        self.voice.stop()

    @log_called_function
    def pause(self):
        pass

    @log_called_function
    def resume(self):
        pass

    @log_called_function
    def loop(self):
        self.looped_playback = not self.looped_playback
        return self.looped_playback

    @property
    def estimated(self):
        t = self.open[0].duration - self.voice.source.progress
        t += sum([req.duration for req in self.open[1:-1]])
        return t


# ------------------------------------------------------------------------------


@dataclass
class Request:
    """Class for keeping track of an item in inventory."""

    message: discord.Message
    query: str
    info: dict
    title: str
    url: str
    duration: float

    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    @classmethod
    async def from_youtube(cls, query, message):
        # with youtube_dl.YoutubeDL(YTDL_OPTIONS) as ydl:
        #    info = ydl.extract_info(query, download=False)

        # ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)
        loop = asyncio.get_event_loop()
        downloader = partial(cls.ytdl.extract_info, query, download=False)
        # , process=False)
        info = await loop.run_in_executor(None, downloader)

        if "entries" in info:
            entry = None
            while entry is None:
                try:
                    entry = info["entries"].pop(0)
                except IndexError:
                    return None
        else:
            entry = info

        # pprint(info)
        return cls(
            message, query, entry, entry["title"], entry["url"], entry["duration"]
        )

    def create_embed_queued(self, estimated="???", position="???"):
        embed = discord.Embed(
            title="Added to queue",
            description=Markdown.bold(self.title),
            color=0x00AFF4,
            url=self.url,
        )
        # embed.set_image(*, query)
        # embed.set_thumbnail(*, url)
        # embed.set_author(*, name, url=Embed.Empty, icon_url=Embed.Empty)
        # print(self.info["thumbnail"])
        # embed.set_image(self.info["thumbnail"])
        # embed.add_field(name=self.title, value=f"[Click]({self.url})")

        embed.set_thumbnail(url=self.info["thumbnail"])

        # Markdown.bold(
        embed.add_field(
            name="Channel", value=str(self.message.author.voice.channel), inline=True,
        )
        embed.add_field(
            name="Song Duration",
            value=convert_to_youtube_time_format(self.duration),
            inline=True,
        )
        embed.add_field(
            name="Estimated time until playing",
            value=convert_to_youtube_time_format(estimated),
            inline=True,
        )
        embed.add_field(
            name="Position in queue", value=position, inline=True,
        )
        return embed


# ------------------------------------------------------------------------------


class GiruMusicBot:
    def __init__(self, guild_id, locale):
        self.guild_id = guild_id
        self.locale = locale

        self.loop = asyncio.get_running_loop()  # client.loop
        self.girumusic = GiruMusic(self.loop, self.locale)
        self.loop.create_task(self.girumusic.run())

    ########################

    async def play_handler(self, message, query):
        # user have to be in a voice channel
        if message.author.voice is None:
            return await message.channel.send(self.locale.error_user_not_in_channel)

        # searching for the given query
        await message.channel.send(self.locale.notif_loop_searching.format(query))
        req = await Request.from_youtube(query, message)

        if req is None:
            return await message.channel.send(self.locale.error_no_matches)

        # play the song
        await self.girumusic.put(self.girumusic.play, req)

    async def join_handler(self, message):
        if message.author.voice is None:
            return await message.channel.send(self.locale.error_user_not_in_channel)
        await self.girumusic._join(message.author.voice.channel)
        await message.channel.send(
            self.locale.notif_joined.format(message.author.voice.channel)
        )

    async def disconnect_handler(self, message):
        if self.girumusic.voice is None:
            return await message.channel.send(self.locale.error_no_voice_channel)
        await self.girumusic._disconnect()
        await message.channel.send(self.locale.notif_disconnected)

    async def pause_handler(self, message):
        if self.girumusic.voice is None:
            await message.channel.send(self.locale.error_no_voice_channel)

        if not self.voice.is_paused():
            self.voice.pause()
            self.event.set()
            return await message.channel.send(self.locale.notif_paused)

        return await message.channel.send(self.locale.error_already_paused)

    async def resume_handler(self, message):
        if self.girumusic.voice is None:
            return await message.channel.send(self.locale.error_no_voice_channel)

        if self.voice.is_paused():
            self.voice.resume()
            return await message.channel.send(self.locale.notif_resumed)

        return await message.channel.send(self.locale.error_not_paused)

    async def skip_handler(self, message):
        if self.girumusic.voice is None:
            return await message.channel.send(self.locale.error_no_voice_channel)

        if self.girumusic.state is GiruState.PLAYING:
            self.girumusic.skip()
            return await message.channel.send(self.locale.notif_skipped)

        return await message.channel.send(self.locale.error_nothing_playing)

    async def loop_handler(self, message):
        if self.girumusic.loop():
            return await message.channel.send(self.locale.notif_loop_enabled)
        return await message.channel.send(self.locale.notif_loop_disabled)

