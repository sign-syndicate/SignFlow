from dataclasses import dataclass, field

from PyQt5.QtCore import QSize

from .theme import AppTheme, get_active_theme


@dataclass(frozen=True)
class AppConfig:
    theme: AppTheme = field(default_factory=get_active_theme)
    orb_diameter: int = 56
    orb_margin: int = 18
    orb_opacity_idle: float = 0.84
    orb_opacity_hover: float = 1.0
    panel_size: QSize = field(default_factory=lambda: QSize(440, 130))
    panel_min_size: QSize = field(default_factory=lambda: QSize(360, 116))
    panel_corner_radius: int = 20
    panel_margin: int = 18
    panel_padding_x: int = 22
    panel_padding_y: int = 14
    open_duration_ms: int = 250
    dim_fade_ms: int = 200
    close_duration_ms: int = 220
    border_timer_ms: int = 30
    caption_timer_ms: int = 2200
    selection_border_width: int = 2
    selection_text: str = "Drag to select a capture region"
    idle_caption: str = "Click the orb to begin"
    open_caption: str = "select a region or press play"
    active_caption_cycle: tuple = (
        "Listening for captions...",
        "Captions update here in real time.",
        "Region locked. Ready for live assistive output.",
        "Premium minimal UI, placeholder text only for now.",
    )
    shortcut_sequence: str = "F8"
    app_name: str = "SignFlow"
