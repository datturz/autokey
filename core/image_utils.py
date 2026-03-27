"""Image comparison and template matching utilities."""
import os
import cv2
import numpy as np
from PIL import Image


def load_image(path: str) -> tuple:
    """Load image and return (cv2_bgr, mask_or_none)."""
    img = Image.open(path)
    if img.mode == "RGBA":
        arr = np.array(img)
        bgr = cv2.cvtColor(arr[:, :, :3], cv2.COLOR_RGB2BGR)
        alpha = arr[:, :, 3]
        mask = (alpha > 128).astype(np.uint8) * 255
        return bgr, mask
    else:
        arr = np.array(img.convert("RGB"))
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        return bgr, None


def match_template(source_bgr: np.ndarray, template_bgr: np.ndarray,
                   mask: np.ndarray = None, threshold: float = 0.8) -> bool:
    """Check if template exists in source image."""
    if source_bgr is None or template_bgr is None:
        return False

    sh, sw = source_bgr.shape[:2]
    th, tw = template_bgr.shape[:2]
    if th > sh or tw > sw:
        return False

    if mask is not None:
        result = cv2.matchTemplate(source_bgr, template_bgr, cv2.TM_CCORR_NORMED, mask=mask)
    else:
        result = cv2.matchTemplate(source_bgr, template_bgr, cv2.TM_CCOEFF_NORMED)

    _, max_val, _, _ = cv2.minMaxLoc(result)
    return max_val >= threshold


def match_png_with_alpha(source_pil: Image.Image, template_path: str,
                         threshold: float = 0.8) -> bool:
    """Match a PNG template (with alpha) against a PIL source image."""
    template_bgr, mask = load_image(template_path)
    source_arr = np.array(source_pil.convert("RGB"))
    source_bgr = cv2.cvtColor(source_arr, cv2.COLOR_RGB2BGR)
    return match_template(source_bgr, template_bgr, mask, threshold)


def denormalize_region(norm_region: tuple, img_width: int, img_height: int) -> tuple:
    """Convert normalized (0-1) region to pixel coordinates."""
    x1_n, y1_n, x2_n, y2_n = norm_region
    return (
        int(x1_n * img_width),
        int(y1_n * img_height),
        int(x2_n * img_width),
        int(y2_n * img_height),
    )


def check_icon_in_region(image: Image.Image, icon_bgr: np.ndarray,
                         region_norm: tuple, threshold: float = 0.75) -> bool:
    """Check if an icon exists in a normalized region of the image."""
    w, h = image.size
    region = denormalize_region(region_norm, w, h)
    x1, y1, x2, y2 = region
    cropped = image.crop((x1, y1, x2, y2))
    crop_arr = np.array(cropped)
    crop_bgr = cv2.cvtColor(crop_arr, cv2.COLOR_RGB2BGR)
    return match_template(crop_bgr, icon_bgr, threshold=threshold)


def load_radar_templates(assets_dir: str, prefix: str) -> list:
    """Load all radar template images matching a prefix."""
    templates = []
    for fname in os.listdir(assets_dir):
        if fname.startswith(prefix) and (fname.endswith(".jpg") or fname.endswith(".png")):
            path = os.path.join(assets_dir, fname)
            if os.path.isfile(path):
                bgr, mask = load_image(path)
                templates.append((bgr, mask, fname))
    return templates
