import discord
from math import floor, ceil

from utils import convert_to_youtube_time_format, Markdown
from options import QUEUE_MAX_DISPLAYED

VOID_TOKEN = "\u200B"


class EmbedGenerator:
    @staticmethod
    def queue(ctx, queue: "PlayerQueue", page=1):

        queued = len(queue) - 1
        displayed = min(queued, QUEUE_MAX_DISPLAYED)
        pages = max(ceil(queued / QUEUE_MAX_DISPLAYED), 1)

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
                "✅" if queue.loop_enabled else "❌",
                "✅" if queue.loopqueue_enabled else "❌",
            ),
            icon_url=ctx.message.author.avatar_url,
        )

        return embed

    @staticmethod
    def play_queued(req, estimated="???", position="???"):
        embed = discord.Embed(
            title="Added to queue",
            description=Markdown.bold(req.title),
            color=0x00AFF4,
            url=f"https://www.youtube.com/watch?v={req.info['display_id']}",
        )
        # embed.set_image(*, query)
        # embed.set_thumbnail(*, url)
        # embed.set_author(*, name, url=Embed.Empty, icon_url=Embed.Empty)
        # print(req.info["thumbnail"])
        # embed.set_image(req.info["thumbnail"])
        # embed.add_field(name=req.title, value=f"[Click]({req.url})")

        embed.set_thumbnail(url=req.info["thumbnail"])

        # Markdown.bold(
        embed.add_field(
            name="Channel", value=str(req.message.author.voice.channel), inline=True,
        )
        embed.add_field(
            name="Song Duration",
            value=convert_to_youtube_time_format(req.duration),
            inline=True,
        )
        embed.add_field(
            name="Estimated time until playing",
            value=estimated
            if isinstance(estimated, str)
            else convert_to_youtube_time_format(estimated),
            inline=True,
        )
        embed.add_field(
            name="Position in queue", value=position, inline=True,
        )
        return embed

    @staticmethod
    def nowplaying(req, t, ticks=30):
        x = int(ticks * (t / req.duration))
        print(t, req.duration, x, "%")

        embed = discord.Embed(
            title=req.title,
            url=f"https://www.youtube.com/watch?v={req.info['display_id']}",
            # description=Markdown.bold(req.title),
            color=0x00AFF4,
        )
        embed.set_thumbnail(url=req.info["thumbnail"])
        embed.set_author(name="Now Playing ♪")
        # "ㅤ"
        # progress bar
        line = "".join(["▬" if t != x else "🔘" for t in range(ticks)])
        embed.add_field(
            name="\rx", value=Markdown.code(line) + "\n\u200b", inline=False,
        )
        # 5:26 / 16:26
        d_current = convert_to_youtube_time_format(t)
        d_end = convert_to_youtube_time_format(req.duration)
        line = f"{d_current} / {d_end}"
        embed.add_field(
            name="\rx", value=Markdown.code(line) + "\n\u200b", inline=False,
        )
        # Requested by
        line = f"`Requested by:` {req.message.author.name}"
        embed.add_field(name="\rx", value=line, inline=False)
        # return "\u200B"
        return embed

    @staticmethod
    def ping(
        api_response_time: int, message_response_time: int, websocket_heartbeat: int
    ):
        """
        API response time
        Message response time
        Websocket heartbeat
        """
        embed = discord.Embed(color=0x00FF00)
        embed.add_field(
            name=VOID_TOKEN, value=f":hourglass: {api_response_time}ms", inline=False
        )
        embed.add_field(
            name=VOID_TOKEN,
            value=f":stopwatch: {message_response_time}ms",
            inline=False,
        )
        embed.add_field(
            name=VOID_TOKEN, value=f":heartbeat: {websocket_heartbeat}ms", inline=False
        )
        return embed
