"""Tests for parse_spotify_url() — pure URL parsing, no network calls."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import requests

from downtify.downloader import _download_cover
from downtify.spotify import (
    _largest_image,
    normalize_spotify_cover_url,
    parse_spotify_url,
    spotify_cover_url_candidates,
)

# ── valid URLs ────────────────────────────────────────────────────────────────


def test_parse_track_url():
    result = parse_spotify_url(
        'https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT'
    )
    assert result == ('track', '4cOdK2wGLETKBW3PvgPWqT')


def test_parse_album_url():
    result = parse_spotify_url(
        'https://open.spotify.com/album/1DFixLWuPkv3KT3TnV35m3'
    )
    assert result == ('album', '1DFixLWuPkv3KT3TnV35m3')


def test_parse_playlist_url():
    result = parse_spotify_url(
        'https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M'
    )
    assert result == ('playlist', '37i9dQZF1DXcBWIGoYBM5M')


def test_parse_intl_localized_url():
    result = parse_spotify_url(
        'https://open.spotify.com/intl-pt/track/4cOdK2wGLETKBW3PvgPWqT'
    )
    assert result == ('track', '4cOdK2wGLETKBW3PvgPWqT')


def test_parse_intl_es_localized_url():
    result = parse_spotify_url(
        'https://open.spotify.com/intl-es/album/1DFixLWuPkv3KT3TnV35m3'
    )
    assert result == ('album', '1DFixLWuPkv3KT3TnV35m3')


def test_parse_url_without_scheme():
    result = parse_spotify_url('open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT')
    assert result == ('track', '4cOdK2wGLETKBW3PvgPWqT')


def test_parse_http_scheme():
    result = parse_spotify_url(
        'http://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT'
    )
    assert result == ('track', '4cOdK2wGLETKBW3PvgPWqT')


# ── URI format ────────────────────────────────────────────────────────────────


def test_parse_uri_track():
    result = parse_spotify_url('spotify:track:4cOdK2wGLETKBW3PvgPWqT')
    assert result == ('track', '4cOdK2wGLETKBW3PvgPWqT')


def test_parse_uri_playlist():
    result = parse_spotify_url('spotify:playlist:37i9dQZF1DXcBWIGoYBM5M')
    assert result == ('playlist', '37i9dQZF1DXcBWIGoYBM5M')


def test_parse_uri_album():
    result = parse_spotify_url('spotify:album:1DFixLWuPkv3KT3TnV35m3')
    assert result == ('album', '1DFixLWuPkv3KT3TnV35m3')


def test_parse_uri_malformed_returns_none():
    assert parse_spotify_url('spotify:onlyone') is None


# ── invalid / non-Spotify ─────────────────────────────────────────────────────


def test_parse_empty_string_returns_none():
    assert parse_spotify_url('') is None


def test_parse_youtube_url_returns_none():
    assert (
        parse_spotify_url('https://www.youtube.com/watch?v=dQw4w9WgXcQ')
        is None
    )


def test_parse_random_text_returns_none():
    assert parse_spotify_url('not a url at all') is None


@pytest.mark.parametrize(
    'url',
    [
        'https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT',
        'https://open.spotify.com/album/1DFixLWuPkv3KT3TnV35m3',
        'https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M',
        'spotify:track:4cOdK2wGLETKBW3PvgPWqT',
    ],
)
def test_parse_returns_two_tuple(url):
    result = parse_spotify_url(url)
    assert result is not None
    assert len(result) == 2


@pytest.mark.parametrize(
    'url',
    [
        'https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT',
        'https://open.spotify.com/album/1DFixLWuPkv3KT3TnV35m3',
        'https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M',
    ],
)
def test_parse_id_is_alphanumeric(url):
    result = parse_spotify_url(url)
    assert result is not None
    kind, sid = result
    assert sid.isalnum()


def test_normalize_spotify_cover_url_rewrites_dead_scdn_host():
    image_id = 'ab67616d0000b2739bbb6c626af68e56023c777a'
    assert normalize_spotify_cover_url(
        f'https://i.scdn.co/image/{image_id}'
    ) == (f'https://image-cdn-fa.spotifycdn.com/image/{image_id}')


def test_normalize_spotify_cover_url_keeps_working_cdn():
    url = (
        'https://image-cdn-fa.spotifycdn.com/image/'
        'ab67616d0000b2739bbb6c626af68e56023c777a'
    )
    assert normalize_spotify_cover_url(url) == url


def test_normalize_spotify_cover_url_leaves_preview_host():
    url = 'https://p.scdn.co/mp3-preview/deadbeef'
    assert normalize_spotify_cover_url(url) == url


def test_largest_image_rewrites_scdn_cover():
    image_id = 'ab67616d0000b2739bbb6c626af68e56023c777a'
    out = _largest_image([
        {'url': f'https://i.scdn.co/image/{image_id}', 'width': 640},
        {
            'url': (f'https://image-cdn-fa.spotifycdn.com/image/{image_id}'),
            'width': 300,
        },
    ])
    assert out == f'https://image-cdn-fa.spotifycdn.com/image/{image_id}'


def test_spotify_cover_url_candidates_fallbacks():
    image_id = 'ab67616d0000b2739bbb6c626af68e56023c777a'
    candidates = spotify_cover_url_candidates(
        f'https://i.scdn.co/image/{image_id}'
    )
    assert candidates == [
        f'https://image-cdn-fa.spotifycdn.com/image/{image_id}',
        f'https://image-cdn-ak.spotifycdn.com/image/{image_id}',
    ]


def test_spotify_cover_url_candidates_prefers_existing_akamai():
    image_id = 'ab67616d0000b2739bbb6c626af68e56023c777a'
    ak = f'https://image-cdn-ak.spotifycdn.com/image/{image_id}'
    candidates = spotify_cover_url_candidates(ak)
    assert candidates[0] == ak
    assert 'image-cdn-fa.spotifycdn.com' in candidates[1]


def test_download_cover_falls_back_to_second_cdn(monkeypatch):
    image_id = 'ab67616d0000b2739bbb6c626af68e56023c777a'
    calls: list[str] = []

    def fake_get(url: str, timeout: int = 15):
        calls.append(url)
        if 'image-cdn-fa' in url:
            raise requests.ConnectionError('fa down')
        resp = MagicMock()
        resp.content = b'jpeg'
        resp.raise_for_status.return_value = None
        return resp

    monkeypatch.setattr('downtify.downloader.requests.get', fake_get)
    assert _download_cover(f'https://i.scdn.co/image/{image_id}') == b'jpeg'
    assert len(calls) == 2
    assert 'image-cdn-fa.spotifycdn.com' in calls[0]
    assert 'image-cdn-ak.spotifycdn.com' in calls[1]
