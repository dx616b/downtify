"""Tests for lrclib fetch and lyrics tag embedding."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from mutagen.id3 import USLT

from downtify.downloader import embed_lyrics
from downtify.lyrics import Lyrics, fetch


def _song(**overrides) -> dict:
    base = {
        'name': 'Test Song',
        'artists': ['Test Artist'],
        'album_name': 'Test Album',
        'duration': 200,
    }
    base.update(overrides)
    return base


def _mock_lrclib_response(
    *,
    status_code: int = 200,
    plain: str = 'Line one\nLine two',
    synced: str = '[00:01.00] Line one\n[00:02.00] Line two',
) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    if status_code == 200:
        resp.json.return_value = {
            'plainLyrics': plain,
            'syncedLyrics': synced,
        }
    return resp


@patch('downtify.lyrics.requests.get')
def test_fetch_lrclib_returns_lyrics(mock_get: MagicMock) -> None:
    mock_get.return_value = _mock_lrclib_response()

    result = fetch(_song(), ['lrclib'])

    assert result is not None
    assert result.plain == 'Line one\nLine two'
    assert result.synced == '[00:01.00] Line one\n[00:02.00] Line two'
    mock_get.assert_called_once()
    call = mock_get.call_args
    assert call.args[0] == 'https://lrclib.net/api/get'
    params = call.kwargs['params']
    assert params['track_name'] == 'Test Song'
    assert params['artist_name'] == 'Test Artist'
    assert params['album_name'] == 'Test Album'
    assert params['duration'] == 200


@patch('downtify.lyrics.requests.get')
def test_fetch_skips_unsupported_providers(mock_get: MagicMock) -> None:
    mock_get.return_value = _mock_lrclib_response(plain='ok', synced='')

    result = fetch(_song(), ['genius', 'lrclib'])

    assert result is not None
    assert result.plain == 'ok'
    mock_get.assert_called_once()


@patch('downtify.lyrics.requests.get')
def test_fetch_returns_none_on_404(mock_get: MagicMock) -> None:
    mock_get.return_value = _mock_lrclib_response(status_code=404)

    assert fetch(_song(), ['lrclib']) is None


def test_fetch_returns_none_without_title_or_artists() -> None:
    assert fetch({'name': '', 'artists': ['A']}, ['lrclib']) is None
    assert fetch({'name': 'Song', 'artists': []}, ['lrclib']) is None


@patch('downtify.downloader.MP3')
def test_embed_lyrics_mp3_writes_uslt_and_lrc(
    mock_mp3: MagicMock, tmp_path: Path
) -> None:
    path = tmp_path / 'track.mp3'
    path.write_bytes(b'\x00')
    audio = MagicMock()
    audio.tags = MagicMock()
    mock_mp3.return_value = audio

    embed_lyrics(
        path,
        Lyrics(
            plain='Plain text',
            synced='[00:01.00] Synced line',
        ),
    )

    audio.tags.delall.assert_called_once_with('USLT')
    added = audio.tags.add.call_args.args[0]
    assert isinstance(added, USLT)
    assert added.text == 'Plain text'
    audio.save.assert_called_once_with(v2_version=3)
    assert (tmp_path / 'track.lrc').read_text(encoding='utf-8') == (
        '[00:01.00] Synced line'
    )


@patch('downtify.downloader.FLAC')
def test_embed_lyrics_flac_writes_vorbis_lyrics(
    mock_flac: MagicMock, tmp_path: Path
) -> None:
    path = tmp_path / 'track.flac'
    path.write_bytes(b'\x00')
    audio = MagicMock()
    mock_flac.return_value = audio

    embed_lyrics(path, Lyrics(plain='Flac lyrics', synced=None))

    audio.__setitem__.assert_called_once_with('lyrics', 'Flac lyrics')
    audio.save.assert_called_once()


@patch('downtify.downloader.MP4')
def test_embed_lyrics_m4a_writes_lyr_tag(
    mock_mp4: MagicMock, tmp_path: Path
) -> None:
    path = tmp_path / 'track.m4a'
    path.write_bytes(b'\x00')
    audio = MagicMock()
    mock_mp4.return_value = audio

    embed_lyrics(path, Lyrics(plain='M4A lyrics', synced=None))

    audio.__setitem__.assert_called_once_with('\xa9lyr', 'M4A lyrics')
    audio.save.assert_called_once()


@patch('downtify.downloader.MP3')
def test_embed_lyrics_synced_only_strips_timestamps_for_tags(
    mock_mp3: MagicMock, tmp_path: Path
) -> None:
    path = tmp_path / 'track.mp3'
    path.write_bytes(b'\x00')
    audio = MagicMock()
    audio.tags = MagicMock()
    mock_mp3.return_value = audio

    embed_lyrics(
        path,
        Lyrics(
            plain=None,
            synced='[00:01.00] Hello\n[00:02.50] World',
        ),
    )

    added = audio.tags.add.call_args.args[0]
    assert added.text == 'Hello\nWorld'
    assert (
        (tmp_path / 'track.lrc')
        .read_text(encoding='utf-8')
        .startswith('[00:01.00]')
    )
