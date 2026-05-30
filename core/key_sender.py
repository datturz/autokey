"""Key sender module - sends keystrokes to game window via PostMessage.

Matches original AutoKeyL2M v2.7 key mapping exactly.
"""
import win32api
import win32con
import time

# ══════════════════════════════════════════════════
# Original AutoKeyL2M __available_keys__ (dropdown list)
# Order: empty, numbers, symbols, function keys, special, letters
# ══════════════════════════════════════════════════

KEY_LIST = [
    "",             # Empty (no key)
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J",
    "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T",
    "U", "V", "W", "X", "Y", "Z",
    "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
    "Tab", "Space", "Esc",
    "[", "]", "\\", "`", "=", "-", ",", ".", ";", "/",
    "PS",
]

# ══════════════════════════════════════════════════
# Original AutoKeyL2M char_to_vk mapping (from utils/excute.py)
# ══════════════════════════════════════════════════

AVAILABLE_KEYS = {
    # ── Numbers ──
    "0": 48, "1": 49, "2": 50, "3": 51, "4": 52,
    "5": 53, "6": 54, "7": 55, "8": 56, "9": 57,

    # ── Letters (A-Z) ──
    "A": 65, "B": 66, "C": 67, "D": 68, "E": 69,
    "F": 70, "G": 71, "H": 72, "I": 73, "J": 74,
    "K": 75, "L": 76, "M": 77, "N": 78, "O": 79,
    "P": 80, "Q": 81, "R": 82, "S": 83, "T": 84,
    "U": 85, "V": 86, "W": 87, "X": 88, "Y": 89,
    "Z": 90,

    # ── Function keys ──
    "F1": 112, "F2": 113, "F3": 114, "F4": 115,
    "F5": 116, "F6": 117, "F7": 118, "F8": 119,
    "F9": 120, "F10": 121, "F11": 122, "F12": 123,

    # ── Special keys ──
    "Tab": 9,
    "Space": 32, "SPACE": 32,
    "Esc": 27, "ESC": 27, "Escape": 27,

    # ── Symbols ──
    "[": 219, "]": 221, "\\": 220,
    "`": 192, "=": 187, "-": 189, ",": 188, ";": 186,
    "/": 191, ".": 190,

    # ── Screenshot ──
    "PS": 44, "PRTSC": 44,
}


class KeySender:
    """Sends keystrokes to a specific window handle via PostMessage.
    Matches original AutoKeyL2M Excute class."""

    def __init__(self, hwnd: int):
        self.hwnd = hwnd

    def _char_to_vk(self, char: str) -> int | None:
        """Convert key name to virtual key code (same as original char_to_vk)."""
        return AVAILABLE_KEYS.get(char.strip())

    def send(self, char: str, hold_time: float = 0.1):
        """Send a single keystroke to the window.
        Default hold_time=0.1s matches original."""
        char = char.strip()
        if not char:
            return

        vk_code = self._char_to_vk(char)
        if vk_code is None:
            print(f"[KeySender] Unknown key: {char}")
            return

        scan_code = win32api.MapVirtualKey(vk_code, 0)
        lparam_down = 1 | (scan_code << 16)
        lparam_up = lparam_down | 0xC0000000  # (1 << 30) | (1 << 31) = 3221225472

        try:
            print(f"[KeySender] Sending '{char}' vk=0x{vk_code:02X} to hwnd={self.hwnd}")
            win32api.PostMessage(self.hwnd, win32con.WM_KEYDOWN, vk_code, lparam_down)
            time.sleep(hold_time)
            win32api.PostMessage(self.hwnd, win32con.WM_KEYUP, vk_code, lparam_up)
            print(f"[KeySender] Sent '{char}' OK")
        except Exception as e:
            print(f"[KeySender] send error for '{char}': {e}")

    def send_burst(self, chars, hold_time: float = 0.05, gap: float = 0.0):
        """Send a sequence of keystrokes back-to-back with NO per-key prints.

        Used for the zero-gap cancel→teleport burst: no logging/capture/assign
        happens between keys, so there is no "hole" for an enemy hit to cancel
        the teleport. hold_time is shorter than send() (0.1) to keep the
        cancel→TP transition tight; `gap` adds optional spacing between keys.
        """
        for char in chars:
            char = char.strip()
            if not char:
                continue
            vk_code = self._char_to_vk(char)
            if vk_code is None:
                continue
            scan_code = win32api.MapVirtualKey(vk_code, 0)
            lparam_down = 1 | (scan_code << 16)
            lparam_up = lparam_down | 0xC0000000
            try:
                win32api.PostMessage(self.hwnd, win32con.WM_KEYDOWN, vk_code, lparam_down)
                time.sleep(hold_time)
                win32api.PostMessage(self.hwnd, win32con.WM_KEYUP, vk_code, lparam_up)
                if gap:
                    time.sleep(gap)
            except Exception as e:
                print(f"[KeySender] send_burst error for '{char}': {e}")

    def send_down(self, char: str):
        """Send key DOWN (press without release). For WASD hold."""
        char = char.strip()
        if not char:
            return
        vk_code = self._char_to_vk(char)
        if vk_code is None:
            return
        scan_code = win32api.MapVirtualKey(vk_code, 0)
        lparam_down = 1 | (scan_code << 16)
        try:
            win32api.PostMessage(self.hwnd, win32con.WM_KEYDOWN, vk_code, lparam_down)
        except Exception:
            pass

    def send_up(self, char: str):
        """Send key UP (release). For WASD hold."""
        char = char.strip()
        if not char:
            return
        vk_code = self._char_to_vk(char)
        if vk_code is None:
            return
        scan_code = win32api.MapVirtualKey(vk_code, 0)
        lparam_up = 1 | (scan_code << 16) | 0xC0000000
        try:
            win32api.PostMessage(self.hwnd, win32con.WM_KEYUP, vk_code, lparam_up)
        except Exception:
            pass

    def send_force(self, char: str):
        """Send keystroke without condition checks (same as original sendKeyForce)."""
        self.send(char, hold_time=0.1)

    def restart_auto_hunting(self):
        """Restart auto hunt - same as original restart_auto_hunting.
        Sequence: \\ → wait 0.5s → \\ → wait 1s → F → wait 0.6s"""
        self.send_force("\\")
        time.sleep(0.5)
        self.send_force("\\")
        time.sleep(1.0)
        self.send_force("F")
        time.sleep(0.6)
