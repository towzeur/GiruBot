from flask import Flask
from threading import Thread

SERVER = Flask(__name__)


@SERVER.route("/")
def home():
    return "Welcome to Juke Bot"


def keep_alive(func):
    def inner():
        t = Thread(target=func)
        t.start()

    return inner


@keep_alive
def run_server():
    SERVER.run(host="0.0.0.0", port=9000)

