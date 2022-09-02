import re


class Xina:
    @classmethod
    async def filter(message):

        text = message.content.lower()

        if "tiananmen" in text:
            msg = f"{message.author.mention} :warning: -999 999 social credit points :warning:"
            await message.channel.send(msg)

