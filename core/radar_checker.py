"""Radar checker - detects targets on the minimap radar."""
import os
import cv2
import numpy as np
from PIL import Image
from .image_utils import denormalize_region, load_image, match_template, load_radar_templates


class RadarChecker:
    """Detects targets on the game's minimap radar."""

    # Normalized regions for radar icon positions
    REGION_RADAR = (0.82, 0.02, 0.98, 0.18)

    # Warning icon regions per resolution
    WARNING_TEMPLATES = {
        1280: "assets/warning_1280.png",
        960: "assets/warning_960_light.png",
        800: "assets/warning_800.png",
        640: "assets/warning_640.png",
    }

    def __init__(self, assets_dir: str = "assets"):
        self.assets_dir = assets_dir
        self._radar_1_templates = load_radar_templates(assets_dir, "radar_1_")
        self._radar_3_templates = load_radar_templates(assets_dir, "radar_3_")
        self._warning_templates = {}
        for res, path in self.WARNING_TEMPLATES.items():
            if os.path.exists(path):
                bgr, mask = load_image(path)
                self._warning_templates[res] = (bgr, mask)

    def has_target_type1(self, image: Image.Image, threshold: float = 0.75) -> bool:
        """Check for type 1 radar targets (player dots)."""
        w, h = image.size
        region = denormalize_region(self.REGION_RADAR, w, h)
        x1, y1, x2, y2 = region
        cropped = image.crop((x1, y1, x2, y2))
        crop_arr = np.array(cropped)
        crop_bgr = cv2.cvtColor(crop_arr, cv2.COLOR_RGB2BGR)

        for template_bgr, mask, _ in self._radar_1_templates:
            if match_template(crop_bgr, template_bgr, mask, threshold):
                return True
        return False

    def has_target_type3(self, image: Image.Image, threshold: float = 0.75) -> bool:
        """Check for type 3 radar targets."""
        w, h = image.size
        region = denormalize_region(self.REGION_RADAR, w, h)
        x1, y1, x2, y2 = region
        cropped = image.crop((x1, y1, x2, y2))
        crop_arr = np.array(cropped)
        crop_bgr = cv2.cvtColor(crop_arr, cv2.COLOR_RGB2BGR)

        for template_bgr, mask, _ in self._radar_3_templates:
            if match_template(crop_bgr, template_bgr, mask, threshold):
                return True
        return False

    def has_warning(self, image: Image.Image, threshold: float = 0.75) -> bool:
        """Check for warning icon (alert target)."""
        w = image.size[0]
        # Pick closest resolution template
        closest_res = min(self._warning_templates.keys(), key=lambda r: abs(r - w), default=None)
        if closest_res is None:
            return False

        template_bgr, mask = self._warning_templates[closest_res]
        source_arr = np.array(image.convert("RGB"))
        source_bgr = cv2.cvtColor(source_arr, cv2.COLOR_RGB2BGR)
        return match_template(source_bgr, template_bgr, mask, threshold)

    def count_targets(self, image: Image.Image) -> int:
        """Count approximate number of targets on radar."""
        count = 0
        if self.has_target_type1(image):
            count += 1
        if self.has_target_type3(image):
            count += 1
        return count
