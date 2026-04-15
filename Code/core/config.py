from dataclasses import dataclass

from .constants import APP_DEFAULTS


APP_NAME = APP_DEFAULTS.name
CURRENT_THEME = APP_DEFAULTS.theme
DEBUG = APP_DEFAULTS.debug
ORB_MAGNETIC_EFFECT_ENABLED = APP_DEFAULTS.orb_magnetic_effect_enabled


@dataclass(frozen=True)
class AppConfig:
    app_name: str = APP_NAME
    current_theme: str = CURRENT_THEME
    debug: bool = DEBUG
    orb_magnetic_effect_enabled: bool = ORB_MAGNETIC_EFFECT_ENABLED
