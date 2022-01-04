import asyncio
import youtube_dl
import time

from multiprocessing import Process, Queue, SimpleQueue

# https://newbedev.com/can-i-use-asyncio-to-read-from-and-write-to-a-multiprocessing-pipe

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
    "default_search": "auto",
    "source_address": "0.0.0.0",
    "usenetrc": True,
    #
    # "logger": MyLogger(),
    # "progress_hooks": [my_hook],
}


def get_info(query):
    ytdl_kwargs = dict(
        download=False,
        ie_key=None,
        extra_info={},
        process=True,
        force_generic_extractor=False,
    )
    with youtube_dl.YoutubeDL(YTDL_OPTIONS) as ytdl:
        ytdl.cache.remove()
        try:
            info = ytdl.extract_info(query, **ytdl_kwargs)
            return info
        except (youtube_dl.utils.ExtractorError, youtube_dl.utils.DownloadError,) as e:
            print("from_youtube", "exception", e)
            print(e)
    return None


def downloader(q0, q1):
    while True:
        print("waiting for a request")
        query = q0.get()
        if query is None:
            break
        info = get_info(query)
        q1.put(info)
    print("downloader ENDED")


async def bot():
    t0 = time.time()
    while True:
        t1 = time.time()
        print("hello", t1 - t0)
        time.sleep(1)
        # await asyncio.sleep(1)
        t0 = t1


async def main():
    q0, q1 = SimpleQueue(), SimpleQueue()
    loop = asyncio.get_event_loop()

    loop.create_task(bot())

    p = Process(target=downloader, args=(q0, q1,))
    p.start()

    # query
    def dl(query_str):
        t0 = time.time()

        q0.put(query_str)
        out = q1.get()

        dt = time.time() - t0
        print("download time", dt)
        return out

    for query in [
        "https://www.youtube.com/watch?v=T59N3DPrvac",
        "https://www.youtube.com/watch?v=ndIyLnJtp54",
        "https://www.youtube.com/watch?v=e97w-GHsRMY",
    ]:
        print(query)
        info = await loop.run_in_executor(None, dl, query)
        print("OK")

    q0.put(None)


if __name__ == "__main__":
    print("-" * 30)
    asyncio.run(main())
