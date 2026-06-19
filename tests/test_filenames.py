import unittest

from sansa_prep.filenames import (
    build_track_filename,
    parse_artist_title,
    sanitize_component,
    strip_title_noise,
)


class FilenameTests(unittest.TestCase):
    def test_sanitize_removes_windows_invalid_characters(self) -> None:
        self.assertEqual(sanitize_component('A:B<C>D/E\\F|G?H*I'), "A-B-C-D-E-F-G-H-I")

    def test_sanitize_handles_reserved_windows_names(self) -> None:
        self.assertEqual(sanitize_component("CON"), "CON_")

    def test_strip_title_noise_removes_common_youtube_suffixes(self) -> None:
        self.assertEqual(strip_title_noise("Artist - Song (Official Video) [HD]"), "Artist - Song")

    def test_parse_artist_title_prefers_title_separator(self) -> None:
        self.assertEqual(parse_artist_title("Artist - Song (Official Audio)", "Uploader"), ("Artist", "Song"))

    def test_parse_artist_title_uses_topic_channel_as_artist(self) -> None:
        self.assertEqual(parse_artist_title("Song", "Artist - Topic"), ("Artist", "Song"))

    def test_build_track_filename_uses_order_artist_and_title(self) -> None:
        self.assertEqual(build_track_filename(3, "Artist", "Song"), "03 - Artist - Song.mp3")


if __name__ == "__main__":
    unittest.main()

