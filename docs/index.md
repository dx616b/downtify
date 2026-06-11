---
icon: lucide/house
hide:
  - navigation
  - toc
---

<div class="hero" markdown>

<img src="assets/logo.svg" class="hero__logo" alt="Downtify logo">

<h1 style="display: none;"></h1>

<div class="hero__title">Downtify</div>

<p class="hero__lead">
The music downloader you can host on your own box.<br>
Drop a Spotify link, get a tagged audio file. No account, no API key, no Premium.
</p>

<div class="hero__cta" markdown>

[Get started](getting-started/installation.md){ .md-button .md-button--primary }
[Source on GitHub](https://github.com/dx616b/downtify){ .md-button }

</div>

<div class="hero__shields" markdown>

[![Test](https://github.com/dx616b/downtify/actions/workflows/test.yml/badge.svg)](https://github.com/dx616b/downtify/actions/workflows/test.yml)
[![Docker Pulls](https://img.shields.io/docker/pulls/dx616b/downtify?color=1AD05C)](https://hub.docker.com/r/dx616b/downtify)
[![License](https://img.shields.io/github/license/dx616b/downtify?color=1AD05C)](https://github.com/dx616b/downtify/blob/main/LICENSE)

</div>

</div>

<section class="home-section" markdown>

## How it actually works

Spotify's official API gates downloads behind a Premium subscription. Downtify takes the side door instead — it reads the metadata Spotify already exposes on its public embed pages, then tries configured audio providers (slskd, YouTube Music, YouTube). Files are tagged with `mutagen` and indexed so playlists are not re-downloaded. The whole pipeline lives in a single Docker container.

<div class="pipeline">
  <div class="pipeline__step"><strong>Spotify embed</strong><br><span>metadata</span></div>
  <div class="pipeline__arrow">→</div>
  <div class="pipeline__step"><strong>Audio providers</strong><br><span>slskd · YT Music</span></div>
  <div class="pipeline__arrow">→</div>
  <div class="pipeline__step"><strong>mutagen · index</strong><br><span>tag &amp; dedupe</span></div>
</div>

</section>

<section class="home-section" markdown>

## What you can paste in

| | |
|---|---|
| Spotify track | `open.spotify.com/track/…` |
| Spotify album | `open.spotify.com/album/…` |
| Spotify playlist | `open.spotify.com/playlist/…` |
| YouTube / YT Music | `youtube.com/watch?v=…` |
| Free-text search | `Arctic Monkeys Do I Wanna Know` |

</section>

<section class="home-section" markdown>

## Highlights

<div class="mini-grid">

<a href="features/playlist-monitor/" class="mini-card">
  <span class="mini-card__icon">👁</span>
  <span class="mini-card__title">Playlist Monitor</span>
  <span class="mini-card__text">Watches a playlist and quietly downloads new tracks as they're added.</span>
</a>

<a href="features/download-settings/" class="mini-card">
  <span class="mini-card__icon">🎚</span>
  <span class="mini-card__title">Five formats</span>
  <span class="mini-card__text">MP3, FLAC, M4A, OGG and OPUS — at the bitrate of your choice.</span>
</a>

<a href="features/lyrics/" class="mini-card">
  <span class="mini-card__icon">📝</span>
  <span class="mini-card__title">Lyrics built-in</span>
  <span class="mini-card__text">Plain and time-synced lyrics fetched from lrclib and embedded in the file.</span>
</a>

<a href="features/player/" class="mini-card">
  <span class="mini-card__icon">🎧</span>
  <span class="mini-card__title">Web player</span>
  <span class="mini-card__text">Shuffle, repeat, volume and album art — straight from the browser.</span>
</a>

<a href="features/m3u-export/" class="mini-card">
  <span class="mini-card__icon">📃</span>
  <span class="mini-card__title">M3U export</span>
  <span class="mini-card__text">Standard EXTM3U files that Jellyfin, Navidrome and Plex pick up automatically.</span>
</a>

<a href="features/file-organization/" class="mini-card">
  <span class="mini-card__icon">📁</span>
  <span class="mini-card__title">Library layout</span>
  <span class="mini-card__text">Flat dump or per-artist folders — whichever your media server prefers.</span>
</a>

</div>

</section>

<section class="home-section" markdown>

## One command and you're done

```bash
docker pull dx616b/downtify:latest

docker run -d -p 8000:30321 --name downtify \
  -e DOWNTIFY_PORT=30321 \
  -v /path/to/music/downloads:/downloads \
  -v /path/to/music/slskd:/slskd \
  -v downtify_data:/data \
  dx616b/downtify:latest
```

Open [`localhost:8000`](http://localhost:8000), paste a link, hit download. Files land in your mounted folders with tags already in place.

[Installation guide](getting-started/installation.md){ .md-button .md-button--primary }
[Docker Compose](getting-started/docker-compose.md){ .md-button }

</section>
