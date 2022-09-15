import asyncio
import os
import time
import discord

from dotenv import load_dotenv

from girubot import Giru
from girubot.utils import debug, eprint, is_replit


# from girubot.cogs import Music, Others, Xina, Utility
async def load_extensions(bot):
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            # cut off the .py from the file name
            await bot.load_extension(f"cogs.{filename[:-3]}")


def main():
    load_dotenv(".env")
    token = os.environ.get("TOKEN")
    if not token:
        eprint("TOKEN not found")
        return -1

    intents = discord.Intents.default()
    intents.message_content = True

    bot = Giru(command_prefix="!", intents=intents)
    #bot.add_cog(Music(bot))
    #bot.add_cog(Others(bot))
    #bot.add_cog(Utility(bot))

    try:
        bot.run(token)
    except discord.errors.LoginFailure:
        eprint("Improper token has been passed.")
    except discord.errors.HTTPException as e:
        # discord.errors.HTTPException
        # 'args', 'code', 'response', 'status', 'text', 'with_traceback'
        print("[Debug] code", e.code)
        print("[Debug] status", e.status)
        #print("[Debug] response", e.response)
        if e.code == 429:  # too many Requests
            eprint("> too many Requests")


if __name__ == "__main__":
    if is_replit():
        from girubot.server import run_server
        t = run_server()
        print('>>**', t)

    main()
    time.sleep(2)

    if is_replit():
        #t.raise_exception()
        print('@@ t.join()')
        t.join()

    #time.sleep(36)
