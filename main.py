import discord
from discord.ext import commands
import random
import json
from os import stat
from dataclasses import dataclass
import traceback
import sys

from utils import loading_bar, debug
from options import LOCALE_DEFAULT, LOCALE_FILE_TEMPLATE

# cog
from music import Music
from locales import Locales


@dataclass
class GiruInstance:
    guild_id: int
    locale: Locales
    music: Music


class GiruInstancesManager:
    INSTANCES = {}

    @staticmethod
    def instanciate(guild_id):
        # TODO : maybe check for the guild's fav locale in a database
        giru_locale = Locales(language=LOCALE_DEFAULT)
        giru_music = Music(guild_id, giru_locale)
        instance = GiruInstance(guild_id, giru_locale, giru_music)
        GiruInstancesManager.INSTANCES[guild_id] = instance

    @staticmethod
    def get(guild_id):
        if guild_id not in GiruInstancesManager.INSTANCES:
            GiruInstancesManager.instanciate(guild_id)
        return GiruInstancesManager.INSTANCES[guild_id]


class Giru(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.game = discord.Game("Giru bot v2")

    async def on_ready(self):
        debug("Logged on as", self.user)
        await self.change_presence(
            status=discord.Status.online, activity=self.game, afk=False
        )

    async def on_disconnect(self):
        pass

    async def on_typing(self, channel, user, when):
        pass

    async def on_group_join(self, channel, user):
        debug("on_group_join", channel, user)
        print(channel, user)
        # print(dir(channel))

    async def on_message_delete(self, message):
        debug("deleted msg", message)

    async def on_member_join(self, member):
        if member.guild.system_channel:
            to_send = f"Welcome {member.mention} to {member.guild.name}!"
            await member.guild.system_channel.send(to_send)

    # @bot.event
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            debug(error)
        else:
            print(f"Ignoring exception in command {ctx.command}:", file=sys.stderr)
            traceback.print_exception(
                type(error), error, error.__traceback__, file=sys.stderr
            )

    # async def on_message(self, message):
    #    # FILTER OWN SELF MESSAGE
    #    if message.author == self.user:
    #        return
    #    # debug("on_message", message)


if __name__ == "__main__":

    with open("secrets.json") as f:
        secret = json.load(f)

    bot = Giru(command_prefix="!")
    bot.add_cog(Locales(bot))
    bot.add_cog(Music(bot))
    bot.run(secret["TOKEN"])
