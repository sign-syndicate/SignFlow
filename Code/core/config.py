from dataclasses import dataclass


APP_NAME = "SignFlow"
CURRENT_THEME = "APPLE"
DEBUG = False
ORB_MAGNETIC_EFFECT_ENABLED = False


@dataclass(frozen=True)
class AppConfig:
    app_name: str = APP_NAME
    current_theme: str = CURRENT_THEME
    debug: bool = DEBUG
    orb_magnetic_effect_enabled: bool = ORB_MAGNETIC_EFFECT_ENABLED
