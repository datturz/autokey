"""Radar tab - radar target detection settings."""
import tkinter as tk
from tkinter import ttk
from core.key_sender import KEY_LIST


class TabRadar:
    """Radar detection settings tab."""

    def __init__(self, parent: ttk.Frame, lang: dict):
        self.parent = parent
        self.lang = lang
        self._build_ui()

    def _build_ui(self):
        # Radar Scan Settings
        scan_frame = ttk.LabelFrame(self.parent, text="Radar Scan", padding=10)
        scan_frame.pack(fill=tk.X, padx=5, pady=5)

        scan_row1 = ttk.Frame(scan_frame)
        scan_row1.pack(fill=tk.X, pady=2)
        self.scan_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(scan_row1, text="Aktifkan Radar Scan",
                        variable=self.scan_enabled).pack(side=tk.LEFT)

        scan_row2 = ttk.Frame(scan_frame)
        scan_row2.pack(fill=tk.X, pady=2)
        ttk.Label(scan_row2, text="Key Radar:").pack(side=tk.LEFT)
        self.scan_key = ttk.Combobox(scan_row2, values=[""] + KEY_LIST, width=6, state="readonly")
        self.scan_key.pack(side=tk.LEFT, padx=5)
        ttk.Label(scan_row2, text="Interval (s):").pack(side=tk.LEFT, padx=(10, 0))
        self.scan_interval = ttk.Entry(scan_row2, width=5)
        self.scan_interval.pack(side=tk.LEFT, padx=5)
        self.scan_interval.insert(0, "3")

        scan_row3 = ttk.Frame(scan_frame)
        scan_row3.pack(fill=tk.X, pady=2)
        ttk.Label(scan_row3, text="Escape Key (kabur):").pack(side=tk.LEFT)
        self.scan_escape_key = ttk.Combobox(scan_row3, values=[""] + KEY_LIST, width=6, state="readonly")
        self.scan_escape_key.pack(side=tk.LEFT, padx=5)

        # Radar Condition 1
        frame1 = ttk.LabelFrame(self.parent, text="Kondisi Radar 1", padding=10)
        frame1.pack(fill=tk.X, padx=5, pady=5)

        row1 = ttk.Frame(frame1)
        row1.pack(fill=tk.X, pady=2)
        self.radar1_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(row1, text=self.lang.get("radar_more_than", "Ketika lebih dari"),
                        variable=self.radar1_enabled).pack(side=tk.LEFT)
        self.radar1_count = ttk.Combobox(row1, values=list(range(1, 10)), width=3, state="readonly")
        self.radar1_count.pack(side=tk.LEFT, padx=5)
        self.radar1_count.set("1")
        ttk.Label(row1, text=self.lang.get("radar_targets", "target")).pack(side=tk.LEFT)

        row1b = ttk.Frame(frame1)
        row1b.pack(fill=tk.X, pady=2)
        ttk.Label(row1b, text=self.lang.get("press_key", "Tekan:")).pack(side=tk.LEFT)
        self.radar1_key = ttk.Combobox(row1b, values=KEY_LIST, width=6, state="readonly")
        self.radar1_key.pack(side=tk.LEFT, padx=5)
        ttk.Label(row1b, text=self.lang.get("wait_time", "Tunggu(s):")).pack(side=tk.LEFT, padx=(10, 0))
        self.radar1_delay = ttk.Entry(row1b, width=5)
        self.radar1_delay.pack(side=tk.LEFT, padx=5)
        self.radar1_delay.insert(0, "3.0")

        # Radar Condition 2
        frame2 = ttk.LabelFrame(self.parent, text="Kondisi Radar 2", padding=10)
        frame2.pack(fill=tk.X, padx=5, pady=5)

        row2 = ttk.Frame(frame2)
        row2.pack(fill=tk.X, pady=2)
        self.radar2_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(row2, text=self.lang.get("radar_more_than", "Ketika lebih dari"),
                        variable=self.radar2_enabled).pack(side=tk.LEFT)
        self.radar2_count = ttk.Combobox(row2, values=list(range(1, 10)), width=3, state="readonly")
        self.radar2_count.pack(side=tk.LEFT, padx=5)
        self.radar2_count.set("2")
        ttk.Label(row2, text=self.lang.get("radar_targets", "target")).pack(side=tk.LEFT)

        row2b = ttk.Frame(frame2)
        row2b.pack(fill=tk.X, pady=2)
        ttk.Label(row2b, text=self.lang.get("press_key", "Tekan:")).pack(side=tk.LEFT)
        self.radar2_key = ttk.Combobox(row2b, values=KEY_LIST, width=6, state="readonly")
        self.radar2_key.pack(side=tk.LEFT, padx=5)
        ttk.Label(row2b, text=self.lang.get("wait_time", "Tunggu(s):")).pack(side=tk.LEFT, padx=(10, 0))
        self.radar2_delay = ttk.Entry(row2b, width=5)
        self.radar2_delay.pack(side=tk.LEFT, padx=5)
        self.radar2_delay.insert(0, "3.0")

        # Warning target
        frame3 = ttk.LabelFrame(self.parent, text="Target Peringatan", padding=10)
        frame3.pack(fill=tk.X, padx=5, pady=5)

        row3 = ttk.Frame(frame3)
        row3.pack(fill=tk.X, pady=2)
        self.warning_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(row3, text=self.lang.get("alert_target", "Saat menemui target peringatan"),
                        variable=self.warning_enabled).pack(side=tk.LEFT)

        row3b = ttk.Frame(frame3)
        row3b.pack(fill=tk.X, pady=2)
        ttk.Label(row3b, text=self.lang.get("press_key", "Tekan:")).pack(side=tk.LEFT)
        self.warning_key = ttk.Combobox(row3b, values=KEY_LIST, width=6, state="readonly")
        self.warning_key.pack(side=tk.LEFT, padx=5)
        ttk.Label(row3b, text=self.lang.get("wait_time", "Tunggu(s):")).pack(side=tk.LEFT, padx=(10, 0))
        self.warning_delay = ttk.Entry(row3b, width=5)
        self.warning_delay.pack(side=tk.LEFT, padx=5)
        self.warning_delay.insert(0, "3.0")
        self.warning_screenshot = tk.BooleanVar(value=False)
        ttk.Checkbutton(row3b, text=self.lang.get("save_image", "Screenshot"),
                        variable=self.warning_screenshot).pack(side=tk.LEFT, padx=(10, 0))

        # Status
        self.status_label = ttk.Label(self.parent, text="Radar: -")
        self.status_label.pack(anchor=tk.W, padx=5, pady=5)

    def apply_settings(self, settings: dict):
        self.scan_enabled.set(settings.get("radar_scan_enabled", False))
        if settings.get("radar_scan_key"):
            self.scan_key.set(settings["radar_scan_key"])
        self.scan_interval.delete(0, tk.END)
        self.scan_interval.insert(0, str(settings.get("radar_scan_interval", 3)))
        if settings.get("radar_scan_escape_key"):
            self.scan_escape_key.set(settings["radar_scan_escape_key"])
        self.radar1_enabled.set(settings.get("radar_condition1_enabled", False))
        self.radar1_count.set(str(settings.get("radar_condition1_count", 1)))
        if settings.get("radar_condition1_key"):
            self.radar1_key.set(settings["radar_condition1_key"])
        self.radar1_delay.delete(0, tk.END)
        self.radar1_delay.insert(0, str(settings.get("radar_condition1_delay", 3.0)))

        self.radar2_enabled.set(settings.get("radar_condition2_enabled", False))
        self.radar2_count.set(str(settings.get("radar_condition2_count", 2)))
        if settings.get("radar_condition2_key"):
            self.radar2_key.set(settings["radar_condition2_key"])
        self.radar2_delay.delete(0, tk.END)
        self.radar2_delay.insert(0, str(settings.get("radar_condition2_delay", 3.0)))

        self.warning_enabled.set(settings.get("radar_warning_enabled", False))
        if settings.get("radar_warning_key"):
            self.warning_key.set(settings["radar_warning_key"])
        self.warning_delay.delete(0, tk.END)
        self.warning_delay.insert(0, str(settings.get("radar_warning_delay", 3.0)))
        self.warning_screenshot.set(settings.get("radar_warning_screenshot", False))

    def collect_settings(self) -> dict:
        return {
            "radar_scan_enabled": self.scan_enabled.get(),
            "radar_scan_key": self.scan_key.get(),
            "radar_scan_interval": float(self.scan_interval.get() or 3),
            "radar_scan_escape_key": self.scan_escape_key.get(),
            "radar_condition1_enabled": self.radar1_enabled.get(),
            "radar_condition1_count": int(self.radar1_count.get() or 1),
            "radar_condition1_key": self.radar1_key.get(),
            "radar_condition1_delay": float(self.radar1_delay.get() or 3.0),
            "radar_condition2_enabled": self.radar2_enabled.get(),
            "radar_condition2_count": int(self.radar2_count.get() or 2),
            "radar_condition2_key": self.radar2_key.get(),
            "radar_condition2_delay": float(self.radar2_delay.get() or 3.0),
            "radar_warning_enabled": self.warning_enabled.get(),
            "radar_warning_key": self.warning_key.get(),
            "radar_warning_delay": float(self.warning_delay.get() or 3.0),
            "radar_warning_screenshot": self.warning_screenshot.get(),
        }
