"""Farming tab - auto teleport and farming settings."""
import tkinter as tk
from tkinter import ttk
from core.key_sender import KEY_LIST


class TabFarming:
    """Farming and teleport settings tab."""

    def __init__(self, parent: ttk.Frame, lang: dict):
        self.parent = parent
        self.lang = lang
        self._build_ui()

    def _build_ui(self):
        # Teleport settings
        tp_frame = ttk.LabelFrame(self.parent, text=self.lang.get("teleport_enabled", "Teleport Otomatis"), padding=10)
        tp_frame.pack(fill=tk.X, padx=5, pady=5)

        self.teleport_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(tp_frame, text=self.lang.get("teleport_enabled", "Teleport otomatis ke spot tersimpan"),
                        variable=self.teleport_enabled).pack(anchor=tk.W)

        # Spot checkboxes
        spot_frame = ttk.Frame(tp_frame)
        spot_frame.pack(fill=tk.X, pady=5)
        self.spot_vars = []
        for i in range(5):
            var = tk.BooleanVar(value=False)
            ttk.Checkbutton(spot_frame, text=f"{self.lang.get('teleport_spot', 'Spot')} {i+1}",
                            variable=var).pack(side=tk.LEFT, padx=5)
            self.spot_vars.append(var)

        # After town teleport
        town_frame = ttk.Frame(tp_frame)
        town_frame.pack(fill=tk.X, pady=2)
        self.tp_after_town = tk.BooleanVar(value=False)
        ttk.Checkbutton(town_frame, text=self.lang.get("teleport_after_town", "Teleport setelah di kota"),
                        variable=self.tp_after_town).pack(side=tk.LEFT)
        self.tp_after_town_min = ttk.Entry(town_frame, width=5)
        self.tp_after_town_min.pack(side=tk.LEFT, padx=5)
        self.tp_after_town_min.insert(0, "5")
        ttk.Label(town_frame, text=self.lang.get("minutes", "menit")).pack(side=tk.LEFT)

        # During farm teleport
        farm_frame = ttk.Frame(tp_frame)
        farm_frame.pack(fill=tk.X, pady=2)
        self.tp_during_farm = tk.BooleanVar(value=False)
        ttk.Checkbutton(farm_frame, text="Pindah spot saat farming",
                        variable=self.tp_during_farm).pack(side=tk.LEFT)
        self.tp_during_farm_min = ttk.Entry(farm_frame, width=5)
        self.tp_during_farm_min.pack(side=tk.LEFT, padx=5)
        self.tp_during_farm_min.insert(0, "30")
        ttk.Label(farm_frame, text=self.lang.get("minutes", "menit")).pack(side=tk.LEFT)

        # Key after teleport
        key_frame = ttk.Frame(tp_frame)
        key_frame.pack(fill=tk.X, pady=2)
        ttk.Label(key_frame, text="Tekan tombol setelah teleport:").pack(side=tk.LEFT)
        self.tp_key_after = ttk.Combobox(key_frame, values=[""] + KEY_LIST, width=6, state="readonly")
        self.tp_key_after.pack(side=tk.LEFT, padx=5)

        # Combat Escape — auto sequence when under attack
        ce_frame = ttk.LabelFrame(self.parent, text="Combat Escape", padding=10)
        ce_frame.pack(fill=tk.X, padx=5, pady=5)

        ce_row0 = ttk.Frame(ce_frame)
        ce_row0.pack(fill=tk.X, pady=2)
        self.combat_escape_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(ce_row0, text="Aktifkan Combat Escape",
                        variable=self.combat_escape_enabled).pack(side=tk.LEFT)

        ce_row1 = ttk.Frame(ce_frame)
        ce_row1.pack(fill=tk.X, pady=2)
        ttk.Label(ce_row1, text="HP Threshold (%):").pack(side=tk.LEFT)
        self.ce_hp_threshold = ttk.Entry(ce_row1, width=5)
        self.ce_hp_threshold.pack(side=tk.LEFT, padx=5)
        self.ce_hp_threshold.insert(0, "50")

        ce_row2 = ttk.Frame(ce_frame)
        ce_row2.pack(fill=tk.X, pady=2)
        ttk.Label(ce_row2, text="1. Ganti Weapon:").pack(side=tk.LEFT)
        self.ce_weapon_key = ttk.Combobox(ce_row2, values=[""] + KEY_LIST, width=6, state="readonly")
        self.ce_weapon_key.pack(side=tk.LEFT, padx=5)

        ce_row3 = ttk.Frame(ce_frame)
        ce_row3.pack(fill=tk.X, pady=2)
        ttk.Label(ce_row3, text="2. Klik Skill:").pack(side=tk.LEFT)
        self.ce_skill_key = ttk.Combobox(ce_row3, values=[""] + KEY_LIST, width=6, state="readonly")
        self.ce_skill_key.pack(side=tk.LEFT, padx=5)
        ttk.Label(ce_row3, text="Slot:").pack(side=tk.LEFT, padx=(10, 0))
        self.ce_skill_slot = ttk.Combobox(ce_row3, values=["1","2","3","4","5","6","7","8"], width=3, state="readonly")
        self.ce_skill_slot.pack(side=tk.LEFT, padx=5)
        self.ce_skill_slot.set("4")

        ce_row4 = ttk.Frame(ce_frame)
        ce_row4.pack(fill=tk.X, pady=2)
        ttk.Label(ce_row4, text="3. Teleport (kabur):").pack(side=tk.LEFT)
        self.ce_teleport_key = ttk.Combobox(ce_row4, values=[""] + KEY_LIST, width=6, state="readonly")
        self.ce_teleport_key.pack(side=tk.LEFT, padx=5)

        ce_row5 = ttk.Frame(ce_frame)
        ce_row5.pack(fill=tk.X, pady=2)
        ttk.Label(ce_row5, text="4. Ganti Balik Weapon:").pack(side=tk.LEFT)
        self.ce_weapon_back_key = ttk.Combobox(ce_row5, values=[""] + KEY_LIST, width=6, state="readonly")
        self.ce_weapon_back_key.pack(side=tk.LEFT, padx=5)

        ce_row6 = ttk.Frame(ce_frame)
        ce_row6.pack(fill=tk.X, pady=2)
        ttk.Label(ce_row6, text="5. Potion di kota:").pack(side=tk.LEFT)
        self.ce_potion_key = ttk.Combobox(ce_row6, values=[""] + KEY_LIST, width=6, state="readonly")
        self.ce_potion_key.pack(side=tk.LEFT, padx=5)

        # Other farming options
        other_frame = ttk.LabelFrame(self.parent, text="Opsi Farming Lainnya", padding=10)
        other_frame.pack(fill=tk.X, padx=5, pady=5)

        self.auto_letter = tk.BooleanVar(value=False)
        row_letter = ttk.Frame(other_frame)
        row_letter.pack(fill=tk.X, pady=2)
        ttk.Checkbutton(row_letter, text=self.lang.get("auto_letter", "Auto terima surat (T)"),
                        variable=self.auto_letter).pack(side=tk.LEFT)
        ttk.Label(row_letter, text=self.lang.get("after", "Setelah")).pack(side=tk.LEFT, padx=(10, 5))
        self.auto_letter_min = ttk.Entry(row_letter, width=5)
        self.auto_letter_min.pack(side=tk.LEFT)
        self.auto_letter_min.insert(0, "30")
        ttk.Label(row_letter, text=self.lang.get("minutes", "menit")).pack(side=tk.LEFT, padx=5)

        self.auto_buy = tk.BooleanVar(value=False)
        ttk.Checkbutton(other_frame, text=self.lang.get("auto_buy", "Beli item otomatis"),
                        variable=self.auto_buy).pack(anchor=tk.W, pady=2)

        # Auto buy potion
        potion_frame = ttk.LabelFrame(self.parent, text="Auto Buy Potion", padding=10)
        potion_frame.pack(fill=tk.X, padx=5, pady=5)

        pot_row1 = ttk.Frame(potion_frame)
        pot_row1.pack(fill=tk.X, pady=2)
        self.auto_potion_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(pot_row1, text="Auto beli potion saat jumlah di bawah",
                        variable=self.auto_potion_enabled).pack(side=tk.LEFT)
        self.potion_threshold = ttk.Entry(pot_row1, width=6)
        self.potion_threshold.pack(side=tk.LEFT, padx=5)
        self.potion_threshold.insert(0, "100")

        pot_row2 = ttk.Frame(potion_frame)
        pot_row2.pack(fill=tk.X, pady=2)
        ttk.Label(pot_row2, text="Posisi potion X%:").pack(side=tk.LEFT)
        self.potion_x = ttk.Entry(pot_row2, width=6)
        self.potion_x.pack(side=tk.LEFT, padx=2)
        self.potion_x.insert(0, "75.0")
        ttk.Label(pot_row2, text="Y%:").pack(side=tk.LEFT)
        self.potion_y = ttk.Entry(pot_row2, width=6)
        self.potion_y.pack(side=tk.LEFT, padx=2)
        self.potion_y.insert(0, "92.0")
        ttk.Label(pot_row2, text="Cek setiap (menit):").pack(side=tk.LEFT, padx=(10, 0))
        self.potion_check_interval = ttk.Entry(pot_row2, width=5)
        self.potion_check_interval.pack(side=tk.LEFT, padx=2)
        self.potion_check_interval.insert(0, "5")

        self.potion_status = ttk.Label(potion_frame, text="")
        self.potion_status.pack(anchor=tk.W, pady=2)

        # Debug & Test
        debug_frame = ttk.LabelFrame(self.parent, text="Debug / Kalibrasi", padding=5)
        debug_frame.pack(fill=tk.X, padx=5, pady=5)

        btn_row = ttk.Frame(debug_frame)
        btn_row.pack(fill=tk.X, pady=2)
        self.btn_screenshot = ttk.Button(btn_row, text="Simpan Screenshot + Grid",
                                          command=self._on_save_screenshot)
        self.btn_screenshot.pack(side=tk.LEFT, padx=2)
        self._save_screenshot_callback = None

        self.btn_test_tp = ttk.Button(btn_row, text="Test Teleport",
                                       command=self._on_test_teleport)
        self.btn_test_tp.pack(side=tk.LEFT, padx=2)
        self._test_tp_callback = None

        # Pin icon position (user-adjustable)
        pin_row = ttk.Frame(debug_frame)
        pin_row.pack(fill=tk.X, pady=2)
        ttk.Label(pin_row, text="Pin icon X%:").pack(side=tk.LEFT)
        self.pin_x = ttk.Entry(pin_row, width=6)
        self.pin_x.pack(side=tk.LEFT, padx=2)
        self.pin_x.insert(0, "4.0")
        ttk.Label(pin_row, text="Y%:").pack(side=tk.LEFT)
        self.pin_y = ttk.Entry(pin_row, width=6)
        self.pin_y.pack(side=tk.LEFT, padx=2)
        self.pin_y.insert(0, "24.0")
        ttk.Label(pin_row, text="(lihat screenshot grid)").pack(side=tk.LEFT, padx=5)

        # Status
        self.status_label = ttk.Label(self.parent, text="")
        self.status_label.pack(anchor=tk.W, padx=5, pady=5)

    def apply_settings(self, settings: dict):
        self.teleport_enabled.set(settings.get("auto_teleport_enabled", False))
        spots = settings.get("teleport_spots", [False] * 5)
        for i, var in enumerate(self.spot_vars):
            var.set(spots[i] if i < len(spots) else False)
        self.tp_after_town.set(settings.get("teleport_after_town_enabled", False))
        self.tp_after_town_min.delete(0, tk.END)
        self.tp_after_town_min.insert(0, str(settings.get("teleport_after_town_minutes", 5)))
        self.tp_during_farm.set(settings.get("teleport_during_farm_enabled", False))
        self.tp_during_farm_min.delete(0, tk.END)
        self.tp_during_farm_min.insert(0, str(settings.get("teleport_during_farm_minutes", 30)))
        if settings.get("teleport_key_after"):
            self.tp_key_after.set(settings["teleport_key_after"])
        self.auto_letter.set(settings.get("auto_check_letter", False))
        self.auto_letter_min.delete(0, tk.END)
        self.auto_letter_min.insert(0, str(settings.get("auto_check_letter_minutes", 30)))
        self.auto_buy.set(settings.get("auto_buy_items", False))
        self.auto_potion_enabled.set(settings.get("auto_potion_enabled", False))
        self.potion_threshold.delete(0, tk.END)
        self.potion_threshold.insert(0, str(settings.get("potion_threshold", 100)))
        self.potion_x.delete(0, tk.END)
        self.potion_x.insert(0, str(settings.get("potion_pos_x", 75.0)))
        self.potion_y.delete(0, tk.END)
        self.potion_y.insert(0, str(settings.get("potion_pos_y", 92.0)))
        self.potion_check_interval.delete(0, tk.END)
        self.potion_check_interval.insert(0, str(settings.get("potion_check_interval", 5)))
        self.combat_escape_enabled.set(settings.get("combat_escape_enabled", False))
        self.ce_hp_threshold.delete(0, tk.END)
        self.ce_hp_threshold.insert(0, str(settings.get("combat_escape_hp", 50)))
        if settings.get("combat_escape_weapon_key"):
            self.ce_weapon_key.set(settings["combat_escape_weapon_key"])
        if settings.get("combat_escape_skill_key"):
            self.ce_skill_key.set(settings["combat_escape_skill_key"])
        self.ce_skill_slot.set(str(settings.get("combat_escape_skill_slot", 4)))
        if settings.get("combat_escape_teleport_key"):
            self.ce_teleport_key.set(settings["combat_escape_teleport_key"])
        if settings.get("combat_escape_weapon_back_key"):
            self.ce_weapon_back_key.set(settings["combat_escape_weapon_back_key"])
        if settings.get("combat_escape_potion_key"):
            self.ce_potion_key.set(settings["combat_escape_potion_key"])

    def _on_save_screenshot(self):
        """Save debug screenshot with grid overlay."""
        if self._save_screenshot_callback:
            self._save_screenshot_callback()

    def _on_test_teleport(self):
        """Trigger test teleport via callback."""
        if self._test_tp_callback:
            import threading
            threading.Thread(target=self._test_tp_callback, daemon=True).start()

    def get_pin_position(self) -> tuple[float, float]:
        """Get pin icon normalized position from UI."""
        try:
            px = float(self.pin_x.get()) / 100.0
            py = float(self.pin_y.get()) / 100.0
            return (px, py)
        except ValueError:
            return (0.04, 0.24)

    def collect_settings(self) -> dict:
        return {
            "auto_teleport_enabled": self.teleport_enabled.get(),
            "teleport_spots": [v.get() for v in self.spot_vars],
            "teleport_after_town_enabled": self.tp_after_town.get(),
            "teleport_after_town_minutes": float(self.tp_after_town_min.get() or 5),
            "teleport_during_farm_enabled": self.tp_during_farm.get(),
            "teleport_during_farm_minutes": float(self.tp_during_farm_min.get() or 30),
            "teleport_key_after": self.tp_key_after.get(),
            "auto_check_letter": self.auto_letter.get(),
            "auto_check_letter_minutes": int(self.auto_letter_min.get() or 30),
            "auto_buy_items": self.auto_buy.get(),
            "auto_potion_enabled": self.auto_potion_enabled.get(),
            "potion_threshold": int(self.potion_threshold.get() or 100),
            "potion_pos_x": float(self.potion_x.get() or 75.0),
            "potion_pos_y": float(self.potion_y.get() or 92.0),
            "potion_check_interval": int(self.potion_check_interval.get() or 5),
            "combat_escape_enabled": self.combat_escape_enabled.get(),
            "combat_escape_hp": int(self.ce_hp_threshold.get() or 50),
            "combat_escape_weapon_key": self.ce_weapon_key.get(),
            "combat_escape_skill_key": self.ce_skill_key.get(),
            "combat_escape_skill_slot": int(self.ce_skill_slot.get() or 4),
            "combat_escape_teleport_key": self.ce_teleport_key.get(),
            "combat_escape_weapon_back_key": self.ce_weapon_back_key.get(),
            "combat_escape_potion_key": self.ce_potion_key.get(),
        }
