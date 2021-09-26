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
    "default_search": "ytsearch",  # "auto"
    "source_address": "0.0.0.0",  # bind to ipv4 since ipv6 addresses cause issues sometimes
    "usenetrc": True,
}

# FFMPEG -----------------------------------------------------------------------

FFMPEG_BEFORE_OPTIONS = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"

FFMPEG_EXECUTABLE = "./ffmpeg.exe"

FFMPEG_OPTIONS = "-vn"

# VOICE ------------------------------------------------------------------------

DEFAULT_VOLUME = 0.5

# LOCALE -----------------------------------------------------------------------

LOCALE_DEFAULT = "en"

LOCALE_FILE_TEMPLATE = "locales/{}.json"
