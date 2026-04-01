"""Game layout constants for Lineage 2M.

ALL coordinates extracted from original AutoKeyL2M v2.7 bytecode.
Normalized (0.0-1.0) coordinates work across any resolution.
Pixel coordinates are at 1280x720 base, auto-scaled via Clicker.scale_coords().
"""


def denormalize(norm_region: tuple, width: int, height: int) -> tuple[int, int, int, int]:
    """Convert normalized (0-1) region to pixel coordinates."""
    x1n, y1n, x2n, y2n = norm_region
    return (int(x1n * width), int(y1n * height),
            int(x2n * width), int(y2n * height))


def denormalize_point(norm_point: tuple, width: int, height: int) -> tuple[int, int]:
    """Convert normalized point to pixel coordinates."""
    xn, yn = norm_point
    return (int(xn * width), int(yn * height))


# ╔══════════════════════════════════════════════════╗
# ║  HP BAR (from func/checkHP.py CheckHP.__init__)  ║
# ╚══════════════════════════════════════════════════╝

# HP bar FULL region for percentage calculation
HP_BAR = (0.0359375, 0.022222222222222223, 0.165625, 0.04027777777777778)

# HP bar sample point for color calibration (leftmost always-filled area)
HP_SAMPLE = (0.0328125, 0.027777777777777776, 0.0359375, 0.03888888888888889)

# HP bar small/thin strip (quick check)
HP_BAR_SMALL = (0.0359375, 0.020833333333333332, 0.165625, 0.02361111111111111)

# Low HP check region (left portion of HP bar)
HP_LOW_REGION = (0.0359375, 0.022222222222222223, 0.0703125, 0.04027777777777778)

# Medium HP check region (right portion of HP bar)
HP_MED_REGION = (0.13046875, 0.025, 0.17109375, 0.03888888888888889)

# HP bar 3-part regions (for robust detection)
HP_PART1 = (0.0328125, 0.022222222222222223, 0.0546875, 0.04027777777777778)
HP_PART2 = (0.05546875, 0.022222222222222223, 0.14453125, 0.04027777777777778)
HP_PART3 = (0.1453125, 0.022222222222222223, 0.171875, 0.04027777777777778)

# Party member HP bars
HP_F1 = (0.02890625, 0.34305555555555556, 0.1390625, 0.3472222222222222)
HP_F2 = (0.02890625, 0.4041666666666667, 0.1390625, 0.4097222222222222)
HP_F3 = (0.02890625, 0.4652777777777778, 0.1390625, 0.46944444444444444)


# ╔══════════════════════════════════════════════════╗
# ║  RADAR (from func/radar.py)                      ║
# ╚══════════════════════════════════════════════════╝

# Radar target icon regions (normalized)
RADAR_TARGET_RIGHT = (0.7765625, 0.29444444444444445, 0.78984375, 0.3472222222222222)
RADAR_TARGET_LEFT = (0.62421875, 0.29444444444444445, 0.6375, 0.3472222222222222)
RADAR_TARGET_TOP = (0.62421875, 0.23333333333333334, 0.6375, 0.2861111111111111)
RADAR_ICON_2 = (0.7765625, 0.29444444444444445, 0.78984375, 0.3472222222222222)
RADAR_ICON_4 = (0.7765625, 0.23333333333333334, 0.78984375, 0.2861111111111111)

# Combined radar area (covers all target icon positions)
RADAR_TARGET_AREA = (0.62421875, 0.23333333333333334, 0.78984375, 0.3472222222222222)

# Warning icon positions (pixel coordinates per resolution)
WARNING_POSITIONS = {
    1280: [
        (1166, 214, 1182, 248), (974, 214, 990, 248),
        (974, 165, 990, 204), (1166, 165, 1182, 204),
        (974, 133, 990, 152), (1168, 133, 1182, 152),
    ],
    800: [(726, 134, 738, 155), (605, 134, 617, 155)],
    640: [(582, 105, 593, 126), (484, 105, 495, 126)],
}

# Warning template files per resolution
WARNING_TEMPLATES = {
    1280: "assets/warning_1280.png",
    960: "assets/warning_960_light.png",
    800: "assets/warning_800.png",
    640: "assets/warning_640.png",
}


# ╔══════════════════════════════════════════════════╗
# ║  MAP AREA POSITIONS (boss/zariche check)          ║
# ╚══════════════════════════════════════════════════╝

# Area template files for map panel (template matching)
MAP_AREA_TEMPLATES = {
    "ALL":    "assets/area_all.png",
    "Gludio": "assets/area_gludio.png",
    "Dion":   "assets/area_dion.png",
    "Giran":  "assets/area_giran.png",
    "Oren":   "assets/area_oren.png",
    "Aden":   "assets/area_aden.png",
}

# Koordinat klik boss/zariche icon setelah area dipilih @1280x720
# Boss icon: (925, 110), Zariche icon: (995, 110)
MAP_BOSS_ICON_1280 = (925, 110)
MAP_ZARICHE_ICON_1280 = (995, 110)

# Koordinat klik boss/zariche entry di list (nama boss) @1280x720
MAP_BOSS_ENTRY_1280 = (230, 250)


# ╔══════════════════════════════════════════════════╗
# ║  SAFE AREA / TOWN (from func/ISafeArea.py)       ║
# ╚══════════════════════════════════════════════════╝

# NPC icons box in viewport (left side when in town)
NPC_ICONS_BOX = (0.03984375, 0.10833333333333334, 0.05234375, 0.2986111111111111)

# Inventory open detection region
INVENTORY_REGION = (0.79609375, 0.1486111111111111, 0.9625, 0.22916666666666666)

# Error message dialog region
ERROR_MESSAGE_REGION = (0.396875, 0.5666666666666667, 0.609375, 0.6486111111111111)

# Shop icon regions (used by check_in_town_by_shop_icon)
# The original uses dynamic NPC box calculation per resolution,
# but these are the base regions for shop icon detection
SHOP_ICON_REGIONS = [
    NPC_ICONS_BOX,  # Main NPC icon box area
]


# ╔══════════════════════════════════════════════════╗
# ║  HUNTING (from func/Hunting.py)                   ║
# ╚══════════════════════════════════════════════════╝

# Minimap / character position indicator
HUNTING_MINIMAP = (0.08203125, 0.15555555555555556, 0.125, 0.2361111111111111)

# Character level/name indicator (top-left corner)
HUNTING_CHAR_INDICATOR = (0.0265625, 0.011111111111111112, 0.034375, 0.02361111111111111)

# Auto-hunt button area
AUTO_HUNT_BUTTON = (0.79296875, 0.48055555555555557, 0.828125, 0.5444444444444444)

# Auto-play/AFK indicator
AUTO_PLAY_INDICATOR = (0.9359375, 0.6277777777777778, 0.96875, 0.6902777777777778)

# Death/resurrection dialog buttons
DEATH_DIALOG_BTN1 = (0.45859375, 0.5722222222222222, 0.5453125, 0.6875)
DEATH_DIALOG_BTN2 = (0.4203125, 0.5722222222222222, 0.50703125, 0.6875)
DEATH_DIALOG_AREA = (0.3828125, 0.5694444444444444, 0.6171875, 0.7013888888888888)

# Combat indicator (red flash near HP area)
COMBAT_INDICATOR = (0.0265625, 0.011111111111111112, 0.034375, 0.02361111111111111)


# ╔══════════════════════════════════════════════════╗
# ║  IGNORE PRESSING KEY (from func/ignorePressingKey)║
# ╚══════════════════════════════════════════════════╝

# Inventory/skill window detection regions
IGNORE_KEY_INVENTORY = (0.69140625, 0.28888888888888886, 0.72421875, 0.5111111111111111)
IGNORE_KEY_SKILL = (0.7421875, 0.6694444444444444, 0.84453125, 0.7263888888888889)
IGNORE_KEY_DIALOG = (0.73125, 0.19027777777777777, 0.7765625, 0.5902777777777778)


# ╔══════════════════════════════════════════════════╗
# ║  TELEPORT (from func/autoTeleport.py)             ║
# ╚══════════════════════════════════════════════════╝

# Press "O" to open saved locations
SAVED_LOCATION_KEY = "O"

# Saved spots dialog detection region
SAVED_SPOTS_DIALOG_REGION = (0.03125, 0.7527777777777778, 0.24765625, 0.8138888888888889)
SAVED_SPOTS_DIALOG_THRESHOLD = 0.4

# Invitation accept/reject icon regions (normalized)
INVITATION_ACCEPT_REGION = (0.375, 0.21388888888888888, 0.4078125, 0.2722222222222222)
INVITATION_REJECT_REGION = (0.3375, 0.21388888888888888, 0.3703125, 0.2722222222222222)
INVITATION_ACCEPT_CLICK_1280 = (502, 176)

# Spot positions at 1280x720 base
# Each spot: (name_x, name_y, teleport_btn_x, teleport_btn_y)
# 1st click = spot name, 2nd click = teleport arrow button
SAVED_SPOT_COORDS_1280 = [
    (194, 228, 302, 274),   # Spot 1
    (194, 284, 302, 330),   # Spot 2
    (194, 336, 302, 382),   # Spot 3
    (194, 388, 302, 434),   # Spot 4
    (194, 440, 302, 450),   # Spot 5
]

# Map teleport button positions (1280x720 base)
MAP_TELEPORT_BTN_1280 = (1154, 478)
MAP_CONFIRM_BTN_1280 = (759, 482)

# Veora map spot positions (1280x720 base)
VEORA_SPOT_COORDS_1280 = [
    (123, 100), (123, 150), (123, 195),
    (123, 240), (123, 290), (124, 325),
]
VEORA_CONFIRM_REGION = (0.453125, 0.5694444444444444, 0.5390625, 0.7916666666666666)
VEORA_CONFIRM_BTN_1280 = (750, 480)

# Dungeon spot positions (1280x720 base)
DUNGEON_SPOT_COORDS_1280 = [
    (835, 145), (835, 208), (835, 268), (835, 334),
    (835, 398), (835, 462), (835, 526), (835, 590), (835, 654),
]
DUNGEON_CONFIRM_BTN_1280 = (1075, 655)
DUNGEON_DIALOG_REGION = (0.6078125, 0.8472222222222222, 0.77578125, 0.9722222222222222)


# ╔══════════════════════════════════════════════════╗
# ║  SCREEN STABILITY (from is_stable_an_hue_icon)    ║
# ╚══════════════════════════════════════════════════╝

# Region where the "an hue" icon appears when screen is stable/loaded
# Template: assets/an_hue_1.png — matched against this region each frame
AN_HUE_ICON_REGION = (0.0265625, 0.011111111111111112, 0.05, 0.055555555555555556)

# Confirm dialog button position at 1280x720
CONFIRM_DIALOG_CLICK_1280 = (640, 576)

# Skill slot icon regions at 1280x720 (for glow/active detection)
# Slot numbering: 1-8 from left to right in the bottom skill bar
# Skill bar is at the very bottom of screen (~92-98% Y)
# Each slot is approximately 44x44 pixels at 1280x720
SKILL_SLOT_REGIONS_1280 = {
    1: (748, 666, 792, 710),
    2: (800, 666, 844, 710),
    3: (852, 666, 896, 710),
    4: (904, 666, 948, 710),
    5: (956, 666, 1000, 710),
    6: (1008, 666, 1052, 710),
    7: (1060, 666, 1104, 710),
    8: (1112, 666, 1156, 710),
}


# ╔══════════════════════════════════════════════════╗
# ║  SCREEN CAPTURE (from utils/screen.py)            ║
# ╚══════════════════════════════════════════════════╝

# Marker regions for screen stability check
SCREEN_MARKER_1 = (0.02578125, 0.019444444444444445, 0.0296875, 0.043055555555555555)
SCREEN_MARKER_2 = (0.02578125, 0.05138888888888889, 0.0296875, 0.06666666666666667)
SCREEN_MARKER_3 = (0.68984375, 0.016666666666666666, 0.7234375, 0.07222222222222222)

# Opening screen close button
OPENING_SCREEN_CLOSE = (0.9359375, 0.006944444444444444, 0.996875, 0.09444444444444444)


# ╔══════════════════════════════════════════════════╗
# ║  LETTER / MAIL (from main_tab4.py)                ║
# ╚══════════════════════════════════════════════════╝

# Letter dialog buttons region
LETTER_BUTTONS_REGION = (0.5234375, 0.875, 0.9734375, 0.9444444444444444)


# ╔══════════════════════════════════════════════════╗
# ║  HELPER FUNCTIONS                                 ║
# ╚══════════════════════════════════════════════════╝

def get_warning_template_path(img_width: int) -> str:
    """Get the warning template file for closest resolution."""
    if img_width >= 960:
        return WARNING_TEMPLATES.get(1280, "assets/warning_1280.png")
    elif img_width >= 750:
        return WARNING_TEMPLATES.get(800, "assets/warning_800.png")
    else:
        return WARNING_TEMPLATES.get(640, "assets/warning_640.png")


def get_warning_positions(img_width: int) -> list:
    """Get warning icon pixel positions for closest resolution."""
    if img_width >= 960:
        return WARNING_POSITIONS.get(1280, [])
    elif img_width >= 750:
        return WARNING_POSITIONS.get(800, [])
    else:
        return WARNING_POSITIONS.get(640, [])


def get_warning_region(img_width: int) -> tuple:
    """Get normalized warning region — scales to ANY resolution.

    Based on 1280x720 reference positions where ❗ icons appear:
    - Rightmost: x=1166-1182 (91%-92% of width)
    - Leftmost:  x=974-990  (76%-77% of width)
    - Top:       y=133-152  (18%-21% of height)
    - Bottom:    y=214-248  (30%-34% of height)

    Add generous padding for different resolutions and radar layouts.
    """
    # Normalized from 1280x720 reference with padding
    return (0.72, 0.15, 0.98, 0.50)
