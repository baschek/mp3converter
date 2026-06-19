from __future__ import annotations

from collections.abc import Iterable, Sequence

from .models import TrackDraft


def apply_track_edits(
    tracks: Sequence[TrackDraft],
    positions: Iterable[int],
    playlist_name: str | None = None,
    artist: str | None = None,
    title: str | None = None,
) -> int:
    changed = 0
    valid_positions = {position for position in positions if 0 <= position < len(tracks)}
    for position in valid_positions:
        track = tracks[position]
        if playlist_name:
            track.playlist_name = playlist_name
            track.album = playlist_name
        if artist:
            track.artist = artist
        if title:
            track.title = title
        track.status = "Ready"
        changed += 1

    if playlist_name:
        reindex_tracks(tracks)
    return changed


def reindex_tracks(tracks: Sequence[TrackDraft]) -> None:
    next_index_by_playlist: dict[str, int] = {}
    for track in tracks:
        playlist = track.playlist_name
        next_index = next_index_by_playlist.get(playlist, 1)
        track.index = next_index
        next_index_by_playlist[playlist] = next_index + 1


def without_positions(tracks: Sequence[TrackDraft], positions: Iterable[int]) -> list[TrackDraft]:
    removed = set(positions)
    remaining = [track for index, track in enumerate(tracks) if index not in removed]
    reindex_tracks(remaining)
    return remaining
