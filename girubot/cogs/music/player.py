import asyncio
import discord

from enum import Enum

from .player_queue import PlayerQueue
from .audio_source_tracked import AudioSourceTracked

from girubot.config import (
    FFMPEG_BEFORE_OPTIONS,
    FFMPEG_BEFORE_OPTIONS,
    FFMPEG_EXECUTABLE,
    FFMPEG_OPTIONS,
    DEFAULT_VOLUME,
)
from girubot.utils import log_called_function, debug, eprint


class Player:
    class State(Enum):
        IDLE = 1
        PLAYING = 2

    def __init__(self, bot, guild_id):
        self.bot = bot
        self.guild_id = guild_id
        self.voice: discord.VoiceClient = None
        self.queue = PlayerQueue()
        self.state = Player.State.IDLE

    # --------------------------------------------------------------------------

    def is_playing(self) -> bool:
        return self.state is Player.State.PLAYING

    def is_idle(self) -> bool:
        return self.state is Player.State.IDLE

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
        if self.state is self.State.IDLE:
            debug("_consume", "(IDLE)", ">> now PLAYING")
            req = self.queue.current
            if req is not None:
                debug("_consume >> PLAYING now")
                self.state = Player.State.PLAYING
                await self.join(req.message.author.voice.channel)
                self._play_now(req)
                return True
            else:
                debug("_consume", "(IDLE)", ">> nothing to consume !")
        elif self.state is self.State.PLAYING:
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
        played_now: bool = await self._consume()
        return played_now

    @log_called_function
    async def disconnect(self):
        if self.voice:
            await self.voice.disconnect()

    @log_called_function
    async def skip(self) -> bool:
        skiped = self.voice and self.is_playing()
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
        replayed = self.voice and self.is_playing()
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
