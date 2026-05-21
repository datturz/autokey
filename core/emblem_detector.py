"""Enemy clan emblem detection.

Proactive escape: detects enemy clan emblems floating above characters
BEFORE radar scan reveals them. Uses multi-scale template matching +
SSIM verify + color pre-filter for performance and accuracy.

Templates: assets/enemy_emblem_*.png — user uploads pre-cropped emblems.
"""
import os
import cv2
import numpy as np
from PIL import Image
from .image_utils import load_image

try:
    from skimage.metrics import structural_similarity as _ssim
    _SSIM_OK = True
except Exception:
    _SSIM_OK = False


class EmblemDetector:
    """Detects enemy clan emblems in the viewport.

    Maintains TWO template sets:
    - enemy_emblem_*.png — clans to escape from
    - own_emblem_*.png — exclusion list (own/ally clan emblems)

    Trigger condition: enemy_max_score >= TM_THRESHOLD AND
                       (enemy_max - own_max) >= MIN_GAP
    """

    ROI = (0.0, 0.0, 1.0, 0.6)
    SCALES = (0.6, 0.8, 1.0, 1.2, 1.5)

    TM_THRESHOLD = 0.85       # min TM to consider for enemy match
    SSIM_STRONG = 0.50        # SSIM this high → enemy at this location IS real
    SSIM_MODERATE = 0.40      # SSIM in this range needs gap check
    NEAR_MISS_LOG_TM = 0.75   # log diagnostic for TM in [0.75, 0.85)
    MIN_GAP = 0.03            # gap required when SSIM only moderate

    RED_MIN_RATIO = 0.0008  # color pre-filter threshold

    def __init__(self, assets_dir: str = "assets"):
        self.assets_dir = assets_dir
        self._enemy_templates = []  # list of (fname, bgr, mask)
        self._own_templates = []    # exclusion list
        self.last_near_miss = None  # (fname, enemy_tm, enemy_ssim, own_max)
        self.last_detected_ssim = 0.0  # SSIM at most-recent successful detection
        self.last_detected_own_tm = 0.0
        self._load_templates()

    def _load_templates(self):
        """Load enemy_emblem_*.png and own_emblem_*.png from assets dir.
        Pre-cache resized templates at all scales for fast per-call detection.
        """
        self._enemy_templates = []
        self._own_templates = []
        if not os.path.isdir(self.assets_dir):
            return
        for fname in sorted(os.listdir(self.assets_dir)):
            lname = fname.lower()
            if not lname.endswith((".png", ".jpg", ".jpeg")):
                continue
            if fname.startswith("enemy_emblem_"):
                bucket = self._enemy_templates
            elif fname.startswith("own_emblem_"):
                bucket = self._own_templates
            else:
                continue
            try:
                bgr, mask = load_image(os.path.join(self.assets_dir, fname))
                if bgr is None:
                    continue
                # Pre-resize at all scales (eliminates per-call resize overhead)
                th, tw = bgr.shape[:2]
                gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
                scaled = []
                for scale in self.SCALES:
                    nh = max(15, int(th * scale))
                    nw = max(15, int(tw * scale))
                    r_bgr = cv2.resize(bgr, (nw, nh), interpolation=cv2.INTER_AREA)
                    r_gray = cv2.resize(gray, (nw, nh), interpolation=cv2.INTER_AREA)
                    r_mask = cv2.resize(mask, (nw, nh), interpolation=cv2.INTER_AREA) if mask is not None else None
                    scaled.append((nh, nw, r_bgr, r_gray, r_mask))
                bucket.append((fname, scaled))
            except Exception:
                pass

    def reload(self):
        """Re-scan assets directory (call after UI upload/delete)."""
        self._load_templates()

    @property
    def template_count(self) -> int:
        return len(self._enemy_templates)

    @property
    def own_template_count(self) -> int:
        return len(self._own_templates)

    @property
    def template_names(self) -> list:
        return [fname for fname, _, _ in self._enemy_templates]

    def _best_match(self, crop_bgr, crop_gray, templates, sh, sw):
        """Find best matching template (cached). Returns
        (fname, tm, ssim, loc, size) or (None, 0.0, 0.0, None, None)."""
        best_score = 0.0
        best_fname = None
        best_loc = None
        best_size = None
        best_tpl_gray = None

        for fname, scaled in templates:
            for nh, nw, r_bgr, r_gray, r_mask in scaled:
                if nh > sh or nw > sw:
                    continue
                if r_mask is not None:
                    result = cv2.matchTemplate(crop_bgr, r_bgr, cv2.TM_CCORR_NORMED, mask=r_mask)
                else:
                    result = cv2.matchTemplate(crop_bgr, r_bgr, cv2.TM_CCOEFF_NORMED)
                # Filter invalid scores (inf/NaN from degenerate variance)
                if not np.all(np.isfinite(result)):
                    result = np.where(np.isfinite(result), result, -1.0)
                _, score, _, loc = cv2.minMaxLoc(result)
                if not np.isfinite(score):
                    continue
                if score > best_score:
                    best_score = float(score)
                    best_fname = fname
                    best_loc = loc
                    best_size = (nh, nw)
                    best_tpl_gray = r_gray

        if best_fname is None:
            return (None, 0.0, 0.0, None, None)

        ssim_score = 1.0
        if _SSIM_OK and best_tpl_gray is not None and best_loc is not None:
            try:
                lx, ly = best_loc
                nh, nw = best_size
                actual = crop_gray[ly:ly + nh, lx:lx + nw]
                if actual.shape == best_tpl_gray.shape:
                    ssim_score = float(_ssim(actual, best_tpl_gray, data_range=255))
            except Exception:
                ssim_score = 0.0
        return (best_fname, best_score, ssim_score, best_loc, best_size)

    def detect(self, image: Image.Image) -> tuple:
        """Detect enemy emblem, excluding matches that look more like own emblems.

        Returns (matched_filename, tm_score) on confirmed enemy match,
        or (None, best_score_seen) otherwise.
        """
        self.last_near_miss = None
        if not self._enemy_templates:
            return (None, 0.0)

        w, h = image.size
        x1 = int(self.ROI[0] * w)
        y1 = int(self.ROI[1] * h)
        x2 = int(self.ROI[2] * w)
        y2 = int(self.ROI[3] * h)

        cropped = image.crop((x1, y1, x2, y2))
        crop_arr = np.array(cropped)
        crop_bgr = cv2.cvtColor(crop_arr, cv2.COLOR_RGB2BGR)
        crop_gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
        sh, sw = crop_bgr.shape[:2]

        # Color pre-filter
        hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
        red1 = cv2.inRange(hsv, np.array([0, 100, 80]), np.array([10, 255, 255]))
        red2 = cv2.inRange(hsv, np.array([170, 100, 80]), np.array([180, 255, 255]))
        red_ratio = (int(np.sum(red1 > 0)) + int(np.sum(red2 > 0))) / max(red1.size, 1)
        if red_ratio < self.RED_MIN_RATIO:
            return (None, 0.0)

        # Spatial exclusion strategy:
        # 1. Find own emblem location first (if templates uploaded)
        # 2. Mask out that region from the search area
        # 3. Search enemy in remaining area — finds REAL enemy location,
        #    not enemy template's fluke-match at own emblem position
        own_fname, own_tm, own_ssim, own_loc, own_size = (None, 0.0, 0.0, None, None)
        if self._own_templates:
            own_fname, own_tm, own_ssim, own_loc, own_size = self._best_match(
                crop_bgr, crop_gray, self._own_templates, sh, sw)

        # Build search regions for enemy: mask own area if own match is strong.
        # Use MEAN brightness fill (not zero) to avoid degenerate variance
        # in TM_CCORR_NORMED which causes inf/NaN scores.
        search_bgr = crop_bgr
        search_gray = crop_gray
        if own_loc is not None and own_size is not None and own_tm >= 0.85:
            search_bgr = crop_bgr.copy()
            search_gray = crop_gray.copy()
            mean_bgr = crop_bgr.reshape(-1, 3).mean(axis=0).astype(np.uint8)
            mean_gray_v = int(crop_gray.mean())
            ox, oy = own_loc
            oh, ow = own_size
            # Add margin to mask slightly larger area (catch fringe of own emblem)
            margin = 8
            ox = max(0, ox - margin)
            oy = max(0, oy - margin)
            ow = min(sw - ox, ow + 2 * margin)
            oh = min(sh - oy, oh + 2 * margin)
            search_bgr[oy:oy + oh, ox:ox + ow] = mean_bgr
            search_gray[oy:oy + oh, ox:ox + ow] = mean_gray_v

        en_fname, en_tm, en_ssim, en_loc, en_size = self._best_match(
            search_bgr, search_gray, self._enemy_templates, sh, sw)
        if en_fname is None:
            return (None, 0.0)

        gap = en_tm - own_tm

        # Log near-misses for diagnostic
        if en_tm < self.NEAR_MISS_LOG_TM:
            return (None, en_tm)

        # Trigger conditions:
        # Rule 1 — Strong SSIM override: SSIM is location-specific, so if enemy
        # template scores SSIM≥0.60 at its best location, the enemy IS visible
        # there REGARDLESS of own emblem score (own emblem may also be visible
        # elsewhere in frame, but enemy match at this point is real).
        # Rule 2 — Moderate SSIM: requires gap discrimination as before.
        tm_ok = en_tm >= self.TM_THRESHOLD
        has_own = bool(self._own_templates)

        if tm_ok and _SSIM_OK and en_ssim >= self.SSIM_STRONG:
            self.last_detected_ssim = en_ssim
            self.last_detected_own_tm = own_tm
            return (en_fname, en_tm)

        ssim_ok_mod = (not _SSIM_OK) or en_ssim >= self.SSIM_MODERATE
        gap_ok = (not has_own) or gap >= self.MIN_GAP
        if tm_ok and ssim_ok_mod and gap_ok:
            self.last_detected_ssim = en_ssim
            self.last_detected_own_tm = own_tm
            return (en_fname, en_tm)

        # Near-miss — log reason
        self.last_near_miss = (en_fname, en_tm, en_ssim, own_tm)
        return (None, en_tm)
