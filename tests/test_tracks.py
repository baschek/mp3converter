import unittest

from sansa_prep.models import TrackDraft
from sansa_prep.tracks import apply_track_edits, reindex_tracks, without_positions


def track(playlist: str, index: int, title: str) -> TrackDraft:
    return TrackDraft(
        source_url=f"https://example.invalid/{title}",
        playlist_name=playlist,
        index=index,
        artist="Artist",
        title=title,
    )


class TrackListTests(unittest.TestCase):
    def test_reindex_tracks_numbers_each_playlist_folder_separately(self) -> None:
        tracks = [
            track("Road", 10, "A"),
            track("Road", 20, "B"),
            track("Gym", 30, "C"),
            track("Road", 40, "D"),
        ]

        reindex_tracks(tracks)

        self.assertEqual([item.index for item in tracks], [1, 2, 1, 3])

    def test_without_positions_removes_selected_tracks_and_reindexes(self) -> None:
        tracks = [
            track("Road", 1, "A"),
            track("Road", 2, "B"),
            track("Road", 3, "C"),
        ]

        remaining = without_positions(tracks, [1])

        self.assertEqual([item.title for item in remaining], ["A", "C"])
        self.assertEqual([item.index for item in remaining], [1, 2])

    def test_apply_track_edits_only_changes_non_empty_fields(self) -> None:
        tracks = [
            track("Road", 1, "A"),
            track("Road", 2, "B"),
        ]

        changed = apply_track_edits(tracks, [0, 1], playlist_name="New Mix", artist="", title="")

        self.assertEqual(changed, 2)
        self.assertEqual([item.playlist_name for item in tracks], ["New Mix", "New Mix"])
        self.assertEqual([item.artist for item in tracks], ["Artist", "Artist"])
        self.assertEqual([item.title for item in tracks], ["A", "B"])
        self.assertEqual([item.index for item in tracks], [1, 2])


if __name__ == "__main__":
    unittest.main()
