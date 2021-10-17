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

FFMPEG_EXECUTABLE = "ffmpeg"  # "./ffmpeg.exe"

FFMPEG_BEFORE_OPTIONS = " ".join(
    ["-reconnect 1", "-reconnect_streamed 1", "-reconnect_delay_max 5", "-nostdin",]
)

FFMPEG_OPTIONS = "-vn"

# VOICE ------------------------------------------------------------------------

DEFAULT_VOLUME = 1.0

# LOCALE -----------------------------------------------------------------------

LOCALE_DEFAULT = "en"

LOCALE_FILE_TEMPLATE = "locales/{}.json"

# COMMANDS ---------------------------------------------------------------------

QUEUE_MAX_DISPLAYED = 10
