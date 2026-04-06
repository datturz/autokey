"""Dungeon navigation — record and replay WASD movement + mouse clicks.

Records WASD key presses (with timing) and mouse clicks on walkable area.
Plays back by sending the same inputs with same timing.
Uses minimap stability check for arrival detection at end.
"""

import json
import os
import time
import threading
import cv2
import numpy as np

from core.game_layout import MINIMAP_FULL_AREA, denormalize


class DungeonPath:
    """A saved dungeon navigation path (sequence of input events)."""

    def __init__(self, name: str = ""):
        self.name = name
        # Events: [{"t": float, "type": "key_down"/"key_up"/"click", "key": str, "x": int, "y": int}]
        self.events: list[dict] = []

    @property
    def duration(self) -> float:
        if not self.events:
            return 0
        return self.events[-1]["t"]

    def save(self, filepath: str):
        data = {"name": self.name, "events": self.events}
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "DungeonPath":
        with open(filepath, "r") as f:
            data = json.load(f)
        path = cls(data.get("name", ""))
        path.events = data.get("events", [])
        return path

    def get_summary(self) -> str:
        """Human-readable summary of the path."""
        if not self.events:
            return "Empty"
        keys = set()
        clicks = 0
        for e in self.events:
            if e["type"] == "key_down":
                keys.add(e["key"])
            elif e["type"] == "click":
                clicks += 1
        dur = self.duration
        parts = []
        if keys:
            parts.append(f"Keys: {','.join(sorted(keys))}")
        if clicks:
            parts.append(f"Clicks: {clicks}")
        parts.append(f"Duration: {dur:.1f}s")
        return " | ".join(parts)


def get_paths_dir() -> str:
    """Get dungeon paths save directory."""
    import sys
    if hasattr(sys, '_MEIPASS'):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = os.path.join(base, "dungeon_paths")
    os.makedirs(d, exist_ok=True)
    return d


def list_saved_paths() -> list[str]:
    """List saved dungeon path names."""
    d = get_paths_dir()
    paths = []
    for f in sorted(os.listdir(d)):
        if f.endswith(".json"):
            paths.append(f[:-5])
    return paths


class DungeonRecorder:
    """Records WASD movement and mouse clicks with timing."""

    WATCH_KEYS = {
        0x57: "W", 0x41: "A", 0x53: "S", 0x44: "D",  # WASD
    }

    def __init__(self, hwnd, stop_event: threading.Event):
        self.hwnd = hwnd
        self.stop_event = stop_event
        self.recording = False
        self.path = DungeonPath()
        self._start_time = 0
        self._keys_down = set()

    def start(self):
        self.recording = True
        self.path = DungeonPath()
        self._start_time = time.time()
        self._keys_down = set()

    def stop(self):
        """Stop recording and release any held keys."""
        now = time.time() - self._start_time
        # Add key_up for any keys still held
        for key in list(self._keys_down):
            self.path.events.append({"t": round(now, 3), "type": "key_up", "key": key})
        self._keys_down.clear()
        self.recording = False

    def poll(self):
        """Poll keyboard and mouse state. Call in a loop (~50ms interval)."""
        import ctypes
        import ctypes.wintypes

        user32 = ctypes.windll.user32
        now = time.time() - self._start_time

        # Check WASD keys
        for vk, key_name in self.WATCH_KEYS.items():
            state = user32.GetAsyncKeyState(vk)
            is_down = bool(state & 0x8000)

            if is_down and key_name not in self._keys_down:
                self._keys_down.add(key_name)
                self.path.events.append({
                    "t": round(now, 3), "type": "key_down", "key": key_name
                })
            elif not is_down and key_name in self._keys_down:
                self._keys_down.discard(key_name)
                self.path.events.append({
                    "t": round(now, 3), "type": "key_up", "key": key_name
                })

        # Check mouse left click (for walkable area clicks)
        VK_LBUTTON = 0x01
        mouse_state = user32.GetAsyncKeyState(VK_LBUTTON)
        mouse_down = bool(mouse_state & 0x8000)

        if mouse_down and not getattr(self, '_mouse_was_down', False):
            pt = ctypes.wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            client_pt = ctypes.wintypes.POINT(pt.x, pt.y)
            user32.ScreenToClient(self.hwnd, ctypes.byref(client_pt))
            rect = ctypes.wintypes.RECT()
            user32.GetClientRect(self.hwnd, ctypes.byref(rect))
            cw, ch = rect.right, rect.bottom

            if cw > 0 and ch > 0:
                x = int(client_pt.x * 1280 / cw)
                y = int(client_pt.y * 720 / ch)
                # Exclude UI areas
                if not (y < 58 or y > 612 or (x < 230 and y < 250) or (x > 1088 and y > 288)):
                    self.path.events.append({
                        "t": round(now, 3), "type": "click", "x": x, "y": y
                    })

        self._mouse_was_down = mouse_down


class DungeonNavigator:
    """Plays back recorded dungeon path."""

    def __init__(self, capturer, clicker, key_sender, stop_event: threading.Event):
        self.capturer = capturer
        self.clicker = clicker
        self.key_sender = key_sender
        self.stop_event = stop_event
        self.navigating = False
        self._on_log = None
        self._on_progress = None
        self._on_done = None

    def _log(self, msg: str):
        if self._on_log:
            self._on_log(msg)

    def _capture_minimap(self) -> np.ndarray | None:
        """Capture minimap region as grayscale for arrival detection."""
        img = self.capturer.capture() if self.capturer else None
        if img is None:
            return None
        w, h = img.size
        x1, y1, x2, y2 = denormalize(MINIMAP_FULL_AREA, w, h)
        crop = img.crop((x1, y1, x2, y2))
        return cv2.cvtColor(np.array(crop), cv2.COLOR_RGB2GRAY)

    def _wait_for_arrival(self, timeout: float = 10) -> bool:
        """Wait until minimap stops changing (character stopped moving)."""
        prev = self._capture_minimap()
        if prev is None:
            return False
        stable_count = 0
        start = time.time()
        while (time.time() - start) < timeout:
            if self.stop_event.is_set() or not self.navigating:
                return False
            time.sleep(1.0)
            curr = self._capture_minimap()
            if curr is None:
                continue
            if prev.shape != curr.shape:
                curr = cv2.resize(curr, (prev.shape[1], prev.shape[0]))
            mean_diff = float(np.mean(cv2.absdiff(prev, curr)))
            if mean_diff < 3.0:
                stable_count += 1
                if stable_count >= 2:
                    return True
            else:
                stable_count = 0
            prev = curr
        return False

    def navigate(self, path: DungeonPath,
                 check_interrupted,
                 auto_hunt: bool = True):
        """Replay recorded path events with original timing.

        During playback, regularly checks check_interrupted().
        If interrupted (combat escape), pauses and waits to resume.
        After all events, optionally presses F for auto hunt.
        """
        if not path.events:
            self._log("[Dungeon] No events to replay!")
            return False

        self.navigating = True
        self._log(f"[Dungeon] Replaying path: {len(path.events)} events, "
                  f"{path.duration:.1f}s duration")

        try:
            start_time = time.time()
            event_idx = 0
            held_keys = set()

            while event_idx < len(path.events):
                if self.stop_event.is_set() or not self.navigating:
                    self._log("[Dungeon] Navigation stopped.")
                    break

                # Check interruption (combat escape / radar)
                if check_interrupted():
                    # Release all held keys before pausing
                    for k in list(held_keys):
                        self.key_sender.send_up(k)
                    held_keys.clear()
                    self._log("[Dungeon] Interrupted — pausing...")
                    while check_interrupted() and not self.stop_event.is_set():
                        time.sleep(1.0)
                    if self.stop_event.is_set():
                        break
                    self._log("[Dungeon] Resuming...")
                    # Re-adjust timing
                    event = path.events[event_idx]
                    start_time = time.time() - event["t"]

                event = path.events[event_idx]
                target_time = start_time + event["t"]
                now = time.time()

                # Wait for event time
                if now < target_time:
                    wait = target_time - now
                    if wait > 0.01:
                        # Sleep in small chunks to stay responsive
                        end = now + wait
                        while time.time() < end:
                            if self.stop_event.is_set() or not self.navigating:
                                break
                            time.sleep(min(0.05, end - time.time()))
                        if self.stop_event.is_set() or not self.navigating:
                            break

                # Execute event
                etype = event["type"]
                if etype == "key_down":
                    key = event["key"]
                    self.key_sender.send_down(key)
                    held_keys.add(key)
                elif etype == "key_up":
                    key = event["key"]
                    self.key_sender.send_up(key)
                    held_keys.discard(key)
                elif etype == "click":
                    self.clicker.click_scaled(event["x"], event["y"])

                # Progress update
                if self._on_progress:
                    pct = (event_idx + 1) / len(path.events)
                    self._on_progress(pct, event_idx + 1, len(path.events))

                event_idx += 1

            # Release any remaining held keys
            for k in list(held_keys):
                self.key_sender.send_up(k)

            if event_idx >= len(path.events):
                self._log("[Dungeon] Playback complete! Waiting for arrival...")
                self._wait_for_arrival(timeout=10)
                self._log("[Dungeon] Arrived at destination!")

                if auto_hunt and self.key_sender:
                    self._log("[Dungeon] Pressing F for auto hunt...")
                    time.sleep(1)
                    self.key_sender.send("F")

                if self._on_done:
                    self._on_done()
                return True

        finally:
            self.navigating = False

        return False

    def stop(self):
        self.navigating = False
