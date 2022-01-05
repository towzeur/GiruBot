import asyncio
import yt_dlp as youtube_dl

youtube_dl.utils.bug_reports_message = lambda: ""

from functools import partial
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

from girubot.utils import debug, eprint


class DownloaderLogger:
    def debug(self, msg):
        print("+ debug", msg)

    def warning(self, msg):
        print("+ warning", msg)

    def error(self, msg):
        print("+ error", msg)

    @staticmethod
    def progress_hooks(d):
        print("=" * 30)
        print(d)
        print("=" * 30)
        # print("+", d["status"])
        # if d["status"] == "finished":
        #    print("Done downloading, now converting ...")


class Downloader:
    YTDL_OPTIONS = {
        "verbose": False,
        "format": "bestaudio/best",
        "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
        "restrictfilenames": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "ignoreerrors": False,
        "logtostderr": False,
        "quiet": True,
        "no_warnings": True,
        "default_search": "auto",  # "ytsearch"
        "source_address": "0.0.0.0",  # bind to ipv4 since ipv6 addresses cause issues sometimes
        "usenetrc": True,
        #
        "logger": DownloaderLogger(),
        "progress_hooks": [DownloaderLogger.progress_hooks],
    }

    YTDL_KWARGS = dict(
        download=False,
        ie_key=None,
        extra_info={},
        process=True,
        force_generic_extractor=False,
    )

    @staticmethod
    async def _blocking(query: str):
        with youtube_dl.YoutubeDL(Downloader.YTDL_OPTIONS) as ytdl:
            print("-" * 30)
            debug("from_youtube, blocking")
            # info = Downloader.get_info(query)
            loop = asyncio.get_running_loop()
            downloader = partial(ytdl.extract_info, query, **Downloader.YTDL_KWARGS)
            info = await loop.run_in_executor(None, downloader)
            print("+" * 30)
            # info = await loop.run_in_executor(None, Downloader.get_info, query)
            # asyncio.set_event_loop(loop_bot)
            # loop.close()
            return info

    @staticmethod
    async def _non_blocking(query: str):
        with youtube_dl.YoutubeDL(Downloader.YTDL_OPTIONS) as ytdl:
            ytdl.cache.remove()
            try:
                info = ytdl.extract_info(query, **Downloader.YTDL_KWARGS)
                # ytdl.prepare_filename(info_dict)
                # ytdl.download([url])
                return info
            except (
                youtube_dl.utils.ExtractorError,
                youtube_dl.utils.DownloadError,
            ) as e:
                debug("from_youtube", "exception", e)
                eprint(e)
        return None

    @staticmethod
    async def get_info(query: str, blocking: bool = True) -> Optional[dict]:
        if blocking:
            info = await Downloader._blocking(query)
        else:
            loop = asyncio.get_running_loop()
            with ProcessPoolExecutor(max_workers=1) as executor:
                info = await loop.run_in_executor(
                    executor, Downloader._non_blocking, query
                )
        return info
