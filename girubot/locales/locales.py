import glob
import json

from os import stat
from typing import Dict, List
from pathlib import Path
from types import SimpleNamespace

from girubot.config import LOCALE_DEFAULT, LOCALE_FILE_TEMPLATE
from girubot.utils import AttrDict


class Language(AttrDict):
    def __init__(self):
        super().__init__()

    @classmethod
    def from_code(cls, code: str):
        filename = Path(LOCALE_FILE_TEMPLATE.format(code))
        if not filename.exists():
            print(f"code : <{code}> not found, loading {LOCALE_DEFAULT}")
            filename = Path(LOCALE_FILE_TEMPLATE.format(LOCALE_DEFAULT))

        with open(filename, "r", encoding="utf8") as file:
            lang = json.load(file)

        return cls.from_dict(lang)

    @staticmethod
    def available() -> List[str]:
        filenames = glob.glob(LOCALE_FILE_TEMPLATE.format("*"))
        return [Path(file).stem for file in filenames]


class Locales:
    LANGUAGES: Dict[str, Language] = {}

    def __init__(self):
        self.get_from_code(LOCALE_DEFAULT)
        self.guilds_code: Dict[int, dict] = {}

    def get_from_code(self, code: str):
        """load in LANGUAGES the given locale"""
        if code not in self.LANGUAGES:
            self.LANGUAGES[code] = Language.from_code(code)
        return self.LANGUAGES[code]

    def get_language(self, ctx) -> Language:
        guild_id = ctx.guild.id
        # Guild's locale already registred
        if guild_id not in self.guilds_code:
            # load it
            # TODO : search in a db for a guild fav locale
            self.guilds_code[guild_id] = LOCALE_DEFAULT

        code = self.guilds_code[guild_id]
        language = self.get_from_code(code)
        return language

    async def send(self, ctx, giru_message, *args, **kwargs):
        language = self.get_language(ctx)
        message = language.get(giru_message).format(*args, **kwargs)
        await ctx.send(message)
