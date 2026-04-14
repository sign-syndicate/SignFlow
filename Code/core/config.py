from dataclasses import dataclass


APP_NAME = "SignFlow"
CURRENT_THEME = "DARK"
DEBUG = False


@dataclass(frozen=True)
class AppConfig:
    app_name: str = APP_NAME
    current_theme: str = CURRENT_THEME
    debug: bool = DEBUG
