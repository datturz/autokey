"""L2M AutoKey - Lineage 2M Automation Tool.

Must be run as Administrator for keystroke sending to work.
License validation (1 PC = 1 Code) via Supabase before launch.

Usage: python main.py
"""
import sys
import os
import ctypes
import hashlib
import uuid
import json


# ── Supabase config (autokey project) ──
SUPABASE_URL = "https://fpccqibibfsqefziavqj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZwY2NxaWJpYmZzcWVmemlhdnFqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMzMTUzNDgsImV4cCI6MjA4ODg5MTM0OH0.PVYyilHJ4VyLdExjhkbPNT4Z8HidV5JPHrNkCDWerL8"


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def run_as_admin():
    """Re-launch this script with administrator privileges."""
    if hasattr(sys, '_MEIPASS'):
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, "", None, 1
        )
    else:
        script = os.path.abspath(__file__)
        params = f'"{script}"'
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, params, None, 1
        )
    return ret > 32


def get_hwid() -> str:
    """Generate hardware ID from machine-specific identifiers.
    Combines: machine UUID + MAC address → SHA256 → 16 char hex.
    """
    try:
        import subprocess
        # Get machine UUID from BIOS (unique per motherboard)
        r = subprocess.run(
            ['wmic', 'csproduct', 'get', 'UUID'],
            capture_output=True, text=True, timeout=5
        )
        machine_uuid = r.stdout.strip().split('\n')[-1].strip()
    except Exception:
        machine_uuid = "unknown"

    # MAC address
    mac = hex(uuid.getnode())

    raw = f"{machine_uuid}:{mac}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16].upper()


def _get_license_cache_path() -> str:
    """Path to cached license code (next to exe or in project root)."""
    if hasattr(sys, '_MEIPASS'):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, ".license")


def _load_cached_code() -> str:
    """Load previously entered code from cache file."""
    path = _get_license_cache_path()
    try:
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
                return data.get("code", "")
    except Exception:
        pass
    return ""


def _save_cached_code(code: str):
    """Save code to cache file so user doesn't re-enter every time."""
    path = _get_license_cache_path()
    try:
        with open(path, 'w') as f:
            json.dump({"code": code}, f)
    except Exception:
        pass


def _check_license_silent(code: str, hwid: str) -> tuple[bool, str]:
    """Check license against Supabase without UI. Returns (valid, message)."""
    from datetime import datetime, timezone
    if not code:
        return False, "No code"
    try:
        from supabase import create_client
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        resp = client.table("licenses").select("*").eq("code", code).execute()
        if not resp.data:
            return False, "Code tidak valid"
        lic = resp.data[0]
        if not lic.get("is_active", False):
            return False, "Code dinonaktifkan"
        expires_str = lic.get("expires_at", "")
        if expires_str:
            try:
                expires = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) > expires:
                    return False, "Code sudah expired"
            except Exception:
                pass
        stored_hwid = lic.get("hwid", "")
        if stored_hwid and stored_hwid != hwid:
            return False, "Code sudah dipakai di PC lain"
        if not stored_hwid:
            client.table("licenses").update({
                "hwid": hwid,
                "activated_at": datetime.now(timezone.utc).isoformat()
            }).eq("code", code).execute()
        return True, "Valid"
    except Exception as e:
        return False, f"Koneksi gagal: {e}"


def validate_license() -> bool:
    """Validate license — auto-check cached code first, show dialog only if needed."""
    import tkinter as tk
    from tkinter import ttk, messagebox
    from datetime import datetime, timezone

    hwid = get_hwid()
    cached_code = _load_cached_code()

    # Auto-validate cached code (skip dialog if still valid)
    if cached_code:
        valid, msg = _check_license_silent(cached_code, hwid)
        if valid:
            print(f"[License] Auto-validated: {cached_code}")
            return True
        else:
            print(f"[License] Cached code failed: {msg}")

    result = {"valid": False}

    def do_validate(code: str, status_label, dialog):
        """Validate code against Supabase."""
        if not code:
            status_label.config(text="Masukkan code!", foreground="red")
            return False

        status_label.config(text="Memvalidasi...", foreground="gray")
        dialog.update()

        try:
            from supabase import create_client
            client = create_client(SUPABASE_URL, SUPABASE_KEY)
            resp = client.table("licenses").select("*").eq("code", code).execute()

            if not resp.data or len(resp.data) == 0:
                status_label.config(text="Code tidak valid!", foreground="red")
                return False

            license_data = resp.data[0]

            # Check is_active
            if not license_data.get("is_active", False):
                status_label.config(text="Code dinonaktifkan!", foreground="red")
                return False

            # Check expiry
            expires_str = license_data.get("expires_at", "")
            if expires_str:
                try:
                    expires = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
                    if datetime.now(timezone.utc) > expires:
                        status_label.config(text="Code sudah expired!", foreground="red")
                        return False
                except Exception:
                    pass

            # Check HWID
            stored_hwid = license_data.get("hwid", "")

            if not stored_hwid:
                # First activation — bind to this PC
                try:
                    client.table("licenses").update({
                        "hwid": hwid,
                        "activated_at": datetime.now(timezone.utc).isoformat()
                    }).eq("code", code).execute()
                    status_label.config(text="Aktivasi berhasil!", foreground="green")
                except Exception as e:
                    status_label.config(text=f"Gagal aktivasi: {e}", foreground="red")
                    return False
            elif stored_hwid != hwid:
                # Different PC
                status_label.config(text="Code sudah dipakai di PC lain!", foreground="red")
                return False

            # Valid!
            _save_cached_code(code)
            return True

        except Exception as e:
            status_label.config(text=f"Koneksi gagal: {e}", foreground="red")
            return False

    def on_submit(event=None):
        code = code_entry.get().strip().upper()
        if do_validate(code, status_label, dialog):
            result["valid"] = True
            dialog.destroy()

    def on_close():
        result["valid"] = False
        dialog.destroy()

    # ── Build dialog ──
    dialog = tk.Tk()
    dialog.title("L2M AutoKey - Aktivasi")
    dialog.geometry("420x250")
    dialog.resizable(False, False)
    dialog.protocol("WM_DELETE_WINDOW", on_close)

    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() - 420) // 2
    y = (dialog.winfo_screenheight() - 250) // 2
    dialog.geometry(f"420x250+{x}+{y}")

    frame = ttk.Frame(dialog, padding=20)
    frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(frame, text="L2M AutoKey", font=("Segoe UI", 14, "bold")).pack(pady=(0, 5))

    # Show HWID
    hwid_frame = ttk.Frame(frame)
    hwid_frame.pack(fill=tk.X, pady=(0, 8))
    ttk.Label(hwid_frame, text="Hardware ID:", foreground="gray").pack(side=tk.LEFT)
    hwid_entry = ttk.Entry(hwid_frame, font=("Consolas", 10), width=20)
    hwid_entry.pack(side=tk.LEFT, padx=5)
    hwid_entry.insert(0, hwid)
    hwid_entry.config(state="readonly")

    def copy_hwid():
        dialog.clipboard_clear()
        dialog.clipboard_append(hwid)
        copy_btn.config(text="Copied!")
        dialog.after(1500, lambda: copy_btn.config(text="Copy"))

    copy_btn = ttk.Button(hwid_frame, text="Copy", command=copy_hwid, width=6)
    copy_btn.pack(side=tk.LEFT)

    # Code input
    ttk.Label(frame, text="Masukkan License Code:").pack(anchor=tk.W)
    code_entry = ttk.Entry(frame, width=30, font=("Consolas", 12))
    code_entry.pack(pady=5, fill=tk.X)
    code_entry.bind("<Return>", on_submit)

    # Pre-fill cached code
    if cached_code:
        code_entry.insert(0, cached_code)
    code_entry.focus()

    ttk.Button(frame, text="Aktivasi", command=on_submit).pack(pady=5)

    status_label = ttk.Label(frame, text="", foreground="gray")
    status_label.pack()

    dialog.mainloop()
    return result["valid"]


def main():
    if hasattr(sys, '_MEIPASS'):
        os.chdir(sys._MEIPASS)
    else:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Auto-elevate to admin if not already
    if not is_admin():
        print("Bukan Administrator. Meminta elevasi...")
        if run_as_admin():
            sys.exit(0)
        else:
            print("Elevasi ditolak. Coba jalankan manual: Klik kanan > Run as Administrator")
            input("Tekan Enter untuk keluar...")
            sys.exit(1)

    # License validation
    if not validate_license():
        sys.exit(0)

    # We are admin + license valid
    import tkinter as tk
    from tkinter import ttk

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    root = tk.Tk()

    style = ttk.Style()
    for preferred in ("clam", "vista", "xpnative", "winnative"):
        if preferred in style.theme_names():
            style.theme_use(preferred)
            break

    style.configure("TLabel", padding=2)
    style.configure("TButton", padding=(8, 4))
    style.configure("TCheckbutton", padding=2)
    style.configure("TLabelframe", padding=5)

    from ui.app import L2MAutoKeyApp
    app = L2MAutoKeyApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
