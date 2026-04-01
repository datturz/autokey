"""Network-based radar — detects enemy players from game server packets.

Uses tshark to passively sniff server packets. When a player entity (type=4/6)
spawns near you (opcode 0x38/0x39), triggers escape IMMEDIATELY.

This is FASTER than screen-based radar because:
- Network packet arrives ~100ms before screen renders
- No template matching delay
- Works even when character is frozen/stunned (can still TP)
"""

import subprocess
import struct
import threading
import time
import os

TSHARK = r'C:\Program Files\Wireshark\tshark.exe'
GAME_SERVER = '34.111.90.128'
GAME_PORT = '9200'


class NetRadar:
    """Background network sniffer for enemy player detection."""

    def __init__(self, interface='6', callback=None):
        self.interface = interface
        self.callback = callback  # Called when enemy detected: callback(entity_info)
        self._proc = None
        self._thread = None
        self._running = False
        self.enemy_count = 0
        self.last_enemy_time = 0
        self._known_entities = {}  # entity_id -> {type, last_seen}

    def start(self):
        """Start the network sniffer in background thread."""
        if self._running:
            return
        if not os.path.exists(TSHARK):
            print("[NetRadar] tshark not found, disabled")
            return

        self._running = True
        self._thread = threading.Thread(target=self._sniff_loop, daemon=True,
                                        name="net_radar")
        self._thread.start()
        print("[NetRadar] Started")

    def stop(self):
        """Stop the sniffer."""
        self._running = False
        if self._proc:
            try:
                self._proc.terminate()
            except Exception:
                pass
        self._proc = None

    def get_nearby_players(self) -> int:
        """Return count of enemy players seen in last 30 seconds."""
        now = time.time()
        count = 0
        expired = []
        for eid, info in self._known_entities.items():
            if info['type'] in (4, 6) and (now - info['last_seen']) < 30:
                count += 1
            elif (now - info['last_seen']) > 60:
                expired.append(eid)
        for eid in expired:
            del self._known_entities[eid]
        return count

    def _sniff_loop(self):
        """Main sniff loop — runs tshark and parses packets."""
        cmd = [
            TSHARK, '-i', self.interface, '-l',
            '-f', f'src host {GAME_SERVER} and tcp port {GAME_PORT}',
            '-T', 'fields', '-e', 'data.data',
        ]

        try:
            self._proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, bufsize=1)

            for line in self._proc.stdout:
                if not self._running:
                    break
                hex_data = line.strip()
                if not hex_data or len(hex_data) < 10:
                    continue
                try:
                    data = bytes.fromhex(hex_data)
                    self._process_packet(data)
                except Exception:
                    pass

        except Exception as e:
            if self._running:
                print(f"[NetRadar] Error: {e}")
        finally:
            self._running = False

    def _process_packet(self, data: bytes):
        """Process a server packet — look for player entities."""
        if len(data) < 10:
            return

        opcode = data[0]

        # Entity spawn/update: opcode 0x38 (spawn) or 0x39 (update)
        if opcode in (0x38, 0x39) and len(data) > 46:
            eid = int.from_bytes(data[3:6], 'little')
            etype = data[6]

            # Type 4 or 6 = player character
            if etype in (4, 6):
                now = time.time()
                is_new = eid not in self._known_entities

                self._known_entities[eid] = {
                    'type': etype,
                    'last_seen': now,
                }

                if is_new:
                    self.enemy_count += 1
                    self.last_enemy_time = now

                    # Trigger callback — enemy player detected!
                    if self.callback:
                        try:
                            self.callback({
                                'entity_id': eid,
                                'type': etype,
                                'time': now,
                                'total_nearby': self.get_nearby_players(),
                            })
                        except Exception:
                            pass
