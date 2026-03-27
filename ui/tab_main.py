"""Main tab - key configurations and HP monitoring."""
import tkinter as tk
from tkinter import ttk
from core.key_sender import KEY_LIST


class TabMain:
    """Main tab with auto-key and HP settings."""

    def __init__(self, parent: ttk.Frame, lang: dict):
        self.parent = parent
        self.lang = lang
        self.key_configs = []  # list of {frame, key_var, interval_var, condition_var}
        self._build_ui()

    def _build_ui(self):
        # === Key Configs Section ===
        key_frame = ttk.LabelFrame(self.parent, text="Auto Key Press", padding=10)
        key_frame.pack(fill=tk.X, padx=5, pady=5)

        self.config_container = ttk.Frame(key_frame)
        self.config_container.pack(fill=tk.X)

        btn_add = ttk.Button(key_frame, text=self.lang.get("add_key", "+ Tambah Tombol"),
                             command=self.add_key_config)
        btn_add.pack(anchor=tk.W, pady=(5, 0))

        # === HP Settings Section ===
        hp_frame = ttk.LabelFrame(self.parent, text="HP Settings", padding=10)
        hp_frame.pack(fill=tk.X, padx=5, pady=5)

        # Low HP
        row1 = ttk.Frame(hp_frame)
        row1.pack(fill=tk.X, pady=2)
        self.enable_low_hp = tk.BooleanVar(value=False)
        ttk.Checkbutton(row1, text=self.lang.get("low_hp", "HP Rendah"),
                        variable=self.enable_low_hp).pack(side=tk.LEFT)
        ttk.Label(row1, text="%").pack(side=tk.RIGHT)
        self.low_hp_percent = ttk.Entry(row1, width=5)
        self.low_hp_percent.pack(side=tk.RIGHT)
        self.low_hp_percent.insert(0, "30")
        ttk.Label(row1, text=self.lang.get("press_key", "Tekan:")).pack(side=tk.RIGHT, padx=(10, 5))
        self.low_hp_key = ttk.Combobox(row1, values=KEY_LIST, width=6, state="readonly")
        self.low_hp_key.pack(side=tk.RIGHT)

        # Medium HP
        row2 = ttk.Frame(hp_frame)
        row2.pack(fill=tk.X, pady=2)
        self.enable_medium_hp = tk.BooleanVar(value=False)
        ttk.Checkbutton(row2, text="HP Sedang", variable=self.enable_medium_hp).pack(side=tk.LEFT)
        ttk.Label(row2, text="%").pack(side=tk.RIGHT)
        self.medium_hp_percent = ttk.Entry(row2, width=5)
        self.medium_hp_percent.pack(side=tk.RIGHT)
        self.medium_hp_percent.insert(0, "60")
        ttk.Label(row2, text=self.lang.get("press_key", "Tekan:")).pack(side=tk.RIGHT, padx=(10, 5))
        self.medium_hp_key = ttk.Combobox(row2, values=KEY_LIST, width=6, state="readonly")
        self.medium_hp_key.pack(side=tk.RIGHT)

        row2b = ttk.Frame(hp_frame)
        row2b.pack(fill=tk.X, pady=2)
        self.medium_hp_only_attacked = tk.BooleanVar(value=False)
        ttk.Checkbutton(row2b, text=self.lang.get("only_when_attacked", "Hanya saat diserang"),
                        variable=self.medium_hp_only_attacked).pack(side=tk.LEFT, padx=(20, 0))
        ttk.Label(row2b, text="Delay (s):").pack(side=tk.LEFT, padx=(10, 5))
        self.medium_hp_delay = ttk.Entry(row2b, width=5)
        self.medium_hp_delay.pack(side=tk.LEFT)
        self.medium_hp_delay.insert(0, "1.0")

        # High HP
        row3 = ttk.Frame(hp_frame)
        row3.pack(fill=tk.X, pady=2)
        self.enable_high_hp = tk.BooleanVar(value=False)
        ttk.Checkbutton(row3, text=self.lang.get("high_hp", "HP Tinggi"),
                        variable=self.enable_high_hp).pack(side=tk.LEFT)
        ttk.Label(row3, text="%").pack(side=tk.RIGHT)
        self.high_hp_percent = ttk.Entry(row3, width=5)
        self.high_hp_percent.pack(side=tk.RIGHT)
        self.high_hp_percent.insert(0, "80")
        ttk.Label(row3, text=self.lang.get("press_key", "Tekan:")).pack(side=tk.RIGHT, padx=(10, 5))
        self.high_hp_key = ttk.Combobox(row3, values=KEY_LIST, width=6, state="readonly")
        self.high_hp_key.pack(side=tk.RIGHT)

        # === Options Section ===
        opt_frame = ttk.LabelFrame(self.parent, text="Opsi", padding=10)
        opt_frame.pack(fill=tk.X, padx=5, pady=5)

        self.no_press_safe = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt_frame, text=self.lang.get("no_press_safe_area", "Jangan tekan di area aman"),
                        variable=self.no_press_safe).pack(anchor=tk.W)

        self.no_press_inventory = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt_frame, text=self.lang.get("no_press_inventory", "Jangan tekan saat inventory terbuka"),
                        variable=self.no_press_inventory).pack(anchor=tk.W)

        self.auto_hunt = tk.BooleanVar(value=False)
        ttk.Checkbutton(opt_frame, text=self.lang.get("auto_hunt", "Tekan auto hunt (F)"),
                        variable=self.auto_hunt).pack(anchor=tk.W)

    def add_key_config(self, key="", interval="5", condition="Kapan saja"):
        """Add a new key config row."""
        row = ttk.Frame(self.config_container)
        row.pack(fill=tk.X, pady=2)

        ttk.Label(row, text=self.lang.get("key", "Tombol:")).pack(side=tk.LEFT)
        key_var = ttk.Combobox(row, values=KEY_LIST, width=6, state="readonly")
        key_var.pack(side=tk.LEFT, padx=(0, 10))
        if key:
            key_var.set(key)

        ttk.Label(row, text=self.lang.get("interval", "Interval(s):")).pack(side=tk.LEFT)
        interval_var = ttk.Entry(row, width=5)
        interval_var.pack(side=tk.LEFT, padx=(0, 10))
        interval_var.insert(0, interval)

        ttk.Label(row, text=self.lang.get("condition", "Kondisi:")).pack(side=tk.LEFT)
        conditions = [
            self.lang.get("anytime", "Kapan saja"),
            self.lang.get("when_attacked", "Saat diserang"),
        ]
        condition_var = ttk.Combobox(row, values=conditions, width=15, state="readonly")
        condition_var.pack(side=tk.LEFT, padx=(0, 10))
        condition_var.set(condition)

        config = {"frame": row, "key": key_var, "interval": interval_var, "condition": condition_var}

        btn_del = ttk.Button(row, text="X", width=3,
                             command=lambda: self._remove_key_config(config))
        btn_del.pack(side=tk.LEFT)

        self.key_configs.append(config)

    def _remove_key_config(self, config):
        config["frame"].destroy()
        self.key_configs.remove(config)

    def apply_settings(self, settings: dict):
        """Apply settings to UI."""
        # Clear existing key configs
        for cfg in list(self.key_configs):
            cfg["frame"].destroy()
        self.key_configs.clear()

        for kc in settings.get("key_configs", []):
            self.add_key_config(kc.get("key", ""), str(kc.get("interval", "5")),
                               kc.get("condition", "Kapan saja"))

        self.enable_low_hp.set(settings.get("enable_low_hp", False))
        self.low_hp_percent.delete(0, tk.END)
        self.low_hp_percent.insert(0, str(settings.get("low_hp_percent", 30)))
        if settings.get("low_hp_key"):
            self.low_hp_key.set(settings["low_hp_key"])

        self.enable_medium_hp.set(settings.get("enable_medium_hp", False))
        self.medium_hp_percent.delete(0, tk.END)
        self.medium_hp_percent.insert(0, str(settings.get("medium_hp_percent", 60)))
        if settings.get("medium_hp_key"):
            self.medium_hp_key.set(settings["medium_hp_key"])
        self.medium_hp_only_attacked.set(settings.get("medium_hp_only_when_attacked", False))
        self.medium_hp_delay.delete(0, tk.END)
        self.medium_hp_delay.insert(0, str(settings.get("medium_hp_delay", 1.0)))

        self.enable_high_hp.set(settings.get("enable_high_hp", False))
        self.high_hp_percent.delete(0, tk.END)
        self.high_hp_percent.insert(0, str(settings.get("high_hp_percent", 80)))
        if settings.get("high_hp_key"):
            self.high_hp_key.set(settings["high_hp_key"])

        self.no_press_safe.set(settings.get("no_press_in_safe_area", True))
        self.no_press_inventory.set(settings.get("no_press_when_inventory_open", True))
        self.auto_hunt.set(settings.get("auto_hunt_enabled", False))

    def collect_settings(self) -> dict:
        """Collect current settings from UI."""
        key_configs = []
        for cfg in self.key_configs:
            key_configs.append({
                "key": cfg["key"].get(),
                "interval": cfg["interval"].get(),
                "condition": cfg["condition"].get(),
            })

        return {
            "key_configs": key_configs,
            "enable_low_hp": self.enable_low_hp.get(),
            "low_hp_percent": int(self.low_hp_percent.get() or 30),
            "low_hp_key": self.low_hp_key.get(),
            "enable_medium_hp": self.enable_medium_hp.get(),
            "medium_hp_percent": int(self.medium_hp_percent.get() or 60),
            "medium_hp_key": self.medium_hp_key.get(),
            "medium_hp_delay": float(self.medium_hp_delay.get() or 1.0),
            "medium_hp_only_when_attacked": self.medium_hp_only_attacked.get(),
            "enable_high_hp": self.enable_high_hp.get(),
            "high_hp_percent": int(self.high_hp_percent.get() or 80),
            "high_hp_key": self.high_hp_key.get(),
            "no_press_in_safe_area": self.no_press_safe.get(),
            "no_press_when_inventory_open": self.no_press_inventory.get(),
            "auto_hunt_enabled": self.auto_hunt.get(),
        }
