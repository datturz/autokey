"""Build L2M AutoKey executable using PyInstaller."""
import subprocess
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--onefile",
    "--windowed",
    "--name", "L2M_AutoKey",
    "--add-data", "assets;assets",
    "--add-data", ".env;.",
    "--add-data", "lang.json;.",
    "--hidden-import", "supabase",
    "--hidden-import", "dotenv",
    "--hidden-import", "postgrest",
    "--hidden-import", "gotrue",
    "--hidden-import", "realtime",
    "--hidden-import", "storage3",
    "--hidden-import", "supafunc",
    "--hidden-import", "httpx",
    "--hidden-import", "win32gui",
    "--hidden-import", "win32con",
    "--hidden-import", "win32api",
    "--hidden-import", "win32process",
    "--hidden-import", "pywintypes",
    "--hidden-import", "cv2",
    "--hidden-import", "mss",
    "--hidden-import", "PIL",
    "--hidden-import", "numpy",
    "main.py",
]

print("Building L2M AutoKey...")
print(" ".join(cmd))
subprocess.run(cmd, check=True)
print("\nDone! Executable at: dist/L2M_AutoKey.exe")
