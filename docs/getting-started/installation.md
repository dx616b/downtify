---
icon: lucide/download
---

# Installation

The quickest way to run Downtify is with a single `docker run` command. No Python, Node.js or other system dependencies needed on the host — everything is bundled inside the image.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed and running

## Docker run

```bash
docker pull dx616b/downtify:latest

docker run -d \
  --name downtify \
  -p 8000:30321 \
  -e DOWNTIFY_PORT=30321 \
  -v /path/to/music/downloads:/downloads \
  -v /path/to/music/slskd:/slskd \
  -v downtify_data:/data \
  --restart unless-stopped \
  dx616b/downtify:latest
```

Replace `/path/to/music/downloads` and `/path/to/music/slskd` with your library paths. Omit the `/slskd` mount if you only use YouTube.

Once the container starts, open **[http://localhost:8000](http://localhost:8000)** in your browser.

## Volumes

| Volume | Purpose |
|--------|---------|
| `/downloads` | Downloaded audio files |
| `/slskd` | Optional shared Soulseek folder (when using slskd) |
| `/data` | Application database and persistent settings |

Volumes persist across container restarts and upgrades.

## Custom port

To expose Downtify on a different host port, change the left side of `-p`:

```bash
docker run -d \
  --name downtify \
  -p 9090:30321 \
  -e DOWNTIFY_PORT=30321 \
  -v /path/to/music/downloads:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  dx616b/downtify:latest
```

Then open **[http://localhost:9090](http://localhost:9090)**.

## Updating

Pull the latest image and recreate the container:

```bash
docker pull dx616b/downtify:latest
docker stop downtify && docker rm downtify
docker run -d --name downtify -p 8000:30321 \
  -e DOWNTIFY_PORT=30321 \
  -v /path/to/music/downloads:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  dx616b/downtify:latest
```

Your music and settings are preserved in the volumes.

## What's next?

- **[Docker Compose](docker-compose.md)** — easier way to manage the container long-term
- **[Environment variables](environment-variables.md)** — tune anti-bot behaviour and other advanced options
- **[Download settings](../features/download-settings.md)** — choose your format and bitrate
