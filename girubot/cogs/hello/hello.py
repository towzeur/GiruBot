from discord.ext import commands


@commands.command()
async def hello(ctx):
    await ctx.send(f"Hello {ctx.author.display_name}.")


def setup(bot):
    print("I am being loaded!")
    bot.add_command(hello)


def teardown(bot):
    print("I am being unloaded!")

