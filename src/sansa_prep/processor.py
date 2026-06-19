from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Callable

from .filenames import build_playlist_folder, build_track_filename
from .models import DuplicateAction, ProcessResult, TrackDraft
from .youtube import download_track, write_mp3_tags

ProgressCallback = Callable[[str], None]


def target_path_for(track: TrackDraft, target_root: Path) -> Path:
    folder = build_playlist_folder(track.playlist_name)
    filename = build_track_filename(track.index, track.artist, track.title)
    return target_root / folder / filename


def mark_duplicates(tracks: list[TrackDraft], target_root: Path) -> None:
    for track in tracks:
        track.duplicate = target_path_for(track, target_root).exists()


def resolve_duplicate(path: Path, action: DuplicateAction) -> Path | None:
    if not path.exists():
        return path
    if action == DuplicateAction.SKIP:
        return None
    if action == DuplicateAction.OVERWRITE:
        return path

    stem = path.stem
    suffix = path.suffix
    for number in range(2, 1000):
        candidate = path.with_name(f"{stem} ({number}){suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"Could not find an unused filename for {path.name}")


def copy_atomically(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(f"{destination.name}.part")
    if partial.exists():
        partial.unlink()
    shutil.copy2(source, partial)
    os.replace(partial, destination)


def prepare_track(
    track: TrackDraft,
    target_root: Path,
    duplicate_action: DuplicateAction = DuplicateAction.SKIP,
    progress: ProgressCallback | None = None,
) -> ProcessResult:
    destination = target_path_for(track, target_root)
    resolved_destination = resolve_duplicate(destination, duplicate_action)
    if resolved_destination is None:
        return ProcessResult(track=track, destination=None, status="skipped", message="File already exists")

    with tempfile.TemporaryDirectory(prefix="sansa-prep-") as temp_dir:
        if progress:
            progress(f"Downloading {track.artist} - {track.title}")
        mp3_path = download_track(track, Path(temp_dir), progress=progress)

        if progress:
            progress("Writing MP3 tags")
        write_mp3_tags(mp3_path, track)

        if progress:
            progress(f"Copying to {resolved_destination.name}")
        copy_atomically(mp3_path, resolved_destination)

    return ProcessResult(
        track=track,
        destination=str(resolved_destination),
        status="done",
        message="Copied",
    )

