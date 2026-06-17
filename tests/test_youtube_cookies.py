"""YouTube cookies settings and yt-dlp option wiring."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from downtify.api import (
    DEFAULT_SETTINGS,
    _effective_youtube_settings,
    _validate_youtube_cookies_bytes,
    _youtube_cookies_storage_path,
    _youtube_settings_for_response,
)
from downtify.downloader import (
    _YTDLP_AUDIO_FORMATS,
    _cookie_yt_player_clients,
    _youtube_download_profiles,
    _youtube_extractor_args,
    _ytdlp_extract_info,
    _ytdlp_ffmpeg_opts,
    _ytdlp_format_unavailable_retry,
    _ytdlp_info_profiles,
    _ytdlp_js_runtime_opts,
    _ytdlp_should_retry_without_cookies,
    _ytdlp_should_try_alternate_video,
    apply_ytdlp_cookie_opts,
    inspect_youtube_cookies,
    ytdlp_cookies_configured,
)


def test_default_settings_includes_youtube():
    assert 'youtube' in DEFAULT_SETTINGS
    assert not DEFAULT_SETTINGS['youtube']['cookies_file']


def test_effective_youtube_settings_strips_paths():
    settings = {
        'youtube': {
            'cookies_file': '  /data/cookies.txt  ',
            'cookies_from_browser': ' chrome:Default ',
            'po_token': '  mweb.gvs+ABC  ',
        }
    }
    out = _effective_youtube_settings(settings)
    assert out['cookies_file'] == '/data/cookies.txt'
    assert out['cookies_from_browser'] == 'chrome:Default'
    assert out['po_token'] == 'mweb.gvs+ABC'


def test_apply_ytdlp_cookie_opts_from_settings(tmp_path: Path):
    cookie_path = tmp_path / 'cookies.txt'
    cookie_path.write_text(
        '# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t0\tx\ty\n',
        encoding='utf-8',
    )
    opts: dict = {}
    apply_ytdlp_cookie_opts(
        opts, {'cookies_file': str(cookie_path), 'cookies_from_browser': ''}
    )
    assert opts['cookiefile'] == str(cookie_path)


def test_apply_ytdlp_cookie_opts_skips_missing_file():
    opts: dict = {}
    apply_ytdlp_cookie_opts(opts, {'cookies_file': '/no/such/cookies.txt'})
    assert 'cookiefile' not in opts


def test_youtube_settings_for_response_exists_flag(tmp_path: Path):
    cookie_path = tmp_path / 'cookies.txt'
    cookie_path.write_text(
        '# Netscape HTTP Cookie File\n'
        '.youtube.com\tTRUE\t/\tTRUE\t0\tLOGIN_INFO\tabc\n'
        '.youtube.com\tTRUE\t/\tTRUE\t0\tSID\txyz\n',
        encoding='utf-8',
    )
    settings = {'youtube': {'cookies_file': str(cookie_path)}}
    out = _youtube_settings_for_response(settings)
    assert out['cookies_file_exists'] is True
    assert out['cookies_looks_authenticated'] is True
    assert 'LOGIN_INFO' in out['cookies_auth_names']


def test_youtube_settings_for_response_weak_cookies(tmp_path: Path):
    cookie_path = tmp_path / 'cookies.txt'
    cookie_path.write_text('.youtube.com\n', encoding='utf-8')
    settings = {'youtube': {'cookies_file': str(cookie_path)}}
    out = _youtube_settings_for_response(settings)
    assert out['cookies_file_exists'] is True
    assert out['cookies_looks_authenticated'] is False


def test_inspect_youtube_cookies_detects_missing_login(tmp_path: Path):
    cookie_path = tmp_path / 'cookies.txt'
    cookie_path.write_text(
        '# Netscape\n.other.com\tTRUE\t/\tFALSE\t0\tfoo\tbar\n',
        encoding='utf-8',
    )
    health = inspect_youtube_cookies(cookie_path)
    assert health['looks_authenticated'] is False
    assert health['warnings']


def test_cookie_yt_player_clients_prefers_web_creator():
    clients = _cookie_yt_player_clients()
    assert clients[0] == 'web_creator'
    assert 'tv' not in clients
    assert 'tv_downgraded' not in clients


def test_cookie_yt_player_clients_prefers_mweb_with_po_token(monkeypatch):
    monkeypatch.setenv('DOWNTIFY_YT_PO_TOKEN', 'web.gvs+TEST')
    clients = _cookie_yt_player_clients()
    assert clients[0] == 'mweb'
    assert clients[1] == 'web_creator'


def test_ytdlp_should_try_alternate_video_on_age_gate():
    assert _ytdlp_should_try_alternate_video(
        Exception('Sign in to confirm your age')
    )


def test_youtube_cookies_storage_path_next_to_settings(tmp_path: Path):
    settings_path = tmp_path / 'settings.json'
    assert _youtube_cookies_storage_path(settings_path) == (
        tmp_path / 'youtube-cookies.txt'
    )


def test_youtube_download_profiles_cookie_then_no_cookies(tmp_path: Path):
    cookie_path = tmp_path / 'cookies.txt'
    cookie_path.write_text('.youtube.com\n', encoding='utf-8')
    settings = {'cookies_file': str(cookie_path)}
    profiles = _youtube_download_profiles('abc123', settings)
    assert len(profiles) == 2
    assert profiles[0]['use_cookies'] is True
    assert profiles[0]['urls'] == ['https://www.youtube.com/watch?v=abc123']
    assert profiles[1]['use_cookies'] is False


def test_youtube_download_profiles_no_cookies_only():
    profiles = _youtube_download_profiles('abc123', {})
    assert len(profiles) == 1
    assert profiles[0]['use_cookies'] is False


def test_ytdlp_should_retry_without_cookies_on_only_images():
    assert _ytdlp_should_retry_without_cookies(
        Exception('Only images are available'),
        used_cookies=True,
    )
    assert _ytdlp_should_retry_without_cookies(
        Exception('This video is DRM protected'),
        used_cookies=True,
    )
    assert not _ytdlp_should_retry_without_cookies(
        Exception('age-restricted'),
        used_cookies=True,
    )


def test_ytdlp_should_try_alternate_video_on_drm():
    assert _ytdlp_should_try_alternate_video(
        Exception('This video is DRM protected')
    )


def test_youtube_watch_urls_prefers_www_with_cookies(tmp_path: Path):
    cookie_path = tmp_path / 'cookies.txt'
    cookie_path.write_text(
        '.youtube.com\n',
        encoding='utf-8',
    )
    settings = {'cookies_file': str(cookie_path)}
    profiles = _youtube_download_profiles('abc123', settings)
    assert profiles[0]['urls'][0] == 'https://www.youtube.com/watch?v=abc123'


def test_youtube_watch_urls_music_first_without_cookies():
    profiles = _youtube_download_profiles('abc123', {})
    assert profiles[0]['urls'][0].startswith('https://music.youtube.com/')


def test_ytdlp_cookies_configured_false_when_missing_file():
    assert not ytdlp_cookies_configured({'cookies_file': '/no/such.txt'})


def test_ytdlp_format_unavailable_retry_detects_message():
    assert _ytdlp_format_unavailable_retry(
        Exception('Requested format is not available')
    )


def test_youtube_extractor_args_includes_po_token(monkeypatch):
    monkeypatch.setenv('DOWNTIFY_YT_PO_TOKEN', 'web.gvs+TEST')
    args = _youtube_extractor_args({}, use_cookies=False)
    assert args['po_token'] == ['web.gvs+TEST']


def test_youtube_extractor_args_prefers_settings_po_token(monkeypatch):
    monkeypatch.setenv('DOWNTIFY_YT_PO_TOKEN', 'web.gvs+ENV')
    settings = {'po_token': 'mweb.gvs+UI'}
    args = _youtube_extractor_args(settings, use_cookies=False)
    assert args['po_token'] == ['mweb.gvs+UI']
    assert 'ios' in args['player_client']


def test_ytdlp_audio_formats_has_fallbacks():
    assert len(_YTDLP_AUDIO_FORMATS) >= 3
    assert _YTDLP_AUDIO_FORMATS[0] == 'bestaudio/best'


def test_ytdlp_info_profiles_cookie_then_no_cookies(tmp_path: Path):
    cookie_path = tmp_path / 'cookies.txt'
    cookie_path.write_text('.youtube.com\n', encoding='utf-8')
    settings = {'cookies_file': str(cookie_path)}
    profiles = _ytdlp_info_profiles(settings)
    assert len(profiles) == 2
    assert profiles[0]['use_cookies'] is False
    assert profiles[1]['use_cookies'] is True


def test_ytdlp_extract_info_retries_with_cookies(tmp_path: Path, monkeypatch):
    cookie_path = tmp_path / 'cookies.txt'
    cookie_path.write_text('.youtube.com\n', encoding='utf-8')
    settings = {'cookies_file': str(cookie_path)}
    calls: list[bool] = []

    class FakeYDL:
        def __init__(self, opts: dict) -> None:
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def extract_info(self, _url: str, download: bool = False):
            used_cookies = 'cookiefile' in self.opts
            calls.append(used_cookies)
            if not used_cookies:
                raise Exception('Requested format is not available')
            return {'title': 'Track', 'duration': 200}

    monkeypatch.setattr(
        'downtify.downloader.yt_dlp.YoutubeDL',
        FakeYDL,
    )
    info = _ytdlp_extract_info(
        'https://www.youtube.com/watch?v=abc123',
        youtube_settings=settings,
    )
    assert info is not None
    assert info['title'] == 'Track'
    assert calls == [False, True]


def test_ytdlp_ffmpeg_opts_uses_path(monkeypatch):
    monkeypatch.setattr(
        'downtify.downloader.shutil.which',
        lambda name: '/usr/bin/ffmpeg' if name == 'ffmpeg' else None,
    )
    assert _ytdlp_ffmpeg_opts() == {'ffmpeg_location': '/usr/bin/ffmpeg'}


def test_ytdlp_js_runtime_opts_uses_deno_when_present(monkeypatch):
    monkeypatch.setattr('downtify.downloader.shutil.which', lambda _: '/usr/bin/deno')
    assert _ytdlp_js_runtime_opts() == {'js_runtimes': {'deno': {}}}


def test_ytdlp_js_runtime_opts_empty_without_deno(monkeypatch):
    monkeypatch.setattr('downtify.downloader.shutil.which', lambda _: None)
    assert _ytdlp_js_runtime_opts() == {}


def test_validate_youtube_cookies_bytes_rejects_empty():
    with pytest.raises(HTTPException) as exc:
        _validate_youtube_cookies_bytes(b'   ')
    assert exc.value.status_code == 400
