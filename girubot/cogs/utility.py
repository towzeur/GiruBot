from datetime import datetime
from typing import Optional

import discord
from discord.embeds import Embed
from discord.ext import commands
from discord.ext.commands import Context, BucketType, Bot
from discord import Member


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot: Bot = bot

    @commands.command(
        brief="Display a user avatar",
        help="Display a user avatar in a embed message.",
        usage="[member]",
    )
    # @commands.cooldown(1, 5.0, BucketType.user)
    @commands.guild_only()
    async def avatar(self, ctx: Context, who: Optional[Member] = None):
        who: Member = ctx.author if who is None else who

        embed = discord.Embed(title="", description="", color=0x4F4F4F)
        embed.set_footer(
            text=f"Requested by {ctx.author}",
            icon_url=f"{ctx.author.display_avatar.url}",
        )
        embed.set_author(
            name=f"{who}'s avatar",
            icon_url="https://cdn.discordapp.com/attachments/573225654452092930/908327963718713404/juke-icon.png",
        )
        embed.set_image(url=who.display_avatar.url)
        # embed.set_image(url=who.avatar_url)
        await ctx.send(embed=embed)
