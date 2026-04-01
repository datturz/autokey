"""Boss timer module — reads boss spawn data from Supabase.

Uses the same database as L2M Boss Timer v2.
Calculates spawn countdowns and identifies upcoming bosses.
"""

import os
import time
from datetime import datetime, timedelta, timezone

# GMT+7 timezone
TZ_GMT7 = timezone(timedelta(hours=7))

# FFA bosses (from boss timer config)
FFA_BOSSES = [
    "Samuel", "Glaki", "Flynt", "Dragon Beast", "Cabrio",
    "Hisilrome", "Mirror of Oblivion", "Landor", "Haff",
    "Andras", "Olkuth", "Orfen",
]

# Spawn display window (seconds) — boss considered "just spawned" within this
SPAWN_DISPLAY_SECONDS = 180


class BossTimer:
    """Reads boss data from Supabase and calculates spawn times."""

    def __init__(self):
        self._client = None
        self._bosses = []
        self._last_fetch = 0
        self._fetch_interval = 3600  # 1 hour between DB fetches

    def _get_client(self):
        """Lazy-init Supabase client."""
        if self._client is not None:
            return self._client
        try:
            from supabase import create_client
            url = os.environ.get("SUPABASE_URL", "")
            key = os.environ.get("SUPABASE_KEY", "")
            if not url or not key:
                # Try loading from .env
                from dotenv import load_dotenv
                env_path = os.path.join(os.path.dirname(os.path.dirname(
                    os.path.abspath(__file__))), '.env')
                load_dotenv(env_path)
                url = os.environ.get("SUPABASE_URL", "")
                key = os.environ.get("SUPABASE_KEY", "")
            if url and key:
                self._client = create_client(url, key)
        except Exception as e:
            print(f"[BossTimer] Supabase init failed: {e}")
        return self._client

    def fetch_bosses(self) -> list:
        """Fetch boss data from Supabase. Returns list of boss dicts."""
        now = time.time()
        if (now - self._last_fetch) < self._fetch_interval and self._bosses:
            return self._bosses

        client = self._get_client()
        if client is None:
            return self._bosses

        try:
            response = client.table("bosses").select("*").execute()
            self._bosses = response.data if response.data else []
            self._last_fetch = now
        except Exception as e:
            print(f"[BossTimer] Fetch error: {e}")

        return self._bosses

    def calculate_spawn_time(self, boss: dict) -> datetime | None:
        """Calculate next spawn time for a boss.

        Same logic as L2M Boss Timer v2:
        spawn_time = kill_time + interval_hours
        """
        kill_time_str = boss.get("kill_time", "")
        interval_hours = boss.get("interval", 8)

        if not kill_time_str:
            return None

        try:
            # Parse HH:MM
            parts = kill_time_str.split(":")
            kill_h = int(parts[0])
            kill_m = int(parts[1]) if len(parts) > 1 else 0
        except (ValueError, IndexError):
            return None

        now = datetime.now(TZ_GMT7)

        # Build kill datetime (today)
        kill_dt = now.replace(hour=kill_h, minute=kill_m, second=0, microsecond=0)

        # If kill time is in the future, it was yesterday
        if kill_dt > now:
            kill_dt -= timedelta(days=1)

        # Calculate spawn time
        spawn_dt = kill_dt + timedelta(hours=interval_hours)

        # If spawn already passed, add another interval cycle
        while spawn_dt < now - timedelta(seconds=SPAWN_DISPLAY_SECONDS):
            spawn_dt += timedelta(hours=interval_hours)

        return spawn_dt

    def get_upcoming_bosses(self, within_minutes: float = 5.0) -> list:
        """Get bosses spawning within N minutes.

        Returns list of dicts sorted by nearest spawn:
        [{"name", "type", "spawn_time", "countdown_sec", "percentage"}]
        """
        bosses = self.fetch_bosses()
        now = datetime.now(TZ_GMT7)
        upcoming = []

        for boss in bosses:
            spawn_time = self.calculate_spawn_time(boss)
            if spawn_time is None:
                continue

            countdown = (spawn_time - now).total_seconds()

            # Include: spawning within window, or just spawned (< 3min ago)
            if countdown <= within_minutes * 60:
                boss_type = boss.get("type", "ours")
                name = boss.get("name", "Unknown")
                if boss_type not in ("ours", "invasion") and name in FFA_BOSSES:
                    boss_type = "ffa"

                upcoming.append({
                    "name": name,
                    "type": boss_type,
                    "spawn_time": spawn_time,
                    "countdown_sec": countdown,
                    "percentage": boss.get("percentage", 100),
                    "kill_time": boss.get("kill_time", ""),
                    "interval": boss.get("interval", 8),
                })

        upcoming.sort(key=lambda b: b["countdown_sec"])
        return upcoming

    def get_all_bosses_with_countdown(self) -> list:
        """Get all bosses with their countdowns. For UI display."""
        bosses = self.fetch_bosses()
        now = datetime.now(TZ_GMT7)
        result = []

        for boss in bosses:
            spawn_time = self.calculate_spawn_time(boss)
            if spawn_time is None:
                continue

            countdown = (spawn_time - now).total_seconds()
            name = boss.get("name", "Unknown")
            boss_type = boss.get("type", "ours")
            if boss_type not in ("ours", "invasion") and name in FFA_BOSSES:
                boss_type = "ffa"

            result.append({
                "name": name,
                "type": boss_type,
                "countdown_sec": countdown,
                "spawn_time": spawn_time.strftime("%H:%M"),
                "kill_time": boss.get("kill_time", ""),
            })

        result.sort(key=lambda b: b["countdown_sec"])
        return result

    def format_countdown(self, seconds: float) -> str:
        """Format countdown seconds to HH:MM:SS or 'SPAWN!'."""
        if seconds <= 0:
            return "SPAWN!"
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
