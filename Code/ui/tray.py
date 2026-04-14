from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QRadialGradient
from PyQt5.QtWidgets import QAction, QMenu, QSystemTrayIcon

from ..core.theme import Theme


def build_tray_icon(theme: Theme) -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    center = pixmap.rect().center()

    glow_color = QColor(theme.glow_color)
    glow_color.setAlphaF(0.45)
    glow = QRadialGradient(center, 24)
    glow.setColorAt(0.0, glow_color)
    glow.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.setPen(Qt.NoPen)
    painter.setBrush(glow)
    painter.drawEllipse(center, 22, 22)

    orb = QRadialGradient(center, 18)
    orb.setColorAt(0.0, QColor(theme.hover_color))
    orb.setColorAt(0.52, QColor(theme.base_color))
    orb.setColorAt(1.0, QColor(theme.base_color).darker(118))
    painter.setBrush(orb)
    painter.drawEllipse(center, 16, 16)

    rim = QPen(QColor(255, 255, 255, 72 if theme.name == "APPLE" else 36))
    rim.setWidthF(1.0)
    painter.setPen(rim)
    painter.setBrush(Qt.NoBrush)
    painter.drawEllipse(center, 16, 16)
    painter.end()

    return QIcon(pixmap)


class SystemTrayController:
    def __init__(self, app, theme: Theme):
        self._app = app
        self._theme = theme
        self._tray = QSystemTrayIcon(build_tray_icon(theme), app)
        self._tray.setToolTip(app.applicationName())

        self._menu = QMenu()
        self._exit_action = QAction("Exit", self._menu)
        self._exit_action.triggered.connect(app.quit)
        self._menu.addAction(self._exit_action)

        self._tray.setContextMenu(self._menu)
        self._tray.show()
