import discord


def create_embed_queue():
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
