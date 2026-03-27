"""Hunting state detection - checks if character is hunting, dead, etc."""
import numpy as np
import cv2
from PIL import Image
from .image_utils import denormalize_region, load_image, match_template


class HuntingChecker:
    """Detects hunting-related states from game screenshots."""

    # Normalized region for the auto-hunt icon area
    REGION_BEING_ATTACKED = (0.45, 0.0, 0.55, 0.08)
    REGION_DEATH = (0.3, 0.3, 0.7, 0.7)

    def __init__(self, assets_dir: str = "assets"):
        self.assets_dir = assets_dir
        self._lost_exp_templates = []
        self._load_templates()

    def _load_templates(self):
        """Load death/lost exp templates."""
        import os
        for fname in os.listdir(self.assets_dir):
            if fname.startswith("lost_exp_"):
                path = os.path.join(self.assets_dir, fname)
                bgr, mask = load_image(path)
                self._lost_exp_templates.append((bgr, mask))

    def is_being_attacked(self, image: Image.Image) -> bool:
        """Check if character is currently being attacked.
        Uses color analysis in the attack indicator region."""
        w, h = image.size
        region = denormalize_region(self.REGION_BEING_ATTACKED, w, h)
        x1, y1, x2, y2 = region
        cropped = image.crop((x1, y1, x2, y2))
        arr = np.array(cropped)
        hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)
        # Check for red combat indicator
        mask_red1 = cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255]))
        mask_red2 = cv2.inRange(hsv, np.array([170, 100, 100]), np.array([180, 255, 255]))
        red_ratio = (np.sum(mask_red1 > 0) + np.sum(mask_red2 > 0)) / mask_red1.size
        return red_ratio > 0.1

    def is_dead(self, image: Image.Image) -> bool:
        """Check if character is dead (lost exp dialog visible)."""
        w, h = image.size
        region = denormalize_region(self.REGION_DEATH, w, h)
        x1, y1, x2, y2 = region
        cropped = image.crop((x1, y1, x2, y2))
        crop_arr = np.array(cropped)
        crop_bgr = cv2.cvtColor(crop_arr, cv2.COLOR_RGB2BGR)

        for template_bgr, mask in self._lost_exp_templates:
            if match_template(crop_bgr, template_bgr, mask, threshold=0.7):
                return True
        return False
