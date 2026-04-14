from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    name: str
    base_color: str
    glow_color: str
    hover_color: str
    opacity_idle: float
    opacity_hover: float
    shadow_strength: float


THEMES = {
    "APPLE": Theme(
        name="APPLE",
        base_color="#F3EFE8",
        glow_color="#D7D2C8",
        hover_color="#FFFFFF",
        opacity_idle=0.84,
        opacity_hover=0.97,
        shadow_strength=0.22,
    ),
    "HACKER": Theme(
        name="HACKER",
        base_color="#11161A",
        glow_color="#38F6C7",
        hover_color="#B06CFF",
        opacity_idle=0.88,
        opacity_hover=1.0,
        shadow_strength=0.48,
    ),
}


def get_theme(theme_name: str) -> Theme:
    normalized = str(theme_name or "APPLE").strip().upper()
    return THEMES.get(normalized, THEMES["APPLE"])