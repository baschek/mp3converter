from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DuplicateAction(str, Enum):
    SKIP = "skip"
    OVERWRITE = "overwrite"
    AUTO_NUMBER = "auto_number"


@dataclass(slots=True)
class TrackDraft:
    source_url: str
    playlist_name: str
    index: int
    artist: str
    title: str
    raw_title: str = ""
    album: str = ""
    duration_seconds: int | None = None
    status: str = "Ready"
    duplicate: bool = False


@dataclass(slots=True)
class ProcessResult:
    track: TrackDraft
    destination: str | None
    status: str
    message: str = ""

