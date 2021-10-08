import glob
import json

from discord.ext import commands
from pathlib import Path
from types import SimpleNamespace

from options import LOCALE_DEFAULT, LOCALE_FILE_TEMPLATE


class Locales(commands.Cog):
    AVAILABLE = [
        Path(file).stem for file in glob.glob(LOCALE_FILE_TEMPLATE.format("*"))
    ]
    CACHE = {}

    def __init__(self, bot):
        self.bot = bot
        self.guilds_language = {}
        Locales.load(LOCALE_DEFAULT)

    @classmethod
    def load(cls, language):
        """load in CACHE the given locale"""
        if language not in cls.AVAILABLE:
            default_locale = cls.CACHE[LOCALE_DEFAULT]
            # raise Exception("Unsuported locale")
            return default_locale
        if language not in cls.CACHE:
            locale_filename = LOCALE_FILE_TEMPLATE.format(language)
            with open(locale_filename, "r", encoding="utf8") as file:
                cls.CACHE[language] = json.load(
                    file, object_hook=lambda d: SimpleNamespace(**d)
                )
        return cls.CACHE[language]

    def get_guild_locale(self, guild_id: int) -> dict:
        # Guild's locale already registred
        if guild_id in self.guilds_language:
            guild_language = self.guilds_language[guild_id]
        else:
            # load it
            # TODO : search in a db for a guild fav locale
            guild_language = LOCALE_DEFAULT

        return Locales.load(guild_language)

    async def send(self, ctx, giru_message, *args):
        locale = self.get_guild_locale(ctx.guild.id)
        message = locale.get(giru_message).format(*args)
        await ctx.send(message)

