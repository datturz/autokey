"""Weapon switch tab - auto weapon switching settings."""
import tkinter as tk
from tkinter import ttk
from core.key_sender import KEY_LIST


class TabWeapon:
    """Weapon switching settings tab."""

    def __init__(self, parent: ttk.Frame, lang: dict):
        self.parent = parent
        self.lang = lang
        self._build_ui()

    def _build_ui(self):
        frame = ttk.LabelFrame(self.parent, text=self.lang.get("weapon_switch", "Ganti Senjata"), padding=10)
        frame.pack(fill=tk.X, padx=5, pady=5)

        row0 = ttk.Frame(frame)
        row0.pack(fill=tk.X, pady=2)
        self.enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(row0, text=self.lang.get("weapon_switch", "Aktifkan ganti senjata"),
                        variable=self.enabled).pack(side=tk.LEFT)

        row1 = ttk.Frame(frame)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text=self.lang.get("weapon_key1", "Tombol 1:")).pack(side=tk.LEFT)
        self.key1 = ttk.Combobox(row1, values=KEY_LIST, width=6, state="readonly")
        self.key1.pack(side=tk.LEFT, padx=5)
        ttk.Label(row1, text=self.lang.get("weapon_key2", "Tombol 2:")).pack(side=tk.LEFT, padx=(20, 0))
        self.key2 = ttk.Combobox(row1, values=KEY_LIST, width=6, state="readonly")
        self.key2.pack(side=tk.LEFT, padx=5)
        ttk.Label(row1, text="Tombol 3:").pack(side=tk.LEFT, padx=(20, 0))
        self.key3 = ttk.Combobox(row1, values=KEY_LIST, width=6, state="readonly")
        self.key3.pack(side=tk.LEFT, padx=5)

        row2 = ttk.Frame(frame)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="Delay (s):").pack(side=tk.LEFT)
        self.delay = ttk.Entry(row2, width=5)
        self.delay.pack(side=tk.LEFT, padx=5)
        self.delay.insert(0, "1.0")

        ttk.Label(row2, text=self.lang.get("weapon_interval", "Interval (menit):")).pack(side=tk.LEFT, padx=(20, 0))
        self.interval = ttk.Entry(row2, width=5)
        self.interval.pack(side=tk.LEFT, padx=5)
        self.interval.insert(0, "60")

        row3 = ttk.Frame(frame)
        row3.pack(fill=tk.X, pady=2)
        self.press_space = tk.BooleanVar(value=False)
        ttk.Checkbutton(row3, text=self.lang.get("press_space", "Tekan Space saat ganti"),
                        variable=self.press_space).pack(side=tk.LEFT)

        # HP trigger section
        hp_frame = ttk.LabelFrame(self.parent, text="HP Trigger", padding=10)
        hp_frame.pack(fill=tk.X, padx=5, pady=5)

        row4 = ttk.Frame(hp_frame)
        row4.pack(fill=tk.X, pady=2)
        self.hp_below_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(row4, text="Ganti saat HP di bawah",
                        variable=self.hp_below_enabled).pack(side=tk.LEFT)
        self.hp_below_key = ttk.Combobox(row4, values=KEY_LIST, width=6, state="readonly")
        self.hp_below_key.pack(side=tk.LEFT, padx=5)
        ttk.Label(row4, text="Interval(s):").pack(side=tk.LEFT, padx=(10, 0))
        self.hp_below_interval = ttk.Entry(row4, width=5)
        self.hp_below_interval.pack(side=tk.LEFT, padx=5)
        self.hp_below_interval.insert(0, "10")

        row5 = ttk.Frame(hp_frame)
        row5.pack(fill=tk.X, pady=2)
        self.hp_above_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(row5, text="Ganti saat HP di atas",
                        variable=self.hp_above_enabled).pack(side=tk.LEFT)
        self.hp_above_key = ttk.Combobox(row5, values=KEY_LIST, width=6, state="readonly")
        self.hp_above_key.pack(side=tk.LEFT, padx=5)
        ttk.Label(row5, text="Interval(s):").pack(side=tk.LEFT, padx=(10, 0))
        self.hp_above_interval = ttk.Entry(row5, width=5)
        self.hp_above_interval.pack(side=tk.LEFT, padx=5)
        self.hp_above_interval.insert(0, "10")

    def apply_settings(self, settings: dict):
        self.enabled.set(settings.get("weapon_switch_enabled", False))
        if settings.get("weapon_key1"):
            self.key1.set(settings["weapon_key1"])
        if settings.get("weapon_key2"):
            self.key2.set(settings["weapon_key2"])
        if settings.get("weapon_key3"):
            self.key3.set(settings["weapon_key3"])
        self.delay.delete(0, tk.END)
        self.delay.insert(0, str(settings.get("weapon_switch_delay", 1.0)))
        self.interval.delete(0, tk.END)
        self.interval.insert(0, str(settings.get("weapon_switch_interval", 60)))
        self.press_space.set(settings.get("weapon_press_space", False))

    def collect_settings(self) -> dict:
        return {
            "weapon_switch_enabled": self.enabled.get(),
            "weapon_key1": self.key1.get(),
            "weapon_key2": self.key2.get(),
            "weapon_key3": self.key3.get(),
            "weapon_switch_delay": float(self.delay.get() or 1.0),
            "weapon_switch_interval": int(self.interval.get() or 60),
            "weapon_press_space": self.press_space.get(),
        }
