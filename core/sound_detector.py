"""Sound-based radar detection — cross-correlation with reference warning sound.

Uses WASAPI loopback via soundcard to capture headphone output.
Only triggers when the EXACT warning sound is detected (not random sounds).
"""
import numpy as np
import threading
import time
import os
import warnings
warnings.filterwarnings("ignore", message="data discontinuity")
warnings.filterwarnings("ignore", category=DeprecationWarning)

try:
    import soundcard as sc
    from scipy import signal
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False


class SoundDetector:
    """Detect radar warning sound via cross-correlation (exact match only)."""

    def __init__(self, reference_path: str = None):
        self.reference_data = None
        self.reference_sr = 44100
        self._detected = False
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        self._last_detect_time = 0.0
        self.on_detect_callback = None

        if reference_path and os.path.exists(reference_path):
            self._load_reference(reference_path)

    def _load_reference(self, path: str):
        """Load reference sound as mono float32 @ 44100Hz."""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(path)
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            if audio.channels == 2:
                samples = samples.reshape(-1, 2).mean(axis=1)
            self.reference_sr = audio.frame_rate
            # Normalize to -1..1
            self.reference_data = samples / (np.max(np.abs(samples)) + 1e-8)
            # Keep only first 0.5s (enough for fingerprint, faster matching)
            max_samples = self.reference_sr // 2
            if len(self.reference_data) > max_samples:
                self.reference_data = self.reference_data[:max_samples]
            print(f"[SoundDetector] Loaded: {path} ({len(self.reference_data)} samples, {self.reference_sr}Hz)")
        except Exception as e:
            print(f"[SoundDetector] Load failed: {e}")
            self.reference_data = None

    def is_detected(self) -> bool:
        with self._lock:
            val = self._detected
            self._detected = False
            return val

    def start(self):
        if not HAS_AUDIO:
            print("[SoundDetector] soundcard/scipy not available")
            return
        if self.reference_data is None:
            print("[SoundDetector] No reference sound loaded")
            return
        if self._running:
            return
        self._running = True
        self._detected = False
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _monitor_loop(self):
        try:
            speaker = sc.default_speaker()
            print(f"[SoundDetector] Loopback: {speaker.name}")
            mic = sc.get_microphone(speaker.id, include_loopback=True)

            sr = self.reference_sr  # Match reference sample rate
            chunk_frames = sr // 10  # 100ms chunks
            # Rolling buffer: 2 seconds
            buf_size = sr * 2
            buffer = np.zeros(buf_size, dtype=np.float32)
            ref = self.reference_data

            with mic.recorder(samplerate=sr, channels=1) as rec:
                while self._running:
                    try:
                        data = rec.record(numframes=chunk_frames)
                    except Exception:
                        time.sleep(0.05)
                        continue

                    mono = data[:, 0] if data.ndim > 1 else data.flatten()

                    # Update rolling buffer
                    buffer = np.roll(buffer, -len(mono))
                    buffer[-len(mono):] = mono

                    # Cross-correlate last 1s of buffer with reference
                    now = time.time()
                    if (now - self._last_detect_time) < 3.0:
                        continue  # Cooldown

                    check = buffer[-sr:]  # Last 1 second
                    check_max = np.max(np.abs(check))
                    if check_max < 0.005:
                        continue  # Too quiet, skip

                    check_norm = check / check_max
                    corr = np.correlate(check_norm, ref, mode='valid')
                    max_corr = np.max(corr) / len(ref)

                    if max_corr > 0.10:
                        self._last_detect_time = now
                        with self._lock:
                            self._detected = True
                        print(f"[SoundDetector] MATCH! corr={max_corr:.4f}")
                        if self.on_detect_callback:
                            try:
                                self.on_detect_callback()
                            except Exception as e:
                                print(f"[SoundDetector] Callback err: {e}")

        except Exception as e:
            print(f"[SoundDetector] Error: {e}")
            import traceback
            traceback.print_exc()
            self._running = False
