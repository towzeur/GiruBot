import os
import time
import discord

from dotenv import load_dotenv

from girubot import Giru
from girubot.utils import debug, eprint
from girubot.cogs import Music, Others, Xina, Utility


def is_replit():
    replit_keys = [k for k in os.environ.keys() if "REPL_" in k]
    return bool(replit_keys)


if is_replit():
    from girubot.server import run_server

    run_server()


def main():
    load_dotenv(".env")
    token = os.environ.get("TOKEN")
    if not token:
        eprint("TOKEN not found")
        return -1

    bot = Giru(command_prefix="!")
    bot.add_cog(Music(bot))
    bot.add_cog(Others(bot))
    bot.add_cog(Utility(bot))

    try:
        bot.run(token)
    except discord.errors.LoginFailure:
        eprint("Improper token has been passed.")
        return -1
    except discord.errors.HTTPException as e:
        # discord.errors.HTTPException
        # 'args', 'code', 'response', 'status', 'text', 'with_traceback'
        print("[Debug] code", e.code)
        # print("[Debug] response", e.response)
        print("[Debug] status", e.status)
        if e.code == 429:  # too many Requests
            pass


if __name__ == "__main__":
    main()
    time.sleep(3600)

