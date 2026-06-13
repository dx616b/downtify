---
icon: lucide/mic-vocal
---

# Lyrics

Downtify can download lyrics and embed them directly into audio files at download time.

## Enabling lyrics

Lyrics are **enabled by default**. You can toggle them in **Settings → Lyrics → Download lyrics**.

## Provider

The only active provider is **[lrclib](https://lrclib.net)** — a free, open, community-maintained lyrics database. No API key is required.

lrclib is queried with the track title, primary artist, and optionally album name and duration. It returns:

- **Plain lyrics** — static text, embedded into the audio file's lyrics tag
- **Synced lyrics** — time-coded LRC format, saved as a `.lrc` sidecar file next to the audio

## Embedding

Downtify writes **plain text only** into the in-file lyrics tag. When lrclib returns synced lyrics but no plain text, timestamps are stripped from the LRC content before embedding.

| Format | In-file lyrics tag |
|--------|-------------------|
| MP3 | `USLT` (ID3 unsynchronised lyrics) |
| FLAC | `LYRICS` (Vorbis comment) |
| M4A | `©lyr` |
| OGG / OPUS | `LYRICS` (Vorbis comment) |

Synced LRC timestamps are **not** embedded in the audio tags. They are written to a sidecar file instead (see below).

## Sidecar .lrc file

When synced lyrics are available, Downtify saves a `.lrc` file next to the audio file with the same base name. Media players that support external lyrics files (Jellyfin, some portable players) can use this file for time-synced display.

## Fallback behaviour

If lrclib returns no result for a track, the download continues normally — the audio file is saved without lyrics. No error is raised. Check the server logs at debug level for `lrclib has no lyrics` messages.

## Legacy settings

Older Downtify configs may still list `genius`, `musixmatch`, or `azlyrics` in `lyrics_providers`. These identifiers are accepted as no-ops so settings round-trip cleanly, but only `lrclib` fetches real lyrics.
