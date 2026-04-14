from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    app_name: str = "SignFlow"
