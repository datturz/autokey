"""Dungeon tab — record WASD + mouse clicks, replay for dungeon navigation."""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time

from core.dungeon_nav import (
    DungeonPath, DungeonRecorder, DungeonNavigator,
    get_paths_dir, list_saved_paths,
)


class TabDungeon:
    """Dungeon navigation settings tab."""

    def __init__(self, parent: ttk.Frame, lang: dict):
        self.parent = parent
        self.lang = lang
        self._recorder = None
        self._record_thread = None
        self._nav_thread = None
        self._navigator = None
        self._current_path = DungeonPath()

        # Bot refs (set by app.py via set_bot_refs)
        self._capturer = None
        self._clicker = None
        self._key_sender = None
        self._stop_event = None
        self._acquire_feature = None
        self._release_feature = None
        self._check_interrupted = None
        self._log_callback = None
        self._hwnd = None

        self._build_ui()

    def set_bot_refs(self, capturer, clicker, key_sender, stop_event,
                     acquire_feature, release_feature, check_interrupted,
                     log_callback, hwnd):
        self._capturer = capturer
        self._clicker = clicker
        self._key_sender = key_sender
        self._stop_event = stop_event
        self._acquire_feature = acquire_feature
        self._release_feature = release_feature
        self._check_interrupted = check_interrupted
        self._log_callback = log_callback
        self._hwnd = hwnd

    def _log(self, msg):
        if self._log_callback:
            self._log_callback(msg)

    def _build_ui(self):
        # ── Path Management ──
        path_frame = ttk.LabelFrame(self.parent, text="Dungeon Path")
        path_frame.pack(fill=tk.X, padx=5, pady=5)

        row0 = ttk.Frame(path_frame)
        row0.pack(fill=tk.X, pady=2, padx=5)
        ttk.Label(row0, text="Path:").pack(side=tk.LEFT)
        self.path_combo = ttk.Combobox(row0, values=list_saved_paths(),
                                        width=20, state="readonly")
        self.path_combo.pack(side=tk.LEFT, padx=5)
        ttk.Button(row0, text="Load", command=self._on_load).pack(side=tk.LEFT, padx=2)
        ttk.Button(row0, text="Delete", command=self._on_delete).pack(side=tk.LEFT, padx=2)
        ttk.Button(row0, text="Refresh", command=self._refresh_path_list).pack(side=tk.LEFT, padx=2)

        row1 = ttk.Frame(path_frame)
        row1.pack(fill=tk.X, pady=2, padx=5)
        ttk.Label(row1, text="Name:").pack(side=tk.LEFT)
        self.path_name = ttk.Entry(row1, width=25)
        self.path_name.pack(side=tk.LEFT, padx=5)
        ttk.Button(row1, text="Save", command=self._on_save).pack(side=tk.LEFT, padx=2)

        # Path info
        self.path_info = ttk.Label(path_frame, text="", foreground="gray")
        self.path_info.pack(fill=tk.X, padx=5, pady=2)

        # ── Recording ──
        rec_frame = ttk.LabelFrame(self.parent, text="Record (WASD + Mouse Click)")
        rec_frame.pack(fill=tk.X, padx=5, pady=5)

        rec_row0 = ttk.Frame(rec_frame)
        rec_row0.pack(fill=tk.X, pady=2, padx=5)
        self.btn_record = ttk.Button(rec_row0, text="Start Recording",
                                      command=self._on_toggle_record)
        self.btn_record.pack(side=tk.LEFT)
        ttk.Button(rec_row0, text="Clear", command=self._on_clear).pack(side=tk.LEFT, padx=10)
        self.rec_status = ttk.Label(rec_row0, text="")
        self.rec_status.pack(side=tk.LEFT, padx=10)

        rec_info = ttk.Label(rec_frame,
                             text="Jalan di dungeon pakai WASD + klik jalanan. Semua input terekam.",
                             foreground="gray")
        rec_info.pack(fill=tk.X, padx=5, pady=2)

        # ── Playback ──
        play_frame = ttk.LabelFrame(self.parent, text="Navigate")
        play_frame.pack(fill=tk.X, padx=5, pady=5)

        play_row0 = ttk.Frame(play_frame)
        play_row0.pack(fill=tk.X, pady=2, padx=5)
        self.btn_navigate = ttk.Button(play_row0, text="Start Navigate",
                                        command=self._on_navigate)
        self.btn_navigate.pack(side=tk.LEFT)
        self.btn_stop_nav = ttk.Button(play_row0, text="Stop",
                                        command=self._on_stop_nav, state=tk.DISABLED)
        self.btn_stop_nav.pack(side=tk.LEFT, padx=5)

        play_row1 = ttk.Frame(play_frame)
        play_row1.pack(fill=tk.X, pady=2, padx=5)
        self.auto_hunt_after = tk.BooleanVar(value=True)
        ttk.Checkbutton(play_row1, text="Auto Hunt (F) setelah sampai",
                        variable=self.auto_hunt_after).pack(side=tk.LEFT)

        # Progress
        self.nav_status = ttk.Label(play_frame, text="", foreground="blue")
        self.nav_status.pack(fill=tk.X, padx=5, pady=2)

    # ── Path Management ──

    def _refresh_path_list(self):
        self.path_combo['values'] = list_saved_paths()

    def _on_load(self):
        name = self.path_combo.get()
        if not name:
            return
        import os
        filepath = os.path.join(get_paths_dir(), f"{name}.json")
        if not os.path.exists(filepath):
            messagebox.showerror("Error", f"Path '{name}' not found!")
            return
        self._current_path = DungeonPath.load(filepath)
        self.path_name.delete(0, tk.END)
        self.path_name.insert(0, self._current_path.name)
        self.path_info.config(text=self._current_path.get_summary())
        self._log(f"[Dungeon] Loaded: {name} — {self._current_path.get_summary()}")

    def _on_save(self):
        name = self.path_name.get().strip()
        if not name:
            messagebox.showwarning("Warning", "Enter a path name!")
            return
        if not self._current_path.events:
            messagebox.showwarning("Warning", "No events to save! Record a path first.")
            return
        import os
        self._current_path.name = name
        filepath = os.path.join(get_paths_dir(), f"{name}.json")
        self._current_path.save(filepath)
        self._refresh_path_list()
        self.path_combo.set(name)
        self._log(f"[Dungeon] Saved: {name} — {self._current_path.get_summary()}")

    def _on_delete(self):
        name = self.path_combo.get()
        if not name:
            return
        import os
        filepath = os.path.join(get_paths_dir(), f"{name}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
        self._refresh_path_list()
        self.path_combo.set("")
        self._current_path = DungeonPath()
        self.path_info.config(text="")

    # ── Recording ──

    def _on_toggle_record(self):
        if self._recorder and self._recorder.recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        if not self._hwnd:
            messagebox.showwarning("Warning", "Bot belum dimulai! Klik 'Mulai' dulu.")
            return
        self._recorder = DungeonRecorder(self._hwnd, self._stop_event)
        self._recorder.start()
        self.btn_record.config(text="Stop Recording")
        self.rec_status.config(text="RECORDING... Jalan pakai WASD/klik",
                               foreground="red")
        self._log("[Dungeon] Recording started — walk with WASD or click paths")

        self._record_thread = threading.Thread(target=self._recording_loop, daemon=True)
        self._record_thread.start()

    def _stop_recording(self):
        if self._recorder:
            self._recorder.stop()
            self._current_path = self._recorder.path
            summary = self._current_path.get_summary()
            self.rec_status.config(text=f"Done! {summary}", foreground="green")
            self.path_info.config(text=summary)
            self._log(f"[Dungeon] Recording stopped — {summary}")
        self.btn_record.config(text="Start Recording")

    def _recording_loop(self):
        last_count = 0
        last_log = time.time()
        while self._recorder and self._recorder.recording:
            if self._stop_event and self._stop_event.is_set():
                break
            self._recorder.poll()
            # Log event count every 3 seconds if changed
            now = time.time()
            count = len(self._recorder.path.events)
            if count != last_count and (now - last_log) > 1:
                self._log(f"[Dungeon] Events: {count} (latest: {self._recorder.path.events[-1]})")
                last_count = count
                last_log = now
                try:
                    self.parent.after(0, self.rec_status.config,
                                      {"text": f"RECORDING... {count} events"})
                except Exception:
                    pass
            time.sleep(0.04)

    def _on_clear(self):
        self._current_path = DungeonPath()
        self.path_info.config(text="")
        self.rec_status.config(text="Cleared")

    # ── Playback ──

    def _on_navigate(self):
        if not self._current_path.events:
            messagebox.showwarning("Warning", "No path! Load or record first.")
            return
        if not self._capturer or not self._key_sender:
            messagebox.showwarning("Warning", "Bot belum dimulai!")
            return

        self.btn_navigate.config(state=tk.DISABLED)
        self.btn_stop_nav.config(state=tk.NORMAL)
        self.nav_status.config(text="Navigating...", foreground="blue")

        self._navigator = DungeonNavigator(
            self._capturer, self._clicker, self._key_sender, self._stop_event)
        self._navigator._on_log = self._log
        self._navigator._on_progress = self._on_progress
        self._navigator._on_done = self._on_nav_done

        self._nav_thread = threading.Thread(target=self._run_navigation, daemon=True)
        self._nav_thread.start()

    def _run_navigation(self):
        try:
            self._navigator.navigate(
                path=self._current_path,
                check_interrupted=self._check_interrupted or (lambda: False),
                auto_hunt=self.auto_hunt_after.get(),
            )
        except Exception as e:
            self._log(f"[Dungeon] Error: {e}")
        finally:
            try:
                self.parent.after(0, self._nav_finished_ui)
            except Exception:
                pass

    def _on_progress(self, pct, current, total):
        try:
            self.parent.after(0, self.nav_status.config,
                              {"text": f"Event {current}/{total} ({pct*100:.0f}%)"})
        except Exception:
            pass

    def _on_nav_done(self):
        try:
            self.parent.after(0, self.nav_status.config,
                              {"text": "Arrived! Auto hunt started.", "foreground": "green"})
        except Exception:
            pass

    def _nav_finished_ui(self):
        self.btn_navigate.config(state=tk.NORMAL)
        self.btn_stop_nav.config(state=tk.DISABLED)

    def _on_stop_nav(self):
        if self._navigator:
            self._navigator.stop()
        self.nav_status.config(text="Stopped", foreground="red")
        self.btn_navigate.config(state=tk.NORMAL)
        self.btn_stop_nav.config(state=tk.DISABLED)

    # ── Settings ──

    def apply_settings(self, settings: dict):
        self.auto_hunt_after.set(settings.get("dungeon_auto_hunt", True))
        last_path = settings.get("dungeon_last_path", "")
        if last_path:
            self.path_combo.set(last_path)

    def collect_settings(self) -> dict:
        return {
            "dungeon_auto_hunt": self.auto_hunt_after.get(),
            "dungeon_last_path": self.path_combo.get(),
        }
