import discord
from math import floor, ceil

from music import PlayerQueue, PlayerModifier
from utils import convert_to_youtube_time_format
from options import QUEUE_MAX_DISPLAYED


def create_embed_queue_0():
    embed = discord.Embed(
        title="Queue for {}".format("Rythm Community"),
        url="https://www.youtube.com/",
        # description='New video guys click on the title'
    )

    # now playing
    embed.add_field(name="\u200B", value="__Now Playing:__", inline=False)
    current = ("【MV】シル・ヴ・プレジデント／P丸様。【大統領になったらね！】", "3:13", "!!!kino25789!!!#4304")
    embed.add_field(
        name="\u200B",
        value="{} | `{} Requested by: {}`".format(current[0], current[1], current[2]),
    )

    # queue
    embed.add_field(name="\u200B", value="__Up Next:__", inline=False)
    L = [
        ("Pon De Replay (Remix)", "3:38", "alex+#8093"),
        ("Voice of the Soul", "3:44", "Saadioz#5211"),
        ("ARTPOP", "4:08", "alex+#8093"),
        ("Shygirl - SIREN (Lyric Video)", "3:57", "alex+#8093"),
    ]
    for i in range(min(len(L), 10)):
        embed.add_field(
            name="\u200B",
            value="`{}.` {} | `{} Requested by: {}`".format(
                i, L[i][0], L[i][1], L[i][2]
            ),
            inline=False,
        )

    embed.add_field(
        name="{} songs in queue | {} total length".format(13, "26:44:01"),
        value="\u200B",
        inline=False,
    )

    embed.set_footer(
        text="Page {}/{} | Loop: {} | Queue Loop: {}".format(1, 2, "❌", "❌")
    )

    return embed


def create_embed_queue(ctx, queue: PlayerQueue, page=1):
    embed = discord.Embed(
        title="Queue for {}".format("Rythm Community"),
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

    else:
        # current
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
        pages = max(ceil(queued / 10), 1)

        if queued > 0:
            embed.add_field(name="\u200B", value="__Up Next:__", inline=False)
            for n in range(displayed):
                index = (queue.cursor + 1 + n) % len(queue)
                req = queue.open[index]
                embed.add_field(
                    name="\u200B",
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
                value="\u200B",
                inline=False,
            )

    # avatar_url_as(*, format=None, static_format='webp', size=1024)
    embed.set_footer(
        text="Page {}/{} | Loop: {} | Queue Loop: {}".format(
            page,
            pages,
            "✅" if queue.flag is PlayerModifier.LOOP else "❌",
            "✅" if queue.flag is PlayerModifier.LOOP else "❌",
        ),
        icon_url=ctx.message.author.avatar_url,
    )

    return embed
