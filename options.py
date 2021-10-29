class MyLogger(object):
    def debug(self, msg):
        print("+ debug", msg)

    def warning(self, msg):
        print("+ warning", msg)

    def error(self, msg):
        print("+ error", msg)


def my_hook(d):
    print("+", d["status"])
    if d["status"] == "finished":
        print("Done downloading, now converting ...")


# YTDL_OPTIONS -----------------------------------------------------------------

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
    "logger": MyLogger(),
    "progress_hooks": [my_hook],
}

# FFMPEG -----------------------------------------------------------------------

FFMPEG_EXECUTABLE = "bin/ffmpeg.exe"

FFMPEG_BEFORE_OPTIONS = " ".join(
    ["-reconnect 1", "-reconnect_streamed 1", "-reconnect_delay_max 5", "-nostdin"]
)

FFMPEG_OPTIONS = "-vn"

# VOICE ------------------------------------------------------------------------

DEFAULT_VOLUME = 1.0

# LOCALE -----------------------------------------------------------------------

LOCALE_DEFAULT = "en"

LOCALE_FILE_TEMPLATE = "locales/{}.json"

# COMMANDS ---------------------------------------------------------------------

QUEUE_MAX_DISPLAYED = 10
