"""Daily tasks tab - boss check, clan attendance, etc."""
import tkinter as tk
from tkinter import ttk
from core.key_sender import KEY_LIST

# Area list dan koordinat Y @1280x720 di panel kiri map
AREA_LIST = ["ALL", "Gludio", "Dion", "Giran", "Oren", "Aden"]


class TabDaily:
    """Daily tasks settings tab."""

    def __init__(self, parent: ttk.Frame, lang: dict):
        self.parent = parent
        self.lang = lang
        self._build_ui()

    def _build_ui(self):
        # Boss check
        boss_frame = ttk.LabelFrame(self.parent, text=self.lang.get("check_boss", "Cek Boss"), padding=10)
        boss_frame.pack(fill=tk.X, padx=5, pady=5)

        row1 = ttk.Frame(boss_frame)
        row1.pack(fill=tk.X, pady=2)
        self.boss_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(row1, text=self.lang.get("check_boss", "Cek boss setiap"),
                        variable=self.boss_enabled).pack(side=tk.LEFT)
        self.boss_interval = ttk.Entry(row1, width=5)
        self.boss_interval.pack(side=tk.LEFT, padx=5)
        self.boss_interval.insert(0, "5")
        ttk.Label(row1, text=self.lang.get("minutes", "menit")).pack(side=tk.LEFT)

        row1b = ttk.Frame(boss_frame)
        row1b.pack(fill=tk.X, pady=2)
        ttk.Label(row1b, text="Key Radar:").pack(side=tk.LEFT)
        self.boss_radar_key = ttk.Combobox(row1b, values=[""] + KEY_LIST, width=6, state="readonly")
        self.boss_radar_key.pack(side=tk.LEFT, padx=5)
        ttk.Label(row1b, text="Key Hit:").pack(side=tk.LEFT, padx=(10, 0))
        self.boss_hit_key = ttk.Combobox(row1b, values=[""] + KEY_LIST, width=6, state="readonly")
        self.boss_hit_key.pack(side=tk.LEFT, padx=5)
        ttk.Label(row1b, text="Tunggu spawn (menit):").pack(side=tk.LEFT, padx=(10, 0))
        self.boss_tp_wait = ttk.Entry(row1b, width=5)
        self.boss_tp_wait.pack(side=tk.LEFT, padx=5)
        self.boss_tp_wait.insert(0, "5")

        # Area checkboxes untuk boss
        row1c = ttk.Frame(boss_frame)
        row1c.pack(fill=tk.X, pady=2)
        ttk.Label(row1c, text="Area:").pack(side=tk.LEFT)
        self.boss_areas = {}
        for area in AREA_LIST:
            var = tk.BooleanVar(value=False)
            ttk.Checkbutton(row1c, text=area, variable=var).pack(side=tk.LEFT, padx=3)
            self.boss_areas[area] = var

        self.boss_status = ttk.Label(boss_frame, text="")
        self.boss_status.pack(anchor=tk.W)

        # Zariche check
        zariche_frame = ttk.LabelFrame(self.parent, text=self.lang.get("check_zariche", "Cek Zariche"), padding=10)
        zariche_frame.pack(fill=tk.X, padx=5, pady=5)

        row2 = ttk.Frame(zariche_frame)
        row2.pack(fill=tk.X, pady=2)
        self.zariche_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(row2, text=self.lang.get("check_zariche", "Cek Zariche setiap"),
                        variable=self.zariche_enabled).pack(side=tk.LEFT)
        self.zariche_interval = ttk.Entry(row2, width=5)
        self.zariche_interval.pack(side=tk.LEFT, padx=5)
        self.zariche_interval.insert(0, "5")
        ttk.Label(row2, text=self.lang.get("minutes", "menit")).pack(side=tk.LEFT)

        row2b = ttk.Frame(zariche_frame)
        row2b.pack(fill=tk.X, pady=2)
        ttk.Label(row2b, text="Key Radar:").pack(side=tk.LEFT)
        self.zariche_radar_key = ttk.Combobox(row2b, values=[""] + KEY_LIST, width=6, state="readonly")
        self.zariche_radar_key.pack(side=tk.LEFT, padx=5)
        ttk.Label(row2b, text="Key Hit:").pack(side=tk.LEFT, padx=(10, 0))
        self.zariche_hit_key = ttk.Combobox(row2b, values=[""] + KEY_LIST, width=6, state="readonly")
        self.zariche_hit_key.pack(side=tk.LEFT, padx=5)
        ttk.Label(row2b, text="Tunggu spawn (menit):").pack(side=tk.LEFT, padx=(10, 0))
        self.zariche_tp_wait = ttk.Entry(row2b, width=5)
        self.zariche_tp_wait.pack(side=tk.LEFT, padx=5)
        self.zariche_tp_wait.insert(0, "5")

        # Area checkboxes untuk zariche
        row2c = ttk.Frame(zariche_frame)
        row2c.pack(fill=tk.X, pady=2)
        ttk.Label(row2c, text="Area:").pack(side=tk.LEFT)
        self.zariche_areas = {}
        for area in AREA_LIST:
            var = tk.BooleanVar(value=False)
            ttk.Checkbutton(row2c, text=area, variable=var).pack(side=tk.LEFT, padx=3)
            self.zariche_areas[area] = var

        self.zariche_status = ttk.Label(zariche_frame, text="")
        self.zariche_status.pack(anchor=tk.W)

        # Daily tasks
        daily_frame = ttk.LabelFrame(self.parent, text="Tugas Harian Otomatis", padding=10)
        daily_frame.pack(fill=tk.X, padx=5, pady=5)

        self.bulk_purchase = tk.BooleanVar(value=False)
        ttk.Checkbutton(daily_frame, text=self.lang.get("auto_bulk_purchase", "Auto bulk purchase dengan currency"),
                        variable=self.bulk_purchase).pack(anchor=tk.W, pady=2)

        self.clan_attendance = tk.BooleanVar(value=False)
        ttk.Checkbutton(daily_frame, text=self.lang.get("auto_clan_attendance", "Auto absen clan"),
                        variable=self.clan_attendance).pack(anchor=tk.W, pady=2)

        self.daily_claim = tk.BooleanVar(value=False)
        ttk.Checkbutton(daily_frame, text=self.lang.get("auto_daily_claim", "Auto klaim hadiah harian"),
                        variable=self.daily_claim).pack(anchor=tk.W, pady=2)

        self.daily_status = ttk.Label(daily_frame, text="")
        self.daily_status.pack(anchor=tk.W, pady=2)

    def apply_settings(self, settings: dict):
        self.boss_enabled.set(settings.get("check_boss_enabled", False))
        self.boss_interval.delete(0, tk.END)
        self.boss_interval.insert(0, str(settings.get("check_boss_interval", 5)))
        if settings.get("check_boss_radar_key"):
            self.boss_radar_key.set(settings["check_boss_radar_key"])
        if settings.get("check_boss_hit_key"):
            self.boss_hit_key.set(settings["check_boss_hit_key"])
        self.boss_tp_wait.delete(0, tk.END)
        self.boss_tp_wait.insert(0, str(settings.get("check_boss_tele_after_min", 5)))
        boss_areas_saved = settings.get("check_boss_areas", [])
        for area, var in self.boss_areas.items():
            var.set(area in boss_areas_saved)

        self.zariche_enabled.set(settings.get("check_zariche_enabled", False))
        self.zariche_interval.delete(0, tk.END)
        self.zariche_interval.insert(0, str(settings.get("check_zariche_interval", 5)))
        if settings.get("check_zariche_radar_key"):
            self.zariche_radar_key.set(settings["check_zariche_radar_key"])
        if settings.get("check_zariche_hit_key"):
            self.zariche_hit_key.set(settings["check_zariche_hit_key"])
        self.zariche_tp_wait.delete(0, tk.END)
        self.zariche_tp_wait.insert(0, str(settings.get("check_zariche_tele_after_min", 5)))
        zariche_areas_saved = settings.get("check_zariche_areas", [])
        for area, var in self.zariche_areas.items():
            var.set(area in zariche_areas_saved)

        self.bulk_purchase.set(settings.get("auto_bulk_purchase", False))
        self.clan_attendance.set(settings.get("auto_clan_attendance", False))
        self.daily_claim.set(settings.get("auto_daily_claim", False))

    def collect_settings(self) -> dict:
        return {
            "check_boss_enabled": self.boss_enabled.get(),
            "check_boss_interval": int(self.boss_interval.get() or 5),
            "check_boss_radar_key": self.boss_radar_key.get(),
            "check_boss_hit_key": self.boss_hit_key.get(),
            "check_boss_tele_after_min": int(self.boss_tp_wait.get() or 5),
            "check_boss_areas": [a for a, v in self.boss_areas.items() if v.get()],
            "check_zariche_enabled": self.zariche_enabled.get(),
            "check_zariche_interval": int(self.zariche_interval.get() or 5),
            "check_zariche_radar_key": self.zariche_radar_key.get(),
            "check_zariche_hit_key": self.zariche_hit_key.get(),
            "check_zariche_tele_after_min": int(self.zariche_tp_wait.get() or 5),
            "check_zariche_areas": [a for a, v in self.zariche_areas.items() if v.get()],
            "auto_bulk_purchase": self.bulk_purchase.get(),
            "auto_clan_attendance": self.clan_attendance.get(),
            "auto_daily_claim": self.daily_claim.get(),
        }
