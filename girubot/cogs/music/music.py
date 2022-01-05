from discord.ext import commands

from girubot.locales import locales
from girubot.utils import log_called_function, debug, eprint
from girubot import embeddings
from girubot import checks

from .player import Player
from .request import Request


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guilds_player = {}

    def get_player(self, ctx) -> Player:
        guild_id = ctx.guild.id
        if guild_id not in self.guilds_player:
            self.guilds_player[guild_id] = Player(self.bot, guild_id)
        return self.guilds_player[guild_id]

    # --------------------------------------------------------------------------
    # Song
    # --------------------------------------------------------------------------

    @commands.command(aliases=["summon"])
    @commands.check(checks.author_channel)
    @commands.guild_only()
    async def join(self, ctx):
        player = self.get_player(ctx)
        locale = locales.get_language(ctx)

        voice_channel = ctx.author.voice.channel
        joined: bool = await player.join(voice_channel)
        if joined:
            await ctx.send(locale.notif_joined.format(voice_channel))
        else:
            debug("join", "not joined")

    @commands.command(aliases=["p"])
    @commands.check(checks.author_channel)
    @commands.guild_only()
    async def play(self, ctx, *args, top=False, skip=False) -> bool:
        # TODO : check if the bot is playing if the author channel is different
        # from the bot's one
        player = self.get_player(ctx)
        locale = locales.get_language(ctx)

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
            embed = embeddings.play_queued(req, estimated="Now", position="Now")
        elif played_now:  # play
            content = locale.notif_playing_now.format(req.title)
        elif top:  # queued top
            embed = embeddings.play_queued(
                req, estimated=player.estimated_next, position=1
            )
        else:  # queued
            embed = embeddings.play_queued(
                req, estimated=player.estimated, position=player.queue.waiting
            )

        await ctx.send(content=content, embed=embed)
        return True

    @commands.command(aliases=["pt", "ptop"])
    async def playtop(self, ctx, *args):
        await self.play(ctx, *args, top=True, skip=False)

    @commands.command(aliases=["ps", "pskip", "playnow", "pn"])
    @commands.check(checks.author_channel)
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
    @commands.check(checks.is_playing)
    @commands.check(checks.same_channel)
    @commands.guild_only()
    async def nowplaying(self, ctx):
        player = self.get_player(ctx)
        locale = locales.get_language(ctx)
        t = player.voice.source.progress
        embed = embeddings.nowplaying(player.queue.current, t)
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
    @commands.check(checks.is_playing)
    @commands.check(checks.same_channel)
    @commands.guild_only()
    async def replay(self, ctx):
        player = self.get_player(ctx)
        locale = locales.get_language(ctx)

        replayed = await player.replay()
        if replayed:
            await ctx.send(locale.notif_replayed)
        else:
            debug("replay", "not replayed")

    @commands.command(aliases=["repeat"])
    @commands.check(checks.same_channel)
    @commands.guild_only()
    async def loop(self, ctx):
        player = self.get_player(ctx)
        locale = locales.get_language(ctx)
        looped = await player.loop()
        if looped:
            await ctx.send(locale.notif_loop_enabled)
        else:
            await ctx.send(locale.notif_loop_disabled)

    @commands.command(aliases=["skip", "next", "s"])
    @commands.check(checks.is_playing)
    @commands.check(checks.same_channel)
    @commands.guild_only()
    async def voteskip(self, ctx):
        player = self.get_player(ctx)
        locale = locales.get_language(ctx)
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
    @commands.check(checks.is_playing)
    @commands.check(checks.same_channel)
    @commands.guild_only()
    async def pause(self, ctx):
        player = self.get_player(ctx)
        locale = locales.get_language(ctx)
        paused = await player.pause()
        if paused:
            await ctx.send(locale.notif_paused)
        else:
            await ctx.send(locale.error_already_paused)

    @commands.command(aliases=["re", "res", "continue"])
    @commands.check(checks.is_playing)
    @commands.check(checks.same_channel)
    @commands.guild_only()
    async def resume(self, ctx):
        player = self.get_player(ctx)
        locale = locales.get_language(ctx)
        resumed = await player.resume()
        if resumed:
            await ctx.send(locale.notif_resumed)
        else:
            await ctx.send(locale.error_not_paused)

    @commands.command(aliases=["l", "ly"])
    async def lyrics(self, ctx):
        await ctx.send("NotImplementedError")

    @commands.command(aliases=["dc", "leave", "dis"])
    @commands.check(checks.same_channel)
    @commands.guild_only()
    async def disconnect(self, ctx):
        player = self.get_player(ctx)
        locale = locales.get_language(ctx)

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
        player = self.get_player(ctx)
        # locale = locales.get_language(ctx)
        embed = embeddings.queue(ctx, player.queue)
        await ctx.send(embed=embed)

    @commands.command(aliases=["qloop", "lq", "queueloop"])
    async def loopqueue(self, ctx):
        player = self.get_player(ctx)
        locale = locales.get_language(ctx)

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

