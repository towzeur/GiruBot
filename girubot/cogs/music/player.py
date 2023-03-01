import asyncio
import discord

from enum import Enum
from typing import Optional

from .player_queue import PlayerQueue
from .audio_source_tracked import AudioSourceTracked

from girubot.config import (
    FFMPEG_BEFORE_OPTIONS,
    FFMPEG_BEFORE_OPTIONS,
    FFMPEG_EXECUTABLE,
    FFMPEG_OPTIONS,
    DEFAULT_VOLUME,
)
from girubot.utils import log_called_function  # , debug, eprint
from loguru import logger


def assert_get_voice(func):
    # create a decorator that will decorate method of the Player class
    # and need to be async to be able to use await
    # before entering the method, it will call self.get_voice()
    # if the method returns None, it will return False
    # otherwise, it will return the result of the method
    async def wrapper(self, *args, **kwargs):
        voice = await self.get_voice()
        if voice is None:
            return False
        return await func(self, *args, **kwargs)

    return wrapper


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

    async def get_voice(
        self,
        channel: Optional[discord.VoiceChannel] = None,
    ) -> Optional[discord.VoiceClient]:
        """
        Return the current voice client if any
        or create a new one if none
        """
        vc_exists = isinstance(self.voice, discord.VoiceClient)
        ch_given = isinstance(channel, discord.VoiceChannel)
        if not vc_exists and not ch_given:
            return None
        # a channel is given
        if ch_given:
            # create a new voice client
            if not vc_exists or not self.voice.is_connected():
                self.voice = await channel.connect()
            # move it to the given channel
            if self.voice.channel.id != channel.id:
                await self.voice.move_to(channel)
        return self.voice

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
            logger.error(f"_after ERROR: {error}")
        self.state = Player.State.IDLE
        self.queue.next()
        self.bot.loop.create_task(self._consume())

    @log_called_function
    def _play_now(self, req) -> bool:
        logger.debug("req.info['webpage_url'] = " + str(req.info["webpage_url"]))
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
            logger.error("[ClientException] Failed to create the subprocess")
            return False

        try:
            # create a player
            player = discord.PCMVolumeTransformer(audio, volume=DEFAULT_VOLUME)
            player = AudioSourceTracked(player)
            player.read()
            # play it
            self.voice.play(player, after=self._after)
            return True
        except discord.ClientException:
            logger.error("[ClientException] Already playing audio or not connected")
        except TypeError:
            logger.error(
                "[TypeError] Source is not a AudioSource or after is not a callable"
            )
        except discord.OpusNotLoaded:
            logger.error(
                "[OpusNotLoaded] Source is not opus encoded and opus is not loaded"
            )
        return False

    @log_called_function
    async def _consume(self):
        msg = ("flag", self.queue.flag, "modifiers", self.queue.modifiers)
        logger.debug(" ".join(map(str, msg)))

        if self.state is self.State.IDLE:
            logger.debug("(IDLE) >> now PLAYING")
            req = self.queue.current
            if req is not None:
                logger.debug("PLAYING now")
                self.state = Player.State.PLAYING
                joined = await self.join(req.message.author.voice.channel)
                if joined:
                    self._play_now(req)
                    return True
                else:
                    logger.error("Failed to join the channel")
            else:
                logger.debug("(IDLE) >> nothing to consume !")
        elif self.state is self.State.PLAYING:
            logger.debug("(PLAYING) >> queued")
        else:
            logger.debug("(UNKOWN) >> ?")
        return False

    # --------------------------------------------------------------------------

    @log_called_function
    async def join(self, channel):
        try:
            await self.get_voice(channel)
            return True
        except asyncio.TimeoutError:
            logger.error(
                "[TimeoutError] Could not connect to the voice channel in time."
            )
        except discord.ClientException:
            logger.error("[ClientException] Already connected to a voice channel.")
        return False

    @log_called_function
    async def play(self, req, top=False) -> bool:
        """
        play the given req
        return False if enqueued
        """
        self.queue.enqueue(req, top=top)
        played_now: bool = await self._consume()
        return played_now

    @log_called_function
    @assert_get_voice
    async def skip(self) -> bool:
        if self.is_playing():
            self.queue.set_skip()
            self.voice.stop()
            return True

    @log_called_function
    async def loop(self) -> bool:
        return self.queue.toggle_loop()

    @log_called_function
    async def loopqueue(self) -> bool:
        return self.queue.toggle_loopqueue()

    @log_called_function
    @assert_get_voice
    async def replay(self) -> bool:
        if self.is_playing():
            self.queue.set_replay()
            self.voice.stop()
            return True

    @log_called_function
    @assert_get_voice
    async def disconnect(self) -> bool:
        if self.voice.is_connected():
            await self.voice.disconnect()
            return True

    @log_called_function
    @assert_get_voice
    async def pause(self) -> bool:
        if self.voice.is_playing():
            self.voice.pause()
            return True

    @log_called_function
    @assert_get_voice
    async def resume(self) -> bool:
        if self.voice.is_paused():
            self.voice.resume()
            return True
