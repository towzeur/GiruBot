import os
from typing import KeysView
import discord

from dotenv import load_dotenv

from girubot.utils import debug, eprint
from girubot.music import Music
from girubot.giru import Giru
from girubot.locales import Locales
from girubot.others import Others


# __import__("girubot.server").run_server()


if __name__ == "__main__":

    load_dotenv(".env")

    bot = Giru(command_prefix="!")
    bot.add_cog(Locales(bot))
    bot.add_cog(Music(bot))
    bot.add_cog(Others(bot))

    try:
        bot.run(os.environ["TOKEN"])
    except KeyError:
        eprint("Error while running the bot")
    except discord.errors.LoginFailure:
        eprint("Improper token has been passed.")
