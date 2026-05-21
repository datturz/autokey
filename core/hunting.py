"""Hunting state detection - checks if character is hunting, dead, etc."""
import numpy as np
import cv2
from PIL import Image
from .image_utils import denormalize_region, load_image, match_template


class HuntingChecker:
    """Detects hunting-related states from game screenshots."""

    # Normalized region for the auto-hunt icon area
    REGION_BEING_ATTACKED = (0.45, 0.0, 0.55, 0.08)
    # Wider death region — covers both "You have been defeated" text (top half)
    # and "Resurrect at Village" button (lower middle).
    REGION_DEATH = (0.2, 0.10, 0.8, 0.85)

    def __init__(self, assets_dir: str = "assets"):
        self.assets_dir = assets_dir
        self._death_templates = []
        self._load_templates()

    def _load_templates(self):
        """Load death detection templates (defeated text, resurrect button).

        Only loads the two current-UI templates. Legacy lost_exp_*.* dropped
        because they match outdated UI and cause false positives.
        """
        import os
        for fname in ("death_defeated.png", "death_resurrect_btn.png"):
            path = os.path.join(self.assets_dir, fname)
            if os.path.exists(path):
                try:
                    bgr, mask = load_image(path)
                    self._death_templates.append((fname, bgr, mask))
                except Exception:
                    pass

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
        """Check if character is dead (defeat screen visible).

        Death dialog ALWAYS shows BOTH:
        - 'You have been defeated' red text (death_defeated.png)
        - 'Resurrect at Village' button (death_resurrect_btn.png)

        Require BOTH templates to match within same frame to confirm death.
        Single template matching alone causes false positives (HUD elements
        in town can fluke-match at small scales).
        """
        if len(self._death_templates) < 2:
            return False
        w, h = image.size
        region = denormalize_region(self.REGION_DEATH, w, h)
        x1, y1, x2, y2 = region
        cropped = image.crop((x1, y1, x2, y2))
        crop_arr = np.array(cropped)
        crop_bgr = cv2.cvtColor(crop_arr, cv2.COLOR_RGB2BGR)
        crop_gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
        ch, cw = crop_gray.shape[:2]

        # Track best score per template name
        best_scores = {}
        for fname, tpl_bgr, _mask in self._death_templates:
            tpl_gray = cv2.cvtColor(tpl_bgr, cv2.COLOR_BGR2GRAY)
            th, tw = tpl_gray.shape[:2]
            best = 0.0
            # Narrower scale range — drop very small scales that fluke-match
            for scale in [0.6, 0.7, 0.8, 0.9, 1.0]:
                nh, nw = max(10, int(th * scale)), max(10, int(tw * scale))
                if nh > ch or nw > cw:
                    continue
                resized = cv2.resize(tpl_gray, (nw, nh), interpolation=cv2.INTER_AREA)
                result = cv2.matchTemplate(crop_gray, resized, cv2.TM_CCOEFF_NORMED)
                _, score, _, _ = cv2.minMaxLoc(result)
                if score > best:
                    best = score
            best_scores[fname] = best

        defeated_score = best_scores.get("death_defeated.png", 0.0)
        resurrect_score = best_scores.get("death_resurrect_btn.png", 0.0)

        # Require BOTH templates to match (stricter threshold per template)
        if defeated_score >= 0.7 and resurrect_score >= 0.7:
            return True

        # Fallback: ONE template with very high confidence (other might be
        # obscured by overlay/notification). Threshold higher to avoid false-pos.
        if defeated_score >= 0.88 or resurrect_score >= 0.88:
            return True

        return False
