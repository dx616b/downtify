"""Background filesystem scans for ``list_library_paths``."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Callable, Optional

from loguru import logger

from .library_paths_cache import (
    paths_rescan_in_progress,
    set_cached_paths,
)

if TYPE_CHECKING:
    from .library_catalog import LibraryContext

_SCAN_INTERVAL_SECONDS = 300.0
_scan_tasks: dict[str, asyncio.Task[None]] = {}


def _cache_key(ctx: LibraryContext) -> str:
    parts = [str(ctx.download_dir.resolve())]
    if ctx.slskd_dir is not None:
        try:
            parts.append(str(ctx.slskd_dir.resolve()))
        except OSError:
            parts.append(str(ctx.slskd_dir))
    else:
        parts.append('')
    return '|'.join(parts)


async def schedule_library_paths_rescan(
    ctx: LibraryContext,
    scan_fn: Callable[[LibraryContext], list[str]],
) -> None:
    """Run a full tree scan off the event loop and refresh the path cache."""

    key = _cache_key(ctx)
    existing = _scan_tasks.get(key)
    if existing is not None and not existing.done():
        return

    async def _run() -> None:
        try:
            paths = await asyncio.to_thread(scan_fn, ctx)
            set_cached_paths(ctx, paths)
            logger.debug('Library path scan finished: {} path(s)', len(paths))
        except Exception:
            logger.exception('Background library path scan failed')
        finally:
            _scan_tasks.pop(key, None)

    _scan_tasks[key] = asyncio.create_task(_run())


async def library_paths_scan_loop(
    get_ctx: Callable[[], Optional[LibraryContext]],
    scan_fn: Callable[[LibraryContext], list[str]],
    *,
    interval_seconds: float = _SCAN_INTERVAL_SECONDS,
) -> None:
    """Periodically refresh the library path cache."""

    while True:
        await asyncio.sleep(interval_seconds)
        ctx = get_ctx()
        if ctx is None:
            continue
        await schedule_library_paths_rescan(ctx, scan_fn)


def library_paths_scan_running(ctx: LibraryContext) -> bool:
    key = _cache_key(ctx)
    task = _scan_tasks.get(key)
    if task is not None and not task.done():
        return True
    return paths_rescan_in_progress(ctx)
