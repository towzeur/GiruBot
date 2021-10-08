import discord
from math import floor, ceil

from music import PlayerQueue, PlayerModifier
from utils import convert_to_youtube_time_format
from options import QUEUE_MAX_DISPLAYED


VOID_TOKEN = "\u200B"


def create_embed_queue(ctx, queue: PlayerQueue, page=1):
    embed = discord.Embed(
        title="Queue for {}".format(ctx.guild.name),
        url="https://www.youtube.com/",
        # description='New video guys click on the title'
    )

    # now playing
    if queue.current is None:
        embed.add_field(
            name="__Now Playing:__",
            value="Nothing, let's get this party started! :tada:",
            inline=False,
        )

    # current
    else:
        req = queue.current
        embed.add_field(
            name="__Now Playing:__",
            value="{} | `{} Requested by: {}#{}`".format(
                req.title,
                convert_to_youtube_time_format(req.duration),
                req.message.author.name,
                req.message.author.discriminator,
            ),
            inline=False,
        )

        # queue
        queued = len(queue) - 1
        displayed = min(queued, QUEUE_MAX_DISPLAYED)
        pages = max(ceil(queued / QUEUE_MAX_DISPLAYED), 1)

        if queued > 0:
            embed.add_field(name=VOID_TOKEN, value="__Up Next:__", inline=False)
            for n in range(displayed):
                index = (queue.cursor + 1 + n) % len(queue)
                req = queue.open[index]
                embed.add_field(
                    name=VOID_TOKEN,
                    value="`{}.` {} | `{} Requested by: {}#{}`".format(
                        n + 1,
                        req.title,
                        convert_to_youtube_time_format(req.duration),
                        req.message.author.name,
                        req.message.author.discriminator,
                    ),
                    inline=False,
                )

            total_length = queue.duration - queue.current.duration
            embed.add_field(
                name="{} songs in queue | {} total length".format(
                    queued, convert_to_youtube_time_format(total_length)
                ),
                value=VOID_TOKEN,
                inline=False,
            )

    # avatar_url_as(*, format=None, static_format='webp', size=1024)
    embed.set_footer(
        text="Page {}/{} | Loop: {} | Queue Loop: {}".format(
            page,
            pages,
            "✅" if PlayerModifier.LOOP in queue.modifiers else "❌",
            "✅" if PlayerModifier.LOOP_QUEUE in queue.modifiers else "❌",
        ),
        icon_url=ctx.message.author.avatar_url,
    )

    return embed
