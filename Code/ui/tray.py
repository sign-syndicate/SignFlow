from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QAction, QMenu, QSystemTrayIcon

from ..core.constants import TRAY_DEFAULTS
from ..core.theme import Theme


def _draw_icon_pixmap(theme: Theme, size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

    margin = max(2, int(round(size * TRAY_DEFAULTS.margin_ratio)))
    diameter = size - (margin * 2)
    border_width = max(1, int(round(size * TRAY_DEFAULTS.border_ratio)))
    inner_margin = border_width + max(1, int(round(size * TRAY_DEFAULTS.inner_margin_ratio)))

    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(theme.tray_fill_color))
    painter.drawEllipse(margin, margin, diameter, diameter)

    border_pen = QPen(QColor(theme.tray_border_color))
    border_pen.setWidth(border_width)
    border_pen.setCapStyle(Qt.RoundCap)
    border_pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(border_pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawEllipse(margin, margin, diameter, diameter)

    highlight_pen = QPen(QColor(theme.tray_highlight_color))
    highlight_pen.setWidth(max(1, border_width - 1))
    highlight_pen.setCapStyle(Qt.RoundCap)
    painter.setPen(highlight_pen)
    painter.drawArc(
        margin + inner_margin,
        margin + inner_margin,
        diameter - (inner_margin * 2),
        diameter - (inner_margin * 2),
        TRAY_DEFAULTS.arc_start_deg * 16,
        TRAY_DEFAULTS.arc_span_deg * 16,
    )

    painter.end()
    return pixmap


def build_tray_icon(theme: Theme) -> QIcon:
    icon = QIcon()
    for size in TRAY_DEFAULTS.icon_sizes_px:
        icon.addPixmap(_draw_icon_pixmap(theme, size))
    return icon


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
