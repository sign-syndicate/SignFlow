import sys

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QAction, QMenu, QStyle, QSystemTrayIcon

from .core.config import AppConfig
from .core.state_manager import AppStateManager


def main():
    config = AppConfig()
    app = QApplication(sys.argv)
    app.setApplicationName(config.app_name)
    app.setQuitOnLastWindowClosed(False)

    _state_manager = AppStateManager()

    icon = QIcon()
    style = app.style()
    if style is not None:
        icon = style.standardIcon(QStyle.SP_ComputerIcon)

    tray = QSystemTrayIcon(icon, app)
    tray.setToolTip(config.app_name)

    menu = QMenu()
    start_action = QAction("Start", menu)
    exit_action = QAction("Exit", menu)

    def _start_noop():
        print("SignFlow: Start clicked")

    start_action.triggered.connect(_start_noop)
    exit_action.triggered.connect(app.quit)
    menu.addAction(start_action)
    menu.addSeparator()
    menu.addAction(exit_action)

    tray.setContextMenu(menu)
    tray.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
