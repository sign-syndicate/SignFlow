from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppDefaults:
    name: str = "SignFlow"
    theme: str = "APPLE"
    debug: bool = False
    orb_magnetic_effect_enabled: bool = False


@dataclass(frozen=True)
class RuntimeTiming:
    next_tick_ms: int = 0


@dataclass(frozen=True)
class SelectorDefaults:
    state_idle: str = "idle"
    state_selecting: str = "selecting"
    state_confirming_roi: str = "confirming_roi"
    confirmation_ms: int = 3000
    fade_in_ms: int = 180
    completion_inset_ms: int = 180
    completion_fade_ms: int = 180
    confirm_padding_px: float = 4.0
    instruction_text: str = "Select a region"
    prime_hide_delay_ms: int = 48
    min_valid_side_px: int = 4
    fallback_screen_width: int = 1280
    fallback_screen_height: int = 720


@dataclass(frozen=True)
class OrbPresentationDefaults:
    state_orb: str = "orb"
    state_panel: str = "panel"
    state_transition_to_panel: str = "transition_to_panel"
    state_transition_to_orb: str = "transition_to_orb"
    edge_left: str = "left"
    edge_right: str = "right"


@dataclass(frozen=True)
class PanelDefaults:
    caption_placeholder: str = "Listening..."
    edge_overhang_px: int = 28
    anchor_orb_diameter_px: int = 56
    anchor_orb_border_px: int = 1
    anchor_orb_shadow_alpha: int = 44
    caption_update_ms: int = 100
    caption_font_px: int = 16
    caption_weight: int = 600
    collapse_button_size_px: int = 24
    collapse_button_font_px: int = 12
    collapse_button_weight: int = 700
    min_caption_width_px: int = 240
    caption_button_gap_px: int = 8


@dataclass(frozen=True)
class TrayDefaults:
    icon_sizes_px: tuple[int, ...] = (16, 20, 24, 32, 40, 48, 64)
    margin_ratio: float = 0.16
    border_ratio: float = 0.10
    inner_margin_ratio: float = 0.04
    arc_start_deg: int = 24
    arc_span_deg: int = 64


APP_DEFAULTS = AppDefaults()
RUNTIME_TIMING = RuntimeTiming()
SELECTOR_DEFAULTS = SelectorDefaults()
ORB_PRESENTATION_DEFAULTS = OrbPresentationDefaults()
PANEL_DEFAULTS = PanelDefaults()
TRAY_DEFAULTS = TrayDefaults()
