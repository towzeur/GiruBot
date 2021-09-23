import discord
import random
import asyncio
import glob
import os
import json
import time
import re

import text_en as TEXT
from utils import loading_bar
from musicBot import GiruMusicBot


def debug(*args, **kwargs):
    t_format = "%H:%M:%S"
    print(f"[{time.strftime(t_format)}]", *args, **kwargs)


def youtube_url_validation(url):
    youtube_regex = (
        r"(https?://)?(www\.)?"
        "(youtube|youtu|youtube-nocookie)\.(com|be)/"
        "(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})"
    )
    youtube_regex_match = re.match(youtube_regex, url)
    return bool(youtube_regex_match)


class GiruClient(discord.Client):
    def __init__(self):
        super().__init__()
        self.music_bots = {}
        self.game = discord.Game("Giru bot v2")

    def get_music_bot(self, message):
        # get the music bot or init it
        music_bot = self.music_bots.get(message.guild.id, None)
        if music_bot is None:
            music_bot = GiruMusicBot(self, message.guild.id)
            self.music_bots[message.guild.id] = music_bot
        return music_bot

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
        guild = member.guild
        if guild.system_channel is not None:
            to_send = "Welcome {0.mention} to {1.name}!".format(member, guild)
            await guild.system_channel.send(to_send)

    async def on_message(self, message):

        # FILTER OWN SELF MESSAGE
        if message.author == self.user:
            return

        # PRIVATE MESSAGE
        if type(message.channel) is discord.channel.DMChannel:
            debug("DM")
            return await message.channel.send(f"Hello {message.author}")

        # RYTHM
        if message.content.startswith("!p "):
            query = message.content[len("!p ") :].strip()
            debug("YOUTUBE (!p)", query)
            music_bot = self.get_music_bot(message)
            return await music_bot.play_handler(message, query)

        # CONCERNED BY THIS MESSAGE
        prefix = "!"
        if message.content.startswith(prefix):
            msg_args = message.content[len(prefix) :].split()
            # debug(str(msg_args))

            music_bot = self.get_music_bot(message)

            if msg_args[0] == "join":
                return await music_bot.join_handler(message)
            elif msg_args[0] == "disconnect":
                return await music_bot.disconnect_handler(message)
            elif msg_args[0] == "pause":
                return await music_bot.pause_handler(message)
            elif msg_args[0] == "resume":
                return await music_bot.resume_handler(message)
            elif msg_args[0] == "skip":
                return await music_bot.skip_handler(message)
            elif msg_args[0] == "loop":
                return await music_bot.loop_handler(message)

            if msg_args[0] == "hello":
                return await message.channel.send("Hello {message.author.mention}")
            elif msg_args[0] == "ping":
                return await message.channel.send("pong")
            elif msg_args[0] == "kamas":
                return await message.channel.send(f"{random.randint(1, 10000)} Kamas")
            elif msg_args[0] == "test":
                embed = discord.Embed(
                    title="Added to queue",
                    description="**Title song**",
                    color=0x0096CF,
                    type="rich",
                )
                # embed.set_image(*, url)
                embed.add_field(name="**Channel**", value="TEST GAME", inline=True)
                embed.add_field(name="**Song Duration**", value="06:32", inline=True)
                embed.add_field(
                    name="**Estimated time until playing**", value="35:32", inline=False
                )
                embed.add_field(name="**Position in queue**", value="1", inline=True)
                # debug(embed.to_dict())
                await message.channel.send(embed=embed)
            else:
                debug("!g ¯\_(ツ)_/¯")

        """
        elif message.content[3:] in [
            "join",
            "disconnect",
            "pause",
            "resume",
            "skip",
            "loop",
        ]:
            bot = self.get_music_bot(message.guild.id)
            handler = getattr(bot, message.content[3:] + "_handler")
            await handler(message)

        elif message.content.startswith("!g ytb"):
            bot = self.get_music_bot(message.guild.id)
            query = message.content[len("!g ytb") :].strip()
            await bot.play_handler(message, query, local=False, feedback=True)

        """


if __name__ == "__main__":

    with open("secrets.json") as f:
        secret = json.load(f)

    client = GiruClient()
    client.run(secret["TOKEN"])
