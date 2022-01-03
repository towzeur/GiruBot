import discord
import asyncio
import yt_dlp as youtube_dl
import sys
import multiprocessing
import os

from discord.ext import commands
from enum import Enum
from pprint import pprint
from dataclasses import dataclass
from functools import partial
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from time import perf_counter_ns

from locales import Locales
from options import (
    YTDL_OPTIONS,
    FFMPEG_BEFORE_OPTIONS,
    FFMPEG_BEFORE_OPTIONS,
    FFMPEG_EXECUTABLE,
    FFMPEG_OPTIONS,
    DEFAULT_VOLUME,
)
from utils import log_called_function, debug, eprint
from embed_generator import EmbedGenerator
from player_queue import PlayerQueue

youtube_dl.utils.bug_reports_message = lambda: ""


def get_locale_from_context(ctx):
    return ctx.bot.get_cog("Locales").get_guild_locale(ctx.guild.id)


# ------------------------------------------------------------------------------


class Check:
    @staticmethod
    async def author_channel(ctx):
        if not (ctx.author.voice and ctx.author.voice.channel):
            locale = get_locale_from_context(ctx)
            await ctx.send(locale.error_user_not_in_channel)
            return False
        return True

    @staticmethod
    async def bot_channel(ctx):
        if not (ctx.guild.voice_client and ctx.guild.voice_client.channel):
            locale = get_locale_from_context(ctx)
            await ctx.send(locale.error_no_voice_channel)
            return False
        return True

    @staticmethod
    async def same_channel(ctx):
        """Checks that the command sender is in the same voice channel as the bot."""
        if not await Check.author_channel(ctx):
            return False
        if not await Check.bot_channel(ctx):
            return False
        if not (ctx.author.voice.channel == ctx.guild.voice_client.channel):
            locale = get_locale_from_context(ctx)
            await ctx.send(locale.error_not_same_channel)
            return False
        return True

    @staticmethod
    async def is_playing(ctx):
        """Checks that audio is currently playing before continuing."""
        # client = ctx.guild.voice_client
        # if not (client and client.channel and client.source):
        #    return False

        player, locale = ctx.bot.get_cog("Music").get_player_and_locale(ctx)
        if not player.PLAYING:
            await ctx.send(locale.error_nothing_playing)
            return False

        return True


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

    # def is_opus(self) -> bool:
    #    try:
    #        return self._source.is_opus()
    #    except:
    #        return True

    def cleanup(self):
        self._source.cleanup()

    @property
    def progress(self) -> float:
        # 20ms
        return self.count * 0.02


# ------------------------------------------------------------------------------


def main():
    read, write = os.pipe()
    writer_process = multiprocessing.Process(target=writer, args=(write,))
    writer_process.start()
    asyncio.get_event_loop().run_until_complete(reader(read))


async def reader(read):
    pipe = os.fdopen(read, mode="r")

    loop = asyncio.get_event_loop()
    stream_reader = asyncio.StreamReader()

    def protocol_factory():
        return asyncio.StreamReaderProtocol(stream_reader)

    transport, _ = await loop.connect_read_pipe(protocol_factory, pipe)
    print(await stream_reader.readline())
    transport.close()


def writer(write):
    os.write(write, b"Hello World\n")


if __name__ == "__main__":
    main()


class Downloader:
    ytdl_kwargs = dict(
        download=False,
        ie_key=None,
        extra_info={},
        process=True,
        force_generic_extractor=False,
    )
    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    @staticmethod
    def get_info(query):
        ytdl_kwargs = dict(
            download=False,
            ie_key=None,
            extra_info={},
            process=True,
            force_generic_extractor=False,
        )
        with youtube_dl.YoutubeDL(YTDL_OPTIONS) as ytdl:
            ytdl.cache.remove()
            try:
                info = ytdl.extract_info(query, **ytdl_kwargs)
                # ytdl.prepare_filename(info_dict)
                # ytdl.download([url])
                return info
            except (
                youtube_dl.utils.ExtractorError,
                youtube_dl.utils.DownloadError,
            ) as e:
                debug("from_youtube", "exception", e)
                eprint(e)
        return None


@dataclass
class Request:
    """Class for keeping track of an item in inventory."""

    message: discord.Message
    query: str
    info: dict
    title: str
    url: str
    duration: float

    @classmethod
    async def from_youtube(cls, query, message, blocking=True):
        t0 = perf_counter_ns()

        """
        print("-" * 30)
        ytdl_kwargs = dict(
            download=False,
            ie_key=None,
            extra_info={},
            process=True,
            force_generic_extractor=False,
        )
        ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)
        loop = asyncio.get_running_loop()
        info = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(query, **ytdl_kwargs)
        )
        print("+" * 30)
        """

        ytdl_kwargs = dict(
            download=False,
            ie_key=None,
            extra_info={},
            process=True,
            force_generic_extractor=False,
        )
        ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

        if blocking:
            print("-" * 30)
            debug("from_youtube, blocking")
            # info = Downloader.get_info(query)
            loop = asyncio.get_running_loop()
            downloader = partial(ytdl.extract_info, query, **ytdl_kwargs)
            info = await loop.run_in_executor(None, downloader)
            print("+" * 30)
            # info = await loop.run_in_executor(None, Downloader.get_info, query)
            # asyncio.set_event_loop(loop_bot)
            # loop.close()

        else:
            debug("from_youtube, non blocking")
            loop = asyncio.get_running_loop()
            with ProcessPoolExecutor(max_workers=1) as executor:
                info = await loop.run_in_executor(executor, Downloader.get_info, query)

        t1 = perf_counter_ns()
        eprint("d1", (t1 - t0) * 1e-6)

        if False:
            try:
                with open("tmp/tmp_entries.txt", "w", encoding="utf-8") as f:
                    pprint(info, stream=f)
            except Exception as e:
                eprint(e)
                print("**" * 20)
                # return None

        # this value is not an exact match, but it's a good approximation
        if "entries" in info:
            print("@from_youtube", 'entry = info["entries"][0]', len(info["entries"]))
            entry = info["entries"][0]
        else:
            print("@from_youtube", "entry = info")
            entry = info

        return cls(
            message=message,
            query=query,
            info=entry,
            title=entry["title"],
            url=entry["url"],
            duration=entry["duration"],
        )


# ------------------------------------------------------------------------------


class Player:
    class State(Enum):
        IDLE = 1
        PLAYING = 2

    def __init__(self, bot, guild_id):
        self.bot = bot
        self.guild_id = guild_id

        # ---

        self.queue = PlayerQueue()
        self.state = Player.State.IDLE

        # ---

        # self.q = asyncio.Queue()
        self.locale = self.bot.get_cog("Locales")
        self.voice: discord.VoiceClient = None

        # event_loop = asyncio.get_event_loop()
        # event_loop.create_task(self.run())

    # --------------------------------------------------------------------------

    @property
    def PLAYING(self) -> bool:
        return self.state is Player.State.PLAYING

    @property
    def IDLE(self):
        return self.state is Player.State.IDLE

    # -------

    @property
    def estimated(self) -> float:
        """estimated times before the last queued request is played"""
        # total duration of the queue
        # minus remaining of the current track
        t = self.queue.duration
        t -= self.voice.source.progress
        t -= self.queue.tail.duration
        return t

    @property
    def estimated_next(self) -> float:
        """estimated time until the end of the current song"""
        return self.queue.current.duration - self.voice.source.progress

    # -------
    @log_called_function
    def _after(self, error=None):
        if error:
            eprint("_after ERROR", error)
        self.state = Player.State.IDLE
        self.queue.next()
        self.bot.loop.create_task(self._consume())

    @log_called_function
    def _play_now(self, req):
        print("_play_now >> vid :", req.info["webpage_url"])

        # create an Audio
        try:
            audio = discord.FFmpegPCMAudio(
                req.url,
                executable=FFMPEG_EXECUTABLE,
                pipe=False,
                stderr=None,  # sys.stdout # None # subprocess.PIPE
                before_options=FFMPEG_BEFORE_OPTIONS,  # "-nostdin",
                options=FFMPEG_OPTIONS,
            )
        except discord.ClientException:
            eprint("_play_now", "The subprocess failed to be created")
            return

        # create a player
        player = discord.PCMVolumeTransformer(audio, volume=DEFAULT_VOLUME)
        player = AudioSourceTracked(player)
        player.read()

        # play it
        try:
            self.voice.play(player, after=self._after)
        except discord.ClientException:
            eprint("ClientException – Already playing audio or not connected")
        except TypeError:
            eprint("Source is not a AudioSource or after is not a callable")
        except discord.OpusNotLoaded:
            eprint("Source is not opus encoded and opus is not loaded")

    @log_called_function
    async def _consume(self):
        debug("_consume", "flag", self.queue.flag, "modifiers", self.queue.modifiers)
        if self.IDLE:
            debug("_consume", "(IDLE)", ">> now playing")
            req = self.queue.current
            if req is not None:
                debug("_consume >> playing now")
                self.state = Player.State.PLAYING
                await self.join(req.message.author.voice.channel)
                self._play_now(req)
                return True
            else:
                debug("_consume", "(IDLE)", ">> nothing to consume !")
        elif self.PLAYING:
            debug("_consume", "(PLAYING)", ">> queued")
        else:
            debug("_consume", "(UNKOWN)", ">> ?")
        return False

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
        """ 
        play the given req
        return False if enqueued
        """
        self.queue.enqueue(req, top=top)
        # await self.put(self._consume)
        # eprint("BEFORE await self._consume()", self.PLAYING)
        played_now: bool = await self._consume()
        # eprint(
        #    "AFTER await self._consume()",
        #   "self.PLAYING",
        #   self.PLAYING,
        #   "played_now",
        #   played_now,
        # )
        return played_now

    @log_called_function
    async def disconnect(self):
        if self.voice:
            await self.voice.disconnect()

    @log_called_function
    async def skip(self) -> bool:
        skiped = self.voice and self.PLAYING
        if skiped:
            self.queue.set_skip()
            self.voice.stop()
        return skiped

    @log_called_function
    async def loop(self) -> bool:
        return self.queue.toggle_loop()

    @log_called_function
    async def loopqueue(self) -> bool:
        return self.queue.toggle_loopqueue()

    @log_called_function
    async def replay(self) -> bool:
        replayed = self.voice and self.PLAYING
        if replayed:
            self.queue.set_replay()
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
        if self.voice.is_playing():
            self.voice.pause()
            return True
        return False

    @log_called_function
    async def resume(self) -> bool:
        if self.voice.is_paused():
            self.voice.resume()
            return True
        return False


# ------------------------------------------------------------------------------


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guilds_player = {}

    def get_player(self, guild_id) -> Player:
        player = self.guilds_player.get(guild_id)
        if player is None:
            player = Player(self.bot, guild_id)
            self.guilds_player[guild_id] = player
        return player

    def get_player_and_locale(self, ctx):
        return self.get_player(ctx.guild.id), get_locale_from_context(ctx)

    # --------------------------------------------------------------------------
    # Song
    # --------------------------------------------------------------------------

    @commands.command(aliases=["summon"])
    @commands.check(Check.author_channel)
    @commands.guild_only()
    async def join(self, ctx):
        player, locale = self.get_player_and_locale(ctx)

        voice_channel = ctx.author.voice.channel
        joined: bool = await player.join(voice_channel)
        if joined:
            await ctx.send(locale.notif_joined.format(voice_channel))
        else:
            debug("join", "not joined")

    @commands.command(aliases=["p"])
    @commands.check(Check.author_channel)
    @commands.guild_only()
    async def play(self, ctx, *args, top=False, skip=False) -> bool:
        # TODO : check if the bot is playing if the author channel is different
        # from the bot's one
        player, locale = self.get_player_and_locale(ctx)

        # searching for the given query
        query = " ".join(args)
        await ctx.send(locale.notif_loop_searching.format(query))
        req = await Request.from_youtube(query, ctx.message)
        if req is None:
            await ctx.send(locale.error_no_matches)
            return False

        # play the song
        played_now: bool = await player.play(req, top=top)
        if skip and not played_now:
            skiped: bool = await player.skip()

        # create the content or embed
        content, embed = None, None
        if skip:  # playskip
            embed = EmbedGenerator.play_queued(req, estimated="Now", position="Now")
        elif played_now:  # play
            content = locale.notif_playing_now.format(req.title)
        elif top:  # queued top
            embed = EmbedGenerator.play_queued(
                req, estimated=player.estimated_next, position=1
            )
        else:  # queued
            embed = EmbedGenerator.play_queued(
                req, estimated=player.estimated, position=player.queue.waiting
            )

        await ctx.send(content=content, embed=embed)
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
        player, locale = self.get_player_and_locale(ctx)
        t = player.voice.source.progress
        embed = EmbedGenerator.nowplaying(player.queue.current, t)
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
        player, locale = self.get_player_and_locale(ctx)
        replayed = await player.replay()
        if replayed:
            await ctx.send(locale.notif_replayed)
        else:
            debug("replay", "not replayed")

    @commands.command(aliases=["repeat"])
    @commands.check(Check.same_channel)
    @commands.guild_only()
    async def loop(self, ctx):
        player, locale = self.get_player_and_locale(ctx)
        looped = await player.loop()
        if looped:
            await ctx.send(locale.notif_loop_enabled)
        else:
            await ctx.send(locale.notif_loop_disabled)

    @commands.command(aliases=["skip", "next", "s"])
    @commands.check(Check.is_playing)
    @commands.check(Check.same_channel)
    @commands.guild_only()
    async def voteskip(self, ctx):
        player, locale = self.get_player_and_locale(ctx)
        skiped: bool = await player.skip()
        if skiped:
            await ctx.send(locale.notif_skipped)
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
        player, locale = self.get_player_and_locale(ctx)
        paused = await player.pause()
        if paused:
            await ctx.send(locale.notif_paused)
        else:
            await ctx.send(locale.error_already_paused)

    @commands.command(aliases=["re", "res", "continue"])
    @commands.check(Check.is_playing)
    @commands.check(Check.same_channel)
    @commands.guild_only()
    async def resume(self, ctx):
        player, locale = self.get_player_and_locale(ctx)
        resumed = await player.resume()
        if resumed:
            await ctx.send(locale.notif_resumed)
        else:
            await ctx.send(locale.error_not_paused)

    @commands.command(aliases=["l", "ly"])
    async def lyrics(self, ctx):
        await ctx.send("NotImplementedError")

    @commands.command(aliases=["dc", "leave", "dis"])
    @commands.check(Check.same_channel)
    @commands.guild_only()
    async def disconnect(self, ctx):
        player, locale = self.get_player_and_locale(ctx)

        disconnected = await player.disconnect()
        if disconnected:
            await ctx.send(locale.notif_disconnected)
        else:
            debug("disconnect", "not disconnected")

    # --------------------------------------------------------------------------
    # Queue
    # --------------------------------------------------------------------------

    @commands.command(aliases=["q"])
    @commands.guild_only()
    async def queue(self, ctx):
        player, locale = self.get_player_and_locale(ctx)
        embed = EmbedGenerator.queue(ctx, player.queue)
        await ctx.send(embed=embed)

    @commands.command(aliases=["qloop", "lq", "queueloop"])
    async def loopqueue(self, ctx):
        player, locale = self.get_player_and_locale(ctx)

        looped_queue = await player.loopqueue()
        if looped_queue:
            await ctx.send(locale.notif_queue_loop_enabled)
        else:
            await ctx.send(locale.notif_queue_loop_disabled)

    @commands.command(aliases=["m", "mv"])
    async def move(self, ctx, old_positon, new_position=None):
        ...

    @commands.command(aliases=["st"])
    async def skipto(self, ctx, position: int):
        ...

    @commands.command(aliases=["random"])
    async def shuffle(self, ctx):
        ...

    @commands.command(aliases=["rm"])
    async def remove(self, ctx, numbers: int):
        ...

    @commands.command(aliases=["cl"])
    async def clear(self, ctx, user):
        ...

    @commands.command(aliases=["lc"])
    async def leavecleanup(self, ctx):
        ...

    @commands.command(aliases=["rmd", "rd", "drm"])
    async def removedupes(self, ctx):
        ...

    # --------------------------------------------------------------------------

    @commands.command()
    async def test(self, ctx):
        ...

