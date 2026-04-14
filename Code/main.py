import sys

from PyQt5.QtWidgets import QApplication

from .core.config import AppConfig
from .core.state_manager import AppStateManager
from .ui.overlay import SignFlowOverlay
from .ui.tray import SystemTrayController


def main():
    config = AppConfig()
    app = QApplication(sys.argv)
    app.setApplicationName(config.app_name)
    app.setQuitOnLastWindowClosed(False)

    state_manager = AppStateManager(config)
    overlay = SignFlowOverlay(config, state_manager)
    tray = SystemTrayController(config)
    tray.open_requested.connect(overlay.show)
    tray.exit_requested.connect(overlay.exit_application)

    overlay.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
