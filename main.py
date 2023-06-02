import asyncio
import os
import time
import discord
from loguru import logger
from functools import wraps

from dotenv import load_dotenv

from girubot import Giru
from girubot.utils import debug, eprint, is_replit


# from girubot.cogs import Music, Others, Xina, Utility
async def load_extensions(bot):
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            # cut off the .py from the file name
            await bot.load_extension(f"cogs.{filename[:-3]}")


def run_server_decorator(enable: bool = True):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            if enable:
                from girubot.server import run_server

                t = run_server()
                logger.debug("run_server() started")
            out = function(*args, **kwargs)
            if enable:
                t.join()
                logger.debug("run_server() joined")
            return out

        return wrapper

    return decorator


@run_server_decorator(enable=is_replit())
def main():
    load_dotenv(".env")
    token = os.environ.get("TOKEN")
    if not token:
        eprint("TOKEN not found")
        return -1

    intents = discord.Intents.default()
    intents.message_content = True

    name = "replit" if is_replit() else "local"
    bot = Giru(command_prefix="!", intents=intents, name=name)

    # bot.add_cog(Music(bot))
    # bot.add_cog(Others(bot))
    # bot.add_cog(Utility(bot))

    while True:
        try:
            bot.run(token)
        except discord.errors.LoginFailure:
            eprint("Improper token has been passed.")

        except discord.errors.HTTPException as e:
            # discord.errors.HTTPException
            # 'args', 'code', 'response', 'status', 'text', 'with_traceback'
            print("[Debug] code", e.code)
            print("[Debug] status", e.status)
            # print("[Debug] response", e.response)
            if e.code == 429:  # too many Requests
                eprint("> too many Requests")
        time.sleep(60)


if __name__ == "__main__":
    logger.debug(f"discord version: {discord.__version__}")
    main()
