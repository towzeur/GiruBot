import discord
import asyncio
import youtube_dl
from enum import Enum
from pprint import pprint

import text_en as TEXT

# from music_data_extractor import MusicFileWrapper
from utils import convert_to_youtube_time_format, Markdown


# Fuck your useless bugreports message that gets two link embeds and confuses users
youtube_dl.utils.bug_reports_message = lambda: ""

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


def search_youtube(query):
    with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(query, download=False)
    if "entries" in info:  # playlist
        info = info["entries"][0]
    return info


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
    def __init__(self):
        self.q = asyncio.Queue()
        self.open, self.close = [], []
        self.state = GiruState.IDLE
        self.loop = False
        self.a = "A"

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
            print("[run] try")
            while True:
                handler, message, args = await self.q.get()
                await handler(message, args)
        except Exception as e:  #  asyncio.CancelledError
            print("[run] Exception", e)
        finally:
            print("[run] finally")

    def play_after(self, e):
        print("play_after")
        if e:
            print("PLAY AFTER", "e", e)

    async def play(self, message, args):
        print("PLAY")

        if self.state is GiruState.IDLE:
            self.open.append(args)
            await self.ensure_voice(message.author.voice.channel)
            audio = discord.FFmpegPCMAudio(args, executable="ffmpeg.exe")
            player = discord.PCMVolumeTransformer(audio, volume=DEFAULT_VOLUME)
            self.voice.play(player, after=self.play_after)

        elif self.state is GiruState.PLAYING:
            pass

        elif self.state is GiruState.PAUSED:
            self.open.append(args)

    def skip(self, message, args):
        pass

    def stop(self, message, args):
        pass

    def pause(self, message, args):
        pass

    def resume(self, message, args):
        pass

    def loop(self, message, args):
        self.loop = not self.loop


# ------------------------------------------------------------------------------


class GiruMusicBot:
    def __init__(self, client, server_id):
        self.client = client
        self.server_id = server_id

        self.girumusic = GiruMusic()
        print(self.girumusic.a, "TESTTTTTTTTTTTTTTTT")
        self.client.loop.create_task(self.girumusic.run())

    # async def ensure_voice(self, author_channel):
    #    author_channel =
    # Check if there is already a voice in the server
    # self.voice = discord.utils.find(
    #    lambda v: v.guild.id == self.server_id, self.client.voice_clients
    # )
    # there is no voice in the guild
    #    if self.voice is None:
    #        self.voice = await author_channel.connect()
    # not in the right voice channel
    #    if self.voice.channel.id != author_channel.id:
    #        await self.voice.move_to(author_channel)

    ########################

    async def play_handler(self, message, query):
        # user have to be in a voice channel
        if message.author.voice is None:
            return await message.channel.send(TEXT.error_user_not_in_channel)

        # searching for the given query
        await message.channel.send(TEXT.notif_loop_searching.format(query))
        info = search_youtube(query)
        if info is None:
            return await message.channel.send(TEXT.error_no_matches)

        # play the song
        await self.girumusic.put((self.girumusic.play, message, info["url"]))

        # embed message
        # if the queue isn't empty
        return
        if self.girumusic.voice.is_playing():
            embed = discord.Embed(
                title="Added to queue",
                description=Markdown.bold(info["title"]),
                color=0x00AFF4,
            )
            # embed.set_image(*, query)
            embed.add_field(
                name=Markdown.bold("Channel"),
                value=str(message.author.voice.channel),
                inline=True,
            )
            embed.add_field(
                name=Markdown.bold("Song Duration"),
                value=convert_to_youtube_time_format(info["duration"]),
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
            return await message.channel.send(embed=embed)

        # now playing
        return await message.channel.send(TEXT.notif_playing_now.format(info["title"]))

    async def join_handler(self, message):
        if message.author.voice is None:
            return await message.channel.send(TEXT.error_user_not_in_channel)
        await self.ensure_voice(message.author.voice.channel)
        await message.channel.send(
            TEXT.notif_joined.format(message.author.voice.channel)
        )

    async def disconnect_handler(self, message):
        self.update_voice()
        if self.voice is not None:
            await self.voice.disconnect()
            await message.channel.send(TEXT.notif_disconnected)
        else:
            await message.channel.send(TEXT.error_no_voice_channel)

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
        self.loop = not self.loop
        if self.loop:
            return await message.channel.send(TEXT.notif_loop_enabled)
        else:
            return await message.channel.send(TEXT.notif_loop_disabled)
