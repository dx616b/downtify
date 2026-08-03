"""slskd per-track timeout and provider fallback."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from downtify.downloader import Downloader
from downtify.slskd_provider import _wait_for_slskd_file


def test_wait_for_slskd_file_queued_timeout_without_transfer(monkeypatch):
    client = MagicMock()
    client.find_transfer.return_value = None

    sleeps: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr('downtify.slskd_provider.time.sleep', fake_sleep)
    monkeypatch.setattr(
        'downtify.slskd_provider._find_on_disk_for_song', lambda *a, **k: None
    )

    settings = {
        'poll_interval_seconds': 1,
        'poll_max_attempts': 10,
        'queued_timeout_seconds': 2,
    }
    clock = {'t': 1000.0}

    def tick() -> float:
        clock['t'] += 1.0
        return clock['t']

    monkeypatch.setattr('downtify.slskd_provider.time.monotonic', tick)

    result = _wait_for_slskd_file(
        client,
        {'name': 'Song'},
        'peer',
        'file.mp3',
        settings,
        [Path('/slskd')],
        deadline=1600.0,
    )
    assert result is None
    assert client.find_transfer.called


def test_wait_for_slskd_file_completed_transfer_not_stalled(
    monkeypatch, tmp_path: Path
):
    """A finished slskd transfer must not stall-timeout before the file appears."""
    client = MagicMock()
    client.find_transfer.return_value = {
        'id': 't1',
        'state': 'Completed, Succeeded',
        'size': 1000,
        'bytesTransferred': 1000,
        'bytesRemaining': 0,
        'percentComplete': 100,
    }

    target = tmp_path / 'file.mp3'
    calls = {'n': 0}

    def fake_find(*_a, **_k):
        calls['n'] += 1
        if calls['n'] < 3:
            return None
        target.write_bytes(b'x' * 1000)
        return target

    monkeypatch.setattr(
        'downtify.slskd_provider.time.sleep', lambda _s: None
    )
    monkeypatch.setattr(
        'downtify.slskd_provider._find_on_disk_for_song', fake_find
    )

    clock = {'t': 1000.0}

    def tick() -> float:
        clock['t'] += 5.0
        return clock['t']

    monkeypatch.setattr('downtify.slskd_provider.time.monotonic', tick)

    result = _wait_for_slskd_file(
        client,
        {'name': 'Song'},
        'peer',
        'file.mp3',
        {
            'poll_interval_seconds': 1,
            'poll_max_attempts': 10,
            # Would fire on a completed transfer under the old stall logic.
            'queued_timeout_seconds': 2,
        },
        [tmp_path],
        expected_size=1000,
        deadline=1600.0,
    )
    assert result == target


def test_resolve_video_id_falls_back_after_slskd_timeout(
    monkeypatch, tmp_path
):
    d = Downloader(
        tmp_path,
        audio_format='mp3',
        audio_providers=['slskd', 'youtube-music'],
        slskd_settings={'enabled': True, 'queued_timeout_seconds': 1},
    )
    monkeypatch.setattr(
        'downtify.downloader.download_from_slskd', lambda *a, **k: None
    )
    monkeypatch.setattr(
        'downtify.downloader.find_match',
        lambda song: ('yt123', {'name': song.get('name')}),
    )

    video_id, match, provider, local = d._resolve_video_id({
        'name': 'Track',
        'artists': ['Artist'],
    })
    assert provider == 'youtube-music'
    assert video_id == 'yt123'
    assert local is None
