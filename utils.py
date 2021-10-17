import glob
import json
import re
import time
import sys

from termcolor import colored, cprint
from functools import wraps
from threading import Lock, Thread


def eprint(*args, **kwargs):
    sep = kwargs.get("sep", " ")
    message = sep.join(args)
    color = "red"
    cprint(message, color, attrs=["bold"], file=sys.stderr, **kwargs)


def debug(*args, **kwargs):
    t_format = "%H:%M:%S"
    msg = f"[{time.strftime(t_format)}]"
    print(msg, *args, **kwargs)


def convert_to_youtube_time_format(total_seconds: float) -> str:
    m, s = divmod(int(total_seconds), 60)
    h, m = divmod(m, 60)

    # if h == 0 and m == 0:
    #    return "%02d" % (s)
    if h == 0:
        return "%02d:%02d" % (m, s)
    return "%02d:%02d:%02d" % (h, m, s)

    # return ["%02d" % x for x in (h, m, s)]


def youtube_url_validation(url):
    youtube_regex = (
        r"(https?://)?(www\.)?"
        "(youtube|youtu|youtube-nocookie)\.(com|be)/"
        "(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})"
    )
    youtube_regex_match = re.match(youtube_regex, url)
    return bool(youtube_regex_match)


def loading_bar(percent, length=10):
    pos = "█"
    neg = "▁"
    n_neg = round(percent * length)
    n_pos = length - n_neg
    return n_pos * pos + n_neg * neg


def get_closest(word, possibilities):
    from difflib import get_close_matches

    def clean(n):
        return "".join([c if ord(c) < 128 else "" for c in n]).lower()

    if word:
        cleaned_word = clean(word)
        cleaned_possibilities = [clean(p) for p in possibilities]

        closer_m = get_close_matches(cleaned_word, cleaned_possibilities, 1)  # list

        if closer_m:
            index = cleaned_possibilities.index(closer_m[0])
            return possibilities[index]

    return None


class Markdown:
    @staticmethod
    def bold(message):
        return "**" + message + "**"

    @staticmethod
    def code(message):
        return "`" + message + "`"


def log_called_function(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        print("@", f.__name__)
        return f(*args, **kwargs)

    return wrapper


class SingletonMeta(type):
    """
    Thread-safe implementation of Singleton from refactoring.guru
    """

    _instances = {}
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]

