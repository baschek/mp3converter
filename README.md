# Sansa Clip Zip Music Prep

A small Python desktop app for preparing music folders for a SanDisk Sansa Clip Zip or similar classic MP3 player.

Paste YouTube video or playlist URLs, review the detected tracks, fix messy titles, remove songs you do not want, and export clean 320 kbps MP3 files into playlist folders.

> Use this only with content you have the right to download and copy. The app does not download from Spotify or bypass DRM.

## What It Does

- Accepts YouTube video URLs and playlist URLs.
- Builds a preview table before downloading anything.
- Lets you edit playlist folder, artist, and title fields.
- Lets you remove selected songs from the batch.
- Converts audio to `320 kbps` MP3 with `yt-dlp` and FFmpeg.
- Writes MP3 tags with artist, title, album, and track number.
- Copies files into playlist folders like:

```text
Road Mix/
  01 - Artist - First Song.mp3
  02 - Artist - Second Song.mp3
```

Existing files are skipped by default, so accidental reruns should not overwrite your music unless you enable overwrite.

## Requirements

- Windows
- Python `3.11` or newer
- Internet access for YouTube metadata/downloads
- A SanDisk Sansa Clip Zip mounted as a normal drive, or any folder you want to use as a staging folder

The app auto-manages FFmpeg through the `imageio-ffmpeg` Python dependency.

## Setup

Open PowerShell in the project folder:

```powershell
cd D:\Programieren\mp3converter
```

Create and activate a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the app:

```powershell
python -m pip install --upgrade pip
python -m pip install -e .
```

If PowerShell blocks activation, run the app with the virtual environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m sansa_prep
```

## Run

With the virtual environment active:

```powershell
python -m sansa_prep
```

Or use the installed command:

```powershell
sansa-prep
```

## Basic Workflow

1. Plug in the Sansa Clip Zip.
2. Make sure it appears as a Windows drive. If it does not, set the player USB mode to `MSC`.
3. Paste one or more YouTube song URLs, or paste a YouTube playlist URL.
4. Click `Load Preview`.
5. Review the detected songs.
6. Select unwanted rows and click `Remove Selected`.
7. Select one or more rows and edit only the fields you want to change.
8. Choose the Sansa music folder or another target folder with `Browse`.
9. Click `Start Processing`.

## Editing Tracks

Single-row edits show that track's current playlist, artist, and title.

Multi-row edits start with blank fields. Only fields you fill in are applied to all selected tracks. For example, if you select ten songs and fill only `Playlist folder`, the artists and titles stay unchanged.

## Duplicate Handling

Before processing, the app checks whether the target filename already exists.

- Default behavior: skip existing files.
- Optional behavior: enable `Overwrite existing files` before processing.

## Development

Run the tests:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests
```

Project layout:

```text
src/sansa_prep/
  app.py          Tkinter desktop UI
  youtube.py      YouTube metadata, download, conversion, and tags
  processor.py    Output paths, duplicate handling, and copy workflow
  tracks.py       Track editing/removal helpers
  filenames.py    Filename cleanup and title parsing
tests/
  test_*.py       Unit tests
```

## Troubleshooting

If downloads fail, update the dependencies:

```powershell
python -m pip install --upgrade yt-dlp imageio-ffmpeg mutagen
```

If the Sansa does not show up as a drive, switch its USB mode to `MSC`, unplug it, and plug it back in.

If filenames look wrong, fix the artist and title in the preview table before processing.
