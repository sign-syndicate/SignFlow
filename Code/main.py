import sys

from PyQt5.QtWidgets import QApplication

from .core.config import AppConfig
from .core.theme import get_theme
from .ui.orb import FloatingOrb
from .ui.tray import SystemTrayController


def main():
    config = AppConfig()
    app = QApplication(sys.argv)
    app.setApplicationName(config.app_name)
    app.setQuitOnLastWindowClosed(False)

    theme = get_theme(config.current_theme)
    if config.debug:
        print(f"theme: {theme.name}")

    tray = SystemTrayController(app, theme)
    orb = FloatingOrb(theme, debug=config.debug)
    orb.show()

    app._signflow_orb = orb
    app._signflow_tray = tray

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
