GiruBot
-------

![Node build](https://github.com/eritislami/evobot/actions/workflows/node.yml/badge.svg)
![Docker build](https://github.com/eritislami/evobot/actions/workflows/docker.yml/badge.svg)
[![Commitizen friendly](https://img.shields.io/badge/commitizen-friendly-brightgreen.svg)](http://commitizen.github.io/cz-cli/)

![logo](https://repository-images.githubusercontent.com/409015826/e9959d0b-71d0-48aa-aaf0-41a846d7c48b)

# GiruBot (Discord Music Bot)
> GiruBot is a Discord Music Bot built with [discord.py](https://github.com/Rapptz/discord.py)

## 📑 Requirements

1. [Python 3.5+](https://www.python.org/ftp/python/3.7.0/python-3.7.0.exe)
2. A Discord Bot Token [Guide](https://discordjs.guide/preparations/setting-up-a-bot-application.html#creating-your-bot)
3. [FFmpeg](https://ffmpeg.org/)

## 🚀 Getting Started

```sh
git clone https://github.com/towzeur/GiruBot.git
cd GiruBot
```

Create a conda env
```sh
conda env create -f environment.yml
```

Activate the new environment
```sh
conda activate girubotenv
```

Verify that the new environment was installed correctly
```sh
conda env list
```

## ⚙️ Configuration

⚠️ Please keep in mind that you should never commit or publicly distribute your token or API keys.⚠️

Create a file `secrets.json` and fill out the values
```json
{
    "TOKEN": "XXXXXXXXXXXXXXXXXXXXXXXX.XXXXXX.XXXXXXXXXXXXXXXXXXXXXXXXXXX",
}
```

## Features & Commands

TODO

## 🌎 Language

Check out Contributing if you want to help add new languages !

Create a json file in the [locales](https://github.com/eritislami/towzeur/tree/master/locales) directory named using the [ISO 639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) two letter format.

List of currently available locales:
- English (en)

## 🤝 Contributing

Contributions are what make the open source community such an amazing place to be learn, 
inspire, and create. Any contributions you make are **greatly appreciated**.

1. [Fork the repository](https://github.com/towzeur/GiruBot/fork)
2. Clone your fork `git clone https://github.com/towzeur/GiruBot.git`
3. Create your feature branch `git checkout -b AmazingFeature`
4. Stage changes `git add .`
5. Commit your changes `git commit -m 'Added some AmazingFeature'`
6. Push to the branch `git push origin AmazingFeature`
7. Submit a pull request

<!-- LICENSE -->
## 🔑 License

Distributed under the MIT License. 
See [LICENSE](https://github.com/towzeur/gym-abalone/blob/master/LICENSE) for more information.

## ❤️ Credits

Realized with ❤️ by [towzeur](https://github.com/towzeur).

