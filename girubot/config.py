
# FFMPEG -----------------------------------------------------------------------

FFMPEG_EXECUTABLE = "ffmpeg" #"bin/ffmpeg.exe"

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
