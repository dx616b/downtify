"""Tests for ``downtify.library_paths_cache``."""

from __future__ import annotations

import asyncio
import threading

from downtify.library_paths_cache import (
    invalidate_library_paths_cache,
    set_paths_rescan_callback,
)


def test_invalidate_rescan_callback_safe_from_worker_thread() -> None:
    loop = asyncio.new_event_loop()
    started: list[str] = []
    done = threading.Event()

    async def _rescan() -> None:
        started.append('ok')
        done.set()

    def _schedule() -> None:
        loop.call_soon_threadsafe(lambda: asyncio.create_task(_rescan()))

    set_paths_rescan_callback(_schedule)
    try:
        thread = threading.Thread(target=invalidate_library_paths_cache)
        thread.start()
        thread.join()

        async def _wait_done() -> None:
            while not done.is_set():
                await asyncio.sleep(0.01)

        loop.run_until_complete(asyncio.wait_for(_wait_done(), timeout=1.0))
        assert started == ['ok']
    finally:
        set_paths_rescan_callback(None)
        loop.close()
