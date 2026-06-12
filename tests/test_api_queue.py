"""Download queue maintenance endpoints."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

from downtify import api


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
        api._register_job(
            {'song_id': 'q-1', 'name': 'B'}, status='queued'
        )
        api.state.connections.broadcast = AsyncMock()

        removed = asyncio.run(api._prune_queue_after_batch())

        assert removed == 1
        assert 'done-1' not in api.state.download_jobs
        assert 'q-1' in api.state.download_jobs
        api.state.connections.broadcast.assert_awaited_once_with(
            {'status': 'playlist_batches_changed', 'queue_pruned': 1}
        )
    finally:
        api.state.download_jobs.clear()


def test_prune_queue_after_batch_broadcasts_when_nothing_to_clear():
    api.state.download_jobs.clear()
    try:
        api._register_job(
            {'song_id': 'q-1', 'name': 'B'}, status='queued'
        )
        api.state.connections.broadcast = AsyncMock()

        removed = asyncio.run(api._prune_queue_after_batch())

        assert removed == 0
        api.state.connections.broadcast.assert_awaited_once_with(
            {'status': 'playlist_batches_changed', 'queue_pruned': 0}
        )
    finally:
        api.state.download_jobs.clear()
