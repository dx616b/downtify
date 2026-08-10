<h1 align="center">
  <a href="https://github.com/dx616b/downtify-ng" target="_blank" rel="noopener noreferrer">
    <picture>
      <img width="80" src="https://github.com/user-attachments/assets/628d4334-7326-446e-9f2a-4d3ab4fc95c3">
    </picture>
  </a>
  <br>
  Downtify NG
</h1>

<p align="center">
  <strong>Self-hosted music downloader. Paste a Spotify link, get a tagged audio file — no API keys, no account, no Premium.</strong>
</p>

<div align="center">

[![Test](https://github.com/dx616b/downtify-ng/actions/workflows/test.yml/badge.svg)](https://github.com/dx616b/downtify-ng/actions/workflows/test.yml)
[![GitHub License](https://img.shields.io/github/license/dx616b/downtify-ng?color=blue)](/LICENSE)
[![Docker Pulls](https://img.shields.io/docker/pulls/dx616b/downtify?color=blue)](https://hub.docker.com/r/dx616b/downtify)

Docker image: [`dx616b/downtify`](https://hub.docker.com/r/dx616b/downtify)

</div>

---

## What is Downtify NG?

Downtify NG is a **self-hosted web app** that downloads music from Spotify without the Spotify Web API, an account, or Premium. Paste a link and get a fully tagged file.

It resolves metadata from Spotify’s public embed pages, then tries your configured **audio sources** (Soulseek via **slskd**, YouTube Music, or YouTube). Files are tagged with `mutagen`, indexed so known tracks are not re-downloaded, and can export **M3U** playlists or sync into **Navidrome**. The app runs in a single Docker container.

Fork of [henriquesebastiao/downtify](https://github.com/henriquesebastiao/downtify) (GPL-3.0). This tree adds slskd, Navidrome sync, a library catalog for `/downloads` and `/slskd`, and skip-re-download via a track index — see [`docs/features/library-catalog.md`](docs/features/library-catalog.md).

---

## Features

| Feature | Details |
|---------|---------|
| **Tracks, albums & playlists** | Spotify track, album, and playlist links |
| **Playlist Monitor** | Watch playlists and auto-download new songs as they appear on Spotify |
| **Rich metadata** | Album art, title, artist, album, year embedded in every file |
| **Multiple formats** | MP3 · FLAC · M4A · OGG · OPUS |
| **Free-text search** | Search YouTube Music directly — no Spotify link needed |
| **Zero Spotify credentials** | No API key, account, or Premium |
| **Real-time progress** | Live download progress via WebSocket |
| **slskd (Soulseek)** | Optional provider via [slskd](https://github.com/slskd/slskd) — leave files in place, real transfer progress |
| **Navidrome playlists** | Sync Spotify playlists into Navidrome after download (Subsonic API) |
| **Library browser** | Lists `/downloads` and `/slskd` using embedded tags |
| **Skip re-downloads** | Spotify track index remembers what is already on disk |
| **Lyrics** | Optional [lrclib](https://lrclib.net) fetch and embed (plain text in-file; synced as `.lrc` sidecar) |
| **Built-in player** | Play from the web UI — queue, shuffle, repeat, volume |
| **Multi-language UI** | English, Spanish, Brazilian Portuguese |

---

## Quick Start

```bash
docker pull dx616b/downtify:latest

docker run -d -p 8000:30321 --name downtify-ng \
  -e DOWNTIFY_PORT=30321 \
  -v /path/to/music/downloads:/downloads \
  -v /path/to/music/slskd:/slskd \
  -v downtify_ng_data:/data \
  dx616b/downtify:latest
```

Open [http://localhost:8000](http://localhost:8000), paste a Spotify link, and download.

Map host paths to your library folders. Omit the `/slskd` mount if you only use YouTube. Paths in the UI are container paths (`/downloads`, `/slskd`). Navidrome must scan the same host folders.

### Docker Compose

```bash
cp docker-compose.example.yml docker-compose.yml
# edit host paths, then:
docker compose pull && docker compose up -d
```

See [`docker-compose.example.yml`](docker-compose.example.yml).

---

## How It Works

```
Spotify embed  →  Provider chain (slskd → YouTube Music → …)  →  Tag & register
  (metadata)         (find audio on disk or download)              (mutagen + index)
```

1. **Metadata** — Track, album, and playlist links use public `open.spotify.com/embed` pages. Large playlists are paginated via Spotify’s anonymous API. No Spotify API key or Premium required.
2. **Audio providers** — Ordered in Settings (see [Audio sources](#audio-sources-slskd--youtube)). **slskd** searches Soulseek and waits for a transfer. **YouTube Music** / **YouTube** use [`ytmusicapi`](https://ytmusicapi.readthedocs.io/) and [`yt-dlp`](https://github.com/yt-dlp/yt-dlp).
3. **Tag & dedupe** — [`mutagen`](https://mutagen.readthedocs.io/) embeds title, artist, album, year, and cover art. A local **track index** under `/data` maps Spotify track IDs to on-disk paths so playlists and the monitor skip songs you already have.
4. **Playlists (optional)** — **M3U** for media servers and/or **Navidrome** playlist sync via the Subsonic API.

More detail: [`docs/how-it-works.md`](docs/how-it-works.md).

---

## Playlist Monitor

Watch Spotify playlists and download new tracks on a schedule.

1. Open **Playlist Monitor** in the nav bar
2. Paste a Spotify playlist URL
3. Choose how often to check (every 15 minutes up to once a day)
4. Click **Watch**

Only tracks added *after* you start watching are downloaded. Songs already on disk (including under `/slskd`) are linked via the track index instead of fetched again. After a sweep, the monitor can regenerate the M3U and sync Navidrome when those options are enabled.

Pause, resume, force a check, or stop monitoring from the same page. See [`docs/features/playlist-monitor.md`](docs/features/playlist-monitor.md).

---

## Download Settings

Open Settings (gear icon). Values are stored under `/data` and survive restarts.

| Setting | Options / notes |
|---------|-----------------|
| **Audio sources** | Ordered list: **slskd**, **YouTube Music**, **YouTube** |
| **Output format** | MP3 · FLAC · M4A · OGG · OPUS |
| **Bitrate** | 128 · 192 · 256 · 320 kbps (ignored for FLAC) |
| **Organize by artist** | Off (default) · On |
| **Generate M3U** | On by default for playlist downloads / monitor |
| **Sync Navidrome** | Create or update a Navidrome playlist after Spotify playlist jobs |
| **Parallel downloads** | How many tracks at once (default 3) |
| **Lyrics** | Optional **lrclib** only |

Full reference: [`docs/features/download-settings.md`](docs/features/download-settings.md).

---

## Audio sources (slskd + YouTube)

In **Settings → Audio sources**, enable providers and drag them into priority order. Downtify NG tries each until one succeeds.

| Provider | Role |
|----------|------|
| **slskd** | Search Soulseek via your [slskd](https://github.com/slskd/slskd) instance; files land in `source_dir` (usually `/slskd`) |
| **YouTube Music** | YT Music search + yt-dlp into `/downloads` (or playlist subfolder) |
| **YouTube** | Plain YouTube search via yt-dlp (also a last-resort search if YT Music finds nothing) |

Recommended for Soulseek + Navidrome: `slskd` → `YouTube Music` (optionally `YouTube`).

If **slskd** is enabled but nothing is queued within **queued timeout** (default 180s), or the transfer exceeds **download timeout** (default 600s), Downtify NG falls back to the next provider.

---

## slskd (Soulseek via slskd)

### Requirements

- A running **slskd** instance with API access (base URL + API key from slskd’s web UI)
- The same music folder visible to Downtify NG and (if used) Navidrome

### Settings → slskd

| Field | Typical value | Meaning |
|-------|----------------|---------|
| **Enable slskd** | On | Turns the provider on (must also appear in Audio sources) |
| **Base URL** | `http://slskd:5030` | slskd API URL **as Downtify NG sees it** |
| **API key** | *(from slskd)* | Required when enabled |
| **slskd folder path in Downtify NG** | `/slskd` | Where finished Soulseek files appear **inside the container** |
| **Leave slskd files in place** | On (recommended) | Tag in place; register `slskd/…` paths in the library index |
| **Download timeout** | `600` | Max seconds to wait for a transfer |
| **Queued timeout** | `180` | Max seconds stuck in queue before falling back |

### Docker volumes

```text
Host                          Downtify NG container
/path/to/music/downloads  →   /downloads
/path/to/music/slskd      →   /slskd        ← slskd must write here too
```

Mount the **same host directory** on Downtify NG and slskd if they are separate containers.

With **leave in place**, library paths look like `slskd/Album Name/track.mp3` and the player serves them from `/media/slskd/…`. Otherwise files are copied into `/downloads`.

---

## Navidrome playlist sync

After a Spotify playlist download, Downtify NG can mirror it into **Navidrome** (Subsonic API):

1. Trigger Navidrome `startScan` (incremental)
2. Wait for the scan (configurable; scales with playlist size)
3. Match tracks in the Navidrome library
4. Update the existing Navidrome playlist with the same name when possible

### Settings → Navidrome

| Field | Notes |
|-------|--------|
| **Enable Navidrome sync** | Master toggle (also enable **Create playlist in Navidrome** under Playlists) |
| **URL** | e.g. `https://music.example.com` |
| **Username / password** | User that should **own** the playlists |
| **Admin username / password** | Optional — only if the main user is not an admin |
| **Public playlist** | Whether the Navidrome playlist is public |

In Navidrome **Settings → Music Library**, include every folder Downtify NG writes to (`/downloads` and `/slskd`, or the matching host paths).

If sync reports `matched=46/55`, missing tracks are usually not scanned yet, outside configured music folders, or failed tag matching. Playlist refresh can delete files whose embedded tags do not match Spotify (`library: deleted wrong file` in logs).

---

## Organize by artist

When **Settings → File organization → Organize by artist** is on, tracks land in per-artist folders:

```
<downloads>/
  Arctic Monkeys/
    Arctic Monkeys - Do I Wanna Know.mp3
  Tame Impala/
    Tame Impala - The Less I Know The Better.mp3
```

Off (default): singles go in the downloads root; playlist/album tracks go in a per-playlist or per-album subfolder.

With both *Organize by artist* and *Generate M3U* on, the M3U is written to `<downloads>/Playlists/<playlist-name>.m3u`.

---

## Supported links

| Link type | Supported |
|-----------|-----------|
| Spotify track | Yes |
| Spotify album | Yes |
| Spotify playlist | Yes |

Free-text search browses YouTube Music results. Pasting a YouTube URL into the search bar does **not** download that video; YouTube URLs are only a manual override on a failed queue item.

---

## M3U playlist export

Downtify NG writes a standard `EXTM3U` whenever a playlist download or monitor sweep keeps at least one track on disk.

| Layout | Path |
|--------|------|
| Organize by artist **off** | `<downloads>/<playlist-name>/<playlist-name>.m3u` |
| Organize by artist **on** | `<downloads>/Playlists/<playlist-name>.m3u` |

Toggle: **Settings → Playlists → Generate M3U file for playlists** (on by default).

**Paths inside the M3U** are absolute paths where Downtify NG found each file, for example:

```text
/downloads/Robot Heart/Artist - Title.mp3
/slskd/Some Album/01 - Track.mp3
```

Use the same volume mounts in Jellyfin, Navidrome, or other tools. Entries under `slskd/…` resolve to `/slskd/…` inside the container even when the M3U lives under `/downloads`.

---

> [!WARNING]
> Users are responsible for their actions and any legal consequences. Downtify NG does not support unauthorized downloading of copyrighted material and takes no responsibility for user actions.

---

## Built-in player

Open the player from the nav bar or play a track from **Library**. Audio is served from `/downloads` and `/slskd`. The Library and player read **embedded tags** (filename fallback). Cover art comes from tags or the optional disk cache.

Includes seek, queue, shuffle, repeat, volume (remembered), search/filter, and delete (file + catalog). Details: [`docs/features/player.md`](docs/features/player.md).

---

## Internationalization

Default language is **English**, with **Spanish** and **Brazilian Portuguese** included. Switch under **Settings → Language** (stored in `localStorage`).

To add a locale, copy `frontend/src/i18n/locales/en.js`, translate values (keep keys and `{placeholders}`), and register it in `frontend/src/i18n/index.js`. See [CONTRIBUTING.md](./CONTRIBUTING.md#translations).

---

## Contributing

Issues and PRs welcome on [dx616b/downtify-ng](https://github.com/dx616b/downtify-ng). See [CONTRIBUTING.md](./CONTRIBUTING.md) for setup and standards.

---

## License

Licensed under [GPL-3.0](./LICENSE). Based on [henriquesebastiao/downtify](https://github.com/henriquesebastiao/downtify).
