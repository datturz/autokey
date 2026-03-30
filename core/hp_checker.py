"""HP checker module - analyzes HP/MP bars from screenshot.

Reconstructed from original AutoKeyL2M CheckHP class bytecode.
Uses HSV color distance + saturation/value filtering.

Enhanced with:
- MP bar detection
- HP smoothing (rolling average to reduce jitter)
- Rate-of-change tracking for emergency burst healing
"""
import time
import numpy as np
import cv2
from PIL import Image
from collections import deque
from core.game_layout import (
    HP_BAR, HP_SAMPLE, HP_BAR_SMALL, HP_LOW_REGION, HP_MED_REGION,
    HP_PART1, HP_PART2, HP_PART3, HP_F1, HP_F2, HP_F3, denormalize,
)

# Default fallback HSV sample when calibration fails (red HP bar)
_DEFAULT_HSV = np.array([5, 250, 150], dtype=np.float64)

# MP bar is blue — default HSV for blue color
_DEFAULT_MP_HSV = np.array([105, 200, 160], dtype=np.float64)

# MP bar region (just below HP bar in L2M UI)
# HP bar: Y ~0.022-0.040 (red/green)
# MP bar: Y ~0.048-0.065 (blue bar, slightly wider Y range for safety)
MP_BAR = (0.0359375, 0.048, 0.165625, 0.065)
MP_SAMPLE = (0.0328125, 0.051, 0.0359375, 0.060)


class HPChecker:
    """Analyzes HP/MP bars from game screenshots using color detection.
    Matches original CheckHP class from func/checkHP.py.

    Enhanced: MP detection, smoothing, rate tracking."""

    def __init__(self, tolerance: int = 30, hue_tolerance: int = 10):
        self.tolerance = tolerance
        self.hue_tolerance = hue_tolerance
        self.sample_hsv = None       # np.array([H, S, V]) mean of sample region
        self.sample_colors = None    # list of sample HSV arrays

        # MP calibration
        self.mp_sample_hsv = None
        self.mp_sample_colors = None

        # Smoothing: rolling window of last 5 HP readings
        self._hp_history = deque(maxlen=5)
        self._mp_history = deque(maxlen=5)
        self._hp_timestamps = deque(maxlen=5)

        # Rate tracking for emergency detection
        self.hp_rate = 0.0       # HP change per second (negative = losing HP)
        self.last_hp_raw = 1.0
        self.last_hp_time = time.time()

    def calibrate(self, image: Image.Image):
        """Sample HP bar colors for calibration.
        Original: extract_from_image → np.mean(hsv, axis=(0,1))
        Called EVERY frame, not just once."""
        w, h = image.size
        x1, y1, x2, y2 = denormalize(HP_SAMPLE, w, h)
        if x2 <= x1 or y2 <= y1:
            return
        try:
            cropped = image.crop((x1, y1, x2, y2))
            arr = np.array(cropped)
            if arr.size == 0:
                return
            hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)
            # Mean of entire region (same as original)
            self.sample_hsv = np.mean(hsv, axis=(0, 1))
            self.sample_colors = [self.sample_hsv]
        except Exception:
            # Fallback: red HP bar default
            self.sample_hsv = _DEFAULT_HSV.copy()
            self.sample_colors = [self.sample_hsv]

    def _calculate_ratio(self, image: Image.Image, region: tuple) -> float:
        """Calculate HP fill ratio in a region.
        Matches original _calculate_ratio_simple_mask:
        1. Compute HSV distance from each sample color
        2. Filter by Saturation > 200
        3. Filter by Value < ref_v * 1.3
        4. Find rightmost column with HP pixels
        """
        if self.sample_colors is None or len(self.sample_colors) == 0:
            return 0.0

        w, h = image.size
        x1, y1, x2, y2 = denormalize(region, w, h)
        if x2 <= x1 or y2 <= y1:
            return 0.0
        cropped = image.crop((x1, y1, x2, y2))
        img_np = np.array(cropped)
        if img_np.size == 0:
            return 0.0
        hsv_img = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)

        # Build mask from sample colors using Euclidean distance in HSV
        mask_total = np.zeros(hsv_img.shape[:2], dtype=np.uint8)
        for sample in self.sample_colors:
            diff = np.linalg.norm(
                hsv_img.astype(np.int16) - sample.astype(np.int16),
                axis=2
            )
            mask = (diff < self.tolerance).astype(np.uint8)
            mask_total = cv2.bitwise_or(mask_total, mask)

        # Filter: Saturation must be > 200 (avoid low-sat background)
        s_mask = (hsv_img[:, :, 1] > 200).astype(np.uint8)

        # Filter: Value must be < ref_v * 1.3 (avoid glow/bright effects)
        ref_v = self.sample_hsv[2] if self.sample_hsv is not None else 150
        v_max = min(220, ref_v * 1.3)
        v_mask = (hsv_img[:, :, 2] < v_max).astype(np.uint8)

        # Apply filters
        mask_total = cv2.bitwise_and(mask_total, s_mask)
        mask_total = cv2.bitwise_and(mask_total, v_mask)

        # Count and find rightmost HP pixel
        red_count = np.count_nonzero(mask_total)
        if red_count == 0:
            return 0.0

        has_red_in_col = np.max(mask_total, axis=0)
        red_indices = np.where(has_red_in_col > 0)[0]
        if len(red_indices) == 0:
            return 0.0

        last_red_pos = red_indices[-1] + 1
        total_width = mask_total.shape[1]
        return min(1.0, last_red_pos / total_width)

    def calibrate_mp(self, image: Image.Image):
        """Sample MP bar colors for calibration (blue bar)."""
        w, h = image.size
        x1, y1, x2, y2 = denormalize(MP_SAMPLE, w, h)
        if x2 <= x1 or y2 <= y1:
            return
        try:
            cropped = image.crop((x1, y1, x2, y2))
            arr = np.array(cropped)
            if arr.size == 0:
                return
            hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)
            self.mp_sample_hsv = np.mean(hsv, axis=(0, 1))
            self.mp_sample_colors = [self.mp_sample_hsv]
        except Exception:
            self.mp_sample_hsv = _DEFAULT_MP_HSV.copy()
            self.mp_sample_colors = [self.mp_sample_hsv]

    def get_hp_percentage(self, image: Image.Image) -> float:
        """Get HP percentage (0.0 - 1.0).
        Re-calibrates EVERY call (same as original).
        Enhanced: updates smoothing and rate tracking."""
        self.calibrate(image)
        raw = self._calculate_ratio(image, HP_BAR)

        now = time.time()
        self._hp_history.append(raw)
        self._hp_timestamps.append(now)

        # Calculate HP rate of change (per second)
        dt = now - self.last_hp_time
        if dt > 0.1:
            self.hp_rate = (raw - self.last_hp_raw) / dt
            self.last_hp_raw = raw
            self.last_hp_time = now

        return raw

    def get_hp_smoothed(self, image: Image.Image) -> float:
        """Get smoothed HP (average of last 5 readings).
        Reduces jitter from frame capture noise."""
        raw = self.get_hp_percentage(image)
        if len(self._hp_history) >= 3:
            # Median of last 5 to reject outliers
            return float(np.median(list(self._hp_history)))
        return raw

    def get_mp_percentage(self, image: Image.Image) -> float:
        """Get MP percentage (0.0 - 1.0)."""
        self.calibrate_mp(image)
        if self.mp_sample_colors is None:
            return 0.0

        # Use MP-specific colors for the ratio calculation
        old_sample = self.sample_colors
        old_hsv = self.sample_hsv
        self.sample_colors = self.mp_sample_colors
        self.sample_hsv = self.mp_sample_hsv

        ratio = self._calculate_ratio(image, MP_BAR)

        # Restore HP colors
        self.sample_colors = old_sample
        self.sample_hsv = old_hsv

        self._mp_history.append(ratio)
        return ratio

    def get_mp_smoothed(self, image: Image.Image) -> float:
        """Get smoothed MP percentage."""
        raw = self.get_mp_percentage(image)
        if len(self._mp_history) >= 3:
            return float(np.median(list(self._mp_history)))
        return raw

    def is_hp_dropping_fast(self, threshold: float = -0.15) -> bool:
        """Detect rapid HP loss (> 15% per second by default).
        Requires at least 3 readings and rate must be within plausible range."""
        if len(self._hp_history) < 3:
            return False
        # Ignore unrealistic rates (>50%/s = capture noise/jitter)
        if abs(self.hp_rate) > 0.50:
            return False
        return self.hp_rate < threshold

    def get_hp_pct(self, image: Image.Image) -> float:
        """Alias for get_hp_percentage (matches original name)."""
        return self.get_hp_percentage(image)

    def get_ratio_full_hp(self, image: Image.Image) -> float:
        """Check if HP is full using medium HP region (right side)."""
        return self._calculate_ratio(image, HP_MED_REGION)

    def get_ratio_low_hp(self, image: Image.Image) -> float:
        """Check low HP region (left side of bar)."""
        return self._calculate_ratio(image, HP_LOW_REGION)

    def get_ratio_stable(self, image: Image.Image) -> float:
        """Get HP ratio from small (thin) bar region."""
        return self._calculate_ratio(image, HP_BAR_SMALL)

    def get_member_hp(self, image: Image.Image, member: int) -> float:
        """Get party member HP (1=F1, 2=F2, 3=F3)."""
        regions = {1: HP_F1, 2: HP_F2, 3: HP_F3}
        return self._calculate_ratio(image, regions.get(member, HP_F1))

    def get_ratio_f1(self, image: Image.Image) -> float:
        return self._calculate_ratio(image, HP_F1)

    def get_ratio_f2(self, image: Image.Image) -> float:
        return self._calculate_ratio(image, HP_F2)

    def get_ratio_f3(self, image: Image.Image) -> float:
        return self._calculate_ratio(image, HP_F3)

    def is_low_hp(self, image: Image.Image, threshold: float = 0.3) -> bool:
        return self.get_hp_percentage(image) < threshold

    def is_high_hp(self, image: Image.Image, threshold: float = 0.8) -> bool:
        return self.get_hp_percentage(image) > threshold


def hp_color(pct: float) -> str:
    """Return color hex string based on HP percentage."""
    if pct > 0.6:
        return "#22c55e"
    elif pct > 0.4:
        return "#f59e0b"
    elif pct > 0.2:
        return "#f97316"
    return "#ef4444"


def mp_color(pct: float) -> str:
    """Return color hex string based on MP percentage."""
    if pct > 0.5:
        return "#3b82f6"
    elif pct > 0.25:
        return "#6366f1"
    return "#8b5cf6"
