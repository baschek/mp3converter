from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Iterable

from .filenames import parse_artist_title
from .models import TrackDraft

ProgressCallback = Callable[[str], None]


class DependencyMissing(RuntimeError):
    pass


def _import_ytdlp():
    try:
        from yt_dlp import YoutubeDL
    except ImportError as exc:
        raise DependencyMissing("yt-dlp is not installed. Run: python -m pip install -e .") from exc
    return YoutubeDL


def _ffmpeg_location() -> str:
    try:
        import imageio_ffmpeg
    except ImportError as exc:
        raise DependencyMissing("imageio-ffmpeg is not installed. Run: python -m pip install -e .") from exc
    return imageio_ffmpeg.get_ffmpeg_exe()


def _entry_source_url(entry: dict[str, Any], fallback_url: str) -> str:
    url = entry.get("webpage_url") or entry.get("original_url")
    if isinstance(url, str) and url.startswith("http"):
        return url
    url = entry.get("url")
    if isinstance(url, str) and url.startswith("http"):
        return url
    video_id = entry.get("id")
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return fallback_url


def _entry_title(entry: dict[str, Any]) -> str:
    for key in ("track", "title", "fulltitle"):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "Unknown Title"


def _entry_artist(entry: dict[str, Any], title: str) -> tuple[str, str]:
    artist = entry.get("artist") or entry.get("creator")
    if isinstance(artist, str) and artist.strip():
        return artist.strip(), title
    uploader = entry.get("uploader") or entry.get("channel")
    return parse_artist_title(title, uploader if isinstance(uploader, str) else None)


def extract_tracks(
    urls: Iterable[str],
    playlist_override: str | None = None,
    progress: ProgressCallback | None = None,
) -> list[TrackDraft]:
    YoutubeDL = _import_ytdlp()
    options = {
        "ignoreerrors": True,
        "no_warnings": True,
        "quiet": True,
        "skip_download": True,
    }
    tracks: list[TrackDraft] = []

    with YoutubeDL(options) as ydl:
        for raw_url in urls:
            url = raw_url.strip()
            if not url:
                continue
            if progress:
                progress(f"Reading {url}")
            info = ydl.extract_info(url, download=False)
            if not info:
                continue

            entries = info.get("entries")
            if isinstance(entries, list):
                playlist_name = playlist_override or info.get("title") or "YouTube Playlist"
                index = 1
                for entry in entries:
                    if not entry:
                        continue
                    title = _entry_title(entry)
                    artist, parsed_title = _entry_artist(entry, title)
                    tracks.append(
                        TrackDraft(
                            source_url=_entry_source_url(entry, url),
                            playlist_name=playlist_name,
                            index=index,
                            artist=artist,
                            title=parsed_title,
                            raw_title=title,
                            album=playlist_name,
                            duration_seconds=entry.get("duration"),
                        )
                    )
                    index += 1
            else:
                playlist_name = playlist_override or "YouTube Songs"
                title = _entry_title(info)
                artist, parsed_title = _entry_artist(info, title)
                tracks.append(
                    TrackDraft(
                        source_url=_entry_source_url(info, url),
                        playlist_name=playlist_name,
                        index=len(tracks) + 1,
                        artist=artist,
                        title=parsed_title,
                        raw_title=title,
                        album=playlist_name,
                        duration_seconds=info.get("duration"),
                    )
                )

    return tracks


def download_track(track: TrackDraft, work_dir: Path, progress: ProgressCallback | None = None) -> Path:
    YoutubeDL = _import_ytdlp()
    ffmpeg = _ffmpeg_location()
    work_dir.mkdir(parents=True, exist_ok=True)

    def hook(data: dict[str, Any]) -> None:
        if not progress:
            return
        status = data.get("status")
        if status == "downloading":
            downloaded = data.get("_percent_str") or ""
            speed = data.get("_speed_str") or ""
            progress(f"Downloading {downloaded.strip()} {speed.strip()}".strip())
        elif status == "finished":
            progress("Converting to MP3")

    options = {
        "ffmpeg_location": ffmpeg,
        "format": "bestaudio/best",
        "noplaylist": True,
        "no_warnings": True,
        "outtmpl": str(work_dir / "source.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }
        ],
        "progress_hooks": [hook],
        "quiet": True,
    }

    before = set(work_dir.glob("*"))
    with YoutubeDL(options) as ydl:
        ydl.download([track.source_url])

    mp3_candidates = sorted(
        [path for path in work_dir.glob("*.mp3") if path not in before],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not mp3_candidates:
        mp3_candidates = sorted(work_dir.glob("*.mp3"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not mp3_candidates:
        raise FileNotFoundError("yt-dlp finished but no MP3 file was produced")
    return mp3_candidates[0]


def write_mp3_tags(path: Path, track: TrackDraft) -> None:
    try:
        from mutagen.easyid3 import EasyID3
        from mutagen.id3 import ID3NoHeaderError
    except ImportError as exc:
        raise DependencyMissing("mutagen is not installed. Run: python -m pip install -e .") from exc

    try:
        tags = EasyID3(path)
    except ID3NoHeaderError:
        tags = EasyID3()

    tags["title"] = track.title
    tags["artist"] = track.artist
    tags["album"] = track.album or track.playlist_name
    tags["tracknumber"] = str(track.index)
    tags.save(path)

