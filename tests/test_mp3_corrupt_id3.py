"""Recover tagging when Soulseek MP3s ship corrupt/truncated ID3 headers."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from mutagen.id3 import ID3, TIT2
from mutagen.id3._util import error as ID3Error
from mutagen.mp3 import MP3

from downtify.downloader import (
    _mpeg_audio_frame_offset,
    _open_mp3_for_tagging,
    embed_metadata,
)


def _synchsafe(size: int) -> bytes:
    return bytes([
        (size >> 21) & 0x7F,
        (size >> 14) & 0x7F,
        (size >> 7) & 0x7F,
        size & 0x7F,
    ])


def _ffmpeg_available() -> bool:
    return shutil.which('ffmpeg') is not None


def _write_tiny_mp3(path: Path) -> None:
    subprocess.run(
        [
            'ffmpeg',
            '-y',
            '-f',
            'lavfi',
            '-i',
            'anullsrc=r=44100:cl=mono',
            '-t',
            '0.2',
            '-q:a',
            '9',
            str(path),
        ],
        check=True,
        capture_output=True,
    )


def _prepend_corrupt_id3(path: Path) -> None:
    path.write_bytes(
        b'ID3\x03\x00\x00' + _synchsafe(351_155) + path.read_bytes()
    )


@pytest.mark.skipif(not _ffmpeg_available(), reason='ffmpeg required')
def test_open_mp3_strips_oversized_corrupt_id3(tmp_path: Path) -> None:
    path = tmp_path / 'track.mp3'
    _write_tiny_mp3(path)
    _prepend_corrupt_id3(path)

    with pytest.raises(ID3Error):
        MP3(str(path), ID3=ID3)

    audio = _open_mp3_for_tagging(path)
    audio.tags.delall('TIT2')
    audio.tags.add(TIT2(encoding=3, text='Recovered'))
    audio.save(v2_version=3)

    tagged = MP3(str(path), ID3=ID3)
    assert str(tagged.tags.get('TIT2')) == 'Recovered'


@pytest.mark.skipif(not _ffmpeg_available(), reason='ffmpeg required')
def test_embed_metadata_recovers_corrupt_id3(tmp_path: Path) -> None:
    path = tmp_path / 'smile.mp3'
    _write_tiny_mp3(path)
    _prepend_corrupt_id3(path)
    embed_metadata(
        path,
        {
            'name': 'I Just Want You To Smile',
            'artists': ['Dancing on Lego'],
            'album_name': 'Single',
            'year': '2024',
        },
    )
    tagged = MP3(str(path), ID3=ID3)
    assert 'Smile' in str(tagged.tags.get('TIT2'))
    assert 'Dancing' in str(tagged.tags.get('TPE1'))


def test_mpeg_audio_frame_offset_skips_oversized_id3_claim() -> None:
    frame = b'\xff\xfb\x90\x00' + b'\x00' * 32
    data = b'ID3\x03\x00\x00' + _synchsafe(351_155) + frame
    assert _mpeg_audio_frame_offset(data) == 10
