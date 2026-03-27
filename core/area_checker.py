"""Area checker - detects if character is in town/safe area."""
import numpy as np
import cv2
from PIL import Image
from .image_utils import denormalize_region, load_image, match_template


class AreaChecker:
    """Checks if the character is in a safe area or town."""

    # Normalized regions for shop/warehouse icons
    REGION_SHOP = (0.0, 0.85, 0.12, 1.0)
    REGION_WAREHOUSE = (0.0, 0.75, 0.12, 0.85)

    def __init__(self, assets_dir: str = "assets"):
        self.assets_dir = assets_dir
        self._shop_templates = []
        self._warehouse_templates = []
        self._load_templates()

    def _load_templates(self):
        """Load shop and warehouse icon templates."""
        import os
        for fname in os.listdir(self.assets_dir):
            path = os.path.join(self.assets_dir, fname)
            if fname.startswith("general_merchant"):
                bgr, mask = load_image(path)
                self._shop_templates.append((bgr, mask))
            elif fname.startswith("warehouse"):
                bgr, mask = load_image(path)
                self._warehouse_templates.append((bgr, mask))

    def is_in_town(self, image: Image.Image) -> bool:
        """Check if character is in town by detecting shop icon."""
        w, h = image.size
        region = denormalize_region(self.REGION_SHOP, w, h)
        x1, y1, x2, y2 = region
        cropped = image.crop((x1, y1, x2, y2))
        crop_arr = np.array(cropped)
        crop_bgr = cv2.cvtColor(crop_arr, cv2.COLOR_RGB2BGR)

        for template_bgr, mask in self._shop_templates:
            if match_template(crop_bgr, template_bgr, mask, threshold=0.7):
                return True
        return False

    def is_shop_open(self, image: Image.Image) -> bool:
        """Check if a shop interface is currently open."""
        # Check for close button or shop UI elements
        return False  # Placeholder - implement based on game UI
