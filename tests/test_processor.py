import unittest
from pathlib import Path

from sansa_prep.models import DuplicateAction, TrackDraft
from sansa_prep.processor import resolve_duplicate, target_path_for


class ProcessorTests(unittest.TestCase):
    def test_target_path_uses_playlist_folder_and_filename(self) -> None:
        track = TrackDraft(
            source_url="https://example.invalid/video",
            playlist_name="Road Mix",
            index=1,
            artist="Artist",
            title="Song",
        )
        self.assertEqual(
            target_path_for(track, Path("M:/Music")),
            Path("M:/Music") / "Road Mix" / "01 - Artist - Song.mp3",
        )

    def test_resolve_duplicate_skip_returns_none(self) -> None:
        path = Path("pyproject.toml")
        self.assertIsNone(resolve_duplicate(path, DuplicateAction.SKIP))

    def test_resolve_duplicate_auto_number_finds_free_name(self) -> None:
        path = Path("pyproject.toml")
        resolved = resolve_duplicate(path, DuplicateAction.AUTO_NUMBER)
        self.assertEqual(resolved, Path("pyproject (2).toml"))


if __name__ == "__main__":
    unittest.main()
