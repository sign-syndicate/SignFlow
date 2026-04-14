from dataclasses import dataclass


@dataclass(frozen=True)
class AppTheme:
    name: str
    orb_fill_top: tuple
    orb_fill_bottom: tuple
    orb_ring: tuple
    orb_glow: tuple
    orb_shadow: tuple
    panel_base: tuple
    panel_top: tuple
    panel_bottom: tuple
    panel_text: tuple
    panel_button_bg: tuple
    panel_button_hover: tuple
    panel_button_pressed: tuple
    panel_button_text: tuple
    panel_button_border: tuple
    dim_color: tuple
    selector_chip_bg: tuple
    selector_chip_border: tuple
    selector_chip_text: tuple
    selector_fill: tuple
    selector_border: tuple
    idle_border_glow: tuple
    idle_border_core: tuple
    selecting_border_glow: tuple
    selecting_border_core: tuple
    active_border_a: tuple
    active_border_b: tuple
    active_border_c: tuple
    tray_outer: tuple
    tray_inner: tuple


THEMES = {
    "neo_dark": AppTheme(
        name="neo_dark",
        orb_fill_top=(43, 56, 74, 255),
        orb_fill_bottom=(25, 31, 41, 255),
        orb_ring=(255, 255, 255, 64),
        orb_glow=(104, 154, 255, 95),
        orb_shadow=(0, 0, 0, 96),
        panel_base=(17, 21, 29, 228),
        panel_top=(28, 36, 48, 236),
        panel_bottom=(13, 17, 24, 236),
        panel_text=(244, 247, 252, 235),
        panel_button_bg=(255, 255, 255, 12),
        panel_button_hover=(255, 255, 255, 22),
        panel_button_pressed=(255, 255, 255, 30),
        panel_button_text=(245, 247, 252, 220),
        panel_button_border=(255, 255, 255, 20),
        dim_color=(8, 10, 15, 118),
        selector_chip_bg=(22, 25, 33, 220),
        selector_chip_border=(255, 255, 255, 24),
        selector_chip_text=(243, 246, 252, 230),
        selector_fill=(102, 187, 255, 42),
        selector_border=(123, 205, 255, 230),
        idle_border_glow=(182, 190, 204, 32),
        idle_border_core=(196, 202, 214, 110),
        selecting_border_glow=(120, 201, 255, 72),
        selecting_border_core=(134, 210, 255, 220),
        active_border_a=(196, 154, 255, 255),
        active_border_b=(140, 98, 255, 255),
        active_border_c=(73, 188, 255, 255),
        tray_outer=(28, 36, 48, 255),
        tray_inner=(90, 143, 255, 255),
    ),
    "apple_light": AppTheme(
        name="apple_light",
        orb_fill_top=(255, 255, 255, 255),
        orb_fill_bottom=(241, 246, 252, 255),
        orb_ring=(125, 146, 176, 132),
        orb_glow=(143, 173, 214, 72),
        orb_shadow=(20, 38, 74, 46),
        panel_base=(255, 255, 255, 246),
        panel_top=(255, 255, 255, 252),
        panel_bottom=(245, 249, 255, 245),
        panel_text=(67, 82, 105, 245),
        panel_button_bg=(242, 246, 252, 230),
        panel_button_hover=(233, 240, 250, 242),
        panel_button_pressed=(222, 232, 246, 245),
        panel_button_text=(68, 86, 112, 236),
        panel_button_border=(177, 196, 224, 178),
        dim_color=(52, 69, 94, 52),
        selector_chip_bg=(255, 255, 255, 226),
        selector_chip_border=(161, 181, 209, 128),
        selector_chip_text=(72, 90, 118, 236),
        selector_fill=(127, 170, 223, 44),
        selector_border=(115, 159, 216, 235),
        idle_border_glow=(173, 190, 212, 34),
        idle_border_core=(158, 178, 205, 124),
        selecting_border_glow=(115, 176, 239, 76),
        selecting_border_core=(103, 165, 232, 228),
        active_border_a=(148, 140, 255, 255),
        active_border_b=(112, 126, 255, 255),
        active_border_c=(118, 190, 255, 255),
        tray_outer=(235, 242, 252, 255),
        tray_inner=(139, 166, 212, 255),
    ),
}

# Change only this value to switch the entire UI theme.
ACTIVE_THEME = "apple_light"


def get_active_theme() -> AppTheme:
    return THEMES.get(ACTIVE_THEME, THEMES["apple_light"])
