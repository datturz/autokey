"""L2M AutoKey - Lineage 2M Automation Tool.

Must be run as Administrator for keystroke sending to work.
PIN validation via Supabase before launch.

Usage: python main.py
"""
import sys
import os
import ctypes


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
        # Running as exe
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


def validate_pin() -> bool:
    """Show PIN dialog and validate against Supabase."""
    import tkinter as tk
    from tkinter import ttk, messagebox

    try:
        from dotenv import load_dotenv
        env_path = get_resource_path('.env')
        if os.path.exists(env_path):
            load_dotenv(env_path)
        else:
            load_dotenv()
    except ImportError:
        pass

    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_KEY", "")

    if not supabase_url or not supabase_key:
        messagebox.showerror("Error", "Konfigurasi server tidak ditemukan.")
        return False

    result = {"valid": False}

    def on_submit(event=None):
        pin = pin_entry.get().strip()
        if not pin:
            status_label.config(text="Masukkan PIN!", foreground="red")
            return

        status_label.config(text="Memvalidasi...", foreground="gray")
        dialog.update()

        try:
            from supabase import create_client
            client = create_client(supabase_url, supabase_key)
            resp = client.table("pin_validation").select("pin").eq("pin", pin).execute()
            if resp.data and len(resp.data) > 0:
                result["valid"] = True
                dialog.destroy()
            else:
                status_label.config(text="PIN salah!", foreground="red")
                pin_entry.delete(0, tk.END)
                pin_entry.focus()
        except Exception as e:
            status_label.config(text=f"Koneksi gagal: {e}", foreground="red")

    def on_close():
        result["valid"] = False
        dialog.destroy()

    dialog = tk.Tk()
    dialog.title("L2M AutoKey - Login")
    dialog.geometry("350x180")
    dialog.resizable(False, False)
    dialog.protocol("WM_DELETE_WINDOW", on_close)

    # Center on screen
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() - 350) // 2
    y = (dialog.winfo_screenheight() - 180) // 2
    dialog.geometry(f"350x180+{x}+{y}")

    frame = ttk.Frame(dialog, padding=20)
    frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(frame, text="L2M AutoKey", font=("Segoe UI", 14, "bold")).pack(pady=(0, 10))
    ttk.Label(frame, text="Masukkan PIN:").pack(anchor=tk.W)

    pin_entry = ttk.Entry(frame, show="*", width=30, font=("Segoe UI", 12))
    pin_entry.pack(pady=5, fill=tk.X)
    pin_entry.bind("<Return>", on_submit)
    pin_entry.focus()

    ttk.Button(frame, text="Login", command=on_submit).pack(pady=5)

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

    # PIN validation
    if not validate_pin():
        sys.exit(0)

    # We are admin + PIN valid
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
