from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QRadialGradient
from PyQt5.QtWidgets import QAction, QMenu, QSystemTrayIcon

from ..core.theme import Theme


def build_tray_icon(theme: Theme) -> QIcon:
    pixmap = QPixmap(96, 96)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    center = QPointF(48.0, 48.0)

    glow_color = QColor(theme.glow_color)
    glow_color.setAlphaF(0.40 if theme.name == "APPLE" else 0.54)
    glow = QRadialGradient(center, 30)
    glow.setColorAt(0.0, glow_color)
    glow.setColorAt(0.55, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 40))
    glow.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.setPen(Qt.NoPen)
    painter.setBrush(glow)
    painter.drawEllipse(center, 25, 25)

    if theme.name == "APPLE":
        shell = QRadialGradient(center - QPointF(3.0, 4.0), 22)
        shell.setColorAt(0.0, QColor(255, 255, 255, 248))
        shell.setColorAt(0.56, QColor(238, 238, 236, 240))
        shell.setColorAt(1.0, QColor(198, 198, 196, 255))
    else:
        shell = QRadialGradient(center - QPointF(3.0, 4.0), 22)
        shell.setColorAt(0.0, QColor(28, 35, 41, 255))
        shell.setColorAt(0.62, QColor(12, 17, 22, 250))
        shell.setColorAt(1.0, QColor(6, 9, 12, 255))
    painter.setBrush(shell)
    painter.drawEllipse(center, 20, 20)

    ring_color = QColor("#A7A7A7") if theme.name == "APPLE" else QColor(theme.glow_color)
    ring_color.setAlphaF(0.95 if theme.name == "APPLE" else 0.85)
    ring_pen = QPen(ring_color, 2.1)
    ring_pen.setCapStyle(Qt.RoundCap)
    ring_pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(ring_pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawEllipse(center, 20, 20)

    accent = QColor(theme.hover_color if theme.name != "APPLE" else "#F6F6F6")
    accent.setAlphaF(0.9 if theme.name != "APPLE" else 0.75)
    accent_pen = QPen(accent, 1.1)
    accent_pen.setCapStyle(Qt.RoundCap)
    painter.setPen(accent_pen)
    painter.drawArc(28, 28, 40, 40, 30 * 16, 70 * 16)
    painter.drawArc(28, 28, 40, 40, 210 * 16, 70 * 16)

    if theme.name == "APPLE":
        dot = QRadialGradient(center - QPointF(6.0, 6.0), 8)
        dot.setColorAt(0.0, QColor(255, 255, 255, 170))
        dot.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(dot)
        painter.drawEllipse(center - QPointF(7.0, 7.0), 14, 14)

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
