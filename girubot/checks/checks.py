from girubot.locales import locales


async def author_channel(ctx) -> bool:
    cond = ctx.author.voice and ctx.author.voice.channel
    if not cond:
        lang = locales.get_language(ctx)
        await ctx.send(lang.error_user_not_in_channel)
    return cond


async def bot_channel(ctx) -> bool:
    cond = ctx.guild.voice_client and ctx.guild.voice_client.channel
    if not cond:
        lang = locales.get_language(ctx)
        await ctx.send(lang.error_no_voice_channel)
    return cond


async def same_channel(ctx) -> bool:
    """Checks that the command sender is in the same voice channel as the bot."""
    if not await author_channel(ctx):
        return False
    if not await bot_channel(ctx):
        return False
    cond = ctx.author.voice.channel == ctx.guild.voice_client.channel
    if not cond:
        lang = locales.get_language(ctx)
        await ctx.send(lang.error_not_same_channel)
    return cond


async def is_playing(ctx) -> bool:
    """Checks that audio is currently playing before continuing."""
    # client = ctx.guild.voice_client
    # if not (client and client.channel and client.source):
    #    return False

    player = ctx.bot.get_cog("Music").get_player(ctx)
    cond = player.is_playing()
    if not cond:
        lang = locales.get(ctx)
        await ctx.send(lang.error_nothing_playing)
    return cond
