"""HP checker module - analyzes HP bar from screenshot.

Reconstructed from original AutoKeyL2M CheckHP class bytecode.
Uses HSV color distance + saturation/value filtering.
"""
import numpy as np
import cv2
from PIL import Image
from core.game_layout import (
    HP_BAR, HP_SAMPLE, HP_BAR_SMALL, HP_LOW_REGION, HP_MED_REGION,
    HP_PART1, HP_PART2, HP_PART3, HP_F1, HP_F2, HP_F3, denormalize,
)

# Default fallback HSV sample when calibration fails (red HP bar)
_DEFAULT_HSV = np.array([5, 250, 150], dtype=np.float64)


class HPChecker:
    """Analyzes HP bar from game screenshots using color detection.
    Matches original CheckHP class from func/checkHP.py."""

    def __init__(self, tolerance: int = 30, hue_tolerance: int = 10):
        self.tolerance = tolerance
        self.hue_tolerance = hue_tolerance
        self.sample_hsv = None       # np.array([H, S, V]) mean of sample region
        self.sample_colors = None    # list of sample HSV arrays

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

    def get_hp_percentage(self, image: Image.Image) -> float:
        """Get HP percentage (0.0 - 1.0).
        Re-calibrates EVERY call (same as original)."""
        self.calibrate(image)
        return self._calculate_ratio(image, HP_BAR)

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
