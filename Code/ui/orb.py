from PyQt5.QtCore import QEasingCurve, QPoint, QPointF, QPropertyAnimation, QRect, QRectF, Qt, pyqtProperty, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QRadialGradient, QPen
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QWidget


class FloatingOrb(QWidget):
    activated = pyqtSignal()
    dock_changed = pyqtSignal(str)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self._dock_edge = "right"
        self._hover_progress = 0.0
        self._dragging = False
        self._drag_offset = QPoint()
        self._press_pos = QPoint()
        self._click_distance = 8
        self._hover_anim = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_anim.setDuration(160)
        self._hover_anim.setEasingCurve(QEasingCurve.OutCubic)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setFixedSize(self._config.orb_diameter, self._config.orb_diameter)
        self.setWindowOpacity(self._config.orb_opacity_idle)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(26)
        shadow.setOffset(0, 7)
        shadow.setColor(QColor(*self._config.theme.orb_shadow))
        self.setGraphicsEffect(shadow)

    def set_dock_edge(self, dock_edge: str):
        if dock_edge == self._dock_edge:
            return
        self._dock_edge = dock_edge
        self.dock_changed.emit(dock_edge)

    def dock_edge(self) -> str:
        return self._dock_edge

    def hoverProgress(self):
        return self._hover_progress

    def setHoverProgress(self, value):
        self._hover_progress = max(0.0, min(1.0, float(value)))
        self.update()

    hoverProgress = pyqtProperty(float, fget=hoverProgress, fset=setHoverProgress)

    def set_hovered(self, hovered: bool):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(1.0 if hovered else 0.0)
        self._hover_anim.start()

    def set_docked_geometry(self, geometry: QRect):
        self.setGeometry(geometry)

    def snap_to_screen_edge(self):
        screen = self.screen()
        if screen is None:
            return
        geometry = screen.availableGeometry()
        size = self.size()
        min_x = geometry.x() + self._config.orb_margin
        max_x = geometry.x() + geometry.width() - size.width() - self._config.orb_margin
        min_y = geometry.y() + self._config.orb_margin
        max_y = geometry.y() + geometry.height() - size.height() - self._config.orb_margin
        current = self.geometry()
        center_x = current.center().x()
        dock_left = center_x < geometry.center().x()
        new_x = min_x if dock_left else max_x
        new_y = max(min_y, min(current.y(), max_y))
        self.move(int(new_x), int(new_y))
        self.set_dock_edge("left" if dock_left else "right")

    def place_default(self):
        screen = self.screen()
        if screen is None:
            return
        geometry = screen.availableGeometry()
        y = geometry.y() + int((geometry.height() - self.height()) / 2)
        x = geometry.x() + self._config.orb_margin
        if self._dock_edge == "right":
            x = geometry.x() + geometry.width() - self.width() - self._config.orb_margin
        self.move(int(x), int(y))

    def enterEvent(self, _event):
        self.set_hovered(True)

    def leaveEvent(self, _event):
        self.set_hovered(False)

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        self._press_pos = event.globalPos()
        self._drag_offset = event.pos()
        self._dragging = False

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if (event.globalPos() - self._press_pos).manhattanLength() > self._click_distance:
            self._dragging = True
        if self._dragging:
            self.move(event.globalPos() - self._drag_offset)

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        if not self._dragging:
            self.activated.emit()
        self._dragging = False
        self.snap_to_screen_edge()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        progress = self._hover_progress
        fill = QRadialGradient(rect.center(), rect.width() * 0.7, QPointF(rect.center().x(), rect.top() + 8))
        top = QColor(*self._config.theme.orb_fill_top)
        bottom = QColor(*self._config.theme.orb_fill_bottom)
        fill.setColorAt(0.0, top.lighter(104))
        fill.setColorAt(0.35, top)
        fill.setColorAt(1.0, bottom)

        glow = QColor(*self._config.theme.orb_glow)
        glow.setAlpha(int(glow.alpha() + 50 * progress))
        painter.setPen(Qt.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(rect.adjusted(-4 - 2 * progress, -4 - 2 * progress, 4 + 2 * progress, 4 + 2 * progress))

        painter.setBrush(fill)
        painter.setPen(QPen(QColor(*self._config.theme.orb_ring), 1.2))
        painter.drawEllipse(rect)

        inner = rect.adjusted(13, 13, -13, -13)
        if inner.width() > 0 and inner.height() > 0:
            accent = QColor(*self._config.theme.panel_top)
            accent.setAlpha(int(92 + 40 * progress))
            painter.setBrush(accent)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(inner.adjusted(6, 6, -6, -6))
