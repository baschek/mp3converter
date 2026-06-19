from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from .config import load_config, save_config
from .filenames import build_track_filename
from .models import DuplicateAction, TrackDraft
from .processor import mark_duplicates, prepare_track
from .tracks import apply_track_edits, reindex_tracks, without_positions
from .youtube import DependencyMissing, extract_tracks


class SansaPrepApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Sansa Clip Zip Music Prep")
        self.geometry("1100x720")
        self.minsize(900, 600)

        self.config_data = load_config()
        self.tracks: list[TrackDraft] = []
        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.cancel_after_current = threading.Event()

        self.url_text: tk.Text
        self.playlist_var = tk.StringVar()
        self.target_var = tk.StringVar(value=str(self.config_data.get("last_target", "")))
        self.status_var = tk.StringVar(value="Paste YouTube video or playlist URLs to start.")
        self.overwrite_var = tk.BooleanVar(value=False)

        self.edit_playlist_var = tk.StringVar()
        self.edit_artist_var = tk.StringVar()
        self.edit_title_var = tk.StringVar()

        self._build_ui()
        self.after(100, self._drain_events)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        top = ttk.Frame(self, padding=12)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(0, weight=1)

        url_label = ttk.Label(top, text="YouTube URLs")
        url_label.grid(row=0, column=0, sticky="w")
        self.url_text = tk.Text(top, height=5, wrap="word", undo=True)
        self.url_text.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(4, 10))

        ttk.Label(top, text="Playlist folder override").grid(row=2, column=0, sticky="w")
        playlist_entry = ttk.Entry(top, textvariable=self.playlist_var)
        playlist_entry.grid(row=3, column=0, sticky="ew", pady=(4, 0))

        ttk.Label(top, text="Target folder").grid(row=2, column=1, sticky="w", padx=(12, 0))
        target_entry = ttk.Entry(top, textvariable=self.target_var)
        target_entry.grid(row=3, column=1, sticky="ew", padx=(12, 0), pady=(4, 0))
        top.columnconfigure(1, weight=1)

        browse = ttk.Button(top, text="Browse", command=self._browse_target)
        browse.grid(row=3, column=2, padx=(8, 0), pady=(4, 0))

        load = ttk.Button(top, text="Load Preview", command=self._load_preview)
        load.grid(row=3, column=3, padx=(8, 0), pady=(4, 0))

        middle = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        middle.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        table_frame = ttk.Frame(middle)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        middle.add(table_frame, weight=4)

        columns = ("index", "playlist", "artist", "title", "filename", "status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="extended")
        headings = {
            "index": "#",
            "playlist": "Playlist Folder",
            "artist": "Artist",
            "title": "Title",
            "filename": "Filename",
            "status": "Status",
        }
        widths = {
            "index": 48,
            "playlist": 160,
            "artist": 180,
            "title": 240,
            "filename": 280,
            "status": 120,
        }
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], minwidth=40, stretch=column not in {"index", "status"})
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        yscroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=yscroll.set)

        editor = ttk.Frame(middle, padding=(12, 0, 0, 0))
        editor.columnconfigure(0, weight=1)
        middle.add(editor, weight=1)

        ttk.Label(editor, text="Selected Track").grid(row=0, column=0, sticky="w")

        ttk.Label(editor, text="Playlist folder").grid(row=1, column=0, sticky="w", pady=(16, 0))
        ttk.Entry(editor, textvariable=self.edit_playlist_var).grid(row=2, column=0, sticky="ew", pady=(4, 0))

        ttk.Label(editor, text="Artist").grid(row=3, column=0, sticky="w", pady=(12, 0))
        ttk.Entry(editor, textvariable=self.edit_artist_var).grid(row=4, column=0, sticky="ew", pady=(4, 0))

        ttk.Label(editor, text="Title").grid(row=5, column=0, sticky="w", pady=(12, 0))
        ttk.Entry(editor, textvariable=self.edit_title_var).grid(row=6, column=0, sticky="ew", pady=(4, 0))

        ttk.Button(editor, text="Apply To Selected", command=self._apply_selected_edits).grid(
            row=7, column=0, sticky="ew", pady=(16, 0)
        )

        ttk.Button(editor, text="Remove Selected", command=self._remove_selected_tracks).grid(
            row=8, column=0, sticky="ew", pady=(8, 0)
        )

        ttk.Separator(editor).grid(row=9, column=0, sticky="ew", pady=20)
        ttk.Checkbutton(editor, text="Overwrite existing files", variable=self.overwrite_var).grid(
            row=10, column=0, sticky="w"
        )

        self.start_button = ttk.Button(editor, text="Start Processing", command=self._start_processing)
        self.start_button.grid(row=11, column=0, sticky="ew", pady=(16, 0))

        self.cancel_button = ttk.Button(editor, text="Cancel After Current", command=self._cancel_processing, state=tk.DISABLED)
        self.cancel_button.grid(row=12, column=0, sticky="ew", pady=(8, 0))

        bottom = ttk.Frame(self, padding=(12, 0, 12, 12))
        bottom.grid(row=2, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)
        self.progress = ttk.Progressbar(bottom, mode="indeterminate")
        self.progress.grid(row=0, column=0, sticky="ew")
        ttk.Label(bottom, textvariable=self.status_var).grid(row=1, column=0, sticky="w", pady=(6, 0))

    def _browse_target(self) -> None:
        initial = self.target_var.get() or str(Path.home())
        folder = filedialog.askdirectory(initialdir=initial, title="Choose Sansa music folder or staging folder")
        if folder:
            self.target_var.set(folder)
            self.config_data["last_target"] = folder
            save_config(self.config_data)
            self._refresh_duplicate_status()

    def _set_busy(self, busy: bool) -> None:
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()

    def _load_preview(self) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("Still working", "Wait for the current task to finish first.")
            return

        urls = [line.strip() for line in self.url_text.get("1.0", tk.END).splitlines() if line.strip()]
        if not urls:
            messagebox.showerror("No URLs", "Paste at least one YouTube video or playlist URL.")
            return

        self.tracks = []
        self._refresh_tree()
        self.status_var.set("Reading YouTube metadata...")
        self._set_busy(True)

        playlist_override = self.playlist_var.get().strip() or None
        self.worker = threading.Thread(
            target=self._preview_worker,
            args=(urls, playlist_override),
            daemon=True,
        )
        self.worker.start()

    def _preview_worker(self, urls: list[str], playlist_override: str | None) -> None:
        try:
            tracks = extract_tracks(urls, playlist_override=playlist_override, progress=self._thread_status)
            self.events.put(("preview_done", tracks))
        except Exception as exc:
            self.events.put(("error", exc))

    def _start_processing(self) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("Still working", "Wait for the current task to finish first.")
            return
        if not self.tracks:
            messagebox.showerror("No tracks", "Load a preview before processing.")
            return

        target_text = self.target_var.get().strip()
        if not target_text:
            messagebox.showerror("No target", "Choose a target folder first.")
            return
        target = Path(target_text)
        if not target.exists():
            create = messagebox.askyesno("Create folder", f"The target folder does not exist:\n\n{target}\n\nCreate it?")
            if not create:
                return
            try:
                target.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                messagebox.showerror("Target error", str(exc))
                return

        self.config_data["last_target"] = str(target)
        save_config(self.config_data)
        self._refresh_duplicate_status()

        self.cancel_after_current.clear()
        self.start_button.configure(state=tk.DISABLED)
        self.cancel_button.configure(state=tk.NORMAL)
        self.status_var.set("Processing tracks...")
        self._set_busy(True)

        action = DuplicateAction.OVERWRITE if self.overwrite_var.get() else DuplicateAction.SKIP
        self.worker = threading.Thread(
            target=self._process_worker,
            args=(target, action),
            daemon=True,
        )
        self.worker.start()

    def _process_worker(self, target: Path, action: DuplicateAction) -> None:
        completed = 0
        skipped = 0
        failed = 0
        try:
            for position, track in enumerate(self.tracks):
                if self.cancel_after_current.is_set():
                    break
                self.events.put(("track_status", (position, "Working")))
                try:
                    result = prepare_track(track, target, duplicate_action=action, progress=self._thread_status)
                    if result.status == "done":
                        completed += 1
                        self.events.put(("track_status", (position, "Done")))
                    elif result.status == "skipped":
                        skipped += 1
                        self.events.put(("track_status", (position, "Skipped")))
                except Exception as exc:
                    failed += 1
                    self.events.put(("track_status", (position, "Failed")))
                    self.events.put(("status", f"Failed: {track.artist} - {track.title}: {exc}"))
            self.events.put(("process_done", (completed, skipped, failed, self.cancel_after_current.is_set())))
        except Exception as exc:
            self.events.put(("error", exc))

    def _cancel_processing(self) -> None:
        self.cancel_after_current.set()
        self.status_var.set("Will cancel after the current track finishes.")

    def _thread_status(self, message: str) -> None:
        self.events.put(("status", message))

    def _drain_events(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "status":
                    self.status_var.set(str(payload))
                elif kind == "preview_done":
                    self.tracks = payload
                    reindex_tracks(self.tracks)
                    self._refresh_duplicate_status()
                    self._refresh_tree()
                    self.status_var.set(f"Loaded {len(self.tracks)} track(s). Review names before processing.")
                    self._set_busy(False)
                elif kind == "track_status":
                    position, status = payload
                    if 0 <= position < len(self.tracks):
                        self.tracks[position].status = status
                        self._update_tree_row(position)
                elif kind == "process_done":
                    completed, skipped, failed, cancelled = payload
                    self._set_busy(False)
                    self.start_button.configure(state=tk.NORMAL)
                    self.cancel_button.configure(state=tk.DISABLED)
                    prefix = "Cancelled. " if cancelled else "Finished. "
                    self.status_var.set(prefix + f"Done: {completed}, skipped: {skipped}, failed: {failed}.")
                    self._refresh_duplicate_status()
                    self._refresh_tree()
                elif kind == "error":
                    self._set_busy(False)
                    self.start_button.configure(state=tk.NORMAL)
                    self.cancel_button.configure(state=tk.DISABLED)
                    self._show_error(payload)
        except queue.Empty:
            pass
        self.after(100, self._drain_events)

    def _show_error(self, exc: Exception) -> None:
        if isinstance(exc, DependencyMissing):
            title = "Missing dependency"
        else:
            title = "Error"
        self.status_var.set(str(exc))
        messagebox.showerror(title, str(exc))

    def _refresh_duplicate_status(self) -> None:
        target_text = self.target_var.get().strip()
        if not target_text or not self.tracks:
            return
        target = Path(target_text)
        if target.exists():
            mark_duplicates(self.tracks, target)
            for track in self.tracks:
                if track.status in {"Ready", "Exists"}:
                    track.status = "Exists" if track.duplicate else "Ready"

    def _refresh_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for position, track in enumerate(self.tracks):
            self.tree.insert("", tk.END, iid=str(position), values=self._row_values(track))

    def _update_tree_row(self, position: int) -> None:
        iid = str(position)
        if self.tree.exists(iid):
            self.tree.item(iid, values=self._row_values(self.tracks[position]))

    def _row_values(self, track: TrackDraft) -> tuple[str, str, str, str, str, str]:
        filename = build_track_filename(track.index, track.artist, track.title)
        return (
            str(track.index),
            track.playlist_name,
            track.artist,
            track.title,
            filename,
            track.status,
        )

    def _selected_positions(self) -> list[int]:
        positions: list[int] = []
        for iid in self.tree.selection():
            try:
                positions.append(int(iid))
            except ValueError:
                continue
        return positions

    def _on_tree_select(self, _event: tk.Event[Any]) -> None:
        positions = self._selected_positions()
        if not positions:
            return
        if len(positions) > 1:
            self.edit_playlist_var.set("")
            self.edit_artist_var.set("")
            self.edit_title_var.set("")
            self.status_var.set(f"{len(positions)} tracks selected. Fill only the fields you want to change.")
            return
        track = self.tracks[positions[0]]
        self.edit_playlist_var.set(track.playlist_name)
        self.edit_artist_var.set(track.artist)
        self.edit_title_var.set(track.title)

    def _apply_selected_edits(self) -> None:
        positions = self._selected_positions()
        if not positions:
            messagebox.showinfo("No selection", "Select one or more tracks to edit.")
            return

        playlist = self.edit_playlist_var.get().strip()
        artist = self.edit_artist_var.get().strip()
        title = self.edit_title_var.get().strip()

        if len(positions) > 1 and not any([playlist, artist, title]):
            messagebox.showinfo("No changes", "Fill at least one field to change the selected tracks.")
            return

        changed = apply_track_edits(self.tracks, positions, playlist_name=playlist, artist=artist, title=title)
        self._refresh_duplicate_status()
        self._refresh_tree()
        self.status_var.set(f"Updated {changed} selected track(s).")

    def _remove_selected_tracks(self) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("Still working", "Wait for the current task to finish first.")
            return

        positions = self._selected_positions()
        if not positions:
            messagebox.showinfo("No selection", "Select one or more tracks to remove.")
            return

        count = len(positions)
        confirmed = messagebox.askyesno(
            "Remove selected tracks",
            f"Remove {count} selected track(s) from this batch?\n\nThis does not delete files from disk.",
        )
        if not confirmed:
            return

        self.tracks = without_positions(self.tracks, positions)
        self.edit_playlist_var.set("")
        self.edit_artist_var.set("")
        self.edit_title_var.set("")
        self._refresh_duplicate_status()
        self._refresh_tree()
        self.status_var.set(f"Removed {count} track(s). {len(self.tracks)} track(s) remain.")


def main() -> None:
    app = SansaPrepApp()
    app.mainloop()
