from flask import Flask
from threading import Thread

server = Flask(__name__)


def keep_alive(func):
    def inner():
        t = Thread(target=func)
        t.start()

    return inner


@server.route('/')
def home():
    return "Welcome to Juke Bot"


@keep_alive
def run():
    server.run(host='0.0.0.0', port=9000)