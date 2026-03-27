"""Window capture module for Lineage 2M.

IMPORTANT: Captures only the CLIENT AREA (game content, without title bar
and window borders). This ensures that:
- Screenshot coordinates match the actual game content
- Mouse click coordinates (PostMessage = client-relative) are correct
"""
import os
import time
import ctypes
import mss
import win32gui
import win32con
import win32api
import win32process
import pywintypes
import cv2
from PIL import Image
import numpy as np
from .image_utils import load_image, match_template
from .game_layout import AN_HUE_ICON_REGION, denormalize


class WindowCapturer:
    """Captures screenshots from a window's CLIENT AREA by HWND."""

    def __init__(self, hwnd: int, stable_wait_ms: float = 300, flat_std_threshold: float = 5.0):
        self.hwnd = hwnd
        self.STABLE_WAIT_MS = stable_wait_ms
        self.FLAT_STD_THRESHOLD = flat_std_threshold
        self._last_rect = None
        self._stable_start_time = None
        # Cached an_hue template for stability detection
        self._an_hue_template = None
        self._an_hue_loaded = False

    def _get_client_rect_screen(self) -> tuple[int, int, int, int] | None:
        """Get the client area rectangle in SCREEN coordinates.

        Returns (x1, y1, x2, y2) of the client area on screen,
        excluding title bar and window borders.
        """
        try:
            # GetClientRect returns (0, 0, width, height)
            cr = win32gui.GetClientRect(self.hwnd)
            client_w = cr[2]
            client_h = cr[3]

            # ClientToScreen converts (0,0) of client area to screen coords
            # This gives us the top-left of the actual game content
            pt = win32gui.ClientToScreen(self.hwnd, (0, 0))
            x1, y1 = pt

            return (x1, y1, x1 + client_w, y1 + client_h)
        except Exception:
            return None

    def get_client_size(self) -> tuple[int, int] | None:
        """Get client area width and height."""
        try:
            cr = win32gui.GetClientRect(self.hwnd)
            return (cr[2], cr[3])
        except Exception:
            return None

    def _get_window_rect(self):
        return win32gui.GetWindowRect(self.hwnd)

    def _is_window_stable(self) -> bool:
        rect = self._get_window_rect()
        if rect != self._last_rect:
            self._last_rect = rect
            self._stable_start_time = time.time()
            return False
        if self._stable_start_time is None:
            self._stable_start_time = time.time()
            return False
        elapsed_ms = (time.time() - self._stable_start_time) * 1000
        return elapsed_ms >= self.STABLE_WAIT_MS

    def _is_image_flat(self, img: Image.Image) -> bool:
        arr = np.array(img.convert("RGB"))
        return arr.std() < self.FLAT_STD_THRESHOLD

    def force_set_foreground(self):
        try:
            fg_win = win32gui.GetForegroundWindow()
            current_thread_id = win32api.GetCurrentThreadId()
            fg_thread_id, _ = win32process.GetWindowThreadProcessId(fg_win)
            win32process.AttachThreadInput(current_thread_id, fg_thread_id, True)
            win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(self.hwnd)
            win32process.AttachThreadInput(current_thread_id, fg_thread_id, False)
        except Exception as e:
            print(f"[WindowCapturer] force_set_foreground error: {e}")

    def capture(self) -> Image.Image | None:
        """Capture the CLIENT AREA of the game window (no title bar/borders)."""
        try:
            client_rect = self._get_client_rect_screen()
            if not client_rect:
                return None

            x1, y1, x2, y2 = client_rect
            w = x2 - x1
            h = y2 - y1
            if w <= 0 or h <= 0:
                return None

            with mss.mss() as sct:
                monitor = {"left": x1, "top": y1, "width": w, "height": h}
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)

            if self._is_image_flat(img):
                return None
            return img
        except Exception as e:
            print(f"[WindowCapturer] capture error: {e}")
            return None

    def _load_an_hue_template(self):
        """Load and cache an_hue_1.png template (once)."""
        if self._an_hue_loaded:
            return
        self._an_hue_loaded = True
        path = os.path.join("assets", "an_hue_1.png")
        if os.path.exists(path):
            try:
                bgr, mask = load_image(path)
                self._an_hue_template = (bgr, mask)
            except Exception as e:
                print(f"[WindowCapturer] Failed to load an_hue_1.png: {e}")

    def is_stable_an_hue_icon(self, img: Image.Image) -> bool:
        """Check if screen is stable by matching an_hue_1.png template.

        Original: is_stable_an_hue_icon(img) — gates many checks.
        Returns True if the an_hue icon is visible in its expected region.
        """
        self._load_an_hue_template()
        if self._an_hue_template is None:
            return True  # No template → assume stable (graceful fallback)

        w, h = img.size
        x1, y1, x2, y2 = denormalize(AN_HUE_ICON_REGION, w, h)
        cropped = img.crop((x1, y1, x2, y2))
        crop_arr = np.array(cropped)
        crop_bgr = cv2.cvtColor(crop_arr, cv2.COLOR_RGB2BGR)
        template_bgr, mask = self._an_hue_template
        return match_template(crop_bgr, template_bgr, mask, threshold=0.7)

    def save_screenshot(self, save_path: str) -> bool:
        self.force_set_foreground()
        time.sleep(0.3)
        img = self.capture()
        if img:
            img.save(save_path)
            return True
        return False

    def safe_get_window_rect(self):
        try:
            if not isinstance(self.hwnd, int) or not win32gui.IsWindow(self.hwnd):
                return None
            return win32gui.GetWindowRect(self.hwnd)
        except pywintypes.error:
            return None
