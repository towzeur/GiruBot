try:
    # check if yt_dlp is installed
    import yt_dlp as youtube_dl
except ImportError:
    # fallback to youtube_dl
    import youtube_dl