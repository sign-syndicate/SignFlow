from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtGui import QColor, QConicalGradient, QIcon, QPainter, QPen, QPixmap, QRadialGradient
from PyQt5.QtWidgets import QAction, QMenu, QSystemTrayIcon

from ..core.theme import Theme


def build_tray_icon(theme: Theme) -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    center = pixmap.rect().center()

    glow_color = QColor(theme.glow_color)
    glow_color.setAlphaF(0.5 if theme.name == "APPLE" else 0.62)
    glow = QRadialGradient(center, 24)
    glow.setColorAt(0.0, glow_color)
    glow.setColorAt(0.55, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 46))
    glow.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.setPen(Qt.NoPen)
    painter.setBrush(glow)
    painter.drawEllipse(center, 22, 22)

    if theme.name == "APPLE":
        shell = QRadialGradient(center - QPointF(2.0, 3.0), 17)
        shell.setColorAt(0.0, QColor(255, 255, 255, 245))
        shell.setColorAt(0.62, QColor(230, 230, 228, 230))
        shell.setColorAt(1.0, QColor(192, 192, 190, 255))
    else:
        shell = QRadialGradient(center - QPointF(2.0, 3.0), 17)
        shell.setColorAt(0.0, QColor(25, 32, 38, 255))
        shell.setColorAt(0.62, QColor(13, 18, 22, 245))
        shell.setColorAt(1.0, QColor(7, 10, 13, 255))
    painter.setBrush(shell)
    painter.drawEllipse(center, 16, 16)

    accent_ring = QConicalGradient(center, 18)
    accent_ring.setColorAt(0.00, QColor(theme.hover_color if theme.name != "APPLE" else "#D4D4D4"))
    accent_ring.setColorAt(0.18, QColor(theme.glow_color))
    accent_ring.setColorAt(0.38, QColor(255, 255, 255, 0))
    accent_ring.setColorAt(0.70, QColor(theme.glow_color))
    accent_ring.setColorAt(1.00, QColor(theme.hover_color if theme.name != "APPLE" else "#F4F4F4"))
    ring_pen = QPen(accent_ring, 1.7)
    ring_pen.setCapStyle(Qt.RoundCap)
    ring_pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(ring_pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawEllipse(center, 16, 16)

    if theme.name == "APPLE":
        dot = QRadialGradient(center - QPointF(5.0, 5.0), 6)
        dot.setColorAt(0.0, QColor(255, 255, 255, 180))
        dot.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(dot)
        painter.drawEllipse(center - QPointF(6.0, 6.0), 12, 12)

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
