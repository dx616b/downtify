FROM python:3.13-alpine AS builder

WORKDIR /build

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir --root-user-action ignore -r requirements.txt

FROM python:3.13-alpine

LABEL maintainer="dx616b"
LABEL version="2.8.0"
LABEL description="Self-hosted Spotify downloader with slskd and Navidrome sync"

LABEL org.opencontainers.image.title="Downtify" \
      org.opencontainers.image.description="Self-hosted Spotify downloader with slskd and Navidrome sync." \
      org.opencontainers.image.version="2.8.0" \
      org.opencontainers.image.authors="dx616b" \
      org.opencontainers.image.url="https://github.com/dx616b/downtify" \
      org.opencontainers.image.source="https://github.com/dx616b/downtify" \
      org.opencontainers.image.licenses="GPL-3.0" \
      org.opencontainers.image.documentation="https://github.com/dx616b/downtify#readme" \
      org.opencontainers.image.vendor="dx616b" \
      org.opencontainers.image.base.name="python:3.13-alpine"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHON_COLORS=0 \
    DOWNTIFY_LOG_LEVEL=info \
    DOWNTIFY_PORT=8000 \
    UID=1000 \
    GID=1000 \
    UMASK=022

WORKDIR /downtify

RUN apk add --no-cache \
    ffmpeg \
    shadow \
    su-exec \
    tini

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY main.py entrypoint.sh ./
COPY downtify ./downtify
COPY frontend/dist ./frontend/dist

RUN sed -i 's/\r$//g' entrypoint.sh && \
    chmod +x entrypoint.sh

ENV PATH="/home/downtify/.local/bin:${PATH}"

VOLUME /downloads
VOLUME /data

EXPOSE ${DOWNTIFY_PORT}

ENTRYPOINT ["/sbin/tini", "-g", "--", "./entrypoint.sh"]
