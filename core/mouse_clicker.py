"""Mouse clicker module - uses real mouse movement (SendInput).

PostMessage mouse clicks don't work with most game emulators.
This module uses SendInput which physically moves the cursor
and clicks, which works with all games and emulators.
"""
import ctypes
import time
import win32gui
import win32api
import win32con

# SendInput structures
INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_ABSOLUTE = 0x8000


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT(ctypes.Structure):
    class _INPUT_UNION(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("union", _INPUT_UNION),
    ]


def _send_input(inputs):
    """Send array of INPUT structures."""
    n = len(inputs)
    arr = (INPUT * n)(*inputs)
    ctypes.windll.user32.SendInput(n, arr, ctypes.sizeof(INPUT))


def _to_absolute(x_screen, y_screen):
    """Convert screen coordinates to absolute (0-65535) for SendInput."""
    screen_w = ctypes.windll.user32.GetSystemMetrics(0)
    screen_h = ctypes.windll.user32.GetSystemMetrics(1)
    abs_x = int(x_screen * 65536 / screen_w)
    abs_y = int(y_screen * 65536 / screen_h)
    return abs_x, abs_y


class MouseClicker:
    """Simulates mouse clicks using real cursor movement (SendInput).

    Coordinates are relative to the window's CLIENT AREA.
    The clicker converts them to screen coordinates before clicking.
    """

    # Base resolution for coordinate scaling (same as original AutoKeyL2M)
    BASE_W = 1280
    BASE_H = 720

    def __init__(self, hwnd: int):
        self.hwnd = hwnd

    def scale_coords(self, x: int, y: int) -> tuple[int, int]:
        """Scale coordinates from 1280x720 base to actual client size.
        This matches the original AutoKeyL2M Clicker._scale_coords()."""
        try:
            rect = win32gui.GetClientRect(self.hwnd)
            cw = rect[2] - rect[0]
            ch = rect[3] - rect[1]
            return (int(x * cw / self.BASE_W), int(y * ch / self.BASE_H))
        except Exception:
            return (x, y)

    def click_scaled(self, x_1280: int, y_720: int, delay: float = 0.1):
        """Click at 1280x720 base coordinates (auto-scaled to actual size)."""
        sx, sy = self.scale_coords(x_1280, y_720)
        self.click(sx, sy, delay)

    def _client_to_screen(self, x: int, y: int) -> tuple[int, int]:
        """Convert client-area coordinates to screen coordinates."""
        try:
            pt = win32gui.ClientToScreen(self.hwnd, (x, y))
            return pt
        except Exception:
            # Fallback: use window rect + offset
            try:
                rect = win32gui.GetWindowRect(self.hwnd)
                return (rect[0] + x, rect[1] + y)
            except Exception:
                return (x, y)

    def click(self, x: int, y: int, delay: float = 0.1):
        """Click at position (x, y) in client area coordinates.

        Physically moves the mouse cursor to the position and clicks.
        """
        # Convert client coords to screen coords
        screen_x, screen_y = self._client_to_screen(x, y)

        # Convert to absolute coordinates for SendInput
        abs_x, abs_y = _to_absolute(screen_x, screen_y)

        # Move mouse
        move = INPUT()
        move.type = INPUT_MOUSE
        move.union.mi.dx = abs_x
        move.union.mi.dy = abs_y
        move.union.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE

        # Mouse down
        down = INPUT()
        down.type = INPUT_MOUSE
        down.union.mi.dwFlags = MOUSEEVENTF_LEFTDOWN

        # Mouse up
        up = INPUT()
        up.type = INPUT_MOUSE
        up.union.mi.dwFlags = MOUSEEVENTF_LEFTUP

        try:
            _send_input([move])
            time.sleep(0.05)
            _send_input([down])
            time.sleep(delay)
            _send_input([up])
        except Exception as e:
            print(f"[MouseClicker] click error at ({x},{y})->screen({screen_x},{screen_y}): {e}")

    def drag(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.3, steps: int = 10):
        """Drag from (x1,y1) to (x2,y2) in client area coordinates."""
        sx1, sy1 = self._client_to_screen(x1, y1)
        sx2, sy2 = self._client_to_screen(x2, y2)

        abs_x1, abs_y1 = _to_absolute(sx1, sy1)

        # Move to start
        move = INPUT()
        move.type = INPUT_MOUSE
        move.union.mi.dx = abs_x1
        move.union.mi.dy = abs_y1
        move.union.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE

        down = INPUT()
        down.type = INPUT_MOUSE
        down.union.mi.dwFlags = MOUSEEVENTF_LEFTDOWN

        try:
            _send_input([move])
            time.sleep(0.05)
            _send_input([down])
            time.sleep(0.05)

            for i in range(1, steps + 1):
                t = i / steps
                cx = int(sx1 + (sx2 - sx1) * t)
                cy = int(sy1 + (sy2 - sy1) * t)
                ax, ay = _to_absolute(cx, cy)

                step_move = INPUT()
                step_move.type = INPUT_MOUSE
                step_move.union.mi.dx = ax
                step_move.union.mi.dy = ay
                step_move.union.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE
                _send_input([step_move])
                time.sleep(duration / steps)

            up = INPUT()
            up.type = INPUT_MOUSE
            up.union.mi.dwFlags = MOUSEEVENTF_LEFTUP
            _send_input([up])
        except Exception as e:
            print(f"[MouseClicker] drag error: {e}")
