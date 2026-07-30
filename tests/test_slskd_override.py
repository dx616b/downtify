"""Manual slskd override (failed-queue retry) tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from downtify.api import _merge_client_track_hints
from downtify.slskd_provider import (
    SlskdClient,
    _download_slskd_direct,
    _enqueue_failures,
    _remote_parent_dir,
    _transfer_remote_size_mismatch,
    _wait_for_slskd_file,
    parse_slskd_override_text,
)


def test_parse_slskd_override_pipe_format():
    text = (
        'Manelo | @@wibgr\\EUROPA\\Ivi Adamou - San Ena Oniro (2012)\\'
        '06 - Ivi Adamou, Melisses - Krata Ta Matia Sou klista.mp3'
    )
    parsed = parse_slskd_override_text(text)
    assert parsed is not None
    assert parsed['username'] == 'Manelo'
    assert parsed['filename'].startswith('@@wibgr')
    assert parsed['filename'].endswith('.mp3')


def test_parse_slskd_override_space_format():
    parsed = parse_slskd_override_text('peer1 @@x\\Artist - Track.mp3')
    assert parsed == {
        'username': 'peer1',
        'filename': '@@x\\Artist - Track.mp3',
    }


def test_merge_applies_slskd_override_hints():
    base: dict[str, Any] = {
        'song_id': 'spotify:id',
        'url': 'https://open.spotify.com/track/x',
    }
    _merge_client_track_hints(
        base,
        {
            'slskd_override': True,
            'slskd_username': ' Manelo ',
            'slskd_filename': '@@wibgr\\track.mp3',
            'slskd_size': 6780000,
        },
    )
    assert base['slskd_override'] is True
    assert base['slskd_username'] == 'Manelo'
    assert base['slskd_filename'] == '@@wibgr\\track.mp3'
    assert base['slskd_size'] == 6780000


def test_download_slskd_direct_skips_search(monkeypatch, tmp_path: Path):
    slskd_dir = tmp_path / 'slskd'
    slskd_dir.mkdir()
    track = slskd_dir / '06 - Track.mp3'
    track.write_bytes(b'0' * 80_000)

    enqueued: list[dict[str, Any]] = []

    def _fake_client(_settings: dict[str, Any]) -> MagicMock:
        client = MagicMock()
        client.base_url = 'http://slskd:5030'
        client.configured.return_value = True
        client.can_connect.return_value = True
        client.remote_download_directories.return_value = []

        def _enqueue(row: dict[str, Any]) -> bool:
            enqueued.append(dict(row))
            return True

        client.enqueue_download.side_effect = _enqueue
        client.find_transfer.return_value = {
            'state': 'Completed',
            'bytesTransferred': 80_000,
            'size': 80_000,
            'percentComplete': 100,
        }
        return client

    monkeypatch.setattr(
        'downtify.slskd_provider.SlskdClient',
        _fake_client,
    )
    monkeypatch.setattr(
        'downtify.slskd_provider._find_on_disk_for_song',
        lambda *args, **kwargs: track,
    )
    monkeypatch.setattr(
        'downtify.slskd_provider.verify_downloaded_file_matches_spotify',
        lambda path, row: True,
    )
    monkeypatch.setattr(
        'downtify.slskd_provider._slskd_semaphore',
        lambda settings: MagicMock(
            __enter__=lambda self: self, __exit__=lambda *a: None
        ),
    )

    settings = {
        'enabled': True,
        'source_dir': str(slskd_dir),
        'output_dir': str(tmp_path / 'downloads'),
        'leave_in_place': True,
        'download_timeout_seconds': 600,
        'queued_timeout_seconds': 180,
    }
    song = {
        'name': 'Krata Ta Matia Sou klista',
        'artists': ['Ivi Adamou', 'Melisses'],
        'slskd_override': True,
        'slskd_username': 'Manelo',
        'slskd_filename': '@@wibgr\\Album\\06 - Track.mp3',
        'slskd_size': 80_000,
    }

    result = _download_slskd_direct(song, settings)
    assert result == track
    assert len(enqueued) == 1
    assert enqueued[0]['username'] == 'Manelo'
    assert enqueued[0]['filename'].startswith('@@wibgr')


def test_download_slskd_direct_keeps_file_when_tags_differ(
    monkeypatch, tmp_path: Path
):
    slskd_dir = tmp_path / 'slskd'
    slskd_dir.mkdir()
    track = slskd_dir / '18 - Audiense - Desert Rose (Original Mix).mp3'
    track.write_bytes(b'0' * 80_000)

    def _fake_client(_settings: dict[str, Any]) -> MagicMock:
        client = MagicMock()
        client.configured.return_value = True
        client.can_connect.return_value = True
        client.remote_download_directories.return_value = []
        client.enqueue_download.return_value = True
        client.find_transfer.return_value = {
            'state': 'Completed, Succeeded',
            'bytesTransferred': 80_000,
            'size': 80_000,
            'percentComplete': 100,
        }
        return client

    monkeypatch.setattr('downtify.slskd_provider.SlskdClient', _fake_client)
    monkeypatch.setattr(
        'downtify.slskd_provider._find_on_disk_for_song',
        lambda *args, **kwargs: track,
    )
    monkeypatch.setattr(
        'downtify.slskd_provider.verify_downloaded_file_matches_spotify',
        lambda path, row: False,
    )
    monkeypatch.setattr(
        'downtify.slskd_provider.read_audio_metadata',
        lambda path: {
            'title': 'Desert Rose (Original Mix)',
            'artists': ['Audiense'],
        },
    )
    monkeypatch.setattr(
        'downtify.slskd_provider._slskd_semaphore',
        lambda settings: MagicMock(
            __enter__=lambda self: self, __exit__=lambda *a: None
        ),
    )

    settings = {
        'enabled': True,
        'source_dir': str(slskd_dir),
        'output_dir': str(tmp_path / 'downloads'),
        'leave_in_place': True,
    }
    song = {
        'name': 'Desert Rose (DOTB Deepdub) - Mixed',
        'artists': ['Audiense'],
        'slskd_override': True,
        'slskd_username': 'Zambererronni',
        'slskd_filename': (
            '@@x\\Album\\18 - Audiense - Desert Rose (Original Mix).mp3'
        ),
        'slskd_size': 80_000,
    }

    assert _download_slskd_direct(song, settings) == track
    assert track.is_file()


def test_remote_parent_dir_handles_soulseek_separators():
    assert (
        _remote_parent_dir('@@wibgr\\Album\\06 - Track.mp3')
        == '@@wibgr\\Album'
    )
    assert _remote_parent_dir('share/Album/track.flac') == 'share/Album'
    assert not _remote_parent_dir('track.flac')


def test_enqueue_failures_reads_slskd_response():
    assert _enqueue_failures({
        'enqueued': [],
        'failed': [{'filename': 'x.mp3', 'message': 'File not shared'}],
    }) == ['File not shared']
    assert _enqueue_failures({'enqueued': [{'id': '1'}], 'failed': []}) == []
    assert _enqueue_failures(None) == []


def test_transfer_remote_size_mismatch_parses_exception():
    transfer = {
        'state': 'Completed, Aborted',
        'exception': (
            'Transfer aborted: the remote size of 36988402 does not '
            'match expected size 0'
        ),
    }
    assert _transfer_remote_size_mismatch(transfer) == 36988402
    assert _transfer_remote_size_mismatch({'state': 'Errored'}) == 0


def test_remote_file_size_browses_peer_directory(monkeypatch):
    client = SlskdClient({'base_url': 'http://slskd:5030', 'api_key': 'k'})
    calls: list[tuple[str, str, Any]] = []

    def _request(
        method: str, path: str, *, json_body: Any = None
    ) -> list[dict[str, Any]]:
        calls.append((method, path, json_body))
        return [
            {
                'name': '@@wibgr\\Album',
                'files': [
                    {'filename': 'other.mp3', 'size': 1},
                    {
                        'filename': '@@wibgr\\Album\\06 - Track.flac',
                        'size': 36988402,
                    },
                ],
            }
        ]

    monkeypatch.setattr(client, '_request', _request)
    size = client.remote_file_size(
        'Pixel9098', '@@wibgr\\Album\\06 - Track.flac'
    )
    assert size == 36988402
    assert calls[0][0] == 'POST'
    assert calls[0][1] == '/api/v0/users/Pixel9098/directory'
    assert calls[0][2] == {'directory': '@@wibgr\\Album'}


def test_remote_file_size_falls_back_to_search(monkeypatch):
    client = SlskdClient({
        'base_url': 'http://slskd:5030',
        'api_key': 'k',
        'search_retries': 1,
        'search_poll_seconds': 1,
    })
    monkeypatch.setattr(client, 'directory_contents', lambda *a, **k: [])
    monkeypatch.setattr(client, 'start_search', lambda q: 'search-1')
    monkeypatch.setattr(
        client,
        '_request',
        lambda method, path, **kw: {'isComplete': True},
    )
    monkeypatch.setattr(
        client,
        'search_responses',
        lambda search_id: [
            {
                'username': 'misticgris',
                'files': [
                    {
                        'filename': (
                            '@@xjjro\\MUSIC\\Mantra (Elfenberg Remix).mp3'
                        ),
                        'size': 12_345_678,
                    }
                ],
            }
        ],
    )
    deleted: list[str] = []
    monkeypatch.setattr(client, 'delete_search', deleted.append)

    size = client.remote_file_size(
        'misticgris',
        '@@xjjro\\MUSIC\\Mantra (Elfenberg Remix).mp3',
    )
    assert size == 12_345_678
    assert deleted == ['search-1']


def test_find_transfer_prefers_active_over_aborted():
    client = SlskdClient({'base_url': 'http://slskd:5030', 'api_key': 'k'})
    client.list_download_transfers = lambda: [  # type: ignore[method-assign]
        {
            'username': 'misticgris',
            'directories': [
                {
                    'files': [
                        {
                            'id': 'abort-1',
                            'filename': '@@x\\Mantra.mp3',
                            'state': 'Completed, Aborted',
                            'size': 0,
                        },
                        {
                            'id': 'ok-1',
                            'filename': '@@x\\Mantra.mp3',
                            'state': 'InProgress',
                            'size': 123,
                        },
                    ]
                }
            ],
        }
    ]
    row = client.find_transfer('misticgris', '@@x\\Mantra.mp3')
    assert row is not None
    assert row['id'] == 'ok-1'
    ignored = client.find_transfer(
        'misticgris', '@@x\\Mantra.mp3', ignore_ids={'ok-1'}
    )
    assert ignored is not None
    assert ignored['id'] == 'abort-1'


def test_manual_override_resolves_missing_size_before_enqueue(
    monkeypatch, tmp_path: Path
):
    slskd_dir = tmp_path / 'slskd'
    slskd_dir.mkdir()
    track = slskd_dir / 'Track.flac'
    track.write_bytes(b'0' * 80_000)

    enqueued: list[dict[str, Any]] = []

    def _fake_client(_settings: dict[str, Any]) -> MagicMock:
        client = MagicMock()
        client.configured.return_value = True
        client.can_connect.return_value = True
        client.remote_download_directories.return_value = []
        client.remote_file_size.return_value = 36988402
        client.enqueue_download.side_effect = lambda row: bool(
            enqueued.append(dict(row)) or True
        )
        client.find_transfer.return_value = {
            'state': 'Completed, Succeeded',
            'bytesTransferred': 36988402,
            'size': 36988402,
            'percentComplete': 100,
        }
        return client

    monkeypatch.setattr('downtify.slskd_provider.SlskdClient', _fake_client)
    monkeypatch.setattr(
        'downtify.slskd_provider._find_on_disk_for_song',
        lambda *args, **kwargs: track,
    )
    monkeypatch.setattr(
        'downtify.slskd_provider.verify_downloaded_file_matches_spotify',
        lambda path, row: True,
    )
    monkeypatch.setattr(
        'downtify.slskd_provider._disk_complete',
        lambda path, expected: True,
    )
    monkeypatch.setattr(
        'downtify.slskd_provider._slskd_semaphore',
        lambda settings: MagicMock(
            __enter__=lambda self: self, __exit__=lambda *a: None
        ),
    )

    settings = {
        'enabled': True,
        'source_dir': str(slskd_dir),
        'output_dir': str(tmp_path / 'downloads'),
        'leave_in_place': True,
    }
    song = {
        'name': 'Tab Leh',
        'artists': ['Hrag Mikkel'],
        'slskd_override': True,
        'slskd_username': 'Pixel9098',
        'slskd_filename': 'Dj\\Indian\\49 - Tab Leh.flac',
    }

    assert _download_slskd_direct(song, settings) == track
    assert len(enqueued) == 1
    assert enqueued[0]['size'] == 36988402


def test_wait_reenqueues_with_remote_size_after_mismatch(
    monkeypatch, tmp_path: Path
):
    monkeypatch.setattr('downtify.slskd_provider.time.sleep', lambda _s: None)
    enqueued: list[dict[str, Any]] = []
    aborted = {
        'id': 'abort-1',
        'state': 'Completed, Aborted',
        'exception': (
            'Transfer aborted: the remote size of 36988402 does not '
            'match expected size 0'
        ),
        'bytesTransferred': 0,
        'size': 0,
    }
    active = {
        'id': 'ok-1',
        'state': 'InProgress',
        'bytesTransferred': 36988402,
        'size': 36988402,
        'percentComplete': 100,
    }
    # After retry, slskd often still lists the aborted transfer first.
    transfers = [aborted, aborted, active]

    client = MagicMock()

    def _find(
        user: str, name: str, ignore_ids: Any = None
    ) -> dict[str, Any] | None:
        ignored = ignore_ids or set()
        while transfers:
            row = transfers.pop(0)
            if str(row.get('id') or '') in ignored:
                continue
            return row
        return None

    client.find_transfer.side_effect = _find
    client.enqueue_download.side_effect = lambda row: bool(
        enqueued.append(dict(row)) or True
    )

    found = tmp_path / 'Track.flac'
    found.write_bytes(b'0')
    calls = {'n': 0}

    def _find_disk(*_args: Any, **_kwargs: Any) -> Any:
        calls['n'] += 1
        return found if calls['n'] > 2 else None

    monkeypatch.setattr(
        'downtify.slskd_provider._find_on_disk_for_song', _find_disk
    )
    monkeypatch.setattr(
        'downtify.slskd_provider._disk_complete',
        lambda path, expected: True,
    )

    result = _wait_for_slskd_file(
        client,
        {'name': 'Tab Leh'},
        'Pixel9098',
        'Dj\\Indian\\49 - Tab Leh.flac',
        {'poll_interval_seconds': 1, 'poll_max_attempts': 5},
        [tmp_path],
        expected_size=0,
    )
    assert result == found
    assert enqueued == [
        {
            'username': 'Pixel9098',
            'filename': 'Dj\\Indian\\49 - Tab Leh.flac',
            'size': 36988402,
        }
    ]
    client.cancel_transfer.assert_called_once_with('Pixel9098', 'abort-1')
