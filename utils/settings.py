"""Settings manager - save/load bot configurations."""
import json
import os
import sys


def _get_settings_dir():
    """Get settings dir — next to exe for PyInstaller, or project root for dev."""
    if hasattr(sys, '_MEIPASS'):
        # Running as exe — save next to the exe file
        return os.path.join(os.path.dirname(sys.executable), "settings")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "settings")


SETTINGS_DIR = _get_settings_dir()


def ensure_settings_dir():
    os.makedirs(SETTINGS_DIR, exist_ok=True)


def _sanitize_filename(title: str) -> str:
    """Convert window title to safe filename."""
    return "".join(c if c.isalnum() or c in "._- " else "_" for c in title).strip()


def list_profiles() -> list[str]:
    """List all available setting profiles."""
    ensure_settings_dir()
    profiles = []
    for f in os.listdir(SETTINGS_DIR):
        if f.endswith(".json"):
            profiles.append(f[:-5])
    return profiles


def load_settings(profile_name: str) -> dict:
    """Load settings from a profile."""
    ensure_settings_dir()
    path = os.path.join(SETTINGS_DIR, f"{_sanitize_filename(profile_name)}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return get_default_settings()


def save_settings(profile_name: str, settings: dict):
    """Save settings to a profile."""
    ensure_settings_dir()
    path = os.path.join(SETTINGS_DIR, f"{_sanitize_filename(profile_name)}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)


def get_default_settings() -> dict:
    """Return default settings."""
    return {
        # Main tab - key configs
        "key_configs": [],  # list of {key, interval, condition}

        # HP settings
        "enable_low_hp": False,
        "low_hp_percent": 30,
        "low_hp_key": "F1",
        "enable_medium_hp": False,
        "medium_hp_percent": 60,
        "medium_hp_key": "",
        "medium_hp_delay": 1.0,
        "medium_hp_only_when_attacked": False,
        "enable_high_hp": False,
        "high_hp_percent": 80,
        "high_hp_key": "",

        # General options
        "no_press_in_safe_area": True,
        "no_press_when_inventory_open": True,
        "auto_hunt_enabled": False,

        # Radar tab
        "radar_condition1_enabled": False,
        "radar_condition1_count": 1,
        "radar_condition1_key": "",
        "radar_condition1_delay": 3.0,
        "radar_condition2_enabled": False,
        "radar_condition2_count": 2,
        "radar_condition2_key": "",
        "radar_condition2_delay": 3.0,
        "radar_warning_enabled": False,
        "radar_warning_key": "",
        "radar_warning_delay": 3.0,
        "radar_warning_screenshot": False,

        # Weapon switch tab
        "weapon_switch_enabled": False,
        "weapon_key1": "",
        "weapon_key2": "",
        "weapon_switch_delay": 1.0,
        "weapon_switch_interval": 60,
        "weapon_press_space": False,

        # Farming tab
        "auto_teleport_enabled": False,
        "teleport_spots": [False] * 5,
        "teleport_after_town_enabled": False,
        "teleport_after_town_minutes": 5,
        "teleport_during_farm_enabled": False,
        "teleport_during_farm_minutes": 30,
        "teleport_key_after": "",
        "auto_check_letter": False,
        "auto_check_letter_minutes": 30,
        "auto_buy_items": False,

        # Daily tasks tab
        "check_boss_enabled": False,
        "check_boss_interval": 5,
        "check_boss_tele_after_min": 5,
        "check_boss_radar_key": "",
        "check_boss_hit_key": "",
        "check_zariche_enabled": False,
        "check_zariche_interval": 5,
        "check_zariche_tele_after_min": 5,
        "check_zariche_radar_key": "",
        "check_zariche_hit_key": "",
        "auto_bulk_purchase": False,
        "auto_clan_attendance": False,
        "auto_daily_claim": False,
    }
