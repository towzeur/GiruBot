import typing

from datetime import datetime
from discord.ext import commands

from girubot import embeddings


class Others(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        aliases=["purge", "clean"], brief="Deletes the bot's messages and commands."
    )
    @commands.guild_only()
    async def prune(self, ctx):
        await ctx.send("NotImplementedError")

    @commands.command(aliases=["links"], brief="Shows GiruBot's official links!")
    @commands.guild_only()
    async def invite(self, ctx):
        await ctx.send("NotImplementedError")

    @commands.command(aliases=[], brief="Shows information about GiruBot!")
    @commands.guild_only()
    async def info(self, ctx):
        await ctx.send("NotImplementedError")

    @commands.command(
        aliases=["debug"], brief="Checks the server shard your server is in."
    )
    @commands.guild_only()
    async def shard(self, ctx):
        await ctx.send("NotImplementedError")

    @commands.command(aliases=[], brief="Checks the bot's response time to Discord.")
    @commands.guild_only()
    async def ping(self, ctx):
        api_response_time = -1
        message_response_time = -1
        # Measures latency between a HEARTBEAT and a HEARTBEAT_ACK in seconds.
        # This could be referred to as the Discord WebSocket protocol latency.
        websocket_heartbeat: float = int(1000 * self.bot.latency)

        embed = embeddings.ping(
            api_response_time, message_response_time, websocket_heartbeat
        )
        await ctx.send(embed=embed)

    @commands.command(aliases=[], brief="Lists all command aliases.")
    @commands.guild_only()
    async def aliases(self, ctx):
        await ctx.send("NotImplementedError")

