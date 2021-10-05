from msvcrt import putch
import discord
import asyncio
from discord import channel
import youtube_dl
import inspect

from discord.ext import commands
from re import S
from enum import Enum
from pprint import pprint
from dataclasses import dataclass
from functools import partial

from locales import Locales
from options import (
    YTDL_OPTIONS,
    FFMPEG_BEFORE_OPTIONS,
    FFMPEG_BEFORE_OPTIONS,
    FFMPEG_EXECUTABLE,
    FFMPEG_OPTIONS,
    DEFAULT_VOLUME,
)
from utils import convert_to_youtube_time_format, Markdown, log_called_function, debug

youtube_dl.utils.bug_reports_message = lambda: ""

# ------------------------------------------------------------------------------


class Check:
    @staticmethod
    async def author_channel(ctx):
        if ctx.author.voice and ctx.author.voice.channel:
            return True

        locale = ctx.bot.get_cog("Locales")
        await locale.send(ctx, "error_user_not_in_channel")
        return False
        # commands.CommandError

    @staticmethod
    async def bot_channel(ctx):
        voice_bot = ctx.guild.voice_client
        if voice_bot and voice_bot.channel:
            return True

        locale = ctx.bot.get_cog("Locales")
        await locale.send(ctx, "error_no_voice_channel")
        return False
        # voice_author.channel == voice_bot.channel

    @staticmethod
    async def same_channel(ctx):
        """Checks that the command sender is in the same voice channel as the bot."""
        if not await Check.author_channel(ctx):
            return False
        if not await Check.bot_channel(ctx):
            return False
        if ctx.author.voice.channel == ctx.guild.voice_client.channel:
            return True

        locale = ctx.bot.get_cog("Locales")
        await locale.send(ctx, "error_not_same_channel")
        return False
        # voice_author.channel == voice_bot.channel

    @staticmethod
    async def is_playing(ctx):
        """Checks that audio is currently playing before continuing."""
        client = ctx.guild.voice_client
        if client and client.channel and client.source:
            return True

        locale = ctx.bot.get_cog("Locales")
        await locale.send(ctx, "error_nothing_playing")
        return False


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
            value=estimated
            if isinstance(estimated, str)
            else convert_to_youtube_time_format(estimated),
            inline=True,
        )
        embed.add_field(
            name="Position in queue", value=position, inline=True,
        )
        return embed

    def create_embed_np(self, t, ticks=30):
        x = int(ticks * (t / self.duration))
        print(t, self.duration, x, "%")

        embed = discord.Embed(
            title=self.title,
            url=self.url,
            # description=Markdown.bold(self.title),
            color=0x00AFF4,
        )
        embed.set_thumbnail(url=self.info["thumbnail"])
        embed.set_author(name="Now Playing ♪")
        # "ㅤ"
        # progress bar
        line = "".join(["▬" if t != x else "🔘" for t in range(ticks)])
        embed.add_field(
            name="\rx", value=Markdown.code(line) + "\n\u200b", inline=False,
        )
        # 5:26 / 16:26
        d_current = convert_to_youtube_time_format(t)
        d_end = convert_to_youtube_time_format(self.duration)
        line = f"{d_current} / {d_end}"
        embed.add_field(
            name="\rx", value=Markdown.code(line) + "\n\u200b", inline=False,
        )
        # Requested by
        line = f"`Requested by:` {self.message.author.name}"
        embed.add_field(name="\rx", value=line, inline=False)
        # return "\u200B"
        return embed


# ------------------------------------------------------------------------------


class PlayerFlag(Enum):
    SKIP = 1
    REPLAY = 2


class PlayerOption(Enum):
    LOOP = 1
    LOOP_QUEUE = 2


class PlayerQueue:
    def __init__(self):
        self.close, self.open = [], []
        self.cursor = 0

    def __len__(self):
        return len(self.open)

    def next(self, flag: PlayerFlag = None, option: PlayerOption = None):
        # flags have a higher priority
        if flag is PlayerFlag.SKIP:
            self.dequeue(idx=self.cursor)
            return self.current
        elif flag is PlayerFlag.REPLAY:
            return self.current

        # optons have a lower priority
        if option is PlayerOption.LOOP:
            return self.current
        elif option is PlayerOption.LOOP_QUEUE:
            self.cursor = (self.cursor + 1) % len(self.open)
            return self.current
        else:  # next song
            for _ in range(self.cursor + 1):
                self.dequeue(idx=0)
            self.cursor = 0
            return self.current

    def enqueue(self, elt, top=False):
        if top:
            self.open.insert(self.cursor + 1, elt)
        else:
            self.open.append(elt)

    def dequeue(self, idx=0) -> bool:
        try:
            elt = self.open.pop(idx)
        except IndexError:
            return False
        else:
            self.close.append(elt)
            return True

    @property
    def head(self):
        return self.open[0] if self.open else None

    @property
    def tail(self):
        return self.open[-1] if self.open else None

    @property
    def current(self):
        try:
            return self.open[self.cursor]
        except IndexError:
            return None

    @property
    def duration(self) -> int:
        return sum([req.duration for req in self.open])


class GiruState(Enum):
    IDLE = 1
    PLAYING = 2


class Player:
    def __init__(self, bot, guild_id):
        self.bot = bot
        self.guild_id = guild_id

        # ---

        self.queue = PlayerQueue()

        self.state = GiruState.IDLE
        self.flag: PlayerFlag = None
        self.option: PlayerOption = None

        # ---

        self.q = asyncio.Queue()
        self.event_loop = asyncio.get_event_loop()
        self.locale = self.bot.get_cog("Locales")
        self.voice: discord.VoiceClient = None

        self.event_loop.create_task(self.run())

    # -------

    @property
    def estimated(self):
        """estimated times before the last queued request is played"""
        # total duration of the queue
        # minus remaining of the current track
        t = self.queue.duration
        t -= self.voice.source.progress
        t -= self.queue.tail.duration
        return t

    @property
    def estimated_next(self):
        """estimated time until the end of the current song"""
        return self.queue.current.duration - self.voice.source.progress

    @property
    def current_progress(self):
        if self.voice.source:
            return self.voice.source.progress

    @property
    def current_remaining(self):
        return

    @property
    def waiting(self):
        return max(len(self.queue) - 1, 0)

    # -------

    @log_called_function
    async def put(self, callback, *args, **kwargs):
        await self.q.put(partial(callback, *args, **kwargs))

    @log_called_function
    async def run(self):
        try:
            while True:
                callback = await self.q.get()
                print("**callback**")
                await callback()
        except Exception as e:
            print("[run] Exception", e)
        finally:
            print("[run] finally")

    # -------

    @log_called_function
    async def _play_now(self, req):
        def after(e):
            print("after", e)
            self.queue.next(flag=self.flag, option=self.option)
            self.state = GiruState.IDLE
            self.flag = None
            self.q.put_nowait(self._consume)

        await self.join(req.message.author.voice.channel)
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
        self.voice.play(player, after=after)

    @log_called_function
    async def _consume(self, play=False):
        debug("_consume", "flag", self.flag, "option", self.option)
        if self.state is GiruState.IDLE:
            debug("_consume (GiruState.IDLE) >> now playing")
            if self.queue.current:
                debug("_consume >> playing now")
                self.state = GiruState.PLAYING
                await self._play_now(self.queue.current)
            else:
                debug("_consume >> nothing to consume !")
        elif self.state is GiruState.PLAYING:
            debug("_consume (GiruState.PLAYING) >> queued")
        else:
            debug("_consume (UNKOWN) >> ?")

    # --------------------------------------------------------------------------

    @log_called_function
    async def join(self, channel):
        if self.voice is None or not self.voice.is_connected():
            try:
                self.voice = await channel.connect()
            except asyncio.TimeoutError:
                return "Could not connect to the voice channel in time."
            except discord.ClientException:
                return "Already connected to a voice channel."
        if self.voice.channel.id != channel.id:
            await self.voice.move_to(channel)
        return True

    @log_called_function
    async def play(self, req, top=False):
        self.queue.enqueue(req, top=top)
        await self.put(self._consume)
        return self.state is GiruState.IDLE

    @log_called_function
    async def disconnect(self):
        if self.voice:
            await self.voice.disconnect()

    @log_called_function
    async def skip(self) -> bool:
        skiped = self.voice and self.state is GiruState.PLAYING
        if skiped:
            self.flag = PlayerFlag.SKIP
            self.voice.stop()
        return skiped

    @log_called_function
    async def loop(self) -> bool:
        if self.option is PlayerOption.LOOP:
            self.option = None
        else:
            self.option = PlayerOption.LOOP
        return self.option is PlayerOption.LOOP

    @log_called_function
    async def replay(self) -> bool:
        replayed = self.voice and self.state is GiruState.PLAYING
        if replayed:
            self.flag = PlayerFlag.REPLAY
            self.voice.stop()
        return replayed

    @log_called_function
    async def disconnect(self) -> bool:
        disconnected = self.voice is not None
        if disconnected:
            await self.voice.disconnect()
            del self.voice
            self.voice = None
        return disconnected

    @log_called_function
    async def pause(self) -> bool:
        paused = self.voice.is_playing()
        if paused:
            self.voice.pause()
        return paused

    @log_called_function
    async def resume(self) -> bool:
        resumed = self.voice.is_paused()
        if resumed:
            self.voice.resume()
        return resumed


# ------------------------------------------------------------------------------


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guilds_player = {}

    def get_guild_music(self, guild_id: int) -> dict:
        if guild_id not in self.guilds_player:
            self.guilds_player[guild_id] = Player(self.bot, guild_id)
        return self.guilds_player[guild_id]

    # --------------------------------------------------------------------------
    # Song
    # --------------------------------------------------------------------------

    @commands.command(aliases=["summon"])
    @commands.check(Check.author_channel)
    @commands.guild_only()
    async def join(self, ctx):
        player = self.get_guild_music(ctx.guild.id)
        locale = ctx.bot.get_cog("Locales")

        voice_channel = ctx.author.voice.channel
        joined: bool = await player.join(voice_channel)
        if joined:
            await locale.send(ctx, "notif_joined", voice_channel)
        else:
            debug("join", "not joined")

    @commands.command(aliases=["p"])
    @commands.check(Check.author_channel)
    @commands.guild_only()
    async def play(self, ctx, *args, top=False, skip=False) -> bool:
        # TODO : check if the bot is playing if the author channel is different
        # from the bot's one
        locale = ctx.bot.get_cog("Locales")

        # searching for the given query
        query = " ".join(args)
        await locale.send(ctx, "notif_loop_searching", query)
        req = await Request.from_youtube(query, ctx.message)
        if req is None:
            await locale.send(ctx, "error_no_matches")
            return False

        # play the song
        player = self.get_guild_music(ctx.guild.id)
        now_played: bool = await player.play(req, top=top)

        if skip:  # playtop
            embed = req.create_embed_queued(estimated="Now", position="Now")
            await ctx.send(embed=embed)
            if not now_played:  # skip if necessary
                skiped: bool = await player.skip()
        elif now_played:
            await locale.send(ctx, "notif_playing_now", req.title)
        else:
            estimated = player.estimated_next if top else player.estimated
            position = 1 if top else player.waiting
            embed = req.create_embed_queued(estimated=estimated, position=position)
            await ctx.send(embed=embed)
        return True

    @commands.command(aliases=["pt", "ptop"])
    async def playtop(self, ctx, *args):
        await self.play(ctx, *args, top=True, skip=False)

    @commands.command(aliases=["ps", "pskip", "playnow", "pn"])
    @commands.check(Check.author_channel)
    @commands.guild_only()
    async def playskip(self, ctx, *args):
        await self.play(ctx, *args, top=True, skip=True)

    @commands.command(aliases=["find"])
    async def search(self, ctx):
        await ctx.send("NotImplementedError")

    @commands.command(aliases=["sc"])
    async def soundcloud(self, ctx):
        await ctx.send("NotImplementedError")

    @commands.command(aliases=["np"])
    @commands.check(Check.is_playing)
    @commands.check(Check.same_channel)
    @commands.guild_only()
    async def nowplaying(self, ctx):
        player = self.get_guild_music(ctx.guild.id)

        t = player.voice.source.progress
        embed = player.queue.head.create_embed_np(t)

        await ctx.send(embed=embed)

    @commands.command(aliases=["save", "yoink"])
    async def grab(self, ctx):
        await ctx.send("NotImplementedError")

    @commands.command(aliases=[])
    async def seek(self, ctx):
        await ctx.send("NotImplementedError")

    @commands.command(aliases=["rwd"])
    async def rewind(self, ctx):
        await ctx.send("NotImplementedError")

    @commands.command(aliases=["fwd"])
    async def forward(self, ctx):
        await ctx.send("NotImplementedError")

    @commands.command(aliases=[])
    @commands.check(Check.is_playing)
    @commands.check(Check.same_channel)
    @commands.guild_only()
    async def replay(self, ctx):
        player = self.get_guild_music(ctx.guild.id)
        locale = ctx.bot.get_cog("Locales")

        replayed = await player.replay()
        if replayed:
            await locale.send(ctx, "notif_replayed")
        else:
            debug("replay", "not replayed")

    @commands.command(aliases=["repeat"])
    @commands.check(Check.same_channel)
    @commands.guild_only()
    async def loop(self, ctx):
        player = self.get_guild_music(ctx.guild.id)
        locale = ctx.bot.get_cog("Locales")

        looped = await player.loop()
        if looped:
            await locale.send(ctx, "notif_loop_enabled")
        else:
            await locale.send(ctx, "notif_loop_disabled")

    @commands.command(aliases=["skip", "next", "s"])
    @commands.check(Check.is_playing)
    @commands.check(Check.same_channel)
    @commands.guild_only()
    async def voteskip(self, ctx):
        player = self.get_guild_music(ctx.guild.id)
        locale = ctx.bot.get_cog("Locales")

        skiped: bool = await player.skip()
        if skiped:
            await locale.send(ctx, "notif_skipped")
        else:
            debug("voteskip", "not skiped")
        return skiped

    @commands.command(aliases=["fs", "fskip"])
    async def forceskip(self, ctx):
        await self.voteskip(ctx)

    @commands.command(aliases=["stop"])
    @commands.check(Check.is_playing)
    @commands.check(Check.same_channel)
    @commands.guild_only()
    async def pause(self, ctx):
        player = self.get_guild_music(ctx.guild.id)
        locale = ctx.bot.get_cog("Locales")

        paused = await player.pause()
        if paused:
            await locale.send(ctx, "notif_paused")
        else:
            await locale.send(ctx, "error_already_paused")

    @commands.command(aliases=["re", "res", "continue"])
    @commands.check(Check.is_playing)
    @commands.check(Check.same_channel)
    @commands.guild_only()
    async def resume(self, ctx):
        player = self.get_guild_music(ctx.guild.id)
        locale = ctx.bot.get_cog("Locales")

        resumed = await player.resume()
        if resumed:
            await locale.send(ctx, "notif_resumed")
        else:
            await locale.send(ctx, "error_not_paused")

    @commands.command(aliases=["l", "ly"])
    async def lyrics(self, ctx):
        await ctx.send("NotImplementedError")

    @commands.command(aliases=["dc", "leave", "dis"])
    @commands.check(Check.same_channel)
    @commands.guild_only()
    async def disconnect(self, ctx):
        player = self.get_guild_music(ctx.guild.id)
        locale = ctx.bot.get_cog("Locales")

        disconnected = await player.disconnect()
        if disconnected:
            await locale.send(ctx, "notif_disconnected")
        else:
            debug("disconnect", "not disconnected")

    # --------------------------------------------------------------------------

    @commands.command()
    async def test(self, ctx):
        from embed_generator import create_embed_queue

        embed = create_embed_queue()
        await ctx.send(embed=embed)
