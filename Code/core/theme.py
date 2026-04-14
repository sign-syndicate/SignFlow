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
    primary_color: str
    primary_color_light: str | None
    overlay_color: str
    overlay_opacity: float
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
        primary_color="#FAFAFA",
        primary_color_light="#DCDCDC",
        overlay_color="#0F1115",
        overlay_opacity=0.52,
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
        primary_color="#35F0C6",
        primary_color_light="#1CA68B",
        overlay_color="#040608",
        overlay_opacity=0.58,
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


def _clamp_channel(value: float) -> int:
    return max(0, min(255, int(round(value))))


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    normalized = str(color).strip().lstrip("#")
    if len(normalized) != 6:
        return 255, 255, 255
    return tuple(int(normalized[index : index + 2], 16) for index in (0, 2, 4))


def _rgb_to_hex(red: int, green: int, blue: int) -> str:
    return f"#{red:02X}{green:02X}{blue:02X}"


def brighten_hex(color: str, amount: float) -> str:
    amount = max(0.0, min(1.0, float(amount)))
    red, green, blue = _hex_to_rgb(color)
    return _rgb_to_hex(
        _clamp_channel(red + ((255 - red) * amount)),
        _clamp_channel(green + ((255 - green) * amount)),
        _clamp_channel(blue + ((255 - blue) * amount)),
    )


def resolve_primary_light_color(theme: Theme) -> str:
    if theme.primary_color_light:
        return theme.primary_color_light

    # Derive a brighter entry color when no light variant is provided.
    if theme.name == "APPLE":
        return brighten_hex(theme.primary_color, 0.12)
    return brighten_hex(theme.primary_color, 0.28)