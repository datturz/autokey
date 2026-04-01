"""Daily tasks tab - boss check, clan attendance, etc."""
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from core.key_sender import KEY_LIST

# Area list dan koordinat Y @1280x720 di panel kiri map
AREA_LIST = ["ALL", "Gludio", "Dion", "Giran", "Oren", "Aden"]

_ACCESS_KEY = "DAWNSHATTER"


class TabDaily:
    """Daily tasks settings tab."""

    def __init__(self, parent: ttk.Frame, lang: dict):
        self.parent = parent
        self.lang = lang
        self._unlocked = False
        self._pending_settings = None

        # Stub attributes — prevent AttributeError when locked
        # These get replaced by real widgets when _build_ui() runs
        self.boss_enabled = tk.BooleanVar(value=False)
        self.zariche_enabled = tk.BooleanVar(value=False)
        self.bulk_purchase = tk.BooleanVar(value=False)
        self.clan_attendance = tk.BooleanVar(value=False)
        self.daily_claim = tk.BooleanVar(value=False)
        self.boss_status = ttk.Label(parent)
        self.zariche_status = ttk.Label(parent)
        self.daily_status = ttk.Label(parent)

        self._build_lock_screen()

    def _build_lock_screen(self):
        """Show lock screen until correct password is entered."""
        self._lock_frame = ttk.Frame(self.parent)
        self._lock_frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(self._lock_frame, text="🔒 Feature ini memerlukan akses khusus",
                  font=("", 12)).pack(pady=(80, 10))
        ttk.Button(self._lock_frame, text="Unlock",
                   command=self._on_unlock).pack(pady=10)

    def _on_unlock(self):
        pwd = simpledialog.askstring("Access Key", "Masukkan access key:",
                                     show="*", parent=self.parent)
        if pwd == _ACCESS_KEY:
            self._unlocked = True
            self._lock_frame.destroy()
            self._build_ui()
            # Apply any pending settings that were loaded before unlock
            if hasattr(self, '_pending_settings') and self._pending_settings:
                self.apply_settings(self._pending_settings)
                self._pending_settings = None
        elif pwd is not None:
            messagebox.showerror("Error", "Access key salah!", parent=self.parent)

    def _build_ui(self):
        # Keep hidden vars for backward compatibility with settings/app.py references
        self.boss_enabled = tk.BooleanVar(value=False)
        self.boss_interval = tk.StringVar(value="5")
        self.boss_radar_key = tk.StringVar(value="")
        self.boss_hit_key = tk.StringVar(value="")
        self.boss_tp_wait = tk.StringVar(value="5")
        self.boss_areas = {}
        self.boss_status = ttk.Label(self.parent)
        self.zariche_enabled = tk.BooleanVar(value=False)
        self.zariche_interval = tk.StringVar(value="5")
        self.zariche_radar_key = tk.StringVar(value="")
        self.zariche_hit_key = tk.StringVar(value="")
        self.zariche_tp_wait = tk.StringVar(value="5")
        self.zariche_areas = {}
        self.zariche_status = ttk.Label(self.parent)

        # Smart Boss Hunt (timer-driven)
        smart_frame = ttk.LabelFrame(self.parent, text="Smart Boss Hunt (Timer-Driven)", padding=10)
        smart_frame.pack(fill=tk.X, padx=5, pady=5)

        sr0 = ttk.Frame(smart_frame)
        sr0.pack(fill=tk.X, pady=2)
        self.smart_boss_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(sr0, text="Aktifkan Smart Boss Hunt",
                        variable=self.smart_boss_enabled).pack(side=tk.LEFT)

        sr1 = ttk.Frame(smart_frame)
        sr1.pack(fill=tk.X, pady=2)
        ttk.Label(sr1, text="Pre-position (menit sebelum spawn):").pack(side=tk.LEFT)
        self.smart_boss_prepos = ttk.Entry(sr1, width=4)
        self.smart_boss_prepos.pack(side=tk.LEFT, padx=5)
        self.smart_boss_prepos.insert(0, "1")

        sr2 = ttk.Frame(smart_frame)
        sr2.pack(fill=tk.X, pady=2)
        ttk.Label(sr2, text="Key Hit Boss:").pack(side=tk.LEFT)
        self.smart_boss_hit_key = ttk.Combobox(sr2, values=[""] + KEY_LIST, width=6, state="readonly")
        self.smart_boss_hit_key.pack(side=tk.LEFT, padx=5)
        ttk.Label(sr2, text="Key Radar:").pack(side=tk.LEFT, padx=(10, 0))
        self.smart_boss_radar_key = ttk.Combobox(sr2, values=[""] + KEY_LIST, width=6, state="readonly")
        self.smart_boss_radar_key.pack(side=tk.LEFT, padx=5)

        sr3 = ttk.Frame(smart_frame)
        sr3.pack(fill=tk.X, pady=2)
        ttk.Label(sr3, text="Key Clan Menu:").pack(side=tk.LEFT)
        self.smart_boss_clan_key = ttk.Combobox(sr3, values=[""] + KEY_LIST, width=6, state="readonly")
        self.smart_boss_clan_key.pack(side=tk.LEFT, padx=5)
        ttk.Label(sr3, text="Nama karakter:").pack(side=tk.LEFT, padx=(10, 0))
        self.smart_boss_char_name = ttk.Entry(sr3, width=15)
        self.smart_boss_char_name.pack(side=tk.LEFT, padx=5)

        sr4 = ttk.Frame(smart_frame)
        sr4.pack(fill=tk.X, pady=2)
        ttk.Label(sr4, text="Boss types:").pack(side=tk.LEFT)
        self.smart_boss_type_ours = tk.BooleanVar(value=True)
        self.smart_boss_type_ffa = tk.BooleanVar(value=False)
        self.smart_boss_type_inv = tk.BooleanVar(value=False)
        ttk.Checkbutton(sr4, text="Ours", variable=self.smart_boss_type_ours).pack(side=tk.LEFT, padx=3)
        ttk.Checkbutton(sr4, text="FFA", variable=self.smart_boss_type_ffa).pack(side=tk.LEFT, padx=3)
        ttk.Checkbutton(sr4, text="Invasion", variable=self.smart_boss_type_inv).pack(side=tk.LEFT, padx=3)

        self.smart_boss_status = ttk.Label(smart_frame, text="")
        self.smart_boss_status.pack(anchor=tk.W, pady=2)

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
        if not self._unlocked:
            self._pending_settings = settings
            return
        # Old boss/zariche settings (kept for backward compatibility, hidden)
        self.boss_enabled.set(settings.get("check_boss_enabled", False))
        self.zariche_enabled.set(settings.get("check_zariche_enabled", False))

        self.bulk_purchase.set(settings.get("auto_bulk_purchase", False))
        self.clan_attendance.set(settings.get("auto_clan_attendance", False))
        self.daily_claim.set(settings.get("auto_daily_claim", False))

        # Smart boss hunt
        self.smart_boss_enabled.set(settings.get("smart_boss_enabled", False))
        self.smart_boss_prepos.delete(0, tk.END)
        self.smart_boss_prepos.insert(0, str(settings.get("smart_boss_prepos_min", 1)))
        if settings.get("smart_boss_hit_key"):
            self.smart_boss_hit_key.set(settings["smart_boss_hit_key"])
        if settings.get("smart_boss_radar_key"):
            self.smart_boss_radar_key.set(settings["smart_boss_radar_key"])
        if settings.get("smart_boss_clan_key"):
            self.smart_boss_clan_key.set(settings["smart_boss_clan_key"])
        self.smart_boss_char_name.delete(0, tk.END)
        self.smart_boss_char_name.insert(0, settings.get("smart_boss_char_name", ""))
        self.smart_boss_type_ours.set(settings.get("smart_boss_type_ours", True))
        self.smart_boss_type_ffa.set(settings.get("smart_boss_type_ffa", False))
        self.smart_boss_type_inv.set(settings.get("smart_boss_type_inv", False))

    def collect_settings(self) -> dict:
        if not self._unlocked:
            return {}
        return {
            "check_boss_enabled": False,  # Removed, use smart_boss_enabled
            "check_zariche_enabled": False,  # Removed
            "auto_bulk_purchase": self.bulk_purchase.get(),
            "auto_clan_attendance": self.clan_attendance.get(),
            "auto_daily_claim": self.daily_claim.get(),
            # Smart boss hunt
            "smart_boss_enabled": self.smart_boss_enabled.get(),
            "smart_boss_prepos_min": float(self.smart_boss_prepos.get() or 1),
            "smart_boss_hit_key": self.smart_boss_hit_key.get(),
            "smart_boss_radar_key": self.smart_boss_radar_key.get(),
            "smart_boss_clan_key": self.smart_boss_clan_key.get(),
            "smart_boss_char_name": self.smart_boss_char_name.get(),
            "smart_boss_type_ours": self.smart_boss_type_ours.get(),
            "smart_boss_type_ffa": self.smart_boss_type_ffa.get(),
            "smart_boss_type_inv": self.smart_boss_type_inv.get(),
        }
