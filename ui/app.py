"""Main application window for L2M AutoKey."""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import traceback
import warnings
warnings.filterwarnings("ignore", message="data discontinuity")
warnings.filterwarnings("ignore", category=DeprecationWarning)
import os
import sys
import cv2
import numpy as np
import win32gui


def _get_debug_dir():
    """Get persistent debug directory (next to exe, not in temp _MEIPASS)."""
    if hasattr(sys, '_MEIPASS'):
        # Running as PyInstaller exe — save next to the exe file
        exe_dir = os.path.dirname(sys.executable)
        d = os.path.join(exe_dir, "debug")
    else:
        d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "debug")
    os.makedirs(d, exist_ok=True)
    return d

# Suppress PIL palette warnings
warnings.filterwarnings("ignore", message="Palette images with Transparency")

from core.screen_capture import WindowCapturer
from core.key_sender import KeySender, KEY_LIST
from core.mouse_clicker import MouseClicker
from core.hp_checker import HPChecker, hp_color, mp_color
from core.boss_timer import BossTimer
from core.net_radar import NetRadar
from core.image_utils import load_image, match_template
from core.hunting import HuntingChecker
try:
    from core.sound_detector import SoundDetector, HAS_AUDIO
except ImportError:
    HAS_AUDIO = False
    SoundDetector = None
from core.game_layout import (
    denormalize, denormalize_point,
    SHOP_ICON_REGIONS, COMBAT_INDICATOR,
    DEATH_DIALOG_AREA, DEATH_DIALOG_BTN1, DEATH_DIALOG_BTN2,
    RADAR_TARGET_AREA,
    SAVED_LOCATION_KEY, SAVED_SPOT_COORDS_1280,
    SAVED_SPOTS_DIALOG_REGION, SAVED_SPOTS_DIALOG_THRESHOLD,
    CONFIRM_DIALOG_CLICK_1280,
    IGNORE_KEY_INVENTORY, IGNORE_KEY_SKILL, IGNORE_KEY_DIALOG,
    SKILL_SLOT_REGIONS_1280,
    get_warning_template_path, get_warning_region,
    get_warning_positions, WARNING_POSITIONS,
    MAP_AREA_TEMPLATES, MAP_BOSS_ICON_1280, MAP_ZARICHE_ICON_1280, MAP_BOSS_ENTRY_1280,
)
from utils.settings import load_settings, save_settings, list_profiles, get_default_settings
from utils.lang import load_lang
from ui.tab_main import TabMain
from ui.tab_radar import TabRadar
from ui.tab_weapon import TabWeapon
from ui.tab_farming import TabFarming
from ui.tab_daily import TabDaily
from ui.tab_dungeon import TabDungeon

__version__ = "1.1.0"


class L2MAutoKeyApp:
    """Main application class."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"L2M AutoKey v{__version__}")
        self.root.geometry("750x720")
        self.root.resizable(True, True)

        # State
        self.lang = load_lang()
        self.window_list: list[tuple[int, str]] = []
        self.target_hwnd: int = 0
        self.target_title: str = ""
        self.stop_event = threading.Event()
        self.threads: list[threading.Thread] = []
        self._lock = threading.Lock()

        # Core modules
        self.capturer: WindowCapturer | None = None
        self.key_sender: KeySender | None = None
        self.clicker: MouseClicker | None = None
        self.hp_checker = HPChecker()
        self.hunting_checker = HuntingChecker()
        # Sound-based radar detection
        self.sound_detector = None
        if HAS_AUDIO and SoundDetector:
            sound_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                       "assets", "enemy_warning.mp3")
            # Also check common download path
            alt_path = "c:/Users/hiday/Downloads/Enemy Is Here.mp3"
            if os.path.exists(sound_path):
                self.sound_detector = SoundDetector(sound_path)
            elif os.path.exists(alt_path):
                self.sound_detector = SoundDetector(alt_path)

        # Tracking state
        self.is_running = False
        self.last_hp_pct = 1.0
        self.is_in_town = False
        self._prev_in_town = False  # For state transition detection (original flow)
        self.is_attacked = False
        self.last_attack_time = 0.0
        self.last_in_town_time = 0.0
        self.last_in_hunting_time = 0.0
        self._is_stable = False  # Screen stability via an_hue_icon

        # Teleport state
        self._tp_last_time = 0.0
        self._tp_last_spot_index = -1

        # Boss/zariche template images
        self._boss_template = None
        self._zariche_template = None
        self._load_check_templates()

        # Town detection - shop/warehouse/te_dan icon templates
        self._shop_templates = []
        self._warehouse_templates = []
        self._load_shop_templates()

        # Confirm dialog template
        self._need_confirm_template = None
        self._load_confirm_template()

        self._build_ui()
        self.refresh_windows()

    def _load_check_templates(self):
        """Load boss and zariche check templates."""
        try:
            path = os.path.join("assets", "check_boss.jpg")
            if os.path.exists(path):
                self._boss_template = load_image(path)
        except Exception:
            pass
        try:
            path = os.path.join("assets", "check_zariche.jpg")
            if os.path.exists(path):
                self._zariche_template = load_image(path)
        except Exception:
            pass

    def _load_shop_templates(self):
        """Load shop, te_dan, and warehouse icon templates for town detection."""
        for fname in os.listdir("assets"):
            try:
                path = os.path.join("assets", fname)
                if fname.startswith("general_merchant") or fname.startswith("te_dan"):
                    bgr, mask = load_image(path)
                    self._shop_templates.append((bgr, mask, fname))
                elif fname.startswith("warehouse"):
                    bgr, mask = load_image(path)
                    self._warehouse_templates.append((bgr, mask, fname))
            except Exception:
                pass

    def _load_confirm_template(self):
        """Load need_confirm_1.jpg template for confirm dialog detection."""
        path = os.path.join("assets", "need_confirm_1.jpg")
        if os.path.exists(path):
            try:
                bgr, mask = load_image(path)
                self._need_confirm_template = (bgr, mask)
            except Exception:
                pass

    def _build_ui(self):
        """Build the main UI."""
        # === Status bar (bottom) ===
        status_frame = ttk.Frame(self.root, relief=tk.SUNKEN)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_label = ttk.Label(status_frame, text=self.lang.get("status_ready", "Status: Siap"))
        self.status_label.pack(side=tk.LEFT, padx=5)
        self.area_label = ttk.Label(status_frame, text="")
        self.area_label.pack(side=tk.LEFT, padx=10)
        self.hp_label = ttk.Label(status_frame, text="HP: -")
        self.hp_label.pack(side=tk.RIGHT, padx=5)
        self.log_label = ttk.Label(status_frame, text="")
        self.log_label.pack(side=tk.RIGHT, padx=10)

        # === Top controls ===
        top_frame = ttk.Frame(self.root, padding=5)
        top_frame.pack(fill=tk.X)

        ttk.Label(top_frame, text=self.lang.get("select_window", "Window:")).pack(side=tk.LEFT)
        self.window_combo = ttk.Combobox(top_frame, width=35, state="readonly")
        self.window_combo.pack(side=tk.LEFT, padx=5)
        self.window_combo.bind("<<ComboboxSelected>>", self._on_window_selected)

        ttk.Button(top_frame, text=self.lang.get("refresh", "Refresh"),
                   command=self.refresh_windows).pack(side=tk.LEFT, padx=2)

        ttk.Label(top_frame, text=self.lang.get("profile", "Profil:")).pack(side=tk.LEFT, padx=(15, 0))
        self.profile_combo = ttk.Combobox(top_frame, width=15, state="readonly")
        self.profile_combo.pack(side=tk.LEFT, padx=5)
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_selected)

        # Buttons
        btn_frame = ttk.Frame(self.root, padding=5)
        btn_frame.pack(fill=tk.X)

        self.btn_start = ttk.Button(btn_frame, text=self.lang.get("start", "Mulai"),
                                    command=self.start_all)
        self.btn_start.pack(side=tk.LEFT, padx=5)

        self.btn_stop = ttk.Button(btn_frame, text=self.lang.get("stop", "Berhenti"),
                                   command=self.stop_all, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        # === Notebook (tabs) ===
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        tab1_frame = ttk.Frame(self.notebook, padding=5)
        tab2_frame = ttk.Frame(self.notebook, padding=5)
        tab3_frame = ttk.Frame(self.notebook, padding=5)
        tab4_frame = ttk.Frame(self.notebook, padding=5)
        tab5_frame = ttk.Frame(self.notebook, padding=5)

        self.notebook.add(tab1_frame, text=self.lang.get("tab_main", "Utama"))
        self.notebook.add(tab2_frame, text=self.lang.get("tab_radar", "Radar"))
        self.notebook.add(tab3_frame, text=self.lang.get("tab_weapon", "Ganti Senjata"))
        self.notebook.add(tab4_frame, text=self.lang.get("tab_farming", "Farming"))
        self.notebook.add(tab5_frame, text=self.lang.get("tab_daily", "Harian"))
        # Dungeon tab — WIP, hidden until testing complete
        # tab6_frame = ttk.Frame(self.notebook, padding=5)
        # self.notebook.add(tab6_frame, text="Dungeon")

        self.tab_main = TabMain(tab1_frame, self.lang)
        self.tab_radar = TabRadar(tab2_frame, self.lang)
        self.tab_weapon = TabWeapon(tab3_frame, self.lang)
        self.tab_farming = TabFarming(tab4_frame, self.lang)
        self.tab_farming._test_tp_callback = self._test_teleport_now
        self.tab_farming._save_screenshot_callback = self._save_debug_screenshot
        self.tab_daily = TabDaily(tab5_frame, self.lang)
        # self.tab_dungeon = TabDungeon(tab6_frame, self.lang)
        self.tab_dungeon = None

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ──────────────────────────────────────────────
    #  Window / Profile management
    # ──────────────────────────────────────────────

    def refresh_windows(self):
        self.window_list.clear()
        app_title = self.root.title()

        def enum_handler(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if not title or title == app_title:
                    return
                lower = title.lower()
                keywords = ("lineage", "l2m", "mmu", "bluestack", "ldplayer",
                            "nox", "memu", "mobilemate", "gameloop")
                if any(kw in lower for kw in keywords):
                    self.window_list.append((hwnd, title))

        win32gui.EnumWindows(enum_handler, None)

        titles = [f"{title} (#{hwnd})" for hwnd, title in self.window_list]
        self.window_combo["values"] = titles
        if titles:
            self.window_combo.current(0)
            self._on_window_selected(None)

        profiles = list_profiles()
        self.profile_combo["values"] = profiles

    def _on_window_selected(self, event):
        idx = self.window_combo.current()
        if idx < 0 or idx >= len(self.window_list):
            return
        self.target_hwnd, self.target_title = self.window_list[idx]
        self.capturer = WindowCapturer(self.target_hwnd)
        self.key_sender = KeySender(self.target_hwnd)
        self.clicker = MouseClicker(self.target_hwnd)
        settings = load_settings(self.target_title)
        self._apply_all_settings(settings)

    def _on_profile_selected(self, event):
        profile = self.profile_combo.get()
        if profile:
            settings = load_settings(profile)
            self._apply_all_settings(settings)

    def _apply_all_settings(self, settings: dict):
        self.tab_main.apply_settings(settings)
        self.tab_radar.apply_settings(settings)
        self.tab_weapon.apply_settings(settings)
        self.tab_farming.apply_settings(settings)
        self.tab_daily.apply_settings(settings)
        if self.tab_dungeon:
            self.tab_dungeon.apply_settings(settings)

    def _collect_all_settings(self) -> dict:
        settings = {}
        settings.update(self.tab_main.collect_settings())
        settings.update(self.tab_radar.collect_settings())
        settings.update(self.tab_weapon.collect_settings())
        settings.update(self.tab_farming.collect_settings())
        settings.update(self.tab_daily.collect_settings())
        if self.tab_dungeon:
            settings.update(self.tab_dungeon.collect_settings())
        return settings

    # ──────────────────────────────────────────────
    #  Log helper
    # ──────────────────────────────────────────────

    def _log(self, msg: str):
        """Log message to status bar and console."""
        print(f"[L2M] {msg}")
        try:
            self.root.after(0, self.log_label.config, {"text": msg})
        except Exception:
            pass

    def _cleanup_screenshots(self, max_keep: int = 10):
        """Delete old screenshot files, keep only the most recent ones."""
        import glob
        patterns = ["screenshot_*.png", "screenshot_*.jpeg", "debug_screenshot.png"]
        all_files = []
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for pat in patterns:
            all_files.extend(glob.glob(os.path.join(base_dir, pat)))
        if len(all_files) <= max_keep:
            return
        # Sort by modification time, oldest first
        all_files.sort(key=os.path.getmtime)
        to_delete = all_files[:len(all_files) - max_keep]
        for f in to_delete:
            try:
                os.remove(f)
                print(f"[Cleanup] Deleted: {os.path.basename(f)}")
            except Exception:
                pass

    # ──────────────────────────────────────────────
    #  Start / Stop
    # ──────────────────────────────────────────────

    def start_all(self):
        if not self.target_hwnd:
            messagebox.showwarning(
                self.lang.get("error", "Error"),
                self.lang.get("must_select_window", "Harus pilih window Lineage")
            )
            return

        settings = self._collect_all_settings()
        save_settings(self.target_title, settings)

        # Cleanup old screenshots (keep max 10, delete oldest)
        self._cleanup_screenshots()

        self.is_running = True
        self.stop_event.clear()
        self.is_in_town = False
        self._prev_in_town = False
        self.is_attacked = False
        self.under_attack_time = 0.0
        self.last_in_town_time = 0.0
        self.last_in_hunting_time = 0.0
        self.last_auto_tp_at = 0.0
        self._tp_last_spot_index = -1
        self.do_auto_hunt = False
        self.isBlockedByMouseAction = False
        self.letter_last_time = 0.0
        self.boss_last_check = 0.0
        self.zariche_last_check = 0.0
        self._boss_last_check = 0.0
        self._zariche_last_check = 0.0
        self._boss_tele_at = 0.0
        self._zariche_tele_at = 0.0
        self._is_stable = False
        self._escaped_to_town_at = 0.0  # When radar triggered escape to town
        self._radar_last_trigger_at = 0.0  # Radar cooldown timestamp
        self._last_img_for_checks = None  # Cache latest image for other threads
        self._combat_escape_triggered = False  # Combat escape already fired this cycle
        self._combat_escape_last_at = 0.0  # Timestamp of last combat escape

        # Feature lock — prevents race conditions between features
        # Only ONE feature can run at a time (weapon switch, boss check, combat escape, etc.)
        import threading
        self._feature_lock = threading.Lock()
        self._feature_active = ""  # Name of currently running feature

        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.status_label.config(text=self.lang.get("status_active", "Status: Aktif"))
        self._log("Bot dimulai")

        # Boss timer Supabase disabled — usage too high
        self._boss_timer = None

        # Network radar disabled — entity type 4/6 includes ALL players (party, friendly)
        # causing false positives. Need game's radar warning packet decoded first.
        self._net_radar = None

        # Sound detection disabled — loopback too unstable (data discontinuity)
        # Using visual-only radar detection

        # Thread 1: Screen capture + HP + area detection
        self._start_thread(self._screen_capture_loop, "screen_capture")

        # Thread 2: Auto key press loops (one per key config)
        for cfg in self.tab_main.key_configs:
            key = cfg["key"].get()
            interval = cfg["interval"].get()
            condition = cfg["condition"].get()
            if key and interval:
                try:
                    iv = float(interval)
                except ValueError:
                    iv = 5.0
                self._start_thread(self._key_loop, f"key_{key}", args=(key, iv, condition))

        # Thread 3: Weapon switch
        if settings.get("weapon_switch_enabled"):
            self._start_thread(self._weapon_switch_loop, "weapon_switch")

        # Thread 4: Other tasks (teleport, auto hunt, letter, boss, daily)
        self._start_thread(self._other_tasks, "other_tasks")

        # Thread 5: Smart boss hunt (timer-driven)
        # Smart boss hunt disabled — Supabase usage too high
        # self._start_thread(self._smart_boss_hunt_loop, "smart_boss_hunt")

        # Thread 6: Radar scan
        if settings.get("radar_scan_enabled"):
            self._start_thread(self._radar_key_spam_loop, "radar_key_spam")

        # Wire dungeon tab refs (WIP — hidden until testing complete)
        # if self.tab_dungeon:
        #     self.tab_dungeon.set_bot_refs(
        #         capturer=self.capturer, clicker=self.clicker,
        #         key_sender=self.key_sender, stop_event=self.stop_event,
        #         acquire_feature=self._acquire_feature,
        #         release_feature=self._release_feature,
        #         check_interrupted=lambda: self.is_in_town or self._escaped_to_town_at > 0,
        #         log_callback=self._log,
        #         hwnd=self.capturer.hwnd if self.capturer else None,
        #     )

    def _start_thread(self, target, name, args=()):
        t = threading.Thread(target=target, args=args, daemon=True, name=name)
        t.start()
        self.threads.append(t)

    def stop_all(self):
        self.stop_event.set()
        self.is_running = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.status_label.config(text=self.lang.get("status_stopped", "Status: Berhenti"))
        self._log("Bot dihentikan")

        if self.sound_detector and hasattr(self.sound_detector, '_running') and self.sound_detector._running:
            self.sound_detector.stop()

        # Stop network radar
        if hasattr(self, '_net_radar') and self._net_radar:
            self._net_radar.stop()

        def _stop_worker():
            for t in self.threads:
                if t.is_alive():
                    t.join(timeout=3)
            self.threads.clear()
        threading.Thread(target=_stop_worker, daemon=True).start()

    # ──────────────────────────────────────────────
    #  Town detection (via shop icon matching)
    # ──────────────────────────────────────────────

    def _check_in_town_by_shop_icon(self, img) -> bool:
        """Check if character is in town by detecting shop/te_dan icons.

        Original: check_in_town_by_shop_icon(img) — template matching only.
        """
        w, h = img.size
        for region_norm in SHOP_ICON_REGIONS:
            rx1, ry1, rx2, ry2 = denormalize(region_norm, w, h)
            crop = img.crop((rx1, ry1, rx2, ry2))
            crop_bgr = cv2.cvtColor(np.array(crop), cv2.COLOR_RGB2BGR)
            for template_bgr, mask, fname in self._shop_templates:
                try:
                    if match_template(crop_bgr, template_bgr, mask, threshold=0.60):
                        return True
                except Exception:
                    pass
            for template_bgr, mask, fname in self._warehouse_templates:
                try:
                    if match_template(crop_bgr, template_bgr, mask, threshold=0.60):
                        return True
                except Exception:
                    pass
        return False

    def _is_opening_shop(self, img) -> bool:
        """Check if a shop/warehouse interface is currently open.

        Original: is_opening_shop(img) — checks warehouse templates in wider region.
        """
        w, h = img.size
        # Wider region for open shop detection
        SHOP_OPEN_REGION = (0.0, 0.70, 0.15, 1.0)
        rx1, ry1, rx2, ry2 = denormalize(SHOP_OPEN_REGION, w, h)
        crop = img.crop((rx1, ry1, rx2, ry2))
        crop_bgr = cv2.cvtColor(np.array(crop), cv2.COLOR_RGB2BGR)
        for template_bgr, mask, fname in self._warehouse_templates:
            try:
                if match_template(crop_bgr, template_bgr, mask, threshold=0.60):
                    return True
            except Exception:
                pass
        return False

    def _need_confirm(self, img) -> bool:
        """Check if a confirm dialog is showing (need_confirm_1.jpg).

        Original: need_confirm(img) → click (640, 576) @1280x720.
        """
        if self._need_confirm_template is None:
            return False
        w, h = img.size
        # Confirm dialog appears in center area
        CONFIRM_REGION = (0.35, 0.45, 0.65, 0.85)
        rx1, ry1, rx2, ry2 = denormalize(CONFIRM_REGION, w, h)
        crop = img.crop((rx1, ry1, rx2, ry2))
        crop_bgr = cv2.cvtColor(np.array(crop), cv2.COLOR_RGB2BGR)
        template_bgr, mask = self._need_confirm_template
        return match_template(crop_bgr, template_bgr, mask, threshold=0.7)

    def _is_inventory_or_skill_open(self, img) -> bool:
        """Check if inventory or skill window is open (blocks key sending).

        Original: ignorePressingKey checks IGNORE_KEY_INVENTORY and IGNORE_KEY_SKILL regions.
        """
        w, h = img.size
        # Check inventory region — dark panel with specific patterns
        for region in [IGNORE_KEY_INVENTORY, IGNORE_KEY_SKILL, IGNORE_KEY_DIALOG]:
            rx1, ry1, rx2, ry2 = denormalize(region, w, h)
            crop = img.crop((rx1, ry1, rx2, ry2))
            arr = np.array(crop)
            gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
            # These UI panels have dark backgrounds
            dark_ratio = np.sum(gray < 60) / gray.size
            if dark_ratio > 0.50:
                return True
        return False

    def _load_skill_templates(self):
        """Load skill state templates from assets (once)."""
        if hasattr(self, '_skill_templates_loaded') and self._skill_templates_loaded:
            return
        self._skill_templates_loaded = True
        self._skill_tpl = {}
        for state_name in ("idle", "self", "active", "cooldown"):
            path = os.path.join("assets", f"skill_{state_name}.png")
            if os.path.exists(path):
                bgr, mask = load_image(path)
                self._skill_tpl[state_name] = (bgr, mask)

    def _get_skill_state_by_template(self, img, debug: bool = False) -> str:
        """Detect skill state by template matching against bottom 25% of screen.

        Scans the bottom skill bar area for matching skill_idle/self/active/cooldown templates.
        Returns: 'active', 'self', 'cooldown', 'idle', or 'unknown'.
        """
        self._load_skill_templates()
        if not self._skill_tpl:
            return "unknown"

        w, h = img.size
        # Crop bottom 25% of screen (skill bar area)
        bottom = img.crop((0, int(h * 0.75), w, h))
        bottom_bgr = cv2.cvtColor(np.array(bottom), cv2.COLOR_RGB2BGR)

        # Scale templates to match resolution (templates are from ~80px crops at ~960x540)
        scale = h / 720.0  # approximate scale factor

        best_state = "unknown"
        best_score = 0.0

        # Check priority: cooldown first (most important to detect), then active, self, idle
        for state_name in ("cooldown", "active", "self", "idle"):
            if state_name not in self._skill_tpl:
                continue
            tpl_bgr, tpl_mask = self._skill_tpl[state_name]

            # Scale template
            th, tw = tpl_bgr.shape[:2]
            new_w = max(1, int(tw * scale))
            new_h = max(1, int(th * scale))
            scaled_tpl = cv2.resize(tpl_bgr, (new_w, new_h))
            scaled_mask = cv2.resize(tpl_mask, (new_w, new_h)) if tpl_mask is not None else None

            # Check template fits in bottom crop
            bh, bw = bottom_bgr.shape[:2]
            if new_w > bw or new_h > bh:
                continue

            # Match
            if scaled_mask is not None:
                result = cv2.matchTemplate(bottom_bgr, scaled_tpl, cv2.TM_CCORR_NORMED, mask=scaled_mask)
            else:
                result = cv2.matchTemplate(bottom_bgr, scaled_tpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if debug:
                print(f"[CE] template {state_name}: score={max_val:.3f}")

            if max_val > best_score and max_val > 0.7:
                best_score = max_val
                best_state = state_name

        if debug:
            print(f"[CE] Best match: {best_state} ({best_score:.3f})")

        return best_state

    def _is_skill_slot_active(self, img, slot: int = 4, debug: bool = False) -> bool:
        """Legacy wrapper — returns True if skill is active."""
        state = self._get_skill_state_by_template(img, debug)
        return state in ("active", "self")

    def _load_radar_warning_template(self):
        """Load warning template (❗ icon) once."""
        if hasattr(self, '_radar_warn_tpl_loaded') and self._radar_warn_tpl_loaded:
            return
        self._radar_warn_tpl_loaded = True
        self._radar_warn_tpl = None
        # Pilih template sesuai resolusi
        w = 1280
        if self.capturer:
            img = self.capturer.capture()
            if img:
                w = img.size[0]
        path = get_warning_template_path(w)
        if os.path.exists(path):
            try:
                bgr, mask = load_image(path)
                self._radar_warn_tpl = (bgr, mask)
            except Exception:
                pass

    def _fast_radar_warning_check(self, img) -> bool:
        """Radar warning detection — template match ❗ icon di area radar.

        Match warning_*.png template di region radar (kanan atas).
        Lebih reliable dari color detection.
        """
        self._load_radar_warning_template()

        w, h = img.size

        # Method 1: Template match warning ❗ di area radar (kanan layar 75-100%, 15-50%)
        tpl_match = False
        if self._radar_warn_tpl is not None:
            rx1 = int(w * 0.75)
            ry1 = int(h * 0.15)
            rx2 = w
            ry2 = int(h * 0.50)

            crop = img.crop((rx1, ry1, rx2, ry2))
            crop_bgr = cv2.cvtColor(np.array(crop), cv2.COLOR_RGB2BGR)
            ch, cw = crop_bgr.shape[:2]

            tpl_bgr, tpl_mask = self._radar_warn_tpl
            th, tw = tpl_bgr.shape[:2]
            scale = h / 720.0
            if abs(scale - 1.0) > 0.05:
                new_w = max(1, int(tw * scale))
                new_h = max(1, int(th * scale))
                if new_w < cw and new_h < ch:
                    tpl_bgr = cv2.resize(tpl_bgr, (new_w, new_h))
                    tpl_mask = cv2.resize(tpl_mask, (new_w, new_h)) if tpl_mask is not None else None
                    th, tw = new_h, new_w

            if th <= ch and tw <= cw:
                if tpl_mask is not None:
                    result = cv2.matchTemplate(crop_bgr, tpl_bgr, cv2.TM_CCORR_NORMED, mask=tpl_mask)
                else:
                    result = cv2.matchTemplate(crop_bgr, tpl_bgr, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)
                tpl_match = max_val >= 0.70

        # Method 2: Detect ❗ merah di WARNING_POSITIONS (backup)
        color_match = False
        positions = get_warning_positions(w)
        if not positions:
            sx, sy = w / 1280, h / 720
            positions = [(int(x1*sx), int(y1*sy), int(x2*sx), int(y2*sy))
                         for x1, y1, x2, y2 in WARNING_POSITIONS.get(1280, [])]

        for (x1, y1, x2, y2) in positions:
            x1 = max(0, min(x1, w-1))
            y1 = max(0, min(y1, h-1))
            x2 = max(x1+1, min(x2, w))
            y2 = max(y1+1, min(y2, h))
            crop = img.crop((x1, y1, x2, y2))
            arr = np.array(crop)
            if arr.size == 0:
                continue
            hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)
            m1 = cv2.inRange(hsv, np.array([0, 80, 80]), np.array([10, 255, 255]))
            m2 = cv2.inRange(hsv, np.array([170, 80, 80]), np.array([180, 255, 255]))
            red = np.sum(m1 > 0) + np.sum(m2 > 0)
            total = m1.size
            if total > 0 and (red / total) > 0.20:
                color_match = True
                break

        # SALAH SATU method match cukup (2-frame confirm di main loop handles false positive)
        return tpl_match or color_match

    # ──────────────────────────────────────────────
    #  Screen capture loop (HP, area, attack detection)
    # ──────────────────────────────────────────────

    def _screen_capture_loop(self):
        """Screen capture loop matching original AutoKeyL2M v2.7 flow.

        Per-tick (0.3s):
        1. Capture img
        2. Check isLocationSaveDialogOpening every frame
        3. Check is_stable_an_hue_icon every frame
        4. Town check (ONLY if not blocked, not dialog, is stable)
        5. When stable + ratio > 80%: re-capture and re-check town (double-confirm)
        6. State transitions via _prev_in_town
        7. isDead → click resurrection
        8. need_confirm → click confirm
        9. HP as int 0-100
        10. HP-based actions
        11. Attack detection via HuntingChecker
        12. Radar check (skip when in town)
        13. sleep 0.3
        """
        if not self.capturer:
            return

        while not self.stop_event.is_set():
            try:
                # 1. Capture img
                img = self.capturer.capture()
                if img is None:
                    self.stop_event.wait(1)
                    continue

                now = time.time()

                # RADAR detection moved to _check_radar_actions (line ~888)
                # Uses warning_1280.png + radar_1_/radar_3_ from original AutoKeyL2M v2.7

                # 2. Check saved spots dialog every frame
                dialog_open = self._is_saved_spots_dialog_open(img)

                # 3. Check screen stability every frame
                self._is_stable = self.capturer.is_stable_an_hue_icon(img)

                # 7. Death detection → click resurrection (640, 600) @1280x720
                # Original: tab4.nhan_hoi_sinh() → clicker.click(640, 600)
                try:
                    if self.hunting_checker.is_dead(img):
                        self._log("Dead! Klik resurrection (640,600)...")
                        if self.clicker:
                            self.clicker.click_scaled(640, 600)
                            time.sleep(2.0)
                except Exception:
                    pass

                # 8. Confirm dialog → click confirm
                try:
                    if self._need_confirm(img):
                        self._log("Confirm dialog! Klik OK...")
                        if self.clicker:
                            self.clicker.click_scaled(
                                CONFIRM_DIALOG_CLICK_1280[0],
                                CONFIRM_DIALOG_CLICK_1280[1])
                            time.sleep(0.5)
                except Exception:
                    pass

                # 9. HP as int 0-100 (original uses int)
                try:
                    hp_float = self.hp_checker.get_hp_percentage(img)
                    hp_drop = self.last_hp_pct - hp_float

                    # Read MP too (every frame, low cost)
                    try:
                        mp_float = self.hp_checker.get_mp_percentage(img)
                    except Exception:
                        mp_float = -1.0

                    # Guard: HP sudden drop > 30% dalam 1 frame = capture error
                    # (alt-tab, minimize, frame corrupted)
                    # HP real tidak mungkin drop >30% dalam 0.3 detik
                    if hp_drop > 0.30 and self.last_hp_pct > 0.20:
                        hp_pct = int(self.last_hp_pct * 100)  # lock ke nilai terakhir
                    elif hp_float < 0.01 and self.last_hp_pct > 0.10:
                        hp_pct = int(self.last_hp_pct * 100)  # lock ke nilai terakhir
                    else:
                        hp_pct = int(hp_float * 100)
                        self.last_hp_pct = hp_float
                        self.root.after(0, self._update_hp_display, hp_float, mp_float)
                except Exception:
                    hp_pct = int(self.last_hp_pct * 100)

                # 4. Town check (ONLY if not blocked, not dialog, is stable)
                try:
                    if not self.isBlockedByMouseAction and not dialog_open and self._is_stable:
                        # If radar just triggered escape → FORCE town state
                        if self._escaped_to_town_at > 0:
                            if (now - self._escaped_to_town_at) > 300:
                                self._escaped_to_town_at = 0
                                self.is_in_town = False
                                self._log("Radar escape timeout (5m), reset")
                            else:
                                if not self.is_in_town:
                                    self.is_in_town = True
                                    self.last_in_town_time = now
                        else:
                            # Template-based town detection (original)
                            in_town_now = (self._check_in_town_by_shop_icon(img)
                                           or self._is_opening_shop(img))

                            # 5. Double-confirm: when stable + ratio > 80%, re-capture
                            if in_town_now and hp_pct > 80:
                                img2 = self.capturer.capture()
                                if img2 is not None:
                                    in_town_now = (self._check_in_town_by_shop_icon(img2)
                                                   or self._is_opening_shop(img2))

                            # 6. State transitions via _prev_in_town
                            if in_town_now and not self._prev_in_town:
                                self.is_in_town = True
                                self.last_in_town_time = now
                                self._log("Kota terdeteksi (shop icon)")
                            elif not in_town_now and self._prev_in_town:
                                self.is_in_town = False
                                self.last_in_hunting_time = now
                                self.last_in_town_time = 0
                                # Full reset ALL features — clean state for hunting
                                self._escaped_to_town_at = 0
                                self._radar_last_trigger_at = 0
                                self._combat_escape_triggered = False
                                self._combat_escape_last_at = 0
                                self._potion_low_count = 0
                                self._potion_buy_active = False
                                self._log("Kembali hunting (all features reset)")
                            self._prev_in_town = in_town_now

                    if not self.is_in_town:
                        self.last_in_hunting_time = now

                    area_text = "Area: Kota (radar)" if self.is_in_town and self._escaped_to_town_at > 0 \
                        else "Area: Kota" if self.is_in_town \
                        else "Area: Hunting"
                    self.root.after(0, self.area_label.config, {"text": area_text})
                except Exception:
                    pass

                # Store image for other threads
                self._last_img_for_checks = img

                # 11. Attack detection via HuntingChecker
                try:
                    was_attacked = self.is_attacked
                    self.is_attacked = self.hunting_checker.is_being_attacked(img)
                    if self.is_attacked:
                        self.last_attack_time = now
                except Exception:
                    pass

                # 12. Combat Escape FIRST (HP critical = immediate action)
                # SKIP saat map terbuka (isBlockedByMouseAction)
                # Radar + Combat Escape are ONE UNIT:
                # Radar detects enemy → escape. If radar fails → combat escape handles HP drop.
                # Both run independently, both can trigger escape.
                # Only blocked when already in town or already escaped.
                if (not self.is_in_town
                        and self._escaped_to_town_at == 0
                        and (now - getattr(self, 'last_in_town_time', 0)) > 3):
                    self._check_radar_actions(img)

                # 12. Combat Escape: detect combat icon (crossed swords)
                # HP-based CE removed — HP checker unreliable due to visual effects
                # Combat icon detection is more accurate and consistent
                if (not self.is_in_town and not self.isBlockedByMouseAction
                        and self._escaped_to_town_at == 0):
                    self._check_combat_icon_escape(img)

                # 10. HP-based actions (skip saat map terbuka)
                if not self.isBlockedByMouseAction:
                    self._check_hp_actions(hp_pct / 100.0)

                # 13. sleep 0.3
                self.stop_event.wait(0.3)

            except Exception as e:
                print(f"[ScreenCapture] error: {e}")
                traceback.print_exc()
                self.stop_event.wait(1)

    def _update_hp_display(self, pct: float, mp_pct: float = -1.0):
        color = hp_color(pct)
        rate = self.hp_checker.hp_rate
        # Only show rate if it's reasonable (< 50%/s) and significant
        rate_str = ""
        if 0.05 < abs(rate) < 0.50:
            rate_str = f" ({rate*100:+.0f}%/s)"
        hp_text = f"HP: {pct*100:.0f}%{rate_str}"
        if 0.0 < mp_pct <= 1.0:
            hp_text += f"  MP: {mp_pct*100:.0f}%"
        self.hp_label.config(text=hp_text, foreground=color)

    # ──────────────────────────────────────────────
    #  Combat Escape (weapon → skill → teleport)
    # ──────────────────────────────────────────────

    def _on_net_radar_enemy(self, info: dict):
        """Callback from NetRadar — enemy player detected via network.
        This fires INSTANTLY when server sends player entity packet.
        Triggers escape without waiting for screen template matching."""
        if self.is_in_town or self._escaped_to_town_at > 0:
            return
        if not self.key_sender:
            return

        now = time.time()
        # Cooldown: don't retrigger within 15s
        if (now - getattr(self, '_net_radar_last_trigger', 0)) < 15:
            return

        radar_settings = self.tab_radar.collect_settings()
        radar_enabled = (radar_settings.get("radar_scan_enabled")
                         or radar_settings.get("radar_condition1_enabled")
                         or radar_settings.get("radar_warning_enabled"))
        if not radar_enabled:
            return

        # Get escape key
        esc_key = radar_settings.get("radar_scan_escape_key", "")
        if not esc_key:
            esc_key = radar_settings.get("radar_warning_key", "")
        if not esc_key:
            esc_key = radar_settings.get("radar_condition1_key", "")
        if not esc_key:
            return

        nearby = info.get('total_nearby', 1)
        self._log(f"[NetRadar] ENEMY DETECTED! ({nearby} players) → ESCAPE: {esc_key}")

        self._net_radar_last_trigger = now

        # IMMEDIATE escape — no delay, no template check
        self.key_sender.send(esc_key)
        time.sleep(0.3)
        self.key_sender.send(esc_key)

        self._escaped_to_town_at = now
        self._radar_last_trigger_at = now
        self.is_in_town = True
        self.last_in_town_time = now
        self.do_auto_hunt = True

    def _acquire_feature(self, name: str, timeout: float = 0.5) -> bool:
        """Try to acquire the feature lock. Returns True if acquired.
        If another feature is running, waits up to timeout seconds."""
        acquired = self._feature_lock.acquire(timeout=timeout)
        if acquired:
            self._feature_active = name
        return acquired

    def _release_feature(self):
        """Release the feature lock."""
        self._feature_active = ""
        try:
            self._feature_lock.release()
        except RuntimeError:
            pass  # Already released

    def _is_feature_busy(self) -> bool:
        """Check if any feature is currently running."""
        return self._feature_active != ""

    def _check_combat_icon_escape(self, img):
        """Combat Escape: detect combat icon (crossed swords).

        Detects the red crossed-swords icon that appears when character
        is being attacked. More reliable than HP-based detection which
        can misread due to visual effects, darkness debuff, etc.
        Selama icon terdeteksi, terus trigger — cooldown pendek (3s).
        """
        settings = self.tab_farming.collect_settings()
        if not settings.get("combat_escape_enabled"):
            return
        if not self.key_sender:
            return

        # Short cooldown — agresif selama icon masih terdeteksi
        now = time.time()
        if (now - getattr(self, '_combat_icon_escape_last_at', 0)) < 3:
            return

        # Search for combat icon ONLY to the RIGHT of X button
        # Farming sword icon (left of X) has similar red color — must exclude it
        # Combat icon appears right of X button near edge: ~(0.85, 0.60) to (1.0, 0.82)
        w, h = img.size
        rx1 = int(w * 0.85)
        ry1 = int(h * 0.60)
        rx2 = w  # all the way to right edge
        ry2 = int(h * 0.82)

        cropped = img.crop((rx1, ry1, rx2, ry2))
        crop_bgr = cv2.cvtColor(np.array(cropped), cv2.COLOR_RGB2BGR)

        # Step 1: Grayscale SHAPE matching (not color-based)
        # Red mask approach fails: spell effects flood region with red → false positive
        # Grayscale TM_CCOEFF_NORMED matches the crossed-sword SHAPE reliably
        combat_icon_path = os.path.join("assets", "combat_icon.png")
        if not os.path.exists(combat_icon_path):
            return

        try:
            template_bgr_orig, _ = load_image(combat_icon_path)
            crop_gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
            tmpl_gray_orig = cv2.cvtColor(template_bgr_orig, cv2.COLOR_BGR2GRAY)
            sh, sw = crop_gray.shape[:2]

            # Multi-scale: template from 1280x720, scale to current resolution
            scales = [0.5, 0.625, 0.75, 0.8, 0.9, 1.0, 1.1, 1.25, 1.5]
            best_val = 0

            for scale in scales:
                th_orig, tw_orig = tmpl_gray_orig.shape[:2]
                new_w = max(10, int(tw_orig * scale))
                new_h = max(10, int(th_orig * scale))
                if new_h > sh or new_w > sw:
                    continue

                tmpl_gray = cv2.resize(tmpl_gray_orig, (new_w, new_h),
                                       interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)

                result = cv2.matchTemplate(crop_gray, tmpl_gray, cv2.TM_CCOEFF_NORMED)
                _, max_val_s, _, _ = cv2.minMaxLoc(result)

                if max_val_s > best_val:
                    best_val = max_val_s

            if best_val < 0.85:
                return

            self._log(f"[CE] Combat icon detected! (score={best_val:.3f})")
        except Exception:
            return

        # Trigger combat escape with hp_pct=0 (darkness = can't read HP)
        tp_key = settings.get("combat_escape_teleport_key", "")
        if not tp_key:
            return

        if not self._acquire_feature("combat_escape", timeout=2.0):
            self._log(f"[CE] Waiting for {self._feature_active}...")
            return

        self._combat_escape_triggered = True
        self._combat_escape_last_at = now
        self._combat_icon_escape_last_at = now
        self._log("[CE] Combat Escape triggered by combat icon!")
        self._save_combat_escape_screenshot("CombatIcon")

        try:
            self._do_combat_escape(settings, 0, 0)
        finally:
            self._release_feature()

    def _save_combat_escape_screenshot(self, reason: str):
        """Save screenshot when combat escape triggers for debugging."""
        try:
            img = self.capturer.capture() if self.capturer else None
            if not img:
                return
            if hasattr(sys, '_MEIPASS'):
                base = os.path.dirname(sys.executable)
            else:
                base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ce_dir = os.path.join(base, "combat_escape_logs")
            os.makedirs(ce_dir, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            fname = f"CE_{reason}_{ts}.png"
            img.save(os.path.join(ce_dir, fname))
            self._log(f"[CE] Screenshot saved: {fname}")
        except Exception:
            pass

    def _do_combat_escape(self, settings, hp_pct_int, threshold):
        """Internal combat escape — simple reliable flow:

        1. Weapon switch
        2. Skill 2x (activate: SELF popup + confirm)
        3. Wait 1.5s (skill becomes active = stun immune)
        4. Skill 2x (cancel)
        5. TP spam (immediately after cancel, no gap)

        No state detection — always full sequence.
        If skill is on cooldown, presses do nothing (safe).
        """
        weapon_key = settings.get("combat_escape_weapon_key", "")
        skill_key = settings.get("combat_escape_skill_key", "")
        tp_key = settings.get("combat_escape_teleport_key", "")
        weapon_back_key = settings.get("combat_escape_weapon_back_key", "")
        potion_key = settings.get("combat_escape_potion_key", "")

        # Step 1: Weapon switch
        if weapon_key:
            self._log(f"[CE] Weapon: {weapon_key}")
            self.key_sender.send(weapon_key)
            time.sleep(0.3)

        # Step 2: Skill 2x (press → 0.05s → press)
        if skill_key:
            self._log(f"[CE] Skill 2x")
            self.key_sender.send(skill_key)
            time.sleep(0.05)
            self.key_sender.send(skill_key)

            # Step 3: Wait 1s (skill active = stun immune)
            time.sleep(1.0)

            # Step 4: Cancel 2x BURST + TP BURST — zero gap
            self._log(f"[CE] Cancel+TP")
            self.key_sender.send(skill_key)
            self.key_sender.send(skill_key)
            for _ in range(10):
                self.key_sender.send(tp_key)
        else:
            for _ in range(10):
                self.key_sender.send(tp_key)

        # Set town state
        self._escaped_to_town_at = time.time()
        self.is_in_town = True
        self.last_in_town_time = time.time()
        self.do_auto_hunt = True

        # === Wait for town arrival ===
        self._log("[CE] Waiting for town...")
        arrived = False
        for wait_try in range(10):
            time.sleep(1.0)
            if self.stop_event.is_set():
                return
            try:
                img = self.capturer.capture() if self.capturer else None
                if img and (self._check_in_town_by_shop_icon(img) or self._is_opening_shop(img)):
                    arrived = True
                    self._log(f"[CE] Town OK! ({wait_try+1}s)")
                    break
            except Exception:
                pass

        if not arrived:
            self._log("[CE] Town not confirmed, wait 3s")
            time.sleep(3)

        # === Wait screen loaded, then weapon back ===
        if weapon_back_key:
            self._log("[CE] Wait screen load...")
            for _lt in range(10):
                time.sleep(0.5)
                if self.stop_event.is_set():
                    return
                try:
                    img = self.capturer.capture() if self.capturer else None
                    if img and self.capturer.is_stable_an_hue_icon(img):
                        break
                except Exception:
                    pass
            else:
                time.sleep(1)

            self._log(f"[CE] Weapon back: {weapon_back_key}")
            self.key_sender.send(weapon_back_key)
            time.sleep(0.5)
            self.key_sender.send(weapon_back_key)

        # === Potion spam ===
        if potion_key:
            time.sleep(0.5)
            self._log(f"[CE] Potion: {potion_key} (5x)")
            for _ in range(5):
                self.key_sender.send(potion_key)
                time.sleep(0.4)

        # Reset potion state — prevent false trigger after combat escape
        self._potion_low_count = 0
        self._potion_last_check = time.time()

    # ──────────────────────────────────────────────
    #  HP-based actions
    # ──────────────────────────────────────────────

    def _check_hp_actions(self, hp_pct: float):
        """HP-based key presses with cooldown (like original).
        Enhanced: emergency burst healing when HP drops fast."""
        settings = self.tab_main.collect_settings()
        now = time.time()

        # Emergency burst: HP dropping fast (>15%/sec) → spam low HP key rapidly
        if (settings.get("enable_low_hp") and self.key_sender
                and self.hp_checker.is_hp_dropping_fast(-0.15)):
            key = settings.get("low_hp_key", "")
            if key and now - getattr(self, '_hp_burst_last', 0) > 0.3:
                self._send_key_safe(key)
                self._hp_burst_last = now
                if now - getattr(self, '_hp_burst_log', 0) > 3.0:
                    self._log(f"HP dropping fast! ({self.hp_checker.hp_rate*100:.0f}%/s) burst {key}")
                    self._hp_burst_log = now
                return  # Skip normal checks during burst

        # Low HP action (press heal key)
        if settings.get("enable_low_hp") and self.key_sender:
            threshold = settings.get("low_hp_percent", 30) / 100.0
            if hp_pct < threshold:
                # Faster cooldown when HP is very low (<15%)
                cooldown = 0.5 if hp_pct < 0.15 else 1.0
                if now - getattr(self, '_hp_low_last', 0) > cooldown:
                    key = settings.get("low_hp_key", "")
                    if key:
                        self._send_key_safe(key)
                        self._hp_low_last = now

        # Medium HP action
        if settings.get("enable_medium_hp") and self.key_sender:
            threshold = settings.get("medium_hp_percent", 60) / 100.0
            if hp_pct < threshold:
                only_attacked = settings.get("medium_hp_only_when_attacked", False)
                if not only_attacked or self.is_attacked:
                    delay = max(1.0, float(settings.get("medium_hp_delay", 1.0)))
                    if now - getattr(self, '_hp_med_last', 0) > delay:
                        key = settings.get("medium_hp_key", "")
                        if key:
                            self._send_key_safe(key)
                            self._hp_med_last = now

        # High HP action (ONLY press once every 30 seconds to prevent spam!)
        if settings.get("enable_high_hp") and self.key_sender:
            threshold = settings.get("high_hp_percent", 80) / 100.0
            if hp_pct > threshold:
                if now - getattr(self, '_hp_high_last', 0) > 30.0:
                    key = settings.get("high_hp_key", "")
                    if key:
                        self._send_key_safe(key)
                        self._hp_high_last = now

    # ──────────────────────────────────────────────
    #  Radar actions
    # ──────────────────────────────────────────────

    def _check_radar_actions(self, img):
        """Check radar for targets using warning icon template matching."""
        settings = self.tab_radar.collect_settings()
        if not self.key_sender:
            return

        # "Aktifkan Radar Scan" enables ALL detection (condition 1, 2, warning)
        radar_scan_enabled = settings.get("radar_scan_enabled", False)
        cond1 = settings.get("radar_condition1_enabled") or radar_scan_enabled
        cond2 = settings.get("radar_condition2_enabled") or radar_scan_enabled
        warn = settings.get("radar_warning_enabled") or radar_scan_enabled

        if not cond1 and not cond2 and not warn:
            return

        # Cooldown after radar triggered — don't spam
        # _radar_last_trigger_at is set when radar presses escape key
        radar_cooldown = getattr(self, '_radar_last_trigger_at', 0)
        if radar_cooldown > 0 and (time.time() - radar_cooldown) < 60:
            return

        w, h = img.size

        # Count radar targets FIRST (using radar_1_/radar_3_ templates)
        # These are more reliable than warning icon alone
        count = 0
        if cond1 or cond2:
            count = self._count_radar_targets(img)

        # Radar condition 2 first (more targets = higher priority)
        if cond2 and count > 0:
            target_count = int(settings.get("radar_condition2_count", 2))
            if count >= target_count:
                key = settings.get("radar_condition2_key", "") or settings.get("radar_scan_escape_key", "")
                if key:
                    self._log(f"Radar: {count} >= {target_count} target! Tekan {key}")
                    self.key_sender.send(key)
                    self._escaped_to_town_at = time.time()
                    self._radar_last_trigger_at = time.time()
                    self.is_in_town = True
                    self.last_in_town_time = time.time()
                    time.sleep(float(settings.get("radar_condition2_delay", 3.0)))
                    return

        # Radar condition 1
        if cond1 and count > 0:
            target_count = int(settings.get("radar_condition1_count", 1))
            if count >= target_count:
                key = settings.get("radar_condition1_key", "") or settings.get("radar_scan_escape_key", "")
                if key:
                    self._log(f"Radar: {count} >= {target_count} target! Tekan {key}")
                    self.key_sender.send(key)
                    self._escaped_to_town_at = time.time()
                    self._radar_last_trigger_at = time.time()
                    self.is_in_town = True
                    self.last_in_town_time = time.time()
                    time.sleep(float(settings.get("radar_condition1_delay", 3.0)))

    def _count_radar_targets(self, img) -> int:
        """Count radar targets using template matching on minimap.

        Uses RADAR_TARGET_AREA (full radar number zone) with padding.
        Searches for radar_1_/radar_3_ number templates AND radar_warn_icon.
        Both a number AND warning icon must match to confirm enemy presence.
        """
        from core.game_layout import RADAR_TARGET_AREA

        w, h = img.size

        # Use full radar area with extra padding so templates aren't clipped
        ax1, ay1, ax2, ay2 = denormalize(RADAR_TARGET_AREA, w, h)
        pad = 10
        ax1 = max(0, ax1 - pad)
        ay1 = max(0, ay1 - pad)
        ax2 = min(w, ax2 + pad)
        ay2 = min(h, ay2 + pad)

        cropped = img.crop((ax1, ay1, ax2, ay2))
        crop_bgr = cv2.cvtColor(np.array(cropped), cv2.COLOR_RGB2BGR)

        # Skip radar_1_640 if width > 660 (same as original)
        skip_640 = w > 660

        # Step 1: Check for number templates (radar_1_ or radar_3_)
        number_found = False
        for fname in os.listdir("assets"):
            if not (fname.startswith("radar_1_") or fname.startswith("radar_3_")):
                continue
            if skip_640 and "640" in fname:
                continue
            if not fname.endswith(('.png', '.jpg', '.jpeg')):
                continue

            try:
                template_bgr, mask = load_image(os.path.join("assets", fname))
                th, tw = template_bgr.shape[:2]
                sh, sw = crop_bgr.shape[:2]
                if th > sh or tw > sw:
                    continue
                if mask is not None:
                    result = cv2.matchTemplate(crop_bgr, template_bgr, cv2.TM_CCORR_NORMED, mask=mask)
                else:
                    result = cv2.matchTemplate(crop_bgr, template_bgr, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)
                if max_val >= 0.82:
                    number_found = True
                    self._log(f"Radar: {fname} matched (score={max_val:.3f})")
                    break
            except Exception:
                pass

        if not number_found:
            return 0

        # Step 2: Confirm with warning icon (radar_warn_icon.png)
        # Enemy radar always shows number + ❗ icon together
        warn_path = os.path.join("assets", "radar_warn_icon.png")
        if os.path.exists(warn_path):
            try:
                # Use wider region for warning icon (it appears to the side of numbers)
                warn_region = img.crop((
                    max(0, ax1 - 40), max(0, ay1 - 20),
                    min(w, ax2 + 40), min(h, ay2 + 20)
                ))
                warn_bgr = cv2.cvtColor(np.array(warn_region), cv2.COLOR_RGB2BGR)
                warn_tmpl, warn_mask = load_image(warn_path)
                wth, wtw = warn_tmpl.shape[:2]
                wsh, wsw = warn_bgr.shape[:2]
                if wth <= wsh and wtw <= wsw:
                    if warn_mask is not None:
                        result = cv2.matchTemplate(warn_bgr, warn_tmpl, cv2.TM_CCORR_NORMED, mask=warn_mask)
                    else:
                        result = cv2.matchTemplate(warn_bgr, warn_tmpl, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, _ = cv2.minMaxLoc(result)
                    if max_val >= 0.75:
                        self._log(f"Radar: warn_icon confirmed (score={max_val:.3f})")
                        return 1
                    else:
                        self._log(f"Radar: number found but warn_icon low (score={max_val:.3f}), skip")
                        return 0
            except Exception:
                pass

        # If warn icon file missing, fall back to number-only (but high threshold)
        return 1

    # ──────────────────────────────────────────────
    #  Key sending with safety checks
    # ──────────────────────────────────────────────

    def _send_key_safe(self, key: str):
        """Send key with safety checks matching original sendKey().

        Original differences:
        - Block when in town for > 3 seconds (not just any is_in_town)
        - Block when inventory/skill window open
        - F5/F6/F10: double-press with 0.3s gap
        - PS key: capture screenshot and save to file
        """
        if not self.key_sender or not key:
            return

        # Block ALL keys when escaped to town via radar (waiting for TP back)
        if self._escaped_to_town_at > 0:
            return

        settings = self.tab_main.collect_settings()

        # Block when in town for > 3 seconds (original: last_time_in_town > 3s)
        if settings.get("no_press_in_safe_area") and self.is_in_town:
            if self.last_in_town_time > 0 and (time.time() - self.last_in_town_time) > 3:
                return

        # Block when inventory/skill window is open
        img = self._last_img_for_checks
        if img is not None:
            try:
                if self._is_inventory_or_skill_open(img):
                    return
            except Exception:
                pass

        # PS key: capture screenshot and save to file
        if key.upper() in ("PS", "PRTSC"):
            try:
                if self.capturer:
                    ts = time.strftime("%Y%m%d_%H%M%S")
                    save_path = os.path.abspath(f"screenshot_{ts}.png")
                    self.capturer.save_screenshot(save_path)
                    self._log(f"Screenshot: {save_path}")
            except Exception as e:
                print(f"[SendKey] PS screenshot error: {e}")
            return

        # F5/F6/F10: double-press with 0.3s gap (original behavior)
        if key in ("F5", "F6", "F10"):
            self.key_sender.send(key)
            time.sleep(0.3)
            self.key_sender.send(key)
        else:
            self.key_sender.send(key)

    def _send_key_force(self, key: str):
        """Send key without any checks."""
        if self.key_sender and key:
            self.key_sender.send(key)

    # ──────────────────────────────────────────────
    #  Auto key loop
    # ──────────────────────────────────────────────

    def _key_loop(self, key: str, interval: float, condition: str):
        """Key press loop - matches original send_key_loop logic.
        Conditions: anytime, when_attacked (same as original 5 conditions)."""
        TICK = 0.3  # Check every 0.3s like original
        anytime = self.lang.get("anytime", "Kapan saja")
        last_press = 0.0

        while not self.stop_event.is_set():
            try:
                now = time.monotonic()

                # Skip during mouse actions (like original)
                if self.isBlockedByMouseAction:
                    self.stop_event.wait(TICK)
                    continue

                # Check condition
                should_send = False
                if condition == anytime:
                    should_send = True
                else:
                    # "Saat diserang" condition
                    should_send = self.is_attacked

                # Check interval and send
                if should_send and (now - last_press) >= interval:
                    self._send_key_safe(key)
                    last_press = time.monotonic()

                self.stop_event.wait(TICK)

            except Exception as e:
                print(f"[KeyLoop] {key} error: {e}")
                self.stop_event.wait(1)

    # ──────────────────────────────────────────────
    #  Weapon switch loop
    # ──────────────────────────────────────────────

    def _weapon_switch_loop(self):
        """Weapon switch loop — fire setiap interval, tunda saat di-hit.

        - Selalu berjalan sesuai interval
        - Saat kena hit → tunda sampai tidak diserang lagi
        - Skip saat map terbuka, di kota, atau escaped
        """
        last_switch = 0  # Fire immediately on first iteration

        while not self.stop_event.is_set():
            settings = self.tab_weapon.collect_settings()
            interval_sec = settings.get("weapon_switch_interval", 60) * 60
            delay = settings.get("weapon_switch_delay", 1.0)
            key1 = settings.get("weapon_key1", "")
            key2 = settings.get("weapon_key2", "")

            if not key1 or not self.key_sender:
                self.stop_event.wait(1)
                continue

            now = time.time()
            if (now - last_switch) < interval_sec:
                self.stop_event.wait(1)
                continue

            # Guard: skip saat map terbuka, di kota, escaped, atau combat escape aktif
            if self.isBlockedByMouseAction:
                self.stop_event.wait(1)
                continue
            if self.is_in_town or self._escaped_to_town_at > 0:
                self.stop_event.wait(1)
                continue
            if self._combat_escape_triggered:
                self.stop_event.wait(1)
                continue

            # Tunda saat sedang diserang
            if self.is_attacked:
                self.stop_event.wait(0.5)
                continue

            # Acquire feature lock — skip if another feature is running
            if not self._acquire_feature("weapon_switch", timeout=0.1):
                self.stop_event.wait(1)
                continue

            last_switch = now

            self._log(f"Ganti senjata: {key1}")
            self.key_sender.send(key1)
            self.stop_event.wait(delay)

            if self.stop_event.is_set():
                break

            if settings.get("weapon_press_space"):
                self.key_sender.send("Space")
                self.stop_event.wait(0.5)

            if key2:
                self.stop_event.wait(delay)
                # Re-check: abort key2 if combat escape triggered during delay
                if self.stop_event.is_set():
                    self._release_feature()
                    break
                if self._combat_escape_triggered or self._escaped_to_town_at > 0:
                    self._log(f"Ganti senjata kembali SKIP (combat escape aktif)")
                    self._release_feature()
                    continue
                self._log(f"Ganti senjata kembali: {key2}")
                self.key_sender.send(key2)

            self._release_feature()

    # ──────────────────────────────────────────────
    #  Radar Scan loop
    # ──────────────────────────────────────────────

    def _load_radar_alert_template(self):
        """Load radar alert templates (once). Tries small ❗ icon first (faster)."""
        if hasattr(self, '_radar_alert_tpl_loaded') and self._radar_alert_tpl_loaded:
            return
        self._radar_alert_tpl_loaded = True
        self._radar_alert_tpl = None
        self._radar_warn_icon_tpl = None

        # Primary: small ❗ icon (fast, reliable)
        icon_path = os.path.join("assets", "radar_warn_icon.png")
        if os.path.exists(icon_path):
            try:
                bgr, mask = load_image(icon_path)
                self._radar_warn_icon_tpl = (bgr, mask)
            except Exception:
                pass

        # Fallback: full radar entry
        path = os.path.join("assets", "radar_alert.png")
        if os.path.exists(path):
            try:
                bgr, mask = load_image(path)
                self._radar_alert_tpl = (bgr, mask)
            except Exception:
                pass

    def _fast_radar_color_detect(self, img) -> bool:
        """Fast radar detection — detect ❗ warning icon by RED COLOR.

        The ❗ icon is bright red/orange on dark background.
        Scans the radar area (right side, 55-80% x, 20-50% y) for
        concentrated red pixels. Much faster than template matching.
        """
        w, h = img.size
        # Radar area: right side of screen where player list appears
        rx1 = int(w * 0.55)
        ry1 = int(h * 0.15)
        rx2 = int(w * 0.85)
        ry2 = int(h * 0.55)

        crop = img.crop((rx1, ry1, rx2, ry2))
        crop_bgr = cv2.cvtColor(np.array(crop), cv2.COLOR_RGB2BGR)
        crop_hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)

        # Detect bright red/orange pixels (the ❗ icon color)
        # Red hue: 0-10 or 170-180, high saturation, high value
        mask_low = cv2.inRange(crop_hsv, (0, 150, 150), (10, 255, 255))
        mask_high = cv2.inRange(crop_hsv, (170, 150, 150), (180, 255, 255))
        # Also detect orange (the ❗ can be orange-red)
        mask_orange = cv2.inRange(crop_hsv, (10, 150, 150), (25, 255, 255))

        red_mask = cv2.bitwise_or(mask_low, mask_high)
        red_mask = cv2.bitwise_or(red_mask, mask_orange)

        red_pixels = np.count_nonzero(red_mask)
        total_pixels = crop_hsv.shape[0] * crop_hsv.shape[1]
        ratio = red_pixels / total_pixels if total_pixels > 0 else 0

        # The ❗ icon is small but distinct — even 0.3% of radar area is enough
        # (at 200x200 crop, ❗ icon is ~15x15 = 225px, ratio = 225/40000 = 0.56%)
        return ratio > 0.003

    def _is_radar_alert_visible(self, img) -> bool:
        """Check if radar alert ❗ icon is visible (enemy detected).

        Uses small ❗ icon template (radar_warn_icon.png) for fast matching.
        Searches right 40% of screen, top 60%.
        """
        self._load_radar_alert_template()

        w, h = img.size
        # Search area: right 45%, top 60% (where radar entries appear)
        rx1 = int(w * 0.55)
        ry1 = 0
        rx2 = w
        ry2 = int(h * 0.60)
        cropped = img.crop((rx1, ry1, rx2, ry2))
        crop_bgr = cv2.cvtColor(np.array(cropped), cv2.COLOR_RGB2BGR)
        bh, bw = crop_bgr.shape[:2]
        scale = h / 720.0

        # Match full radar entry template (radar_alert.png — number + shield + name + ❗)
        # Small ❗ icon disabled — too many false positives from game UI elements
        if self._radar_alert_tpl is not None:
            tpl_bgr, tpl_mask = self._radar_alert_tpl
            th, tw = tpl_bgr.shape[:2]
            new_w = max(1, int(tw * scale))
            new_h = max(1, int(th * scale))
            if new_w > bw or new_h > bh:
                s2 = min(bw / tw, bh / th) * 0.9
                new_w = max(1, int(tw * s2))
                new_h = max(1, int(th * s2))
            s_tpl = cv2.resize(tpl_bgr, (new_w, new_h))
            s_mask = cv2.resize(tpl_mask, (new_w, new_h)) if tpl_mask is not None else None
            if s_mask is not None:
                result = cv2.matchTemplate(crop_bgr, s_tpl, cv2.TM_CCORR_NORMED, mask=s_mask)
            else:
                result = cv2.matchTemplate(crop_bgr, s_tpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)
            if max_val > 0.80:
                return True

        return False

    # ──────────────────────────────────────────────
    #  Smart Boss Hunt (timer-driven)
    # ──────────────────────────────────────────────

    def _smart_boss_hunt_loop(self):
        """Smart boss hunt — polls Supabase for upcoming bosses, auto TP + hit.

        Flow:
        1. Poll boss timer every 30s
        2. When boss countdown < pre-position time → trigger hunt
        3. Open map → find boss → find glowing skull → teleport
        4. Wait + radar spam → boss bar → hit
        5. Boss dies → screenshot → TP back to farm
        """
        boss_timer = getattr(self, '_boss_timer', BossTimer())
        hunted_bosses = set()

        while not self.stop_event.is_set():
            self.stop_event.wait(10)  # Poll every 10s
            if self.stop_event.is_set():
                break

            settings = self.tab_daily.collect_settings()
            if not settings.get("smart_boss_enabled"):
                continue

            # Skip if in town, escaping, or busy
            if self.is_in_town or self._escaped_to_town_at > 0:
                continue
            if self._is_feature_busy():
                continue

            prepos_min = settings.get("smart_boss_prepos_min", 1)
            hit_key = settings.get("smart_boss_hit_key", "")
            radar_key = settings.get("smart_boss_radar_key", "")

            # Which boss types to hunt
            allowed_types = set()
            if settings.get("smart_boss_type_ours"): allowed_types.add("ours")
            if settings.get("smart_boss_type_ffa"): allowed_types.add("ffa")
            if settings.get("smart_boss_type_inv"): allowed_types.add("invasion")

            if not allowed_types:
                continue

            # Get upcoming bosses within pre-position window
            upcoming = boss_timer.get_upcoming_bosses(within_minutes=prepos_min)

            # Filter by type and not already hunted
            targets = [b for b in upcoming
                       if b["type"] in allowed_types
                       and b["name"] not in hunted_bosses]

            if not targets:
                # Update status with next boss info
                all_bosses = boss_timer.get_upcoming_bosses(within_minutes=120)
                filtered = [b for b in all_bosses if b["type"] in allowed_types]
                if filtered:
                    nxt = filtered[0]
                    cd = boss_timer.format_countdown(nxt["countdown_sec"])
                    self.root.after(0, self.tab_daily.smart_boss_status.config,
                                    {"text": f"Next: {nxt['name']} in {cd}"})
                continue

            # Target the nearest boss
            target = targets[0]
            boss_name = target["name"]
            cd = boss_timer.format_countdown(target["countdown_sec"])
            self._log(f"[SmartBoss] Target: {boss_name} (countdown={cd})")
            self.root.after(0, self.tab_daily.smart_boss_status.config,
                            {"text": f"HUNTING: {boss_name} ({cd})"})

            # Acquire feature lock
            if not self._acquire_feature("smart_boss_hunt", timeout=5.0):
                self._log(f"[SmartBoss] Cannot start — {self._feature_active} running")
                continue

            try:
                success = self._execute_smart_boss_hunt(boss_name, settings)
                hunted_bosses.add(boss_name)
                if success:
                    self._log(f"[SmartBoss] {boss_name} — HIT!")
                else:
                    self._log(f"[SmartBoss] {boss_name} — MISS or DEAD")

                # Reset hunted list after 30 min (boss respawn cycle)
                # So we can re-hunt the same boss next spawn
            except Exception as e:
                self._log(f"[SmartBoss] Error: {e}")
                import traceback
                traceback.print_exc()
            finally:
                self._release_feature()

            # Clear hunted bosses after 1 hour
            if len(hunted_bosses) > 20:
                hunted_bosses.clear()

    def _execute_smart_boss_hunt(self, boss_name: str, settings: dict) -> bool:
        """Execute the full boss hunt sequence for one boss.

        Uses the existing _check_boss_or_zariche flow but with smart settings.
        The Smart Boss Hunt provides the TIMING, the existing code does the MAP work.

        Returns True if boss was found and teleported to.
        """
        hit_key = settings.get("smart_boss_hit_key", "")
        radar_key = settings.get("smart_boss_radar_key", "")

        if not self.capturer or not self.key_sender or not self.clicker:
            return False

        self._load_boss_zariche_templates()

        # Build settings that _check_boss_or_zariche expects
        boss_settings = {
            "check_boss_enabled": True,
            "check_boss_interval": 0,  # No interval — trigger now
            "check_boss_radar_key": radar_key,
            "check_boss_hit_key": hit_key,
            "check_boss_tele_after_min": 5,
            "check_boss_areas": ["ALL"],  # Check ALL areas
        }

        # Force reset the last check time so it triggers immediately
        self._boss_last_check = 0

        # Track if we were in town before (means we teleported to boss)
        was_in_town = self.is_in_town

        # Use existing boss check flow (handles map, area search, skull, TP, fight)
        # _skip_lock=True because smart hunt already holds the feature lock
        self._check_boss_or_zariche(boss_settings, kind="boss", _skip_lock=True)

        # Check if we actually teleported (boss was found)
        # If _boss_tele_at changed, we teleported to a boss
        boss_found = getattr(self, '_boss_tele_at', 0) > 0

        # Only screenshot if boss was actually found and we left farming spot
        if boss_found:
            try:
                img = self.capturer.capture()
                if img:
                    debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                             '..', 'debug')
                    os.makedirs(debug_dir, exist_ok=True)
                    ts = time.strftime('%Y%m%d_%H%M%S')
                    path = os.path.join(debug_dir, f'boss_{boss_name}_{ts}.png')
                    img.save(path)
                    self._log(f"[SmartBoss] Screenshot: {path}")
            except Exception:
                pass
            return True
        else:
            self._log(f"[SmartBoss] {boss_name} not found on map, no screenshot")
            return False

    def _radar_key_spam_loop(self):
        """Spam radar scan key (R) periodically. Detection is in main loop."""
        settings = self.tab_radar.collect_settings()
        scan_key = settings.get("radar_scan_key", "")
        interval = settings.get("radar_scan_interval", 3)

        if not scan_key or not self.key_sender:
            return

        while not self.stop_event.is_set():
            try:
                if (self.is_in_town or self._escaped_to_town_at > 0
                        or self.isBlockedByMouseAction
                        or self._combat_escape_triggered):
                    self.stop_event.wait(1)
                    continue

                self.key_sender.send(scan_key)
                self.stop_event.wait(interval)
            except Exception:
                self.stop_event.wait(1)

    def _radar_scan_loop(self):
        """Radar scan loop — spam radar key, check for alerts, trigger escape."""
        settings = self.tab_radar.collect_settings()
        scan_key = settings.get("radar_scan_key", "")
        escape_key = settings.get("radar_scan_escape_key", "")
        interval = settings.get("radar_scan_interval", 3)

        if not scan_key or not self.key_sender:
            return

        while not self.stop_event.is_set():
            try:
                # Skip saat di kota, escaped, atau baru keluar dari kota (3s grace)
                in_town_recently = (time.time() - getattr(self, 'last_in_town_time', 0)) < 3
                if self.is_in_town or self._escaped_to_town_at > 0 or in_town_recently:
                    # Auto-reset _escaped_to_town_at setelah 60s (prevent stuck)
                    if self._escaped_to_town_at > 0 and (time.time() - self._escaped_to_town_at) > 60:
                        self._escaped_to_town_at = 0
                        self._log("[RADAR] Reset escaped state (timeout 60s)")
                    self.stop_event.wait(1)
                    continue

                # Skip saat mouse action or combat escape active
                if self.isBlockedByMouseAction:
                    self.stop_event.wait(0.5)
                    continue
                if self._combat_escape_triggered:
                    self.stop_event.wait(1)
                    continue

                # Press radar scan key
                self.key_sender.send(scan_key)
                # Wait for radar UI to appear AND settle (avoid matching radar UI itself)
                time.sleep(1.0)

                # Skip if combat escape triggered during wait
                if self._combat_escape_triggered or self._escaped_to_town_at > 0:
                    continue

                # Detection handled by _check_radar_actions in main loop
                # This thread ONLY spams the R key
                self.stop_event.wait(interval)

            except Exception as e:
                print(f"[RadarScan] error: {e}")
                self.stop_event.wait(1)

    # ──────────────────────────────────────────────
    #  Farming loop (teleport, auto hunt, letter)
    # ──────────────────────────────────────────────

    def _other_tasks(self):
        """Secondary task loop - matches original AutoKeyL2M other_tasks.

        Runs every 1 second. Handles:
        - Town false-positive correction (original: "Lỗi nhầm lẫn merchant")
        - Auto hunt restart (with debounce)
        - Teleport (after town / during farm)
        - Auto check letter
        - Boss/zariche check
        - Daily tasks (bulk purchase, clan, daily claim)
        """
        TICK = 1  # 1 second between ticks (same as original)

        while not self.stop_event.is_set():
            try:
                # Skip during combat or combo
                if self.is_attacked:
                    self.stop_event.wait(TICK)
                    continue

                settings = self._collect_all_settings()
                now = time.time()

                # NOTE: isBlockedByMouseAction hanya di-set True saat map/mouse action
                # (boss check, teleport), bukan sepanjang tick

                # ── Town false-positive correction (original: "Lỗi nhầm lẫn merchant") ──
                # SKIP jika escaped via combat escape/radar — kita TAHU di kota
                # If last_time_in_town > 3s AND NOT check_in_town AND NOT dialog → reset
                if self.is_in_town and self.last_in_town_time > 0 and self._escaped_to_town_at == 0:
                    if (now - self.last_in_town_time) > 3:
                        img = self._last_img_for_checks
                        if img is not None:
                            try:
                                if (not self._check_in_town_by_shop_icon(img)
                                        and not self._is_saved_spots_dialog_open(img)):
                                    self._log("Town false-positive detected, reset")
                                    self.is_in_town = False
                                    self._prev_in_town = False
                                    self.last_in_town_time = 0
                                    self.last_in_hunting_time = now
                                    self._escaped_to_town_at = 0
                            except Exception:
                                pass

                # ── Auto Hunt Restart (with debounce matching original) ──
                if settings.get("auto_hunt_enabled") and self.key_sender:
                    if self.do_auto_hunt and not self.is_in_town:
                        # Original: 10-20s since last hunting, attack_flag > 10s
                        hunt_ok = (now - self.last_in_hunting_time) > 10
                        attack_ok = (now - self.last_attack_time) > 10
                        if hunt_ok and attack_ok:
                            self._start_auto_hunt()
                            self.do_auto_hunt = False

                # ── Teleport Logic (same as original teleport_to_spots) ──
                if settings.get("auto_teleport_enabled"):
                    self._check_teleport_conditions(settings, now)

                # ── Auto Check Letter ──
                if settings.get("auto_check_letter") and self.key_sender:
                    interval_sec = settings.get("auto_check_letter_minutes", 30) * 60
                    if now - self.letter_last_time > interval_sec:
                        self._send_key_force("T")
                        time.sleep(2)
                        self._send_key_force("Escape")
                        self.letter_last_time = now
                        self._log("Auto check letter: tekan T")

                # ── Auto Buy Potion (LOWEST priority) ──
                # Only runs when ALL higher priority features are idle:
                # 1. Not in town (not after combat escape / radar escape)
                # 2. No escape in progress
                # 3. Radar hasn't triggered in last 30s
                # 4. Combat escape hasn't triggered in last 60s
                # 5. No feature lock active
                if (not self.is_in_town
                        and self._escaped_to_town_at == 0
                        and not self._combat_escape_triggered
                        and (now - getattr(self, '_radar_last_trigger_at', 0)) > 30
                        and (now - getattr(self, '_combat_escape_last_at', 0)) > 60
                        and not self._is_feature_busy()):
                    self._check_auto_potion(settings, now)

                # ── Skip boss/zariche/daily saat di kota (escaped) ──
                if not self.is_in_town and self._escaped_to_town_at == 0:
                    # ── Daily Tasks (bulk purchase, clan, daily claim) ──
                    self._check_and_run_daily_tasks(settings)

                    # ── Boss Check (full map flow) ──
                    self._check_boss(settings)

                    # ── Zariche Check (full map flow) ──
                    self._check_zariche(settings)

                self.stop_event.wait(TICK)

            except Exception as e:
                self.isBlockedByMouseAction = False  # Safety reset on error
                print(f"[OtherTasks] error: {e}")
                traceback.print_exc()
                self.stop_event.wait(TICK)

    def _check_teleport_conditions(self, settings: dict, now: float):
        """Check if should teleport back to farming spot.

        Triggers:
        1. RADAR ESCAPE: Radar detected enemy → pressed escape key → went to town
           → wait N minutes → teleport back to farming spot
        2. IDLE/TOWN: HP full + no combat for long time → likely in town
           → wait N minutes → teleport back to farming spot
        3. DURING FARM: Change spot after N minutes of farming
        """

        # Cooldown - don't spam teleport
        TP_COOLDOWN = 60
        if self.last_auto_tp_at > 0 and (now - self.last_auto_tp_at) < TP_COOLDOWN:
            return

        # ── Trigger 1: Escaped to town (combat escape / radar) ──
        if settings.get("teleport_after_town_enabled") and self._escaped_to_town_at > 0:
            wait_min = settings.get("teleport_after_town_minutes", 1)
            wait_sec = wait_min * 60
            time_since_escape = now - self._escaped_to_town_at
            remaining = wait_sec - time_since_escape
            if int(remaining) % 10 == 0 and remaining > 0:
                self._log(f"[TP] Tunggu {remaining:.0f}s lagi untuk TP balik...")
            if time_since_escape >= wait_sec:
                self._log(f"Radar escape {time_since_escape:.0f}s lalu, teleport ke farming!")
                self._teleport_to_spot(settings)
                self.last_auto_tp_at = now
                self._escaped_to_town_at = 0
                self._radar_last_trigger_at = 0  # Reset radar cooldown
                self.do_auto_hunt = True
                return

        # ── Trigger 2: Idle/town detection (HP full + no combat) ──
        if settings.get("teleport_after_town_enabled") and self.is_in_town and self.last_in_town_time > 0:
            wait_min = settings.get("teleport_after_town_minutes", 1)
            wait_sec = wait_min * 60
            time_in_town = now - self.last_in_town_time
            if time_in_town >= wait_sec:
                self._log(f"Idle/kota {time_in_town:.0f}s, teleport ke farming!")
                self._teleport_to_spot(settings)
                self.last_auto_tp_at = now
                self.is_in_town = False
                self._prev_in_town = False
                self.last_in_town_time = 0
                self.do_auto_hunt = True
                return

        # ── Trigger 3: Change spot during farming ──
        if settings.get("teleport_during_farm_enabled") and not self.is_in_town:
            farm_min = settings.get("teleport_during_farm_minutes", 30)
            farm_sec = farm_min * 60
            if self.last_auto_tp_at > 0 and (now - self.last_auto_tp_at) >= farm_sec:
                self._log(f"Farming {farm_min}m, pindah spot!")
                self._teleport_to_spot(settings, rotate=True)
                self.last_auto_tp_at = now

    def _load_autohunt_templates(self):
        """Load autohunt on/off templates (once)."""
        if hasattr(self, '_ah_templates_loaded') and self._ah_templates_loaded:
            return
        self._ah_templates_loaded = True
        self._autohunt_on_tpl = None
        self._autohunt_off_tpl = None
        for name, attr in [("autohunt_on.png", "_autohunt_on_tpl"),
                           ("autohunt_off.png", "_autohunt_off_tpl")]:
            path = os.path.join("assets", name)
            if os.path.exists(path):
                try:
                    bgr, mask = load_image(path)
                    setattr(self, attr, (bgr, mask))
                except Exception:
                    pass

    def _is_autohunt_on(self, img=None) -> bool | None:
        """Cek apakah auto hunt sedang ON via template matching.

        Match autohunt_on.png dan autohunt_off.png di area kanan layar.
        Returns: True=ON, False=OFF, None=tidak bisa detect.
        """
        self._load_autohunt_templates()
        if img is None:
            if not self.capturer:
                return None
            img = self.capturer.capture()
            if img is None:
                return None

        w, h = img.size
        # Auto hunt icon di kanan layar (75-100% width, 30-65% height)
        rx1 = int(w * 0.75)
        ry1 = int(h * 0.30)
        rx2 = w
        ry2 = int(h * 0.65)
        crop = img.crop((rx1, ry1, rx2, ry2))
        crop_bgr = cv2.cvtColor(np.array(crop), cv2.COLOR_RGB2BGR)
        ch, cw = crop_bgr.shape[:2]
        scale = h / 720.0

        on_score = 0.0
        off_score = 0.0

        # Check ON template
        if self._autohunt_on_tpl is not None:
            tpl_bgr, tpl_mask = self._autohunt_on_tpl
            th, tw = tpl_bgr.shape[:2]
            s_tpl, s_mask = tpl_bgr, tpl_mask
            if abs(scale - 1.0) > 0.05:
                nw = max(1, int(tw * scale))
                nh = max(1, int(th * scale))
                if nw < cw and nh < ch:
                    s_tpl = cv2.resize(tpl_bgr, (nw, nh))
                    s_mask = cv2.resize(tpl_mask, (nw, nh)) if tpl_mask is not None else None
            sth, stw = s_tpl.shape[:2]
            if sth <= ch and stw <= cw:
                if s_mask is not None:
                    result = cv2.matchTemplate(crop_bgr, s_tpl, cv2.TM_CCORR_NORMED, mask=s_mask)
                else:
                    result = cv2.matchTemplate(crop_bgr, s_tpl, cv2.TM_CCOEFF_NORMED)
                _, on_score, _, _ = cv2.minMaxLoc(result)

        # Check OFF template
        if self._autohunt_off_tpl is not None:
            tpl_bgr, tpl_mask = self._autohunt_off_tpl
            th, tw = tpl_bgr.shape[:2]
            s_tpl, s_mask = tpl_bgr, tpl_mask
            if abs(scale - 1.0) > 0.05:
                nw = max(1, int(tw * scale))
                nh = max(1, int(th * scale))
                if nw < cw and nh < ch:
                    s_tpl = cv2.resize(tpl_bgr, (nw, nh))
                    s_mask = cv2.resize(tpl_mask, (nw, nh)) if tpl_mask is not None else None
            sth, stw = s_tpl.shape[:2]
            if sth <= ch and stw <= cw:
                if s_mask is not None:
                    result = cv2.matchTemplate(crop_bgr, s_tpl, cv2.TM_CCORR_NORMED, mask=s_mask)
                else:
                    result = cv2.matchTemplate(crop_bgr, s_tpl, cv2.TM_CCOEFF_NORMED)
                _, off_score, _, _ = cv2.minMaxLoc(result)

        try:
            print(f"[AutoHunt] ON={on_score:.3f} OFF={off_score:.3f}")
        except Exception:
            pass

        # Return yang score tertinggi (min 0.6)
        if on_score >= 0.6 and on_score > off_score:
            return True
        if off_score >= 0.6 and off_score > on_score:
            return False
        return None

    def _start_auto_hunt(self):
        """Restart auto hunt — HANYA jika autohunt OFF (template match).
        Tidak fire jika ON atau unknown.
        Cooldown 30s antara attempts.
        """
        if not self.key_sender:
            return
        # Cooldown
        now = time.time()
        last_attempt = getattr(self, '_autohunt_last_attempt', 0)
        if (now - last_attempt) < 30:
            return
        self._autohunt_last_attempt = now
        # Cek apakah sudah ON via template
        is_on = self._is_autohunt_on()
        if is_on is True:
            self._log("Auto hunt sudah ON, skip")
            self.do_auto_hunt = False
            return
        if is_on is False:
            self._log("Auto hunt OFF → tekan F")
            self.key_sender.send("F")
            return
        # Unknown → skip, jangan spam
        self._log("Auto hunt: tidak bisa detect, skip")

    # ──────────────────────────────────────────────
    #  Boss / Zariche check (original Tab5 flow)
    # ──────────────────────────────────────────────

    def _load_boss_zariche_templates(self):
        """Load boss, zariche, normal_map, confirm_tele templates (once)."""
        if hasattr(self, '_bz_templates_loaded') and self._bz_templates_loaded:
            return
        self._bz_templates_loaded = True
        self._normal_map_tpl = None
        self._confirm_tele_tpl = None
        self._confirm_dialog_tpl = None
        self._close_map_tpl = None
        self._boss_target_bar_tpls = []  # Multiple templates
        for name, attr in [("normal_map.jpg", "_normal_map_tpl"),
                           ("confirm_tele.jpg", "_confirm_tele_tpl"),
                           ("confirm_diaglog.jpg", "_confirm_dialog_tpl"),
                           ("close.jpg", "_close_map_tpl")]:
            path = os.path.join("assets", name)
            if os.path.exists(path):
                try:
                    bgr, mask = load_image(path)
                    setattr(self, attr, (bgr, mask))
                except Exception:
                    pass
        # Load semua boss_target_bar variants
        for fname in ["boss_target_bar.png", "boss_target_bar_2.png"]:
            path = os.path.join("assets", fname)
            if os.path.exists(path):
                try:
                    bgr, mask = load_image(path)
                    self._boss_target_bar_tpls.append((bgr, mask, fname))
                except Exception:
                    pass
        # Load boss_notyet_spawn (normal state = diamond+gold display)
        self._boss_notyet_tpl = None
        path = os.path.join("assets", "boss_notyet_spawn.png")
        if os.path.exists(path):
            try:
                bgr, mask = load_image(path)
                self._boss_notyet_tpl = (bgr, mask)
            except Exception:
                pass

    def _load_area_templates(self):
        """Load area text templates for map panel (once)."""
        if hasattr(self, '_area_tpls_loaded') and self._area_tpls_loaded:
            return
        self._area_tpls_loaded = True
        self._area_templates = {}
        for area, path in MAP_AREA_TEMPLATES.items():
            if os.path.exists(path):
                try:
                    bgr, mask = load_image(path)
                    self._area_templates[area] = (bgr, mask)
                except Exception:
                    pass

    def _find_and_click_area(self, img, area: str) -> bool:
        """Find area text on screen via template matching and click it.

        Scales template to match current resolution.
        Returns True if found and clicked.
        """
        self._load_area_templates()
        tpl_data = self._area_templates.get(area)
        if tpl_data is None:
            return False

        tpl_bgr, tpl_mask = tpl_data
        w, h = img.size

        # Search in left panel only (0-30% width)
        panel_w = int(w * 0.30)
        LEFT_PANEL = (0, 0, panel_w, h)
        crop = img.crop(LEFT_PANEL)
        crop_bgr = cv2.cvtColor(np.array(crop), cv2.COLOR_RGB2BGR)
        ch, cw = crop_bgr.shape[:2]

        # Scale template to match current resolution
        # Templates captured at ~1280x720, scale proportionally
        th, tw = tpl_bgr.shape[:2]
        scale = h / 720.0
        new_w = max(1, int(tw * scale))
        new_h = max(1, int(th * scale))

        # Pastikan template tidak lebih besar dari crop
        if new_w > cw or new_h > ch:
            scale2 = min(cw / tw, ch / th) * 0.9
            new_w = max(1, int(tw * scale2))
            new_h = max(1, int(th * scale2))

        scaled_tpl = cv2.resize(tpl_bgr, (new_w, new_h))
        scaled_mask = cv2.resize(tpl_mask, (new_w, new_h)) if tpl_mask is not None else None

        if scaled_mask is not None:
            result = cv2.matchTemplate(crop_bgr, scaled_tpl, cv2.TM_CCORR_NORMED, mask=scaled_mask)
        else:
            result = cv2.matchTemplate(crop_bgr, scaled_tpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= 0.7:
            # Click center of match (offset by LEFT_PANEL origin)
            cx = LEFT_PANEL[0] + max_loc[0] + new_w // 2
            cy = LEFT_PANEL[1] + max_loc[1] + new_h // 2
            self.clicker.click(cx, cy)
            return True
        return False

    def _has_template_in_fullscreen(self, img, template_tup, threshold=0.3) -> bool:
        """Check template match against full screenshot, auto-scale template."""
        if template_tup is None:
            return False
        tpl_bgr, tpl_mask = template_tup
        img_bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        sh, sw = img_bgr.shape[:2]
        th, tw = tpl_bgr.shape[:2]

        # Scale template jika resolusi berbeda dari 720p
        scale = sh / 720.0
        if abs(scale - 1.0) > 0.05:  # Hanya scale jika beda > 5%
            new_w = max(1, int(tw * scale))
            new_h = max(1, int(th * scale))
            if new_w < sw and new_h < sh:
                tpl_bgr = cv2.resize(tpl_bgr, (new_w, new_h))
                tpl_mask = cv2.resize(tpl_mask, (new_w, new_h)) if tpl_mask is not None else None

        return match_template(img_bgr, tpl_bgr, tpl_mask, threshold=threshold)

    def _check_hp_interrupt_while_map_open(self) -> bool:
        """Cek apakah HP drop saat map terbuka → close map + abort.

        Returns True jika interrupt terjadi (map di-close, harus abort).
        """
        settings = self.tab_farming.collect_settings()
        if not settings.get("combat_escape_enabled"):
            return False
        threshold = settings.get("combat_escape_hp", 50)
        # Cek HP dari last known value
        hp_pct = int(self.last_hp_pct * 100)
        if hp_pct > 0 and hp_pct < threshold:
            self._log(f"[MAP INTERRUPT] HP={hp_pct}% < {threshold}%, close map!")
            self._close_map()
            return True
        return False

    def _close_map(self, img=None):
        """Close map by clicking close.jpg button, fallback to koordinat, fallback to Escape."""
        # Try 1: template matching close.jpg (auto-scale)
        if self._close_map_tpl is not None and self.clicker:
            cap = img or (self.capturer.capture() if self.capturer else None)
            if cap:
                tpl_bgr, tpl_mask = self._close_map_tpl
                img_bgr = cv2.cvtColor(np.array(cap), cv2.COLOR_RGB2BGR)
                sh, sw = img_bgr.shape[:2]
                th, tw = tpl_bgr.shape[:2]

                # Scale template
                scale = sh / 720.0
                if abs(scale - 1.0) > 0.05:
                    new_w = max(1, int(tw * scale))
                    new_h = max(1, int(th * scale))
                    if new_w < sw and new_h < sh:
                        tpl_bgr = cv2.resize(tpl_bgr, (new_w, new_h))
                        tpl_mask = cv2.resize(tpl_mask, (new_w, new_h)) if tpl_mask is not None else None
                        th, tw = new_h, new_w

                if th <= sh and tw <= sw:
                    if tpl_mask is not None:
                        result = cv2.matchTemplate(img_bgr, tpl_bgr, cv2.TM_CCORR_NORMED, mask=tpl_mask)
                    else:
                        result = cv2.matchTemplate(img_bgr, tpl_bgr, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, max_loc = cv2.minMaxLoc(result)
                    if max_val >= 0.6:
                        cx = max_loc[0] + tw // 2
                        cy = max_loc[1] + th // 2
                        self.clicker.click(cx, cy)
                        self._log("[Map] Klik close (template)")
                        time.sleep(0.5)
                        return

        # Try 2: fallback klik posisi close →] @1280x720 (auto-scaled)
        if self.clicker:
            self._log("[Map] Klik close (fallback)")
            self.clicker.click_scaled(1230, 88)
            time.sleep(0.5)
            return

        # Try 3: tekan Escape
        if self.key_sender:
            self.key_sender.send("Escape")
            time.sleep(0.5)

    def _is_boss_target_bar_visible(self, img, debug: bool = False) -> bool:
        """Cek apakah boss target bar ada di frame.

        Boss bar = garis merah horizontal + nama boss di PALING ATAS layar.
        Two methods:
        1. Template matching (primary)
        2. Red HP bar color detection in top strip (fallback)
        """
        w, h = img.size
        # Region: top 8% of screen, right of player HP bar (40-100% width)
        rx1 = int(w * 0.35)
        ry1 = 0
        rx2 = w
        ry2 = int(h * 0.08)

        crop = img.crop((rx1, ry1, rx2, ry2))
        crop_bgr = cv2.cvtColor(np.array(crop), cv2.COLOR_RGB2BGR)
        ch, cw = crop_bgr.shape[:2]
        scale = h / 720.0

        # Method 1: Template matching
        if self._boss_target_bar_tpls:
            for tpl_bgr, tpl_mask, fname in self._boss_target_bar_tpls:
                th, tw = tpl_bgr.shape[:2]
                s_tpl = tpl_bgr
                s_mask = tpl_mask
                if abs(scale - 1.0) > 0.05:
                    new_w = max(1, int(tw * scale))
                    new_h = max(1, int(th * scale))
                    if new_w < cw and new_h < ch:
                        s_tpl = cv2.resize(tpl_bgr, (new_w, new_h))
                        s_mask = cv2.resize(tpl_mask, (new_w, new_h)) if tpl_mask is not None else None

                sth, stw = s_tpl.shape[:2]
                if sth > ch or stw > cw:
                    continue

                if s_mask is not None:
                    result = cv2.matchTemplate(crop_bgr, s_tpl, cv2.TM_CCORR_NORMED, mask=s_mask)
                else:
                    result = cv2.matchTemplate(crop_bgr, s_tpl, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)

                if debug:
                    print(f"[TargetBar] {fname}: score={max_val:.3f}")

                if max_val >= 0.60:
                    return True

        # Method 2: Fallback — detect red HP bar via HSV color
        # Boss target bar is a distinct red horizontal bar
        crop_hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
        # Red hue: 0-10 or 170-180, high saturation, medium+ value
        mask_low = cv2.inRange(crop_hsv, (0, 120, 80), (10, 255, 255))
        mask_high = cv2.inRange(crop_hsv, (170, 120, 80), (180, 255, 255))
        red_mask = cv2.bitwise_or(mask_low, mask_high)
        red_pixels = np.count_nonzero(red_mask)
        red_ratio = red_pixels / (ch * cw) if ch * cw > 0 else 0

        if debug:
            print(f"[TargetBar] Red fallback: {red_pixels}px ratio={red_ratio:.3f}")

        # Boss bar typically fills >2% of the top strip with red
        if red_ratio > 0.02:
            return True

        return False

    def _wait_boss_dead_then_tp(self, settings: dict, label: str = "Boss"):
        """Tunggu boss/zariche mati, loot, TP ke farm.

        Enhanced precision:
        1. Loading 5s
        2. Spam radar continuously (every 3s, even during fight)
        3. Multi-hit: press hit key repeatedly until boss engaged
        4. Faster death detection: 3x bar gone (9s) instead of 5x (15s)
        5. Adaptive loot wait: 15s base, check if target bar reappears
        6. Auto re-engage if boss bar comes back (wasn't dead)
        """
        if not self.capturer:
            return

        label_lower = label.lower()
        radar_key = settings.get(f"check_{label_lower}_radar_key", "")
        hit_key = settings.get(f"check_{label_lower}_hit_key", "")
        tele_wait_min = settings.get(f"check_{label_lower}_tele_after_min", 5)
        max_wait = tele_wait_min * 60

        # Loading
        self._log(f"[{label}] Loading teleport...")
        self.stop_event.wait(5)
        if self.stop_event.is_set():
            return

        # Map closed → unblock combat escape
        self.isBlockedByMouseAction = False

        self._log(f"[{label}] Monitoring boss bar (max {tele_wait_min}m)...")
        start = time.time()
        last_radar_press = 0.0
        last_hit_press = 0.0
        boss_spawned = False
        boss_engaged = False  # True after we confirmed hitting boss
        gone_count = 0
        hit_count = 0

        while not self.stop_event.is_set():
            elapsed = time.time() - start
            now = time.time()

            if elapsed > max_wait:
                self._log(f"[{label}] Timeout {tele_wait_min}m -> TP ke farm")
                break

            # Spam radar continuously (every 3s) — boss may move/respawn
            if radar_key and self.key_sender and (now - last_radar_press) > 3:
                self.key_sender.send(radar_key)
                last_radar_press = now

            img = self.capturer.capture()
            if img is None:
                self.stop_event.wait(1)
                continue

            debug = (int(elapsed) % 15 == 0 and elapsed > 1)
            bar_visible = self._is_boss_target_bar_visible(img, debug=debug)

            if bar_visible and not boss_spawned:
                # Boss bar APPEARS -> boss spawned!
                boss_spawned = True
                gone_count = 0
                self._log(f"[{label}] BOSS SPAWN! Bar detected!")

                # Immediate radar + hit
                if radar_key and self.key_sender:
                    self.key_sender.send(radar_key)
                    time.sleep(0.3)
                if hit_key and self.key_sender:
                    self._log(f"[{label}] Hit: {hit_key}")
                    self.key_sender.send(hit_key)
                    last_hit_press = now
                    hit_count = 1

            elif bar_visible and boss_spawned:
                # Still fighting — keep hitting every 2s until engaged
                gone_count = 0
                if hit_key and self.key_sender and not boss_engaged:
                    if (now - last_hit_press) > 2.0 and hit_count < 5:
                        self.key_sender.send(hit_key)
                        last_hit_press = now
                        hit_count += 1
                        self._log(f"[{label}] Re-hit #{hit_count}")
                    elif hit_count >= 5:
                        boss_engaged = True
                        self._log(f"[{label}] Engaged! Fighting...")

                if debug:
                    self._log(f"[{label}] Fighting... ({elapsed:.0f}s)")

            elif not bar_visible and boss_spawned:
                # Bar gone after spawn -> boss dead? Verify 3x (faster)
                gone_count += 1
                if gone_count <= 3:
                    self._log(f"[{label}] Bar gone? ({gone_count}/3)")
                if gone_count >= 3:
                    self._log(f"[{label}] BOSS DEAD! Looting...")
                    # Adaptive loot: wait 15s, then check if bar reappears
                    self.stop_event.wait(15)
                    if self.stop_event.is_set():
                        return
                    # Double-check: bar might reappear (boss wasn't dead)
                    recheck = self.capturer.capture()
                    if recheck and self._is_boss_target_bar_visible(recheck):
                        self._log(f"[{label}] Boss NOT dead! Bar came back, re-engaging...")
                        gone_count = 0
                        boss_engaged = False
                        hit_count = 0
                        continue
                    # Confirmed dead
                    self._log(f"[{label}] Confirmed dead. Wait 10s more for loot...")
                    self.stop_event.wait(10)
                    break

            elif not bar_visible and not boss_spawned:
                # Not spawned yet
                if int(elapsed) % 15 == 0 and elapsed > 1:
                    self._log(f"[{label}] Waiting spawn... ({elapsed:.0f}s/{max_wait}s)")

            self.stop_event.wait(2)  # Check every 2s (was 3s)

        if self.stop_event.is_set():
            return

        # TP ke farming spot
        self._log(f"[{label}] TP ke farming spot!")
        if settings.get("auto_teleport_enabled"):
            self._teleport_to_spot(settings)
        self.do_auto_hunt = True

    def _get_confirm_position(self, img) -> tuple | None:
        """Find confirm_tele button position in screenshot.

        Original: searches 2 positions and returns center of match.
        Positions @1280x720: (925,110) area and (230,250) area.
        """
        if self._confirm_tele_tpl is None:
            return None
        tpl_bgr, tpl_mask = self._confirm_tele_tpl
        img_bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        sh, sw = img_bgr.shape[:2]
        th, tw = tpl_bgr.shape[:2]
        if th > sh or tw > sw:
            return None
        if tpl_mask is not None:
            result = cv2.matchTemplate(img_bgr, tpl_bgr, cv2.TM_CCORR_NORMED, mask=tpl_mask)
        else:
            result = cv2.matchTemplate(img_bgr, tpl_bgr, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val >= 0.7:
            cx = max_loc[0] + tw // 2
            cy = max_loc[1] + th // 2
            return (cx, cy)
        return None

    def _check_boss(self, settings: dict):
        """Check boss — wrapper yang loop area."""
        self._check_boss_or_zariche(settings, kind="boss")

    def _check_zariche(self, settings: dict):
        """Check zariche — wrapper yang loop area."""
        self._check_boss_or_zariche(settings, kind="zariche")

    def _check_boss_or_zariche(self, settings: dict, kind: str = "boss", _skip_lock: bool = False):
        """Unified boss/zariche check — loop selected areas di map.

        Flow:
        1. Buka map → klik icon boss/zariche (panel kanan atas)
        2. List area muncul di panel kiri (ALL, Gludio, dll)
        3. Loop area yang di-checklist:
           - Klik area name → cek apakah boss icon menyala (template match)
           - Menyala → klik boss entry → teleport → fight → loot → TP farm
           - Gelap → skip, next area
        4. Semua area selesai → close map
        """
        label = kind.capitalize()
        enabled_key = f"check_{kind}_enabled"
        interval_key = f"check_{kind}_interval"
        areas_key = f"check_{kind}_areas"
        last_check_attr = f"_{kind}_last_check"
        template = self._boss_template if kind == "boss" else self._zariche_template
        icon_coords = MAP_BOSS_ICON_1280 if kind == "boss" else MAP_ZARICHE_ICON_1280
        status_label = self.tab_daily.boss_status if kind == "boss" else self.tab_daily.zariche_status

        if not settings.get(enabled_key):
            return
        if not self.capturer or not self.key_sender or not self.clicker:
            return

        self._load_boss_zariche_templates()
        now = time.time()

        # Acquire feature lock — skip if called from smart hunt (already locked)
        has_lock = _skip_lock
        if not _skip_lock:
            if not self._acquire_feature(f"check_{kind}", timeout=0.5):
                self._log(f"[{kind.capitalize()}] Waiting for {self._feature_active}...")
                return
            has_lock = True

        # Interval check (skip if called from smart hunt with interval=0)
        last_check = getattr(self, last_check_attr, 0)
        interval_sec = settings.get(interval_key, 5) * 60
        if interval_sec > 0 and (now - last_check) < interval_sec:
            if has_lock and not _skip_lock:
                self._release_feature()
            return

        setattr(self, last_check_attr, now)

        # Areas to check
        areas = settings.get(areas_key, [])
        if not areas:
            areas = ["ALL"]

        self._log(f"[{label}] Checking {len(areas)} area: {', '.join(areas)}")

        # 1. Buka map — block combat escape saat map terbuka
        self.isBlockedByMouseAction = True
        self.key_sender.send("M")
        time.sleep(2)

        map_open = True  # Track map state
        found = False

        try:
            if self._check_hp_interrupt_while_map_open():
                return

            img = self.capturer.capture()
            if img is None:
                return

            # Check normal map
            is_normal = self._has_template_in_fullscreen(img, self._normal_map_tpl, threshold=0.7)
            if not is_normal:
                self._log(f"[{label}] Not normal map, closing")
                self.root.after(0, status_label.config,
                                {"text": f"Not normal map {time.strftime('%H:%M:%S')}"})
                return

            # 2. Klik icon boss/zariche di panel kanan atas DULU
            self._log(f"[{label}] Klik icon {kind} ({icon_coords[0]},{icon_coords[1]})")
            self.clicker.click_scaled(icon_coords[0], icon_coords[1])
            time.sleep(2)

            if self._check_hp_interrupt_while_map_open():
                map_open = False  # HP interrupt sudah close map
                return

            # 3. Loop setiap area yang dipilih
            for area in areas:
                if self.stop_event.is_set():
                    break
                if self._check_hp_interrupt_while_map_open():
                    map_open = False
                    return

                img = self.capturer.capture()
                if img is None:
                    continue

                self._log(f"[{label}] Cari area: {area}")
                clicked = self._find_and_click_area(img, area)
                if not clicked:
                    self._log(f"[{label}] {area}: text tidak ditemukan")
                    continue
                self._log(f"[{label}] Klik area: {area}")
                time.sleep(2)

                if self._check_hp_interrupt_while_map_open():
                    map_open = False
                    return

                img = self.capturer.capture()
                if img is None:
                    continue

                # Cek apakah boss/zariche ada (template icon menyala)
                has_target = self._has_template_in_fullscreen(img, template, threshold=0.7)
                if not has_target:
                    self._log(f"[{label}] {area}: tidak ada {kind}")
                    continue

                # DITEMUKAN!
                self._log(f"[{label}] FOUND di {area}! Klik entry...")
                self.root.after(0, status_label.config, {"text": f"{label} @ {area}!"})

                self.clicker.click_scaled(MAP_BOSS_ENTRY_1280[0], MAP_BOSS_ENTRY_1280[1])
                time.sleep(2)

                if self._check_hp_interrupt_while_map_open():
                    map_open = False
                    return

                img = self.capturer.capture()
                if img is None:
                    break

                # Klik Teleport button (template match atau fallback koordinat)
                confirm_pos = self._get_confirm_position(img)
                if confirm_pos:
                    self._log(f"[{label}] Klik TP button (template)")
                    self.clicker.click(confirm_pos[0], confirm_pos[1])
                else:
                    # Fallback: klik langsung posisi tombol Teleport @1280x720
                    self._log(f"[{label}] Klik TP button (fallback 1098,533)")
                    self.clicker.click_scaled(1098, 533)
                time.sleep(2)

                # Confirm popup (Use Blessed Teleport Scroll)
                # Retry up to 3 times to find and click confirm
                for _confirm_try in range(3):
                    self.stop_event.wait(1)
                    img2 = self.capturer.capture()
                    if not img2:
                        continue
                    # Try template match first
                    confirm_pos = self._get_confirm_position(img2)
                    if confirm_pos:
                        self._log(f"[{label}] Confirm popup (template) → klik")
                        self.clicker.click(confirm_pos[0], confirm_pos[1])
                        time.sleep(2)
                        break
                    has_popup = self._has_template_in_fullscreen(
                        img2, self._confirm_dialog_tpl, threshold=0.5)
                    if has_popup:
                        self._log(f"[{label}] Confirm popup → klik Confirm")
                        self.clicker.click_scaled(740, 490)
                        time.sleep(2)
                        break
                    elif self._need_confirm(img2):
                        self.clicker.click_scaled(740, 490)
                        time.sleep(2)
                        break

                self._log(f"[{label}] Teleported ke {area}! {time.strftime('%H:%M:%S')}")
                self.root.after(0, status_label.config,
                                {"text": f"{label} @ {area} {time.strftime('%H:%M:%S')}"})
                map_open = False  # Teleport closes map
                self._wait_boss_dead_then_tp(settings, label=label)
                found = True
                break

            if not found:
                self._log(f"[{label}] Tidak ditemukan di semua area")
                self.root.after(0, status_label.config,
                                {"text": f"No {kind} {time.strftime('%H:%M:%S')}"})

        except Exception as e:
            self._log(f"[{label}] Error: {e}")
            traceback.print_exc()
        finally:
            # SELALU close map jika masih terbuka
            if map_open:
                self._log(f"[{label}] Closing map...")
                self._close_map()
            # Unblock combat escape
            self.isBlockedByMouseAction = False
            # Release feature lock (only if we acquired it)
            if not _skip_lock:
                self._release_feature()

    # ──────────────────────────────────────────────
    #  Daily tasks (bulk purchase, clan, daily claim)
    # ──────────────────────────────────────────────

    def _get_daily_cycle_id(self) -> str:
        """Get current daily cycle ID (resets at 6:00 AM)."""
        from datetime import datetime, timedelta
        now = datetime.now()
        six_am = now.replace(hour=6, minute=0, second=0, microsecond=0)
        if now < six_am:
            cycle_start = (now - timedelta(days=1)).date()
        else:
            cycle_start = now.date()
        return str(cycle_start)

    def _load_daily_state(self) -> dict:
        """Load daily task state from JSON."""
        import json
        state_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "daily_state.json")
        state_path = os.path.abspath(state_path)
        try:
            if os.path.exists(state_path):
                with open(state_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_daily_state(self, data: dict):
        """Save daily task state to JSON."""
        import json
        state_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "daily_state.json")
        state_path = os.path.abspath(state_path)
        try:
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _check_and_run_daily_tasks(self, settings: dict):
        """Run daily tasks (bulk purchase, clan attendance, daily claim).

        Original: tracks per-character per-cycle completion in daily_state.json.
        Each task runs once per day (cycle resets at 6:00 AM).
        """
        if not self.capturer or not self.key_sender or not self.clicker:
            return

        cycle_id = self._get_daily_cycle_id()
        character = self.target_title or "UNKNOWN"

        tasks = []
        if settings.get("auto_bulk_purchase"):
            tasks.append(("auto_bulk_purchase", self._run_auto_bulk_purchase))
        if settings.get("auto_clan_attendance"):
            tasks.append(("auto_clan_attendance", self._run_auto_clan_attendance))
        if settings.get("auto_daily_claim"):
            tasks.append(("auto_daily_claim", self._run_auto_daily_claim))

        if not tasks:
            return

        state = self._load_daily_state()
        char_state = state.setdefault(character, {})

        for task_name, runner in tasks:
            last_cycle = char_state.get(task_name, "")
            if last_cycle == cycle_id:
                continue  # Already done today

            self._log(f"[Daily] Running {task_name} for {character}")
            try:
                success = runner()
                if success:
                    char_state[task_name] = cycle_id
                    state[character] = char_state
                    self._save_daily_state(state)
                    self._log(f"[Daily] {task_name} completed!")
                    self.root.after(0, self.tab_daily.daily_status.config,
                                    {"text": f"{task_name} done {time.strftime('%H:%M:%S')}"})
                else:
                    self._log(f"[Daily] {task_name} returned False, will retry")
            except Exception as e:
                self._log(f"[Daily] {task_name} error: {e}")

    def _run_auto_bulk_purchase(self) -> bool:
        """Auto bulk purchase — original flow.

        1. Load dialog_bulk_trade.jpg + dialog_bulk_trade_available.jpg
        2. Press 'U' (open shop) → sleep 3s
        3. Click (480, 108) @1280 — bulk trade tab → sleep 0.5s
        4. Check remaining items → buy available rows
        5. Press 'ESC'
        """
        if self.stop_event.is_set():
            return False

        self._log("[BulkPurchase] Opening shop (U)...")
        self.key_sender.send("U")
        time.sleep(3)

        # Click bulk trade tab (480, 108) @1280x720
        self.clicker.click_scaled(480, 108)
        time.sleep(0.5)

        # Load templates
        trade_path = os.path.join("assets", "dialog_bulk_trade.jpg")
        avail_path = os.path.join("assets", "dialog_bulk_trade_available.jpg")
        if not os.path.exists(trade_path) or not os.path.exists(avail_path):
            self.key_sender.send("Escape")
            return False

        trade_tpl = load_image(trade_path)
        avail_tpl = load_image(avail_path)

        # Check if bulk trade dialog is open
        img = self.capturer.capture()
        if img is None:
            self.key_sender.send("Escape")
            return False

        # Check remaining (dialog_bulk_trade in region 23-37% x, 78-90% y)
        REMAINING_REGION = (0.234375, 0.7778, 0.375, 0.8972)
        w, h = img.size
        rx1, ry1, rx2, ry2 = denormalize(REMAINING_REGION, w, h)
        crop_bgr = cv2.cvtColor(np.array(img.crop((rx1, ry1, rx2, ry2))), cv2.COLOR_RGB2BGR)
        if not match_template(crop_bgr, trade_tpl[0], trade_tpl[1], threshold=0.3):
            self._log("[BulkPurchase] Dialog not open")
            self.key_sender.send("Escape")
            return False

        # Buy available rows — click (184, row_y) for available, (250, row_y) for buy
        # Row positions: approximately y=380 for first row @1280x720
        # Loop buying until no more available
        bought = False
        for attempt in range(10):
            if self.stop_event.is_set():
                break
            img = self.capturer.capture()
            if img is None:
                break

            # Check if available items exist
            AVAIL_REGION = (0.14375, 0.5278, 0.1953, 0.625)
            ax1, ay1, ax2, ay2 = denormalize(AVAIL_REGION, w, h)
            acrop = cv2.cvtColor(np.array(img.crop((ax1, ay1, ax2, ay2))), cv2.COLOR_RGB2BGR)
            if not match_template(acrop, avail_tpl[0], avail_tpl[1], threshold=0.3):
                break  # No more available

            # Click buy row
            self.clicker.click_scaled(250, 380)
            time.sleep(0.5)
            bought = True

        self.key_sender.send("Escape")
        time.sleep(0.5)
        return True

    def _run_auto_clan_attendance(self) -> bool:
        """Auto clan attendance — original flow.

        1. Press 'H' (open clan) → sleep 0.5s
        2. Click (355, 520) @1280 → sleep 0.5s
        3. Click (700, 660) @1280 → sleep 1s
        4. Click (300, 570) @1280 → sleep 0.5s
        5. Press 'ESC'
        """
        if self.stop_event.is_set():
            return False

        self._log("[ClanAttendance] Opening clan (H)...")
        self.key_sender.send("H")
        time.sleep(0.5)

        self.clicker.click_scaled(355, 520)
        time.sleep(0.5)

        self.clicker.click_scaled(700, 660)
        time.sleep(1)

        self.clicker.click_scaled(300, 570)
        time.sleep(0.5)

        self.key_sender.send("Escape")
        time.sleep(0.5)
        return True

    def _run_auto_daily_claim(self) -> bool:
        """Auto daily claim — original flow.

        1. Press ';' → sleep 0.5s
        2. Click (970, 380) @1280 → sleep 0.5s
        3. Press 'ESC'
        """
        if self.stop_event.is_set():
            return False

        self._log("[DailyClaim] Opening daily (;)...")
        self.key_sender.send(";")
        time.sleep(0.5)

        self.clicker.click_scaled(970, 380)
        time.sleep(0.5)

        self.key_sender.send("Escape")
        time.sleep(0.5)
        return True

    # ──────────────────────────────────────────────
    #  Auto Buy Potion
    # ──────────────────────────────────────────────

    def _read_quickslot_potion(self, img) -> int:
        """Read potion count from quickslot area (large numbers next to icons).

        The quickslot shows items with count like "1374" in white text.
        Searches bottom 15% of screen, left 55%.
        Finds potion icon, then reads number to the RIGHT of it.
        """
        w, h = img.size

        # Quickslot area: bottom 15%, x: 15-55%
        qs_y1 = int(h * 0.85)
        qs_x1 = int(w * 0.15)
        qs_x2 = int(w * 0.55)
        qs_crop = img.crop((qs_x1, qs_y1, qs_x2, h))
        qs_bgr = cv2.cvtColor(np.array(qs_crop), cv2.COLOR_RGB2BGR)
        qs_h, qs_w = qs_bgr.shape[:2]

        # Find potion icon in quickslot
        if not hasattr(self, '_potion_icon_tpl') or self._potion_icon_tpl is None:
            return -1

        tpl_bgr, tpl_mask = self._potion_icon_tpl
        th, tw = tpl_bgr.shape[:2]
        scale = h / 720.0
        if abs(scale - 1.0) > 0.05:
            nw = max(1, int(tw * scale))
            nh = max(1, int(th * scale))
            s_tpl = cv2.resize(tpl_bgr, (nw, nh))
            s_mask = cv2.resize(tpl_mask, (nw, nh)) if tpl_mask is not None else None
        else:
            s_tpl = tpl_bgr
            s_mask = tpl_mask
            nw, nh = tw, th

        if nh > qs_h or nw > qs_w:
            return -1

        result = cv2.matchTemplate(qs_bgr, s_tpl, cv2.TM_CCORR_NORMED, mask=s_mask)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val < 0.60:
            return -1

        # Found icon — number is to the RIGHT of icon
        icon_right_x = max_loc[0] + nw
        num_x1 = icon_right_x + 2
        num_x2 = min(qs_w, icon_right_x + int(nw * 1.5))
        num_y1 = max_loc[1] + int(nh * 0.3)
        num_y2 = max_loc[1] + nh

        if num_x2 <= num_x1 or num_y2 <= num_y1:
            return -1

        num_crop = qs_crop.crop((num_x1, num_y1, num_x2, num_y2))
        arr = np.array(num_crop)
        if arr.size == 0:
            return -1

        # OCR the number — white text on dark background
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        crop_h, crop_w = thresh.shape[:2]
        boxes = [(x, y, bw, bh) for x, y, bw, bh in
                 [cv2.boundingRect(c) for c in contours]
                 if bh > crop_h * 0.25 and bw >= 2]
        boxes.sort(key=lambda b: b[0])

        if not boxes:
            return -1

        # Merge overlapping
        merged = []
        for box in boxes:
            if merged and box[0] < merged[-1][0] + merged[-1][2] + 1:
                px, py, pw, ph = merged[-1]
                merged[-1] = (min(px, box[0]), min(py, box[1]),
                              max(px+pw, box[0]+box[2]) - min(px, box[0]),
                              max(py+ph, box[1]+box[3]) - min(py, box[1]))
            else:
                merged.append(box)

        digits = []
        for bx, by, bw, bh in merged:
            d, conf = self._recognize_digit_with_confidence(thresh[by:by+bh, bx:bx+bw])
            if conf < 2.0:
                return -1  # Low confidence, unreliable
            digits.append(str(d))

        if not digits:
            return -1

        self._last_potion_digit_count = len(digits)
        number_str = "".join(digits)
        try:
            result_val = int(number_str)
        except ValueError:
            return -1

        self._log(f"[Potion] Quickslot OCR: '{number_str}' = {result_val} "
                  f"(score={max_val:.2f}, {len(digits)} digits)")
        return result_val

    def _find_potion_icon(self, img):
        """Find potion icon on screen via template matching with potion_icon.png.

        Resolution-aware: scales template and search area based on actual game size.
        Template potion_icon.png was captured at 1280x720.

        Returns (match_x, match_y, full_tw, full_th) or None.
        """
        if not hasattr(self, '_potion_icon_tpl'):
            self._potion_icon_tpl = None
            self._potion_full_th = 0
            self._potion_full_tw = 0
            path = os.path.join("assets", "potion_icon.png")
            if os.path.exists(path):
                data = load_image(path)
                if data is not None:
                    tpl_bgr, tpl_mask = data
                    self._potion_full_th, self._potion_full_tw = tpl_bgr.shape[:2]
                    icon_mask = np.zeros(tpl_bgr.shape[:2], dtype=np.uint8)
                    cut_h = int(tpl_bgr.shape[0] * 0.60)
                    icon_mask[:cut_h, :] = 255
                    icon_mask_3ch = cv2.merge([icon_mask, icon_mask, icon_mask])
                    self._potion_icon_tpl = (tpl_bgr, icon_mask_3ch)

        if self._potion_icon_tpl is None:
            return None

        tpl_bgr, tpl_mask = self._potion_icon_tpl
        w, h = img.size
        img_bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        # Search hotbar area — normalized percentages (works at any resolution)
        search_y = int(h * 0.73)
        search_x1 = int(w * 0.20)
        search_x2 = int(w * 0.80)
        search_img = img_bgr[search_y:, search_x1:search_x2]
        sh, sw = search_img.shape[:2]

        # Scale template to match current resolution
        # Template was captured at ~1280x720, scale proportionally
        scale = h / 720.0
        th, tw = tpl_bgr.shape[:2]
        nw = max(1, int(tw * scale))
        nh = max(1, int(th * scale))
        if nw < sw and nh < sh:
            s_tpl = cv2.resize(tpl_bgr, (nw, nh))
            s_mask = cv2.resize(tpl_mask, (nw, nh))
        else:
            s_tpl = tpl_bgr
            s_mask = tpl_mask
            nw, nh = tw, th

        if nh > sh or nw > sw:
            return None

        # Try multiple scales if primary doesn't match (resolution might differ)
        best_val = 0
        best_loc = None
        best_tw = nw
        best_th = nh

        for scale_adj in [1.0, 0.9, 1.1, 0.8, 1.2]:
            adj_w = max(1, int(nw * scale_adj))
            adj_h = max(1, int(nh * scale_adj))
            if adj_w >= sw or adj_h >= sh:
                continue
            adj_tpl = cv2.resize(tpl_bgr, (adj_w, adj_h))
            adj_mask = cv2.resize(tpl_mask, (adj_w, adj_h))

            result = cv2.matchTemplate(search_img, adj_tpl, cv2.TM_CCORR_NORMED, mask=adj_mask)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val > best_val:
                best_val = max_val
                best_loc = max_loc
                best_tw = adj_w
                best_th = adj_h
            if max_val >= 0.85:
                break  # Good enough

        if best_val >= 0.75 and best_loc is not None:
            match_x = search_x1 + best_loc[0]
            match_y = search_y + best_loc[1]
            self._log(f"[Potion] Icon found (score={best_val:.2f}) at ({match_x},{match_y})")
            return (match_x, match_y, best_tw, best_th)

        # Debug when not found
        if not hasattr(self, '_potion_find_debug'):
            self._potion_find_debug = 0
        if self._potion_find_debug < 3:
            self._potion_find_debug += 1
            try:
                debug_dir = _get_debug_dir()
                from PIL import Image, ImageDraw
                debug_img = img.copy()
                draw = ImageDraw.Draw(debug_img)
                bx = search_x1 + max_loc[0]
                by = search_y + max_loc[1]
                draw.rectangle([bx, by, bx + tw, by + th], outline="yellow", width=2)
                # Search area boundary (blue)
                draw.rectangle([search_x1, search_y, search_x2, h], outline="blue", width=1)
                debug_img.save(os.path.join(debug_dir, f"potion_find_fail_{self._potion_find_debug}.png"))
                self._log(f"[Potion] Debug: best at ({bx},{by}) score={max_val:.2f}")
            except Exception:
                pass

        self._log(f"[Potion] Icon NOT found (best score={max_val:.2f})")
        return None

    def _read_potion_count(self, img) -> int:
        """Read potion count from quickslot area (bottom of screen).

        Two methods:
        1. Find potion icon in quickslot area, read number to the RIGHT
        2. Fallback: find in hotbar, read number below

        Returns number or -1 if cannot read.
        """
        self._last_potion_digit_count = 0
        w, h = img.size

        # Find potion icon in hotbar, read number with Tesseract
        icon_pos = self._find_potion_icon(img)
        if icon_pos is None:
            return -1

        match_x, match_y, tw, th = icon_pos

        # Full template = icon (top 60%) + number (bottom 40%)
        center_x = match_x + tw // 2
        half_crop_w = int(tw * 0.35)
        num_y1 = match_y + int(th * 0.60)
        num_y2 = min(h, match_y + th + 4)
        num_x1 = max(0, center_x - half_crop_w)
        num_x2 = min(w, center_x + half_crop_w)

        crop = img.crop((num_x1, num_y1, num_x2, num_y2))
        arr = np.array(crop)

        # Try Tesseract OCR first (much more accurate)
        try:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            arr_bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            ch, cw = arr_bgr.shape[:2]
            big = cv2.resize(arr_bgr, (cw*3, ch*3), interpolation=cv2.INTER_CUBIC)
            gray = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)
            _, tess_thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
            config = '--psm 7 -c tessedit_char_whitelist=0123456789'
            tess_result = pytesseract.image_to_string(tess_thresh, config=config).strip()
            if tess_result and tess_result.isdigit():
                val = int(tess_result)
                self._last_potion_digit_count = len(tess_result)
                self._log(f"[Potion] Tesseract: '{tess_result}' = {val} "
                          f"crop={num_x2-num_x1}x{num_y2-num_y1}px")
                return val
        except Exception:
            pass  # Tesseract not available, fallback to bitmap OCR

        # Fallback: bitmap OCR
        max_channel = np.max(arr, axis=2)
        _, thresh = cv2.threshold(max_channel, 200, 255, cv2.THRESH_BINARY)

        # Debug: save first 10 times (persistent dir, survives exe restart)
        if not hasattr(self, '_potion_debug_count'):
            self._potion_debug_count = 0
        if self._potion_debug_count < 10:
            self._potion_debug_count += 1
            try:
                debug_dir = _get_debug_dir()
                crop.save(os.path.join(debug_dir, f"potion_crop_{self._potion_debug_count}.png"))
                from PIL import Image, ImageDraw
                Image.fromarray(thresh).save(os.path.join(debug_dir, f"potion_thresh_{self._potion_debug_count}.png"))
                debug_full = img.copy()
                draw = ImageDraw.Draw(debug_full)
                # Icon match area (green) — top 60% where mask is active
                draw.rectangle([match_x, match_y, match_x + tw, match_y + int(th * 0.60)],
                               outline="green", width=2)
                # Number crop area (red)
                draw.rectangle([num_x1, num_y1, num_x2, num_y2],
                               outline="red", width=3)
                debug_full.save(os.path.join(debug_dir, f"potion_fullscreen_{self._potion_debug_count}.png"))
                self._log(f"[Potion] Debug saved: debug/potion_fullscreen_{self._potion_debug_count}.png")
            except Exception:
                pass

        # Find contours (each digit)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return -1

        crop_h, crop_w = thresh.shape[:2]
        boxes = []
        for cnt in contours:
            bx, by, bw, bh = cv2.boundingRect(cnt)
            if bh > crop_h * 0.20 and bw >= 1:
                boxes.append((bx, by, bw, bh))
        boxes.sort(key=lambda b: b[0])

        # Merge overlapping/adjacent boxes (same digit split into 2 contours)
        merged = []
        for box in boxes:
            if merged and box[0] < merged[-1][0] + merged[-1][2] + 1:
                px, py, pw, ph = merged[-1]
                nx = min(px, box[0])
                ny = min(py, box[1])
                nx2 = max(px + pw, box[0] + box[2])
                ny2 = max(py + ph, box[1] + box[3])
                merged[-1] = (nx, ny, nx2 - nx, ny2 - ny)
            else:
                merged.append(box)

        # Split wide boxes (w/h > 1.0 = likely two merged digits)
        final_boxes = []
        for bx, by, bw, bh in merged:
            if bw > 0 and bh > 0 and bw / bh > 1.0 and bw > 10:
                # Split into two halves
                half = bw // 2
                final_boxes.append((bx, by, half, bh))
                final_boxes.append((bx + half, by, bw - half, bh))
            else:
                final_boxes.append((bx, by, bw, bh))
        boxes = final_boxes

        if not boxes:
            return -1

        # OCR each digit with per-digit validation
        # Skip boxes at x=0..2 (left edge phantom from icon border)
        digits = []
        box_info = []
        digit_confidences = []
        for bx, by, bw, bh in boxes:
            if bw < 1 or bh < 2:
                continue
            if bx < 3 and bw < crop_w * 0.25:
                box_info.append(f"SKIP({bw}x{bh}@x{bx})")
                continue
            d, confidence = self._recognize_digit_with_confidence(thresh[by:by+bh, bx:bx+bw])
            digits.append(str(d))
            digit_confidences.append(confidence)
            box_info.append(f"{d}({bw}x{bh}c={confidence:.1f})")

        # Reject if any digit has very low confidence (< 3.0)
        if digit_confidences and min(digit_confidences) < 2.0:
            self._last_potion_digit_count = len(digits)
            self._log(f"[Potion] Low confidence digit: {', '.join(box_info)} → retry")
            return -1

        # Check for missing leading "1": if first digit box starts at x>8
        # AND first recognized digit is not already "1", a dim "1" was likely missed.
        if (boxes and boxes[0][0] > 8 and len(digits) >= 2
                and digits[0] != '1'):
            gap = max_channel[:, :boxes[0][0]]
            if np.max(gap) > 150:
                digits.insert(0, '1')
                box_info.insert(0, '1(dim)')

        number_str = "".join(digits)
        try:
            result = int(number_str)
        except ValueError:
            result = -1

        # Sanity checks for OCR result
        # Max potion stack in L2M SEA is ~2000
        if result > 5000 and len(digits) > 1:
            # Likely phantom digit from icon edge — try stripping first digit
            stripped = "".join(digits[1:])
            stripped_val = int(stripped) if stripped else -1
            if 0 < stripped_val <= 2500:
                self._log(f"[Potion] OCR: '{number_str}'->'{stripped}' = {stripped_val} "
                          f"(phantom fix) [{len(boxes)} boxes: {', '.join(box_info)}]")
                return stripped_val
            # Try stripping last digit too
            stripped2 = "".join(digits[:-1])
            stripped2_val = int(stripped2) if stripped2 else -1
            if 0 < stripped2_val <= 2500:
                self._log(f"[Potion] OCR: '{number_str}'->'{stripped2}' = {stripped2_val} "
                          f"(tail phantom fix)")
                return stripped2_val

        # If result is 0 but we found boxes — OCR failed, return -1 to retry
        if result == 0 and len(boxes) >= 2:
            self._log(f"[Potion] OCR got 0 but {len(boxes)} boxes found — unreliable, retry")
            return -1

        # Store digit count for reliability check
        self._last_potion_digit_count = len(digits)

        self._log(f"[Potion] OCR: '{number_str}' = {result} "
                  f"[{len(boxes)} boxes: {', '.join(box_info)}] "
                  f"crop={num_x2-num_x1}x{num_y2-num_y1}px")
        return result

    # 5x7 reference bitmaps for digits 0-9 (1=white, 0=black)
    # Multiple variants per digit for better matching across fonts
    _DIGIT_REFS = None

    @classmethod
    def _get_digit_refs(cls):
        if cls._DIGIT_REFS is not None:
            return cls._DIGIT_REFS
        # Standard font + L2M game font variants
        # Each digit can have multiple reference bitmaps
        variants = {
            0: [["01110","10001","10001","10001","10001","10001","01110"],
                ["01110","11011","10001","10001","10001","11011","01110"],
                ["01110","10001","10011","10001","11001","10001","01110"]],
            1: [["00100","01100","00100","00100","00100","00100","01110"],
                ["00010","01110","00010","00010","00010","00010","00010"],
                ["00011","11011","00001","00001","00001","00001","00011"]],
            2: [["01110","10001","00001","00110","01000","10000","11111"],
                ["01110","10011","00001","00110","01110","11100","11111"]],
            3: [["01110","10001","00001","00110","00001","10001","01110"],
                ["01110","00011","00011","00110","00001","10011","01110"]],
            4: [["00110","01010","10010","11111","00010","00010","00010"],
                ["00110","00110","01100","10000","11111","00111","00000"]],
            5: [["11111","10000","11110","00001","00001","10001","01110"]],
            6: [["00110","01000","10000","11110","10001","10001","01110"]],
            7: [["11111","00001","00010","00100","01000","01000","01000"]],
            8: [["01110","10001","10001","01110","10001","10001","01110"],
                ["01110","10011","11011","01110","10001","10001","01110"]],
            9: [["01110","10001","10001","01111","00001","00010","01100"],
                ["01110","10001","10001","01111","00001","00001","01110"]],
        }
        cls._DIGIT_REFS = {}
        for d, var_list in variants.items():
            bitmaps = []
            for rows in var_list:
                bitmap = np.array([[int(c) for c in row] for row in rows], dtype=np.float32)
                bitmaps.append(bitmap)
            cls._DIGIT_REFS[d] = bitmaps
        return cls._DIGIT_REFS

    @classmethod
    def _recognize_digit(cls, digit_img) -> int:
        """Recognize a digit using quadrant fill analysis + bitmap correlation.
        Two-stage: feature filter narrows candidates, then bitmap picks winner."""
        h, w = digit_img.shape
        if h < 2 or w < 1:
            return 0

        # Very thin = "1"
        if w / h < 0.45:
            return 1

        # Very wide and short = noise
        if w / h > 2.0:
            return 0

        # Stage 1: Compute quadrant fill features
        total = np.sum(digit_img > 0)
        area = h * w
        fill = total / area if area > 0 else 0
        mh, mw = h // 2, w // 2
        tl = np.sum(digit_img[:mh, :mw] > 0) / max(1, mh * mw)
        tr = np.sum(digit_img[:mh, mw:] > 0) / max(1, mh * (w - mw))
        bl = np.sum(digit_img[mh:, :mw] > 0) / max(1, (h - mh) * mw)
        br = np.sum(digit_img[mh:, mw:] > 0) / max(1, (h - mh) * (w - mw))
        ch = h // 3
        center = np.sum(digit_img[ch:2*ch, :] > 0) / max(1, ch * w)

        # Bitmap correlation only (feature shortcuts disabled — caused errors on split digits)
        resized = cv2.resize(digit_img, (5, 7), interpolation=cv2.INTER_AREA)
        norm = resized.astype(np.float32) / 255.0

        refs = cls._get_digit_refs()
        best_d, best_score = 0, -999
        for d, bitmaps in refs.items():
            for ref in bitmaps:
                score = np.sum(norm * ref) - np.sum(norm * (1 - ref)) * 0.5
                if score > best_score:
                    best_score = score
                    best_d = d

        return best_d

    @classmethod
    def _recognize_digit_with_confidence(cls, digit_img) -> tuple:
        """Recognize digit and return (digit, confidence_score).
        Higher confidence = more reliable recognition."""
        h, w = digit_img.shape
        if h < 2 or w < 1:
            return (0, 0.0)
        if w / h < 0.45:
            return (1, 10.0)  # Very thin = definitely "1", high confidence
        if w / h > 2.0:
            return (0, 0.0)  # Noise

        total = np.sum(digit_img > 0)
        area = h * w
        fill = total / area if area > 0 else 0
        mh, mw = h // 2, w // 2
        tl = np.sum(digit_img[:mh, :mw] > 0) / max(1, mh * mw)
        tr = np.sum(digit_img[:mh, mw:] > 0) / max(1, mh * (w - mw))
        bl = np.sum(digit_img[mh:, :mw] > 0) / max(1, (h - mh) * mw)
        br = np.sum(digit_img[mh:, mw:] > 0) / max(1, (h - mh) * (w - mw))
        ch = h // 3
        center = np.sum(digit_img[ch:2*ch, :] > 0) / max(1, ch * w)

        # Bitmap correlation with confidence (feature shortcuts disabled)
        resized = cv2.resize(digit_img, (5, 7), interpolation=cv2.INTER_AREA)
        norm = resized.astype(np.float32) / 255.0
        refs = cls._get_digit_refs()
        best_d, best_score = 0, -999
        for d, bitmaps in refs.items():
            for ref in bitmaps:
                score = np.sum(norm * ref) - np.sum(norm * (1 - ref)) * 0.5
                if score > best_score:
                    best_score = score
                    best_d = d

        return (best_d, best_score)

    def _check_auto_potion(self, settings: dict, now: float):
        """Check potion count and auto-buy if below threshold.

        Flow:
        1. Read potion count from hotbar (OCR)
        2. If below threshold 2x consecutive → TP to town
        3. Click "General Merchant" from NPC list
        4. Wait for shop → click "Auto-Trade" → "Confirm"
        5. TP back to farm
        """
        if not settings.get("auto_potion_enabled"):
            return
        if not self.capturer or not self.key_sender or not self.clicker:
            return

        # Skip if another feature is active (combat escape, boss check, etc.)
        if self._is_feature_busy():
            return

        # Interval check
        interval_sec = settings.get("potion_check_interval", 5) * 60
        last_check = getattr(self, '_potion_last_check', 0)
        if (now - last_check) < interval_sec:
            return
        self._potion_last_check = now

        # Read potion count — capture fresh image
        img = self.capturer.capture()
        if img is None:
            return

        threshold = settings.get("potion_threshold", 100)

        count = self._read_potion_count(img)
        digit_count = getattr(self, '_last_potion_digit_count', 0)
        self._log(f"[Potion] Count: {count} digits={digit_count} (threshold: {threshold})")

        # Update status display
        self.root.after(0, self.tab_farming.potion_status.config,
                        {"text": f"Potion: ~{count}" if count > 0 else "Potion: ?"})

        if count < 0:
            self._potion_last_check = now - interval_sec + 5
            return

        # Use DIGIT COUNT as primary check (more reliable than OCR value)
        # 4 digits = 1000-9999 → definitely OK
        # 3 digits = 100-999 → check OCR value against threshold
        # 1-2 digits = 0-99 → likely LOW (but could be OCR error)
        if digit_count >= 4:
            # 4 digits = definitely above any reasonable threshold
            self._potion_low_count = 0
            return
        if digit_count == 3 and count >= threshold:
            self._potion_low_count = 0
            return
        if count >= threshold:
            self._potion_low_count = 0
            return

        # Count appears low — require 3 consecutive low reads (was 2)
        if not hasattr(self, '_potion_low_count'):
            self._potion_low_count = 0
        self._potion_low_count += 1

        if self._potion_low_count < 3:
            self._log(f"[Potion] Low read #{self._potion_low_count}/3, rechecking in 10s...")
            self._potion_last_check = now - interval_sec + 10
            return

        # Confirmed low — double-check with HIGH SCORE reads only
        confirm_ok = False
        for retry in range(5):
            time.sleep(1)
            img2 = self.capturer.capture()
            if img2 is None:
                continue
            count2 = self._read_potion_count(img2)
            self._log(f"[Potion] Confirm read #{retry+1}: {count2}")
            if count2 >= threshold:
                self._log("[Potion] False alarm — confirm read above threshold")
                self._potion_low_count = 0
                return
            if count2 >= 0:
                # Got a valid reading that's still below threshold
                confirm_ok = True
                break
            # count2 == -1: icon blocked, retry

        if not confirm_ok:
            self._log("[Potion] Could not confirm — icon blocked, will retry later")
            self._potion_last_check = now - interval_sec + 15
            return

        self._potion_low_count = 0

        # Potion low! Buy sequence
        self._log(f"[Potion] LOW! ~{count} < {threshold} → TP ke town + buy")
        self.root.after(0, self.tab_farming.potion_status.config,
                        {"text": f"Potion LOW: ~{count} → buying..."})

        self._auto_buy_potion(settings)

    def _auto_buy_potion(self, settings: dict):
        """TP to town, buy potion from General Merchant, TP back.

        Flow:
        1. TP to town (potion_tp_key or fallback combat_escape_teleport_key)
        2. Wait loading
        3. Click "General Merchant" from NPC list (template match)
        4. Wait for shop open (verify icon_inventory.png template)
        5. Click "Auto-Trade" → "Confirm"
        6. Close shop (Escape)
        7. TP back to farm
        """
        if not self.capturer or not self.key_sender or not self.clicker:
            return

        # Acquire feature lock — blocks weapon switch, boss check, etc.
        if not self._acquire_feature("auto_buy_potion", timeout=3.0):
            self._log(f"[Potion] Cannot start buy — {self._feature_active} running")
            return

        # Block ALL other features during entire buy flow
        self.isBlockedByMouseAction = True
        self._potion_buy_active = True
        try:
            # 1. TP to town — use dedicated potion TP key, fallback to combat escape key
            tp_key = settings.get("potion_tp_key", "")
            if not tp_key:
                ce_settings = self.tab_farming.collect_settings()
                tp_key = ce_settings.get("combat_escape_teleport_key", "")
            if tp_key:
                self._log("[Potion] TP ke town...")
                self.key_sender.send(tp_key)
                time.sleep(8)  # Loading
            else:
                self._log("[Potion] No TP key configured! Set 'Key TP ke town' di Auto Buy Potion")
                return

            # 2. Wait for NPC list to appear, find and click General Merchant
            # The NPC list appears on left side (x: 0-40%, y: 5-50%)
            # Scale template to current resolution for accurate matching
            # 2. Find General Merchant — abort immediately if not found
            shop_opened = False
            self._log("[Potion] Cari General Merchant...")
            time.sleep(3)  # Wait for NPC list to load

            # Only use general_merchant_btn.png (194x48, reliable text template)
            # Narrow region to NPC list only (left 20%, y 15-55%)
            # to avoid matching skill icons at top
            gm_pos = self._find_general_merchant(timeout=15)

            if gm_pos is None:
                self._log("[Potion] General Merchant not found! Abort — biarkan TP handle.")
                return

            self._log(f"[Potion] Klik General Merchant at ({gm_pos[0]},{gm_pos[1]})...")
            self.clicker.click(gm_pos[0], gm_pos[1])

            # Wait for character to walk to merchant
            self._log("[Potion] Tunggu karakter jalan ke merchant...")
            time.sleep(4)

            # Verify shop opened (inventory tabs visible)
            self._log("[Potion] Tunggu shop terbuka...")
            inv_pos = self._wait_for_template_in_region(
                "icon_inventory.png", timeout=8,
                region_y_min=0.05, region_y_max=0.30,
                region_x_min=0.60, region_x_max=1.0
            )
            if inv_pos is not None:
                shop_opened = True
                self._log("[Potion] Shop terbuka!")

            if not shop_opened:
                self._log("[Potion] Shop tidak terbuka! Abort — biarkan TP handle.")
                return

            self._log("[Potion] Shop terbuka!")
            time.sleep(1)

            # Find Auto-Trade button in bottom-right
            at_pos = self._wait_for_template_in_region(
                "auto_trade_btn.png", timeout=5,
                region_y_min=0.70, region_y_max=1.0,
                region_x_min=0.70, region_x_max=1.0
            )
            if at_pos is None:
                self._log("[Potion] Auto-Trade btn not found! Close shop + abort.")
                # Close shop via close button (not Escape which may do other things)
                close_pos = self._wait_for_template_in_region(
                    "close.jpg", timeout=3, threshold=0.6,
                    region_y_min=0.0, region_y_max=0.20,
                    region_x_min=0.50, region_x_max=1.0
                )
                if close_pos:
                    self.clicker.click(close_pos[0], close_pos[1])
                else:
                    self.key_sender.send("Escape")
                time.sleep(0.5)
                return

            # 4. Click Auto-Trade button
            self._log("[Potion] Klik Auto-Trade...")
            self.clicker.click(at_pos[0], at_pos[1])
            time.sleep(2)

            # 5. Click Confirm in shop (orange button next to Auto-Trade)
            self._log("[Potion] Cari Confirm di shop...")
            cf_pos = self._wait_for_template_in_region(
                "confirm_trade_btn.png", timeout=5,
                region_y_min=0.70, region_y_max=1.0,
                region_x_min=0.60, region_x_max=1.0
            )
            if cf_pos is not None:
                # Template shows "-Trade | Confirm" — click RIGHT portion (Confirm)
                self._log("[Potion] Klik Confirm di shop...")
                self.clicker.click(cf_pos[0] + 40, cf_pos[1])
                time.sleep(2)
            else:
                self._log("[Potion] Confirm shop not found!")
                return

            # 6. Wait for confirm DIALOG popup, click Confirm in dialog
            self._log("[Potion] Tunggu confirm dialog...")
            dlg_pos = self._wait_for_template_in_region(
                "confirm_diaglog.jpg", timeout=5,
                region_y_min=0.30, region_y_max=0.80,
                region_x_min=0.25, region_x_max=0.80
            )
            if dlg_pos is not None:
                # Template shows "Cancel | Confirm" — click RIGHT portion (Confirm)
                self._log("[Potion] Klik Confirm di dialog...")
                self.clicker.click(dlg_pos[0] + 40, dlg_pos[1])
                time.sleep(3)
            else:
                self._log("[Potion] Confirm dialog not found, lanjut...")

            # 7. Close shop — click close.jpg button (top-right of shop)
            self._log("[Potion] Tutup shop...")
            close_pos = self._wait_for_template_in_region(
                "close.jpg", timeout=5, threshold=0.6,
                region_y_min=0.0, region_y_max=0.20,
                region_x_min=0.50, region_x_max=1.0
            )
            if close_pos is None:
                # Try close_640.jpg as fallback
                close_pos = self._wait_for_template_in_region(
                    "close_640.jpg", timeout=3, threshold=0.6,
                    region_y_min=0.0, region_y_max=0.20,
                    region_x_min=0.50, region_x_max=1.0
                )
            if close_pos is not None:
                self._log(f"[Potion] Close button found, klik...")
                self.clicker.click(close_pos[0], close_pos[1])
                time.sleep(1)
            else:
                # Fallback: Escape sekali untuk tutup shop
                self._log("[Potion] Close button not found, fallback Escape...")
                self.key_sender.send("Escape")
                time.sleep(1)

            self._log("[Potion] Beli selesai!")
            self.root.after(0, self.tab_farming.potion_status.config,
                            {"text": f"Potion bought {time.strftime('%H:%M:%S')}"})

        finally:
            self.isBlockedByMouseAction = False
            self._potion_buy_active = False
            self._release_feature()
            # Always set town state after TP — even on abort
            # This ensures TP-back-to-farm kicks in
            self.is_in_town = True
            self.last_in_town_time = time.time()
            self._escaped_to_town_at = time.time()
            self.do_auto_hunt = True
            self._potion_low_count = 0
            self._potion_last_check = time.time()
            self._log("[Potion] Di kota — tunggu teleport otomatis ke farm...")

    def _find_general_merchant(self, timeout: int = 8):
        """Find General Merchant in NPC list using Tesseract OCR.

        Reads text from NPC list region, finds "General" + "Merchant" words
        on the same line, returns click position. More reliable than template
        matching which kept clicking wrong NPCs.
        """
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

        start = time.time()
        attempt = 0
        while (time.time() - start) < timeout:
            time.sleep(1.5)
            attempt += 1
            img = self.capturer.capture()
            if img is None:
                continue

            w, h = img.size
            # NPC list: left side, below HP bar
            rx1 = 0
            ry1 = int(h * 0.12)
            rx2 = int(w * 0.25)
            ry2 = int(h * 0.55)
            npc_crop = img.crop((rx1, ry1, rx2, ry2))

            try:
                # Preprocess: threshold to make white text on dark bg clearer
                gray = cv2.cvtColor(np.array(npc_crop), cv2.COLOR_RGB2GRAY)
                _, thresh = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY)
                from PIL import Image as PILImage
                thresh_pil = PILImage.fromarray(thresh)
                data = pytesseract.image_to_data(thresh_pil, output_type=pytesseract.Output.DICT)
                # Debug: log what OCR reads
                words = [data['text'][i].strip() for i in range(len(data['text']))
                         if data['text'][i].strip() and int(data['conf'][i]) > 30]
                self._log(f"[Potion] OCR attempt {attempt}: {words[:8]}")
            except Exception as e:
                self._log(f"[Potion] OCR error: {e}")
                continue

            # Find "General" + "Merchant" on the same line (close Y)
            general_pos = None
            merchant_pos = None
            for i, text in enumerate(data['text']):
                t = text.strip().lower()
                if not t or int(data['conf'][i]) < 30:
                    continue
                if 'general' in t or 'neral' in t:
                    general_pos = (data['left'][i], data['top'][i],
                                   data['width'][i], data['height'][i])
                # "Merchant" right after "General" on same line
                if 'merchant' in t and general_pos is not None:
                    my = data['top'][i]
                    gy = general_pos[1]
                    if abs(my - gy) < 20:
                        merchant_pos = (data['left'][i], data['top'][i],
                                        data['width'][i], data['height'][i])
                        break
                    else:
                        general_pos = None  # Different line — skip

            if general_pos and merchant_pos:
                # Click center of "General Merchant" text span
                x1 = general_pos[0]
                y1 = min(general_pos[1], merchant_pos[1])
                x2 = merchant_pos[0] + merchant_pos[2]
                y2 = max(general_pos[1] + general_pos[3],
                         merchant_pos[1] + merchant_pos[3])
                cx = rx1 + (x1 + x2) // 2
                cy = ry1 + (y1 + y2) // 2
                self._log(f"[Potion] General Merchant found (OCR) at ({cx},{cy})")
                return (cx, cy)

        return None

    def _wait_for_template_in_region(self, template_name: str, timeout: int = 15,
                                        threshold: float = 0.7,
                                        region_y_min: float = 0.0, region_y_max: float = 1.0,
                                        region_x_min: float = 0.0, region_x_max: float = 1.0):
        """Wait until template is visible in a specific screen region.

        Region is specified as fractions (0.0-1.0) of screen width/height.
        Returns (cx, cy) in FULL screen coordinates, or None if timeout.
        """
        tpl_path = os.path.join("assets", template_name)
        if not os.path.exists(tpl_path):
            self._log(f"[Potion] Template {template_name} not found")
            return None

        tpl_data = load_image(tpl_path)
        if tpl_data is None:
            return None

        tpl_bgr, tpl_mask = tpl_data
        start = time.time()
        while (time.time() - start) < timeout:
            time.sleep(1)
            img = self.capturer.capture()
            if img is None:
                continue

            w, h = img.size
            img_bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

            # Crop to search region
            ry1 = int(h * region_y_min)
            ry2 = int(h * region_y_max)
            rx1 = int(w * region_x_min)
            rx2 = int(w * region_x_max)
            search_img = img_bgr[ry1:ry2, rx1:rx2]
            sh, sw = search_img.shape[:2]

            # Multi-scale template matching (adapts to any resolution)
            base_scale = h / 720.0
            th_orig, tw_orig = tpl_bgr.shape[:2]
            best_val = 0
            best_loc = None
            best_tw = tw_orig
            best_th = th_orig

            for scale_adj in [1.0, 0.9, 1.1, 0.85, 1.15]:
                s = base_scale * scale_adj
                nw = max(1, int(tw_orig * s))
                nh = max(1, int(th_orig * s))
                if nw >= sw or nh >= sh:
                    continue
                adj_tpl = cv2.resize(tpl_bgr, (nw, nh))
                adj_mask = cv2.resize(tpl_mask, (nw, nh)) if tpl_mask is not None else None

                if adj_mask is not None:
                    result = cv2.matchTemplate(search_img, adj_tpl, cv2.TM_CCORR_NORMED, mask=adj_mask)
                else:
                    result = cv2.matchTemplate(search_img, adj_tpl, cv2.TM_CCOEFF_NORMED)
                _, max_val_s, _, max_loc_s = cv2.minMaxLoc(result)

                if max_val_s > best_val:
                    best_val = max_val_s
                    best_loc = max_loc_s
                    best_tw = nw
                    best_th = nh
                if max_val_s >= 0.90:
                    break

            if best_val >= threshold and best_loc is not None:
                    cx = rx1 + best_loc[0] + best_tw // 2
                    cy = ry1 + best_loc[1] + best_th // 2
                    self._log(f"[Potion] {template_name} found (score={best_val:.2f}) at ({cx},{cy})")
                    return (cx, cy)

        return None

    def _wait_for_template(self, template_name: str, timeout: int = 15, threshold: float = 0.7):
        """Wait until template is visible on screen.

        Returns (cx, cy) center position if found, None if timeout.
        """
        tpl_path = os.path.join("assets", template_name)
        if not os.path.exists(tpl_path):
            self._log(f"[Potion] Template {template_name} not found, fallback wait 8s")
            time.sleep(8)
            return None

        tpl_data = load_image(tpl_path)
        if tpl_data is None:
            time.sleep(8)
            return None

        tpl_bgr, tpl_mask = tpl_data
        start = time.time()
        while (time.time() - start) < timeout:
            time.sleep(1)
            img = self.capturer.capture()
            if img is None:
                continue

            w, h = img.size
            img_bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

            scale = h / 720.0
            th, tw = tpl_bgr.shape[:2]
            s_tpl = tpl_bgr
            s_mask = tpl_mask
            if abs(scale - 1.0) > 0.05:
                nw = max(1, int(tw * scale))
                nh = max(1, int(th * scale))
                if nw < w and nh < h:
                    s_tpl = cv2.resize(tpl_bgr, (nw, nh))
                    s_mask = cv2.resize(tpl_mask, (nw, nh)) if tpl_mask is not None else None
                    th, tw = nh, nw

            if th <= h and tw <= w:
                if s_mask is not None:
                    result = cv2.matchTemplate(img_bgr, s_tpl, cv2.TM_CCORR_NORMED, mask=s_mask)
                else:
                    result = cv2.matchTemplate(img_bgr, s_tpl, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)

                if max_val >= threshold:
                    cx = max_loc[0] + tw // 2
                    cy = max_loc[1] + th // 2
                    self._log(f"[Potion] {template_name} found (score={best_val:.2f}) at ({cx},{cy})")
                    return (cx, cy)

        return None

    def _is_saved_spots_dialog_open(self, img) -> bool:
        """Check if saved spots dialog is currently open using template matching.

        Template is 277x44 at 1280x720. For smaller resolutions, the template
        must be scaled down to fit the crop region.
        """
        template_path = os.path.join("assets", "saved_spots_diaglog.jpg")
        if not os.path.exists(template_path):
            return False
        try:
            w, h = img.size
            # Use a wider region with margin so template always fits
            REGION_WITH_MARGIN = (
                max(0.0, SAVED_SPOTS_DIALOG_REGION[0] - 0.02),
                max(0.0, SAVED_SPOTS_DIALOG_REGION[1] - 0.02),
                min(1.0, SAVED_SPOTS_DIALOG_REGION[2] + 0.02),
                min(1.0, SAVED_SPOTS_DIALOG_REGION[3] + 0.02),
            )
            x1, y1, x2, y2 = denormalize(REGION_WITH_MARGIN, w, h)
            cropped = img.crop((x1, y1, x2, y2))
            crop_bgr = cv2.cvtColor(np.array(cropped), cv2.COLOR_RGB2BGR)
            template_bgr, mask = load_image(template_path)

            # Scale template if it's bigger than crop region
            th, tw = template_bgr.shape[:2]
            ch, cw = crop_bgr.shape[:2]
            if tw > cw or th > ch:
                scale = min(cw / tw, ch / th) * 0.95  # slight margin
                new_w = max(1, int(tw * scale))
                new_h = max(1, int(th * scale))
                template_bgr = cv2.resize(template_bgr, (new_w, new_h))
                if mask is not None:
                    mask = cv2.resize(mask, (new_w, new_h))

            return match_template(crop_bgr, template_bgr, mask,
                                  threshold=SAVED_SPOTS_DIALOG_THRESHOLD)
        except Exception as e:
            print(f"[TP] Dialog detection error: {e}")
            return False

    def _teleport_to_spot(self, settings: dict, rotate: bool = False):
        """Teleport to saved spot - matching original tele_to_saved_spot() bytecode.

        Block combat escape saat dialog terbuka.

        Original flow:
        1. Loop capture max 6s until img != None
        2. Pick random index
        3. VERIFY isLocationSaveDialogOpening via template matching
        4. If NOT open → press 'O'. If open → close('O'), sleep 0.5, reopen('O'), sleep 1
        5. Loop capture AGAIN max 6s
        6. VERIFY dialog is open before clicking (abort if not)
        7. Click spot + teleport button
        8. Call pressing_key_after_teleporting()
        """
        if not self.key_sender or not self.clicker or not self.capturer:
            self._log("Error: modules tidak tersedia")
            return

        self.isBlockedByMouseAction = True
        try:
            self._teleport_to_spot_inner(settings, rotate)
        finally:
            self.isBlockedByMouseAction = False

    def _teleport_to_spot_inner(self, settings: dict, rotate: bool = False):
        spots = settings.get("teleport_spots", [False] * 5)
        checked = [i + 1 for i, v in enumerate(spots) if v]
        if not checked:
            self._log("Tidak ada spot teleport yang dipilih!")
            return

        import random
        if rotate and len(checked) > 1:
            available = [s for s in checked if s != self._tp_last_spot_index]
            if not available:
                available = checked
            index = random.choice(available)
        else:
            index = random.choice(checked) if len(checked) >= 2 else checked[0]

        self._tp_last_spot_index = index

        # ── Step 1: Loop capture max 6s ──
        img = None
        start = time.time()
        while time.time() - start < 6:
            img = self.capturer.capture()
            if img is not None:
                break
            time.sleep(0.1)

        if img is None:
            self._log("Error: tidak bisa capture window")
            return

        w, h = img.size
        self._log(f"Teleport ke spot {index} ({w}x{h})...")

        # ── Step 3: VERIFY dialog state ──
        dialog_open = self._is_saved_spots_dialog_open(img)

        # ── Step 4: Open/reopen dialog ──
        if not dialog_open:
            self.key_sender.send(SAVED_LOCATION_KEY)
            self._log(f"[TP] Tekan '{SAVED_LOCATION_KEY}' - buka dialog")
        else:
            # Already open → close, sleep 0.5, reopen, sleep 1
            self.key_sender.send(SAVED_LOCATION_KEY)  # close
            time.sleep(0.5)
            self.key_sender.send(SAVED_LOCATION_KEY)  # reopen
            self._log("[TP] Dialog sudah terbuka, reopen")
        time.sleep(1.0)

        # ── Step 5: Tunggu dialog terbuka ──
        time.sleep(1.0)

        # ── Step 7: Click spot + teleport button ──
        if index < 1 or index > len(SAVED_SPOT_COORDS_1280):
            self._log(f"[TP] Spot {index} di luar range!")
            return

        x1, y1, x2, y2 = SAVED_SPOT_COORDS_1280[index - 1]

        self._log(f"[TP] Klik spot {index} ({x1},{y1}) @1280x720")
        self.clicker.click_scaled(x1, y1)
        time.sleep(1.0)

        self._log(f"[TP] Klik teleport ({x2},{y2}) @1280x720")
        self.clicker.click_scaled(x2, y2)
        time.sleep(1.0)

        self._log(f"[TP] Teleport ke spot {index}, menunggu stabil...")

        # ── Step 8: pressing_key_after_teleporting() ──
        key_after = settings.get("teleport_key_after", "")
        self._pressing_key_after_teleporting(key_after)

    def _pressing_key_after_teleporting(self, key_after: str = ""):
        """Tunggu loading teleport selesai lalu press key jika autohunt OFF."""
        time.sleep(5.0)  # tunggu loading map selesai

        key = key_after if key_after else "F"

        # Cek autohunt status — hanya tekan jika OFF
        is_on = self._is_autohunt_on()
        if is_on is True:
            self._log(f"[TP] Auto hunt sudah ON, skip tekan {key}")
            return

        if is_on is False:
            self._log(f"[TP] Auto hunt OFF, tekan {key}")
            if self.key_sender:
                self.key_sender.send(key)
        else:
            # Unknown — tekan sekali saja sebagai safety
            self._log(f"[TP] Tekan {key} (1x)")
            if self.key_sender:
                self.key_sender.send(key)

    # ──────────────────────────────────────────────
    #  Daily tasks loop (boss, zariche, etc.)
    # ──────────────────────────────────────────────

    # _daily_tasks_loop removed - merged into _other_tasks above

    # ──────────────────────────────────────────────
    #  Window close
    # ──────────────────────────────────────────────

    def _ensure_modules(self):
        """Ensure core modules are initialized."""
        if not self.target_hwnd:
            return False
        if not self.capturer:
            self.capturer = WindowCapturer(self.target_hwnd)
        if not self.key_sender:
            self.key_sender = KeySender(self.target_hwnd)
        if not self.clicker:
            self.clicker = MouseClicker(self.target_hwnd)
        return True

    def _save_debug_screenshot(self):
        """Save screenshot with coordinate grid overlay for calibration."""
        if not self._ensure_modules():
            self._log("Error: pilih window dulu!")
            return
        img = self.capturer.capture()
        if not img:
            self._log("Error: tidak bisa capture!")
            return

        from PIL import ImageDraw, ImageFont
        w, h = img.size
        draw = ImageDraw.Draw(img)

        # Draw grid every 5%
        for pct in range(0, 101, 5):
            x = int(pct / 100 * w)
            y = int(pct / 100 * h)
            color = "yellow" if pct % 10 == 0 else "gray"
            draw.line([(x, 0), (x, h)], fill=color, width=1)
            draw.line([(0, y), (w, y)], fill=color, width=1)
            if pct % 10 == 0:
                draw.text((x + 2, 2), f"{pct}%", fill="yellow")
                draw.text((2, y + 2), f"{pct}%", fill="yellow")

        # Mark current pin icon position
        pin_pos = self.tab_farming.get_pin_position()
        px, py = int(pin_pos[0] * w), int(pin_pos[1] * h)
        draw.ellipse([(px-8, py-8), (px+8, py+8)], outline="red", width=3)
        draw.text((px+10, py-5), f"PIN ({pin_pos[0]*100:.1f}%, {pin_pos[1]*100:.1f}%)", fill="red")

        # Mark saved spot positions (1280x720 base, scaled to current)
        for i, (sx1, sy1, sx2, sy2) in enumerate(SAVED_SPOT_COORDS_1280):
            # Scale name click position
            nx, ny = int(sx1 / 1280 * w), int(sy1 / 720 * h)
            draw.ellipse([(nx-5, ny-5), (nx+5, ny+5)], outline="lime", width=2)
            draw.text((nx+8, ny-5), f"Spot{i+1}", fill="lime")
            # Scale teleport btn position
            tx, ty = int(sx2 / 1280 * w), int(sy2 / 720 * h)
            draw.ellipse([(tx-3, ty-3), (tx+3, ty+3)], outline="orange", width=2)

        # Mark teleport button position (from SAVED_SPOT_COORDS_1280)
        # The teleport btn is at x2,y2 of each spot, scaled to current res
        from core.game_layout import MAP_CONFIRM_BTN_1280
        cx, cy = int(MAP_CONFIRM_BTN_1280[0] / 1280 * w), int(MAP_CONFIRM_BTN_1280[1] / 720 * h)
        draw.ellipse([(cx-5, cy-5), (cx+5, cy+5)], outline="cyan", width=2)
        draw.text((cx+8, cy-5), "MapConfirm", fill="cyan")

        # Mark skill slot regions
        for slot_num, (bx1, by1, bx2, by2) in SKILL_SLOT_REGIONS_1280.items():
            sx1_ = int(bx1 / 1280 * w)
            sy1_ = int(by1 / 720 * h)
            sx2_ = int(bx2 / 1280 * w)
            sy2_ = int(by2 / 720 * h)
            color = "magenta" if slot_num == 4 else "gray"
            draw.rectangle([(sx1_, sy1_), (sx2_, sy2_)], outline=color, width=2)
            draw.text((sx1_ + 2, sy1_ - 12), f"S{slot_num}", fill=color)

        # Save
        save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "debug_screenshot.png")
        save_path = os.path.abspath(save_path)
        img.save(save_path)
        self._log(f"Screenshot saved: {save_path}")
        self.tab_farming.status_label.config(text=f"Screenshot: {save_path} ({w}x{h})")

        # Open the image
        os.startfile(save_path)

    def _test_teleport_now(self):
        """Test teleport immediately."""
        if not self._ensure_modules():
            self._log("Error: pilih window dulu!")
            return
        settings = self._collect_all_settings()
        self._log("=== TEST TELEPORT ===")
        self._teleport_to_spot(settings)

    def _on_close(self):
        if self.is_running:
            self.stop_all()
            time.sleep(0.5)
        self.root.destroy()
