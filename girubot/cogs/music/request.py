import discord
import asyncio

from functools import partial
from yt_dlp import YoutubeDL
from time import perf_counter_ns
from dataclasses import dataclass

from girubot.utils import debug, eprint

from .downloader import Downloader


@dataclass
class Request:
    """Class for keeping track of an item in inventory."""

    message: discord.Message
    query: str
    info: dict
    title: str
    url: str
    duration: float

    @classmethod
    async def from_youtube(cls, query, message, blocking=True):

        # download info
        t0 = perf_counter_ns()
        info = await Downloader.get_info(query, blocking=blocking)
        dt = perf_counter_ns() - t0
        eprint("Downloader.get_info", dt * 1e-6)

        # save them to a json
        if False:
            try:
                with open("tmp/tmp_entries.txt", "w", encoding="utf-8") as f:
                    pprint(info, stream=f)
            except Exception as e:
                eprint(e)
                print("**" * 20)
                # return None

        # this value is not an exact match, but it's a good approximation
        if "entries" in info:
            print("@from_youtube", 'entry = info["entries"][0]', len(info["entries"]))
            entry = info["entries"][0]
        else:
            print("@from_youtube", "entry = info")
            entry = info

        return cls(
            message=message,
            query=query,
            info=entry,
            title=entry["title"],
            url=entry["url"],
            duration=entry["duration"],
        )
