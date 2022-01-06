import os
import discord

from dotenv import load_dotenv

from girubot import Giru
from girubot.utils import debug, eprint
from girubot.cogs import Music, Others, Xina

from girubot.server import run_server

run_server()


if __name__ == "__main__":
    load_dotenv(".env")
    bot = Giru(command_prefix="!")
    bot.add_cog(Music(bot))
    bot.add_cog(Others(bot))

    try:
        token = os.environ["TOKEN"]
        bot.run(token)
    except KeyError:
        eprint("TOKEN not found in .env")
    except discord.errors.LoginFailure:
        eprint("Improper TOKEN has been passed.")

