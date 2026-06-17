"""Download queue maintenance endpoints."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch

from downtify import api


def test_reconcile_stale_job_heals_when_file_on_disk():
    api.state.download_jobs.clear()
    prev_downloader = api.state.downloader
    api.state.downloader = object()
    api.state.connections.broadcast = AsyncMock()
    try:
        song_id = api._register_job(
            {'song_id': 'stale-1', 'name': 'Zombie'},
            status='downloading',
        )
        job = api.state.download_jobs[song_id]
        job['progress'] = 98
        job['updated_at'] = time.monotonic() - 700

        with patch(
            'downtify.api.resolve_existing_download',
            return_value=('track.mp3', 'Already on disk'),
        ):
            count = asyncio.run(api._reconcile_stale_download_jobs())

        assert count == 1
        assert api.state.download_jobs[song_id]['status'] == 'done'
        assert api.state.download_jobs[song_id]['filename'] == 'track.mp3'
        api.state.connections.broadcast.assert_awaited()
    finally:
        api.state.download_jobs.clear()
        api.state.downloader = prev_downloader


def test_reconcile_stale_job_removes_when_no_file_on_disk():
    api.state.download_jobs.clear()
    prev_downloader = api.state.downloader
    api.state.downloader = object()
    try:
        song_id = api._register_job(
            {'song_id': 'stale-1', 'name': 'Zombie'},
            status='downloading',
        )
        job = api.state.download_jobs[song_id]
        job['progress'] = 98
        job['updated_at'] = time.monotonic() - 700

        with patch(
            'downtify.api.resolve_existing_download',
            return_value=None,
        ):
            count = asyncio.run(api._reconcile_stale_download_jobs())

        assert count == 1
        assert song_id not in api.state.download_jobs
    finally:
        api.state.download_jobs.clear()
        api.state.downloader = prev_downloader


def test_clear_completed_queue_removes_only_done_jobs():
    api.state.download_jobs.clear()
    try:
        done_id = api._register_job(
            {'song_id': 'done-1', 'name': 'A'}, status='done'
        )
        err_id = api._register_job(
            {'song_id': 'err-1', 'name': 'B'}, status='error'
        )
        q_id = api._register_job(
            {'song_id': 'q-1', 'name': 'C'}, status='queued'
        )

        result = api.clear_completed_queue()

        assert result['removed'] == 1
        assert done_id not in api.state.download_jobs
        assert err_id in api.state.download_jobs
        assert q_id in api.state.download_jobs
    finally:
        api.state.download_jobs.clear()


def test_submit_playlist_batch_defers_while_another_runs():
    api.state.download_jobs.clear()
    api.state.pending_playlist_batches.clear()
    api.state.playlist_batch_task = None
    try:

        async def _run() -> None:
            gate = asyncio.Event()
            api.state.playlist_batch_task = asyncio.create_task(gate.wait())
            result = await api._submit_playlist_batch(
                [{'song_id': 'new-1', 'name': 'Fresh', 'url': 'x'}],
                'https://open.spotify.com/playlist/test',
                generate_m3u=False,
            )
            assert result['deferred'] is True
            assert result['queue_position'] == 1
            assert len(api.state.pending_playlist_batches) == 1
            assert 'new-1' in api.state.download_jobs
            gate.set()
            await api.state.playlist_batch_task

        asyncio.run(_run())
    finally:
        api.state.download_jobs.clear()
        api.state.pending_playlist_batches.clear()
        api.state.playlist_batch_task = None


def test_get_download_batch_status_reports_queue():
    api.state.download_jobs.clear()
    api.state.pending_playlist_batches.clear()
    api.state.playlist_batch_task = None
    try:
        api._register_job({'song_id': 'q-1', 'name': 'A'}, status='queued')
        api.state.pending_playlist_batches.append(
            api._PlaylistBatchRequest(
                songs=[{'song_id': 'p-1'}],
                job_ids=['p-1'],
                playlist_url='https://open.spotify.com/playlist/x',
                generate_m3u=False,
            )
        )

        status = api.get_download_batch_status()

        assert status['pending_batches'] == 1
        assert status['pending_tracks'] == 1
        assert status['active_downloads'] == 1
    finally:
        api.state.download_jobs.clear()
        api.state.pending_playlist_batches.clear()


def test_submit_playlist_batch_clears_completed_jobs():
    api.state.download_jobs.clear()
    try:
        api._register_job({'song_id': 'done-1', 'name': 'Old'}, status='done')
        api._register_job(
            {'song_id': 'q-1', 'name': 'Active'}, status='queued'
        )

        asyncio.run(
            api._submit_playlist_batch(
                [{'song_id': 'new-1', 'name': 'Fresh', 'url': 'x'}],
                'https://open.spotify.com/playlist/test',
                generate_m3u=False,
            )
        )

        assert 'done-1' not in api.state.download_jobs
        assert 'q-1' in api.state.download_jobs
        assert 'new-1' in api.state.download_jobs
    finally:
        api.state.download_jobs.clear()


def test_prune_queue_after_batch_clears_done_and_broadcasts():
    api.state.download_jobs.clear()
    try:
        api._register_job({'song_id': 'done-1', 'name': 'A'}, status='done')
        api._register_job({'song_id': 'q-1', 'name': 'B'}, status='queued')
        api.state.connections.broadcast = AsyncMock()

        removed = asyncio.run(api._prune_queue_after_batch())

        assert removed == 1
        assert 'done-1' not in api.state.download_jobs
        assert 'q-1' in api.state.download_jobs
        api.state.connections.broadcast.assert_awaited_once_with({
            'status': 'playlist_batches_changed',
            'queue_pruned': 1,
        })
    finally:
        api.state.download_jobs.clear()


def test_prune_queue_after_batch_broadcasts_when_nothing_to_clear():
    api.state.download_jobs.clear()
    try:
        api._register_job({'song_id': 'q-1', 'name': 'B'}, status='queued')
        api.state.connections.broadcast = AsyncMock()

        removed = asyncio.run(api._prune_queue_after_batch())

        assert removed == 0
        api.state.connections.broadcast.assert_awaited_once_with({
            'status': 'playlist_batches_changed',
            'queue_pruned': 0,
        })
    finally:
        api.state.download_jobs.clear()


def test_retry_failed_queue_requeues_only_errors():
    api.state.download_jobs.clear()
    prev_downloader = api.state.downloader
    prev_connections = api.state.connections
    prev_run_download = api._run_download
    api.state.downloader = object()
    api.state.connections = AsyncMock()
    try:
        err_id = api._register_job(
            {'song_id': 'err-1', 'name': 'Fail'}, status='error'
        )
        done_id = api._register_job(
            {'song_id': 'done-1', 'name': 'Ok'}, status='done'
        )

        async def _noop_download(*_args, **_kwargs):
            return None

        api._run_download = _noop_download  # type: ignore[method-assign]

        result = asyncio.run(api.retry_failed_queue_endpoint())

        assert result['count'] == 1
        assert result['job_ids'] == [err_id]
        assert api.state.download_jobs[err_id]['status'] == 'queued'
        assert api.state.download_jobs[done_id]['status'] == 'done'
        api.state.connections.broadcast.assert_awaited()
    finally:
        api.state.download_jobs.clear()
        api.state.downloader = prev_downloader
        api.state.connections = prev_connections
        api._run_download = prev_run_download
