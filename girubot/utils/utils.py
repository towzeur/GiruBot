# import glob
# import json
import re
import time
import sys
import io
import os

from termcolor import cprint  # , colored
from functools import wraps
from threading import Lock

from loguru import logger


def is_replit() -> bool:
    replit_keys = [k for k in os.environ.keys() if k.startswith("REPL_")]
    logger.debug(f"replit_keys: {replit_keys}")
    return bool(replit_keys)


def sprint(*args, color="red", **kwargs):
    sio = io.StringIO()
    print(*args, **kwargs, file=sio)
    message = sio.getvalue()
    cprint(message, color)


def eprint(*args, **kwargs):
    sep = kwargs.get("sep", " ")
    message = sep.join(map(str, args))
    color = "red"
    cprint(message, color, attrs=["bold"], file=sys.stderr, **kwargs)


def debug(*args, **kwargs):
    t_format = "%H:%M:%S"
    msg = f"[{time.strftime(t_format)}]"
    print(msg, *args, **kwargs)


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


def log_called_function(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        logger.debug(f"call {f.__name__}")
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


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

    @classmethod
    def from_dict(cls, d: dict):
        out = AttrDict(d)
        for k, v in d.items():
            if isinstance(v, dict):
                out[k] = AttrDict.from_dict(v)
        return out
