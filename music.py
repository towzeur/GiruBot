import discord
import asyncio
import youtube_dl

from discord.ext import commands
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
        if not player.is_playing:
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

    @classmethod
    async def from_youtube(cls, query, message, blocking=False):

        ytdl_kwargs = dict(
            download=False,
            ie_key=None,
            extra_info={},
            process=True,
            force_generic_extractor=False,
        )

        with youtube_dl.YoutubeDL(YTDL_OPTIONS) as ytdl:
            # Arguments:
            # url -- URL to extract
            # Keyword arguments:
            # download -- whether to download videos during extraction
            # ie_key -- extractor key hint
            # extra_info -- dictionary containing the extra values to add to each result
            # process -- whether to resolve all unresolved references (URLs, playlist items),
            #    must be True for download to work.
            # force_generic_extractor -- force using the generic extractor
            ytdl.cache.remove()
            # ytdl.prepare_filename(info_dict)
            # ytdl.download([url])
            if blocking:
                info: dict = ytdl.extract_info(query, **ytdl_kwargs)
            else:
                downloader = partial(ytdl.extract_info, query, **ytdl_kwargs)
                # loop = asyncio.get_event_loop()
                loop = asyncio.get_running_loop()
                info: dict = await loop.run_in_executor(None, downloader)

        # except (youtube_dl.utils.ExtractorError, youtube_dl.utils.DownloadError) as e:
        #    debug("from_youtube", "exception", e)
        #    return None

        try:
            with open("tmp_entries.txt", "w", encoding="utf-8") as f:
                pprint(info, stream=f)
        except Exception as e:
            eprint(e)
            print("**" * 20)
            # return None

        # this value is not an exact match, but it's a good approximation
        entry = info["entries"][0] if "entries" in info else info

        # pprint(info)
        return cls(
            message, query, entry, entry["title"], entry["url"], entry["duration"]
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

        self.q = asyncio.Queue()
        self.locale = self.bot.get_cog("Locales")
        self.voice: discord.VoiceClient = None

        event_loop = asyncio.get_event_loop()
        event_loop.create_task(self.run())

    # --------------------------------------------------------------------------

    @property
    def is_playing(self) -> bool:
        return self.state is Player.State.PLAYING

    def set_playing(self):
        self.state = Player.State.PLAYING

    @property
    def is_idle(self) -> bool:
        return self.state is Player.State.IDLE

    def set_idle(self):
        self.state = Player.State.IDLE

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
    def _after(self, error):
        print("after", error)
        self.queue.next()
        self.set_idle()
        self.queue.unset_flag()
        self.q.put_nowait(self._consume)

    @log_called_function
    async def _play_now(self, req):
        print("_play_now >> vid :", req.info["webpage_url"])
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
        self.voice.stop()

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
        debug("_consume", "flag", self.queue.flag, "option", self.queue.modifiers)
        if self.is_idle:
            debug("_consume", "(IDLE)", ">> now playing")
            if self.queue.current:
                debug("_consume >> playing now")
                self.set_playing()
                await self._play_now(self.queue.current)
            else:
                debug("_consume", "(IDLE)", ">> nothing to consume !")
        elif self.is_playing:
            debug("_consume", "(PLAYING)", ">> queued")
        else:
            debug("_consume", "(UNKOWN)", ">> ?")

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
        return self.is_idle

    @log_called_function
    async def disconnect(self):
        if self.voice:
            await self.voice.disconnect()

    @log_called_function
    async def skip(self) -> bool:
        skiped = self.voice and self.is_playing
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
        replayed = self.voice and self.is_playing
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
        now_played: bool = await player.play(req, top=top)

        # playtop
        if skip:
            embed = EmbedGenerator.play_queued(req, estimated="Now", position="Now")
            await ctx.send(embed=embed)
            if not now_played:  # skip if necessary
                skiped: bool = await player.skip()
        elif now_played:
            await ctx.send(locale.notif_playing_now.format(req.title))
        else:
            estimated = player.estimated_next if top else player.estimated
            position = 1 if top else player.queue.waiting
            embed = EmbedGenerator.play_queued(
                req, estimated=estimated, position=position
            )
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

