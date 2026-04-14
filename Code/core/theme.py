from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    name: str
    base_color: str
    glow_color: str
    hover_color: str
    tray_fill_color: str
    tray_border_color: str
    tray_highlight_color: str
    opacity_idle: float
    opacity_hover: float
    shadow_strength: float


THEMES = {
    "APPLE": Theme(
        name="APPLE",
        base_color="#F3EFE8",
        glow_color="#D7D2C8",
        hover_color="#FFFFFF",
        tray_fill_color="#EDEDEA",
        tray_border_color="#656565",
        tray_highlight_color="#FFFFFF",
        opacity_idle=0.84,
        opacity_hover=0.97,
        shadow_strength=0.22,
    ),
    "DARK": Theme(
        name="DARK",
        base_color="#0E141A",
        glow_color="#35F0C6",
        hover_color="#8B6CFF",
        tray_fill_color="#131B22",
        tray_border_color="#9EF3DE",
        tray_highlight_color="#D2C2FF",
        opacity_idle=0.9,
        opacity_hover=1.0,
        shadow_strength=0.42,
    ),
}

LEGACY_THEME_ALIASES = {
    "HACKER": "DARK",
}


def get_theme(theme_name: str) -> Theme:
    normalized = str(theme_name or "APPLE").strip().upper()
    normalized = LEGACY_THEME_ALIASES.get(normalized, normalized)
    return THEMES.get(normalized, THEMES["APPLE"])