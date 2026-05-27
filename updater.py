"""Auto-updater for L2M AutoKey.

Checks GitHub releases for newer version (max once per 24h),
downloads the exe, and replaces the current binary via a detached
batch script that restarts the app.
"""
import os
import sys
import json
import time
import subprocess
import tempfile
import threading
import urllib.request
import tkinter as tk
from tkinter import ttk, messagebox

from version import APP_VERSION

GITHUB_REPO = "datturz/autokey"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
CHECK_INTERVAL_SECONDS = 24 * 3600  # 24 hours


def _get_check_cache_path() -> str:
    """Path to last-check timestamp file (next to exe or in project root)."""
    if hasattr(sys, '_MEIPASS'):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, ".update_check")


def _load_last_check_ts() -> float:
    path = _get_check_cache_path()
    try:
        if os.path.exists(path):
            with open(path, 'r') as f:
                return float(json.load(f).get("ts", 0))
    except Exception:
        pass
    return 0.0


def _save_last_check_ts():
    path = _get_check_cache_path()
    try:
        with open(path, 'w') as f:
            json.dump({"ts": time.time()}, f)
    except Exception:
        pass


def _is_newer(current: str, latest: str) -> bool:
    try:
        cur = [int(x) for x in current.split(".")]
        lat = [int(x) for x in latest.split(".")]
        return lat > cur
    except Exception:
        return False


def _fetch_latest_release(timeout: int = 10):
    """Returns (latest_version, download_url) or None."""
    try:
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={"User-Agent": "L2M-AutoKey-Updater/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
        latest = data.get("tag_name", "").lstrip("v")
        download_url = None
        for asset in data.get("assets", []):
            if asset.get("name", "").endswith(".exe"):
                download_url = asset.get("browser_download_url")
                break
        if latest and download_url:
            return (latest, download_url)
    except Exception as e:
        print(f"[Updater] Check error: {e}")
    return None


def _download_with_progress(url: str, dest: str, progress_cb=None) -> bool:
    """Download URL to dest. progress_cb(downloaded, total) called per chunk."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "L2M-AutoKey-Updater/1.0",
            "Accept": "application/octet-stream",
        })
        with urllib.request.urlopen(req, timeout=300) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            with open(dest, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_cb:
                        progress_cb(downloaded, total)
        actual = os.path.getsize(dest)
        if actual < 10 * 1024 * 1024:
            print(f"[Updater] Downloaded file too small: {actual} bytes")
            return False
        return True
    except Exception as e:
        print(f"[Updater] Download error: {e}")
        return False


def _install_update(temp_file: str, parent=None):
    """Replace current exe with downloaded one via batch script, then exit."""
    if not getattr(sys, 'frozen', False):
        messagebox.showinfo(
            "Update",
            "Update downloaded. Restart in production build to install.",
            parent=parent,
        )
        return

    current_exe = sys.executable
    exe_name = os.path.basename(current_exe)
    exe_dir = os.path.dirname(current_exe)
    batch_file = os.path.join(exe_dir, "update_l2m_autokey.bat")
    batch_content = f'''@echo off
echo Waiting for application to close...
timeout /t 5 /nobreak > nul
taskkill /f /im "{exe_name}" >nul 2>&1
timeout /t 3 /nobreak > nul

:retry
echo Copying update...
copy /y "{temp_file}" "{current_exe}"
if errorlevel 1 (
    echo Copy failed, retrying in 5 seconds...
    taskkill /f /im "{exe_name}" >nul 2>&1
    timeout /t 5 /nobreak > nul
    goto retry
)
del "{temp_file}" 2>nul
echo Starting updated application...
cd /d "{exe_dir}"
start "" "{current_exe}"
timeout /t 3 /nobreak > nul
del "%~f0"
'''
    with open(batch_file, 'w') as f:
        f.write(batch_content)

    CREATE_NEW_PROCESS_GROUP = 0x00000200
    DETACHED_PROCESS = 0x00000008
    subprocess.Popen(
        ['cmd', '/c', batch_file],
        creationflags=CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS,
        close_fds=True,
        cwd=exe_dir,
    )
    sys.exit(0)


def _prompt_and_download(parent, latest: str, download_url: str):
    """Show update dialog, then download + install if user accepts."""
    answer = messagebox.askyesno(
        "Update Tersedia",
        f"Versi baru tersedia: v{latest}\n"
        f"Versi saat ini: v{APP_VERSION}\n\n"
        f"Download dan install sekarang?\n"
        f"(Aplikasi akan restart setelah update)",
        parent=parent,
    )
    if not answer:
        return

    progress_win = tk.Toplevel(parent)
    progress_win.title("Downloading Update")
    progress_win.geometry("400x120")
    progress_win.resizable(False, False)
    progress_win.transient(parent)
    progress_win.grab_set()

    ttk.Label(progress_win, text=f"Downloading v{latest}...").pack(pady=(15, 5))
    pb = ttk.Progressbar(progress_win, length=350, mode='determinate', maximum=100)
    pb.pack(pady=5, padx=20)
    pct_label = ttk.Label(progress_win, text="0%")
    pct_label.pack(pady=5)

    temp_file = os.path.join(tempfile.gettempdir(), "L2M_AutoKey_update.exe")
    state = {"done": False, "ok": False}

    def progress_cb(downloaded, total):
        if total <= 0:
            return
        pct = int(downloaded * 100 / total)
        try:
            parent.after(0, lambda: (pb.configure(value=pct), pct_label.configure(text=f"{pct}%")))
        except Exception:
            pass

    def worker():
        state["ok"] = _download_with_progress(download_url, temp_file, progress_cb)
        state["done"] = True

    threading.Thread(target=worker, daemon=True).start()

    while not state["done"]:
        try:
            progress_win.update()
        except Exception:
            break
        time.sleep(0.05)

    try:
        progress_win.destroy()
    except Exception:
        pass

    if state["ok"]:
        messagebox.showinfo(
            "Update",
            "Download selesai. Aplikasi akan restart sekarang.",
            parent=parent,
        )
        _install_update(temp_file, parent=parent)
    else:
        messagebox.showerror(
            "Update Gagal",
            "Gagal download update. Coba lagi nanti.",
            parent=parent,
        )


def check_for_updates(parent: tk.Tk, force: bool = False):
    """Check GitHub for newer version. Skips if last check <24h ago (unless force)."""
    if not force:
        last = _load_last_check_ts()
        elapsed = time.time() - last
        if elapsed < CHECK_INTERVAL_SECONDS:
            print(f"[Updater] Skip — last check {elapsed/3600:.1f}h ago (<24h)")
            return

    print(f"[Updater] Checking for updates... current=v{APP_VERSION}")

    def worker():
        result = _fetch_latest_release()
        _save_last_check_ts()
        if not result:
            return
        latest, download_url = result
        print(f"[Updater] Latest=v{latest}, current=v{APP_VERSION}")
        if not _is_newer(APP_VERSION, latest):
            print("[Updater] Already on latest version")
            return
        parent.after(0, lambda: _prompt_and_download(parent, latest, download_url))

    threading.Thread(target=worker, daemon=True).start()


def schedule_periodic_check(root: tk.Tk):
    """Run an update check on every startup (force), then every 24h while running."""
    check_for_updates(root, force=True)

    def tick():
        check_for_updates(root, force=True)
        root.after(CHECK_INTERVAL_SECONDS * 1000, tick)

    root.after(CHECK_INTERVAL_SECONDS * 1000, tick)
