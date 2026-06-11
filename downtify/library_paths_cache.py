"""In-memory cache for ``list_library_paths`` (avoids repeated full-tree scans)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .library_catalog import LibraryContext

_PATH_CACHE: dict[str, tuple[float, list[str]]] = {}
_RESCAN_PENDING: set[str] = set()
_CACHE_TTL_SECONDS = 300.0
_rescan_callback: object | None = None
_change_listeners: list[object] = []


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


def set_cached_paths(ctx: LibraryContext, paths: list[str]) -> None:
    """Store a scan result (background job or startup warm-up)."""

    key = _cache_key(ctx)
    _PATH_CACHE[key] = (time.monotonic(), list(paths))
    _RESCAN_PENDING.discard(key)


def paths_rescan_in_progress(ctx: LibraryContext) -> bool:
    return _cache_key(ctx) in _RESCAN_PENDING


def request_paths_rescan(ctx: LibraryContext) -> None:
    """Mark cache stale; keep serving last snapshot until rescan completes."""

    _RESCAN_PENDING.add(_cache_key(ctx))


def get_cached_paths(
    ctx: LibraryContext,
    scan_fn,
    *,
    bootstrap_fn=None,
) -> list[str]:
    """Return cached paths without blocking on a full disk walk."""

    key = _cache_key(ctx)
    now = time.monotonic()
    hit = _PATH_CACHE.get(key)
    if hit is not None:
        return list(hit[1])

    if bootstrap_fn is not None:
        paths = bootstrap_fn(ctx)
        if paths:
            _PATH_CACHE[key] = (now, list(paths))
            return list(paths)

    return []


def set_paths_rescan_callback(callback) -> None:
    """Register a hook that schedules a background path scan."""

    global _rescan_callback
    _rescan_callback = callback


def register_paths_change_listener(callback) -> None:
    """Register hooks that run when library paths change."""

    _change_listeners.append(callback)


def invalidate_library_paths_cache() -> None:
    """Drop cached path lists (call after downloads, deletes, or path reconcile)."""

    _PATH_CACHE.clear()
    _RESCAN_PENDING.clear()
    if _rescan_callback is not None:
        try:
            _rescan_callback()
        except Exception:
            pass
    for listener in _change_listeners:
        try:
            listener()
        except Exception:
            pass
