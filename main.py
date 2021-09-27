from os import stat
import discord
import random
import json
import time
import re
import glob
from pathlib import Path
from dataclasses import dataclass

from utils import loading_bar, debug
from options import LOCALE_DEFAULT, LOCALE_FILE_TEMPLATE
from musicBot import GiruMusicBot


class Locale:
    AVAILABLE = [
        Path(file).stem for file in glob.glob(LOCALE_FILE_TEMPLATE.format("*"))
    ]
    CACHE = {}

    def __init__(self, language=LOCALE_DEFAULT):
        self.language = language
        assert language in Locale.AVAILABLE
        if language not in Locale.CACHE:
            locale_filename = LOCALE_FILE_TEMPLATE.format(language)
            with open(locale_filename, "r", encoding="utf8") as file:
                Locale.CACHE[language] = json.load(file)

    def __getattr__(self, attr):
        return Locale.CACHE[self.language].get(attr, None)


@dataclass
class GiruInstance:
    guild_id: int
    locale: Locale
    music: GiruMusicBot


class GiruInstancesManager:
    INSTANCES = {}

    @staticmethod
    def instanciate(guild_id):
        # TODO : maybe check for the guild's fav locale in a database
        giru_locale = Locale(language=LOCALE_DEFAULT)
        giru_music = GiruMusicBot(guild_id, giru_locale)
        instance = GiruInstance(guild_id, giru_locale, giru_music)
        GiruInstancesManager.INSTANCES[guild_id] = instance

    @staticmethod
    def get(guild_id):
        if guild_id not in GiruInstancesManager.INSTANCES:
            GiruInstancesManager.instanciate(guild_id)
        return GiruInstancesManager.INSTANCES[guild_id]


class GiruClient(discord.Client):
    def __init__(self):
        super().__init__()
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
        print(channel, user)
        print(dir(channel))
        print()

    async def on_message_delete(self, message):
        debug("deleted msg", message)
        # if message.guild.id == 530685859956260924:
        #    return
        # audits = message.guild.audit_logs(
        #    limit=10, action=discord.AuditLogAction.message_delete
        # )
        # find = False
        # async for audit in audits:
        #    if audit.target == message.author:
        #        find = True
        #        break
        # auth = audit.user if find else message.author
        # msg = "{} has deleted the message:```{}```".format(auth, message.content)
        # await message.channel.send(msg)

    async def on_member_join(self, member):
        if member.guild.system_channel:
            to_send = f"Welcome {member.mention} to {member.guild.name}!"
            await member.guild.system_channel.send(to_send)

    async def on_message(self, message):
        # FILTER OWN SELF MESSAGE
        if message.author == self.user:
            return

        instance = GiruInstancesManager.get(message.guild.id)

        # PRIVATE MESSAGE
        if type(message.channel) is discord.channel.DMChannel:
            debug("DM")
            return await message.channel.send(f"Hello {message.author}")

        # RYTHM
        if message.content.startswith("!p "):
            query = message.content[len("!p ") :].strip()
            debug("YOUTUBE (!p)", query)
            return await instance.music.play_handler(message, query)

        # CONCERNED BY THIS MESSAGE
        prefix = "!"
        if message.content.startswith(prefix):
            # debug(str(msg_args))
            msg_args = message.content[len(prefix) :].split()

            # rythm's music commands
            if msg_args[0] in (
                "join",
                "disconnect",
                "pause",
                "resume",
                "skip",
                "loop",
                "np",
                "replay",
            ):
                handler = getattr(instance.music, f"{msg_args[0]}_handler")
                return await handler(message)

            # test
            if msg_args[0] == "hello":
                return await message.channel.send("Hello {message.author.mention}")
            elif msg_args[0] == "ping":
                return await message.channel.send("pong")
            elif msg_args[0] == "kamas":
                return await message.channel.send(f"{random.randint(1, 10000)} Kamas")
            else:
                debug("!g ¯\_(ツ)_/¯")


if __name__ == "__main__":

    with open("secrets.json") as f:
        secret = json.load(f)

    client = GiruClient()
    client.run(secret["TOKEN"])
