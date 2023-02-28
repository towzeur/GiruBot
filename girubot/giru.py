import discord
import traceback
import sys

from discord.ext import commands  # ,tasks

from girubot.utils import debug, eprint
from loguru import logger


class Giru(commands.Bot):
    def __init__(self, *args, name: str = "Giru bot v2", **kwargs):
        super().__init__(*args, **kwargs)
        self.game = discord.Game(name)
        self.initial_extensions = [
            "girubot.cogs.music",
            #'cogs.foo',
            #'cogs.bar',
        ]
        logger.debug("Giru init")

    # -----------------------------------------------------------------------

    async def setup_hook(self):
        # self.background_task.start()
        # self.session = aiohttp.ClientSession()
        logger.debug("Giru setup_hook")
        for ext in self.initial_extensions:
            logger.debug(f"loading {ext} ...")
            await self.load_extension(ext)

    async def close(self):
        await super().close()
        # await self.session.close()

    # @tasks.loop(minutes=10)
    # async def background_task(self):
    #    print('Running background task...')

    # -----------------------------------------------------------------------

    async def on_ready(self):
        logger.info(f"Logged on as {self.user}")
        await self.change_presence(status=discord.Status.online, activity=self.game)

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
            eprint(error)
        elif isinstance(error, commands.errors.CommandNotFound):
            eprint("CommandNotFound", error, commands.errors.CommandNotFound)
        else:
            print(f"Ignoring exception in command {ctx.command}:", file=sys.stderr)
            traceback.print_exception(
                type(error), error, error.__traceback__, file=sys.stderr
            )

    async def on_message(self, message):
        if self.user.mentioned_in(message):
            msg = f"{message.author.mention} hello !"
            await message.channel.send(msg)
        else:
            await self.process_commands(message)

    #    # FILTER OWN SELF MESSAGE
    #    if message.author == self.user:
    #        return
    #    # debug("on_message", message)
