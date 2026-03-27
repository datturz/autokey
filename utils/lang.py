"""Language loader - loads translation strings."""
import json
import os


_lang_cache: dict = {}


def load_lang(path: str = "lang.json") -> dict:
    """Load language strings from JSON file."""
    global _lang_cache
    if _lang_cache:
        return _lang_cache

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            _lang_cache = json.load(f)
    else:
        _lang_cache = _get_default_lang()

    return _lang_cache


def get(key: str, **kwargs) -> str:
    """Get a translated string by key."""
    lang = load_lang()
    text = lang.get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return text


def _get_default_lang() -> dict:
    """Default Indonesian language strings."""
    return {
        "app_title": "L2M AutoKey",
        "setting": "Pengaturan:",
        "refresh": "Refresh",
        "start": "Mulai",
        "stop": "Berhenti",
        "tab_main": "Utama",
        "tab_radar": "Radar",
        "tab_weapon": "Ganti Senjata",
        "tab_farming": "Farming",
        "tab_daily": "Harian",
        "status_ready": "Status: Siap",
        "status_active": "Status: Aktif",
        "status_stopped": "Status: Berhenti",
        "add_key": "Tambah Tombol",
        "profile": "Profil",
        "key": "Tombol:",
        "interval": "Interval (detik):",
        "condition": "Kondisi:",
        "anytime": "Kapan saja",
        "when_attacked": "Saat diserang",
        "remove": "Hapus",
        "low_hp": "HP Rendah",
        "low_hp_bar": "Bar HP rendah",
        "press_key": "Tekan tombol:",
        "high_hp": "HP Tinggi",
        "high_hp_bar": "Bar HP tinggi",
        "no_press_safe_area": "Jangan tekan di area aman",
        "no_press_inventory": "Jangan tekan saat inventory terbuka",
        "auto_hunt": "Tekan auto hunt (F)",
        "radar_more_than": "Ketika lebih dari",
        "radar_targets": "target di radar",
        "alert_target": "Saat menemui target peringatan",
        "weapon_switch": "Ganti senjata",
        "weapon_key1": "Tombol 1:",
        "weapon_key2": "Tombol 2:",
        "weapon_interval": "Interval (menit):",
        "press_space": "Tekan Space saat ganti",
        "teleport_enabled": "Teleport otomatis ke spot tersimpan",
        "teleport_spot": "Spot",
        "teleport_after_town": "Teleport setelah di kota",
        "teleport_minutes": "menit",
        "auto_letter": "Auto terima surat (tekan T)",
        "auto_buy": "Beli item otomatis",
        "check_boss": "Cek boss setiap",
        "check_zariche": "Cek Zariche setiap",
        "auto_bulk_purchase": "Auto bulk purchase",
        "auto_clan_attendance": "Auto absen clan",
        "auto_daily_claim": "Auto klaim harian",
        "minutes": "menit",
        "select_window": "Pilih window Lineage",
        "no_window_found": "Window Lineage tidak ditemukan",
        "must_select_window": "Harus pilih window Lineage",
        "error": "Error",
        "area_safe": "Area: Aman",
        "area_normal": "Area: Normal",
        "area_active": "Aktif",
        "save_image": "Simpan gambar",
        "wait_time": "Waktu tunggu (detik):",
        "only_when_attacked": "Hanya saat diserang",
        "still_press_in_town": "Tetap tekan di kota",
        "after": "Setelah",
        "executed_at": "Terakhir: ",
    }
