"""Radar tab - radar target detection settings."""
import os
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from core.key_sender import KEY_LIST


class TabRadar:
    """Radar detection settings tab."""

    def __init__(self, parent: ttk.Frame, lang: dict):
        self.parent = parent
        self.lang = lang
        self._build_ui()

    def _build_ui(self):
        # ── Make the tab scrollable (content grows tall, window stays compact) ──
        outer = self.parent
        canvas = tk.Canvas(outer, borderwidth=0, highlightthickness=0)
        vbar = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=vbar.set)
        vbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inner = ttk.Frame(canvas)
        inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_inner_configure(_event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        inner.bind("<Configure>", _on_inner_configure)

        def _on_canvas_configure(event):
            canvas.itemconfig(inner_id, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        # Mouse wheel — only active when cursor is over this tab
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))

        # Re-route self.parent so all widgets below pack into the scrollable inner frame
        self.parent = inner

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

        # ── Emblem Detection (DISABLED — commented out for release) ──
        # Feature disabled. Dummy tk vars kept for apply_settings/collect_settings
        # compatibility. Re-enable by removing `if False:` guard below.
        self.emblem_enabled = tk.BooleanVar(value=False)
        self.emblem_escape_key = tk.StringVar(value="")
        self.emblem_delay = tk.StringVar(value="3.0")
        self.emblem_listbox = None
        self.own_emblem_listbox = None
        self._emblem_reload_cb = None

        if False:  # Emblem UI disabled — remove this guard to re-enable
            emblem_frame = ttk.LabelFrame(self.parent, text="Emblem Detection (Pre-Radar)", padding=10)
            emblem_frame.pack(fill=tk.X, padx=5, pady=5)

            em_row1 = ttk.Frame(emblem_frame)
            em_row1.pack(fill=tk.X, pady=2)
            ttk.Checkbutton(em_row1, text="Aktifkan deteksi emblem musuh",
                            variable=self.emblem_enabled).pack(side=tk.LEFT)

            em_row2 = ttk.Frame(emblem_frame)
            em_row2.pack(fill=tk.X, pady=2)
            ttk.Label(em_row2, text="Escape Key:").pack(side=tk.LEFT)
            esc_cb = ttk.Combobox(em_row2, values=KEY_LIST, width=6, state="readonly",
                                  textvariable=self.emblem_escape_key)
            esc_cb.pack(side=tk.LEFT, padx=5)
            ttk.Label(em_row2, text="Wait (s):").pack(side=tk.LEFT, padx=(10, 0))
            delay_entry = ttk.Entry(em_row2, width=5, textvariable=self.emblem_delay)
            delay_entry.pack(side=tk.LEFT, padx=5)

            em_row3 = ttk.Frame(emblem_frame)
            em_row3.pack(fill=tk.X, pady=2)
            ttk.Button(em_row3, text="+ Upload Emblem",
                       command=self._upload_emblem).pack(side=tk.LEFT, padx=2)
            ttk.Button(em_row3, text="- Hapus Selected",
                       command=self._delete_emblem).pack(side=tk.LEFT, padx=2)
            ttk.Button(em_row3, text="Refresh",
                       command=self._refresh_emblem_list).pack(side=tk.LEFT, padx=2)

            em_row4 = ttk.Frame(emblem_frame)
            em_row4.pack(fill=tk.X, pady=2)
            ttk.Label(em_row4, text="Enemy emblem terdaftar:").pack(anchor=tk.W)
            list_frame = ttk.Frame(em_row4)
            list_frame.pack(fill=tk.X, pady=2)
            self.emblem_listbox = tk.Listbox(list_frame, height=3)
            self.emblem_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
            sb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.emblem_listbox.yview)
            sb.pack(side=tk.RIGHT, fill=tk.Y)
            self.emblem_listbox.config(yscrollcommand=sb.set)
            self._refresh_emblem_list()

            own_row = ttk.Frame(emblem_frame)
            own_row.pack(fill=tk.X, pady=(8, 2))
            ttk.Label(own_row, text="Own Emblem (Exclusion):",
                      font=("TkDefaultFont", 9, "bold")).pack(anchor=tk.W)
            own_btn_row = ttk.Frame(emblem_frame)
            own_btn_row.pack(fill=tk.X, pady=2)
            ttk.Button(own_btn_row, text="+ Upload Own Emblem",
                       command=self._upload_own_emblem).pack(side=tk.LEFT, padx=2)
            ttk.Button(own_btn_row, text="- Hapus Selected",
                       command=self._delete_own_emblem).pack(side=tk.LEFT, padx=2)
            own_list_frame = ttk.Frame(emblem_frame)
            own_list_frame.pack(fill=tk.X, pady=2)
            self.own_emblem_listbox = tk.Listbox(own_list_frame, height=3)
            self.own_emblem_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
            sb2 = ttk.Scrollbar(own_list_frame, orient=tk.VERTICAL,
                                command=self.own_emblem_listbox.yview)
            sb2.pack(side=tk.RIGHT, fill=tk.Y)
            self.own_emblem_listbox.config(yscrollcommand=sb2.set)
            self._refresh_own_emblem_list()

        # Status
        self.status_label = ttk.Label(self.parent, text="Radar: -")
        self.status_label.pack(anchor=tk.W, padx=5, pady=5)

    # ── Emblem management ──
    def _assets_dir(self) -> str:
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

    def _refresh_emblem_list(self):
        self.emblem_listbox.delete(0, tk.END)
        assets = self._assets_dir()
        if not os.path.isdir(assets):
            return
        for f in sorted(os.listdir(assets)):
            if f.startswith("enemy_emblem_") and f.lower().endswith((".png", ".jpg", ".jpeg")):
                self.emblem_listbox.insert(tk.END, f)

    def _upload_emblem(self):
        src = filedialog.askopenfilename(
            title="Pilih file emblem (PNG/JPG yang sudah di-crop)",
            filetypes=[("Image files", "*.png *.jpg *.jpeg")],
        )
        if not src:
            return
        name = simpledialog.askstring(
            "Nama Emblem",
            "Nama emblem (contoh: kamel, dragons, dll):\n(huruf/angka/underscore saja)",
        )
        if not name:
            return
        # Sanitize name
        name = "".join(c for c in name.lower() if c.isalnum() or c == "_")
        if not name:
            messagebox.showerror("Error", "Nama tidak valid.")
            return
        ext = os.path.splitext(src)[1].lower() or ".png"
        dst_name = f"enemy_emblem_{name}{ext}"
        dst = os.path.join(self._assets_dir(), dst_name)
        try:
            shutil.copy2(src, dst)
        except Exception as e:
            messagebox.showerror("Error", f"Gagal copy file:\n{e}")
            return
        self._refresh_emblem_list()
        if self._emblem_reload_cb:
            self._emblem_reload_cb()
        messagebox.showinfo("OK", f"Emblem disimpan: {dst_name}")

    def _delete_emblem(self):
        sel = self.emblem_listbox.curselection()
        if not sel:
            return
        fname = self.emblem_listbox.get(sel[0])
        if not messagebox.askyesno("Konfirmasi", f"Hapus emblem {fname}?"):
            return
        try:
            os.remove(os.path.join(self._assets_dir(), fname))
        except Exception as e:
            messagebox.showerror("Error", f"Gagal hapus:\n{e}")
            return
        self._refresh_emblem_list()
        if self._emblem_reload_cb:
            self._emblem_reload_cb()

    def _refresh_own_emblem_list(self):
        self.own_emblem_listbox.delete(0, tk.END)
        assets = self._assets_dir()
        if not os.path.isdir(assets):
            return
        for f in sorted(os.listdir(assets)):
            if f.startswith("own_emblem_") and f.lower().endswith((".png", ".jpg", ".jpeg")):
                self.own_emblem_listbox.insert(tk.END, f)

    def _upload_own_emblem(self):
        src = filedialog.askopenfilename(
            title="Pilih file own emblem (PNG/JPG yang sudah di-crop)",
            filetypes=[("Image files", "*.png *.jpg *.jpeg")],
        )
        if not src:
            return
        name = simpledialog.askstring(
            "Nama Own Emblem",
            "Nama emblem clan sendiri (contoh: toxtricity):\n(huruf/angka/underscore saja)",
        )
        if not name:
            return
        name = "".join(c for c in name.lower() if c.isalnum() or c == "_")
        if not name:
            messagebox.showerror("Error", "Nama tidak valid.")
            return
        ext = os.path.splitext(src)[1].lower() or ".png"
        dst_name = f"own_emblem_{name}{ext}"
        dst = os.path.join(self._assets_dir(), dst_name)
        try:
            shutil.copy2(src, dst)
        except Exception as e:
            messagebox.showerror("Error", f"Gagal copy file:\n{e}")
            return
        self._refresh_own_emblem_list()
        if self._emblem_reload_cb:
            self._emblem_reload_cb()
        messagebox.showinfo("OK", f"Own emblem disimpan: {dst_name}")

    def _delete_own_emblem(self):
        sel = self.own_emblem_listbox.curselection()
        if not sel:
            return
        fname = self.own_emblem_listbox.get(sel[0])
        if not messagebox.askyesno("Konfirmasi", f"Hapus own emblem {fname}?"):
            return
        try:
            os.remove(os.path.join(self._assets_dir(), fname))
        except Exception as e:
            messagebox.showerror("Error", f"Gagal hapus:\n{e}")
            return
        self._refresh_own_emblem_list()
        if self._emblem_reload_cb:
            self._emblem_reload_cb()

    def set_emblem_reload_callback(self, cb):
        """app.py wires this to EmblemDetector.reload()."""
        self._emblem_reload_cb = cb

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

        # Emblem detection (DISABLED — settings still load for forward-compat)
        self.emblem_enabled.set(settings.get("emblem_detection_enabled", False))
        if settings.get("emblem_escape_key"):
            self.emblem_escape_key.set(settings["emblem_escape_key"])
        self.emblem_delay.set(str(settings.get("emblem_delay", 3.0)))

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
            "emblem_detection_enabled": self.emblem_enabled.get(),
            "emblem_escape_key": self.emblem_escape_key.get(),
            "emblem_delay": float(self.emblem_delay.get() or 3.0),
        }
