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
            value=convert_to_youtube_time_format(estimated),
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


class GiruState(Enum):
    UNKNOWN = 1
    IDLE = 2
    PLAYING = 3
    PAUSED = 4


class PlayerQueue:
    def __init__(self):
        self.close, self.open = [], []

    def __len__(self):
        return len(self.open)

    def enqueue(self, elt, top=False):
        if top:
            self.open.insert(1, elt)
        else:
            self.open.append(elt)

    def dequeue(self):
        if self.head:
            self.close.append(self.open.pop(0))
            return True
        return False

    @property
    def head(self):
        return self.open[0] if self.open else None

    @property
    def tail(self):
        return self.open[-1] if self.open else None

    @property
    def duration(self) -> int:
        return sum([req.duration for req in self.open])


class Player:
    def __init__(self, bot, guild_id):
        self.bot = bot
        self.guild_id = guild_id

        # ---

        self.player_queue = PlayerQueue()
        self.state = GiruState.IDLE

        self.flag_loop: bool = False
        self.flag_skip: bool = False
        self.flag_replay: bool = False

        # ---

        self.q = asyncio.Queue()
        self.event_loop = asyncio.get_event_loop()
        self.locale = self.bot.get_cog("Locales")
        self.voice: discord.VoiceClient = None

        self.event_loop.create_task(self.run())

    # -------

    @property
    def estimated(self):
        # total duration of the queue
        # minus remaining of the current track
        return self.player_queue.duration - self.voice.source.progress

    @property
    def waiting(self):
        return max(len(self.player_queue) - 1, 0)

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
    def _play_after(self, e):
        print(e)

        # should the current head (1st position in open list) closed ?
        if self.flag_skip:
            self.flag_skip = False
            skip = True
        elif self.flag_replay:
            self.flag_replay = False
            skip = False
        elif self.flag_loop:  # lower priority
            skip = False
        else:
            skip = True

        # skip if needed
        if skip:
            self.player_queue.dequeue()

        # ensure to set this flag BEFORE calling consume
        self.state = GiruState.IDLE

        # _play_after can't be defined as a coroutine
        self.q.put_nowait(self._consume)
        # coro = self.put(self._consume)
        # fut = asyncio.run_coroutine_threadsafe(coro, self.event_loop)
        # try:
        #    fut.result()
        # except:
        #    pass

    @log_called_function
    async def _play_now(self, req):
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
        self.voice.play(player, after=self._play_after)

    @log_called_function
    async def _consume(self):
        if self.state is GiruState.IDLE:
            req = self.player_queue.head
            if req is not None:
                self.state = GiruState.PLAYING
                return await self._play_now(req)
            else:
                debug("_consume", "req is None")
        else:
            debug("_consume", "self.state != GiruState.IDLE")

    # --------------------------------------------------------------------------

    @log_called_function
    async def join(self, channel):
        if self.voice is None:
            self.voice = await channel.connect()
            return True
        if self.voice.channel.id != channel.id:
            await self.voice.move_to(channel)
            return True
        return False

    @log_called_function
    async def play(self, req, top=False):
        self.player_queue.enqueue(req, top=top)
        await self.put(self._consume)
        return self.state is GiruState.IDLE

    @log_called_function
    async def disconnect(self):
        if self.voice:
            await self.voice.disconnect()


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
    @commands.guild_only()
    @commands.check(Check.author_channel)
    async def join(self, ctx):
        # print(inspect.currentframe().f_code.co_name)
        voice_channel = ctx.author.voice.channel

        player = self.get_guild_music(ctx.guild.id)
        joined: bool = await player.join(voice_channel)

        if joined:
            locale = ctx.bot.get_cog("Locales")
            await locale.send(ctx, "notif_joined", voice_channel)

    @commands.command(aliases=["p"])
    @commands.guild_only()
    @commands.check(Check.author_channel)
    async def play(self, ctx, *args, top=False):
        name = inspect.currentframe().f_code.co_name
        locale = ctx.bot.get_cog("Locales")

        # searching for the given query
        query = " ".join(args)
        await locale.send(ctx, "notif_loop_searching", query)
        req = await Request.from_youtube(query, ctx.message)
        if req is None:
            return await locale.send(ctx, "error_no_matches")

        # play the song
        player = self.get_guild_music(ctx.guild.id)
        now_played: bool = await player.play(req, top=top)

        if now_played:
            await locale.send(ctx, "notif_playing_now", req.title)
        else:
            embed = req.create_embed_queued(
                estimated=player.estimated, position=player.waiting
            )
            await ctx.send(embed=embed)

    @commands.command(aliases=["pt", "ptop"])
    async def playtop(self, ctx, *args):
        await self.play(ctx, *args, top=True)

    @commands.command(aliases=["ps", "pskip", "playnow", "pn"])
    async def playskip(self, ctx):
        await ctx.send("NotImplementedError")

    @commands.command(aliases=["find"])
    async def search(self, ctx):
        await ctx.send("NotImplementedError")

    @commands.command(aliases=["sc"])
    async def soundcloud(self, ctx):
        await ctx.send("NotImplementedError")

    @commands.command(aliases=["np"])
    @commands.guild_only()
    @commands.check(Check.is_playing)
    @commands.check(Check.same_channel)
    async def nowplaying(self, ctx):
        player = self.get_guild_music(ctx.guild.id)

        t = player.voice.source.progress
        embed = player.player_queue.head.create_embed_np(t)

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
    async def replay(self, ctx):
        await ctx.send("NotImplementedError")

    @commands.command(aliases=["repeat"])
    async def loop(self, ctx):
        await ctx.send("NotImplementedError")

    @commands.command(aliases=["skip", "next", "s"])
    async def voteskip(self, ctx):
        await ctx.send("NotImplementedError")

    @commands.command(aliases=["fs", "fskip"])
    async def forceskip(self, ctx):
        await ctx.send("NotImplementedError")

    @commands.command(aliases=["stop"])
    async def pause(self, ctx):
        await ctx.send("NotImplementedError")

    @commands.command(aliases=["re", "res", "continue"])
    async def resume(self, ctx):
        await ctx.send("NotImplementedError")

    @commands.command(aliases=["l", "ly"])
    async def lyrics(self, ctx):
        await ctx.send("NotImplementedError")

    @commands.command(aliases=["dc", "leave", "dis"])
    async def disconnect(self, ctx):
        await ctx.send("NotImplementedError")

    # --------------------------------------------------------------------------

    @commands.command()
    async def test(self, ctx):
        from embed_generator import create_embed_queue

        embed = create_embed_queue()
        await ctx.send(embed=embed)

