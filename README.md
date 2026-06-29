# Stagehand

**This software is somewhat half-baked. It only works (though it works well)
if you have an [Easynews](https://easynews.com) account.  Generic NNTP isn't
supported yet (but help is welcome).**


## What it is

Stagehand is a manager for your favourite TV series.  It automatically
downloads new episodes of the TV shows in your library, and provides a convenient
interface to download previously aired episodes.

Here are some of the main features:

* ~~Pretty, modern-looking UI~~ (Well it was 10 years ago.)
* Support for multiple TV metadata providers (currently TheTVDB and TVmaze): easily choose the authoritative provider per-series
* (Exclusive) support for Easynews HTTP-based global search
* Multi-platform: tested on Linux and Windows (and theoretically works on OS X)

## What it isn't

The core of Stagehand is quite robust, but many essential features are missing:

* NZB and NNTP support (for non-Easynews Usenet services): the most critical missing functionality
* Bittorrent
* Web-based configuration UI
* Ability to import an existing TV library
* ... and a bazillion FIXMEs and TODOs in the source


## What it looks like

![](https://stagehand.ca/img/stagehand.jpg)

![](https://stagehand.ca/img/stagehand2.jpg)



## How to run it

Stagehand requires Python 3.11 or later. The included `Dockerfile` builds a working
image from source using Python 3.13.

```bash
# Generate config modules from their XML sources (one-time, or after pulling changes)
python3 -c "
from stagehand.toolbox import xmlconfig
xmlconfig.convert('stagehand/config.cxml', 'stagehand/config.py', 'stagehand', 'stagehand.toolbox.config')
xmlconfig.convert('stagehand/searchers/easynews_config.cxml', 'stagehand/searchers/easynews_config.py', 'stagehand.searchers', 'stagehand.toolbox.config')
xmlconfig.convert('stagehand/notifiers/email_config.cxml', 'stagehand/notifiers/email_config.py', 'stagehand.notifiers', 'stagehand.toolbox.config')
xmlconfig.convert('stagehand/notifiers/xbmc_config.cxml', 'stagehand/notifiers/xbmc_config.py', 'stagehand.notifiers', 'stagehand.toolbox.config')
"

docker build -t stagehand .

docker run -ti -p 8088:8088 \
  -v $HOME/.config/stagehand:/root/.config/stagehand \
  -v /data/tv:/tv \
  stagehand
```

Change `/data/tv` to the path where you want downloaded episodes stored.

The web interface will be available at `http://localhost:8088`.

👉 You can daemonize the container by adding `-d` to the `docker run` command.


## How to configure it

Ideally you'd be able to configure Stagehand from the web interface, but this isn't
implemented yet. Until then, you will need to edit the config file at
`~/.config/stagehand/config`.

Minimally, you will need these lines, which you can safely append to the bottom
of the file:

```
searchers.enabled[+] = easynews
searchers.easynews.username = your_easynews_username
searchers.easynews.password = your_easynews_password
```

Once you save the config file, you're ready to start using Stagehand.  No reload
is needed, it will pick up the changes dynamically.
