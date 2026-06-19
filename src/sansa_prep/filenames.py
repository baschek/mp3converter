from __future__ import annotations

import re


INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
WHITESPACE = re.compile(r"\s+")
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}

NOISE_PATTERNS = [
    r"\bofficial\s+music\s+video\b",
    r"\bofficial\s+video\b",
    r"\bofficial\s+audio\b",
    r"\blyric\s+video\b",
    r"\blyrics?\b",
    r"\bvisualizer\b",
    r"\bmusic\s+video\b",
    r"\bremaster(?:ed)?(?:\s+\d{4})?\b",
    r"\bhd\b",
    r"\b4k\b",
]


def collapse_whitespace(value: str) -> str:
    return WHITESPACE.sub(" ", value).strip()


def sanitize_component(value: str | None, fallback: str = "Unknown", max_length: int = 120) -> str:
    text = collapse_whitespace(value or "")
    text = INVALID_FILENAME_CHARS.sub("-", text)
    text = collapse_whitespace(text).strip(" .")
    if not text:
        text = fallback
    if text.upper() in WINDOWS_RESERVED_NAMES:
        text = f"{text}_"
    if len(text) > max_length:
        text = text[:max_length].rstrip(" .")
    return text or fallback


def strip_title_noise(raw_title: str) -> str:
    title = raw_title
    for pattern in NOISE_PATTERNS:
        title = re.sub(rf"\s*[\[(]\s*{pattern}\s*[\])]\s*", " ", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+\|\s+.*$", "", title)
    return collapse_whitespace(title)


def clean_uploader_name(uploader: str | None) -> str:
    text = collapse_whitespace(uploader or "")
    text = re.sub(r"\s*-\s*Topic$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+VEVO$", "", text, flags=re.IGNORECASE)
    return collapse_whitespace(text)


def parse_artist_title(raw_title: str, uploader: str | None = None) -> tuple[str, str]:
    cleaned = strip_title_noise(raw_title)
    for separator in (" - ", " -- ", " / "):
        if separator in cleaned:
            artist, title = cleaned.split(separator, 1)
            artist = collapse_whitespace(artist)
            title = collapse_whitespace(title)
            if artist and title:
                return artist, title

    uploader_name = clean_uploader_name(uploader)
    return uploader_name or "Unknown Artist", cleaned or raw_title or "Unknown Title"


def build_playlist_folder(name: str | None) -> str:
    return sanitize_component(name, fallback="Playlist")


def build_track_filename(index: int, artist: str, title: str) -> str:
    safe_artist = sanitize_component(artist, fallback="Unknown Artist", max_length=80)
    safe_title = sanitize_component(title, fallback="Unknown Title", max_length=100)
    return f"{index:02d} - {safe_artist} - {safe_title}.mp3"

