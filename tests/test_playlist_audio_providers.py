"""Tests for per-playlist audio provider overrides."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from downtify.api import (
    _effective_playlist_audio_providers,
    _run_download,
    _save_playlist_audio_providers,
    state,
)
from downtify.playlist_catalog import PlaylistCatalog


@pytest.fixture
def catalog(tmp_path: Path) -> PlaylistCatalog:
    return PlaylistCatalog(tmp_path / 'library.db')


def test_catalog_audio_providers_round_trip(catalog: PlaylistCatalog) -> None:
    catalog.set_audio_providers(
        spotify_id='pl123',
        playlist_name='My Mix',
        audio_providers=['youtube-music', 'youtube'],
    )
    assert catalog.get_audio_providers('pl123') == [
        'youtube-music',
        'youtube',
    ]

    catalog.set_audio_providers(
        spotify_id='pl123',
        playlist_name='My Mix',
        audio_providers=None,
    )
    assert catalog.get_audio_providers('pl123') is None


def test_effective_playlist_audio_providers_uses_override(
    catalog: PlaylistCatalog,
) -> None:
    catalog.set_audio_providers(
        spotify_id='pl123',
        playlist_name='Rock',
        audio_providers=['youtube'],
    )
    state.playlist_catalog = catalog
    settings = {
        'audio_providers': ['youtube-music'],
        'slskd': {'enabled': False},
    }
    try:
        assert _effective_playlist_audio_providers('pl123', settings) == [
            'youtube'
        ]
        assert _effective_playlist_audio_providers('other', settings) == [
            'youtube-music'
        ]
    finally:
        state.playlist_catalog = None


def test_save_playlist_audio_providers_persists(
    catalog: PlaylistCatalog,
) -> None:
    state.playlist_catalog = catalog
    settings = {
        'audio_providers': ['youtube-music'],
        'slskd': {'enabled': False},
    }
    try:
        _save_playlist_audio_providers(
            'sid9',
            'Jazz',
            ['youtube-music', 'youtube'],
        )
        assert catalog.get_audio_providers('sid9') == [
            'youtube-music',
            'youtube',
        ]
        assert _effective_playlist_audio_providers('sid9', settings) == [
            'youtube-music',
            'youtube',
        ]
    finally:
        state.playlist_catalog = None


def test_run_download_passes_playlist_providers() -> None:
    with (
        patch('downtify.api.resolve_existing_download', return_value=None),
        patch('downtify.api.state') as mock_state,
    ):
        downloader = MagicMock()
        downloader.youtube_settings = {}
        downloader.download.return_value = 'Artist - Song.mp3'

        catalog = MagicMock()
        catalog.get_audio_providers.return_value = ['youtube']

        mock_state.downloader = downloader
        mock_state.playlist_catalog = catalog
        mock_state.track_index = None
        mock_state.settings = {
            'audio_providers': ['slskd', 'youtube-music'],
            'slskd': {'enabled': True},
        }
        mock_state.download_jobs = {}
        mock_state.download_limiter = None
        mock_state.loop = None
        mock_state.connections = MagicMock()
        mock_state.connections.broadcast = AsyncMock(return_value=None)

        async def _run() -> None:
            await _run_download(
                {'name': 'Song', 'artists': ['Artist'], 'song_id': 't1'},
                't1',
                spotify_playlist_id='playlist42',
                refresh_playlists=False,
            )

        asyncio.run(_run())

        downloader.download.assert_called_once()
        kwargs = downloader.download.call_args.kwargs
        assert kwargs['audio_providers'] == ['youtube']
