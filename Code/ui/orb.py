from __future__ import annotations

import math

from PyQt5.QtCore import QEasingCurve, QPoint, QPointF, QPropertyAnimation, QRectF, Qt, QTimer, pyqtProperty
from PyQt5.QtGui import QColor, QBrush, QCursor, QGuiApplication, QLinearGradient, QPainter, QPen, QRadialGradient, QConicalGradient
from PyQt5.QtWidgets import QApplication, QWidget

from ..core.theme import Theme


class FloatingOrb(QWidget):
    BASE_DIAMETER = 56.0
    WIDGET_DIAMETER = 124

    def __init__(self, theme: Theme, debug: bool = False, parent=None):
        super().__init__(parent)
        self._theme = theme
        self._debug = debug
        self._scale = 1.0
        self._hover_progress = 0.0
        self._magnet_offset = QPointF(0.0, 0.0)
        self._dragging = False
        self._press_global = QPoint()
        self._press_window_pos = QPoint()
        self._drag_threshold_exceeded = False
        self._drag_start_distance = QApplication.startDragDistance()
        self._positioned = False
        self._snap_animation = None
        self._border_phase = 0.0
        self._cursor_proximity = 0.0

        self.setFixedSize(self.WIDGET_DIAMETER, self.WIDGET_DIAMETER)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_Hover, True)

        self._breathing_animation = QPropertyAnimation(self, b"scale", self)
        self._breathing_animation.setDuration(2800)
        self._breathing_animation.setLoopCount(-1)
        self._breathing_animation.setEasingCurve(QEasingCurve.InOutSine)
        self._breathing_animation.setStartValue(0.98)
        self._breathing_animation.setKeyValueAt(0.5, 1.02)
        self._breathing_animation.setEndValue(0.98)
        self._breathing_animation.start()

        self._hover_animation = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_animation.setDuration(120)
        self._hover_animation.setEasingCurve(QEasingCurve.OutCubic)

        self._magnet_timer = QTimer(self)
        self._magnet_timer.setInterval(16)
        self._magnet_timer.timeout.connect(self._update_magnetic_offset)
        self._magnet_timer.start()

        QTimer.singleShot(0, self._position_initially)

    def theme(self) -> Theme:
        return self._theme

    def getScale(self) -> float:
        return self._scale

    def setScale(self, value: float):
        self._scale = float(value)
        self.update()

    scale = pyqtProperty(float, fget=getScale, fset=setScale)

    def getHoverProgress(self) -> float:
        return self._hover_progress

    def setHoverProgress(self, value: float):
        self._hover_progress = max(0.0, min(1.0, float(value)))
        self.update()

    hoverProgress = pyqtProperty(float, fget=getHoverProgress, fset=setHoverProgress)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._positioned:
            self._position_initially()
        if self._debug:
            print(f"orb theme: {self._theme.name}")
            print(f"orb position: {self.pos().x()}, {self.pos().y()}")

    def enterEvent(self, event):
        self._animate_hover(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animate_hover(False)
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.fillRect(self.rect(), Qt.transparent)

        center = QPointF(self.rect().center()) + self._magnet_offset
        effective_scale = self._scale * (1.0 + 0.05 * self._hover_progress)
        effective_scale += 0.012 * self._cursor_proximity
        diameter = self.BASE_DIAMETER * effective_scale
        radius = diameter / 2.0
        orb_rect = QRectF(center.x() - radius, center.y() - radius, diameter, diameter)

        glow_color = QColor(self._theme.glow_color)
        glow_strength = 0.17 + (self._theme.shadow_strength * 0.28) + (0.08 * self._hover_progress) + (0.06 * self._cursor_proximity)
        glow_color.setAlphaF(max(0.0, min(1.0, glow_strength)))
        glow_gradient = QRadialGradient(center, radius * (1.45 + (0.12 * self._hover_progress) + (0.08 * self._cursor_proximity)))
        glow_gradient.setColorAt(0.0, glow_color)
        glow_soft = QColor(glow_color)
        glow_soft.setAlphaF(glow_color.alphaF() * 0.22)
        glow_gradient.setColorAt(0.7, glow_soft)
        glow_gradient.setColorAt(1.0, QColor(0, 0, 0, 0))

        painter.setPen(Qt.NoPen)
        painter.setBrush(glow_gradient)
        painter.drawEllipse(orb_rect.adjusted(-radius * 0.45, -radius * 0.45, radius * 0.45, radius * 0.45))

        fill_gradient = QRadialGradient(orb_rect.topLeft() + QPointF(radius * 0.28, radius * 0.24), radius * 1.2)
        highlight = QColor(self._theme.hover_color)
        highlight.setAlphaF(0.96 if self._theme.name == "APPLE" else 0.52)
        base = QColor(self._theme.base_color)
        base_darker = QColor(self._theme.base_color).darker(112 if self._theme.name == "APPLE" else 128)
        fill_gradient.setColorAt(0.0, highlight)
        fill_gradient.setColorAt(0.5, base)
        fill_gradient.setColorAt(1.0, base_darker)

        painter.setBrush(fill_gradient)
        painter.drawEllipse(orb_rect)

        sheen = QLinearGradient(orb_rect.topLeft(), orb_rect.bottomRight())
        sheen_color = QColor(255, 255, 255, 36 if self._theme.name == "APPLE" else 14)
        sheen.setColorAt(0.0, sheen_color)
        sheen.setColorAt(0.4, QColor(255, 255, 255, 0))
        sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(sheen)
        painter.drawEllipse(orb_rect.adjusted(radius * 0.08, radius * 0.08, -radius * 0.12, -radius * 0.12))

        border_rect = orb_rect.adjusted(-4.2, -4.2, 4.2, 4.2)
        painter.setPen(Qt.NoPen)

        if self._theme.name == "APPLE":
            border_gradient = QConicalGradient(center, self._border_phase)
            border_gradient.setColorAt(0.00, QColor(248, 248, 248, 255))
            border_gradient.setColorAt(0.14, QColor(216, 216, 216, 228))
            border_gradient.setColorAt(0.30, QColor(178, 178, 178, 0))
            border_gradient.setColorAt(0.52, QColor(255, 255, 255, 42))
            border_gradient.setColorAt(0.72, QColor(196, 196, 196, 220))
            border_gradient.setColorAt(1.00, QColor(248, 248, 248, 255))
            border_brush = QBrush(border_gradient)
            border_width = 2.3
        else:
            border_gradient = QConicalGradient(center, self._border_phase)
            border_gradient.setColorAt(0.00, QColor(self._theme.hover_color))
            border_gradient.setColorAt(0.18, QColor(self._theme.glow_color))
            border_gradient.setColorAt(0.34, QColor(0, 0, 0, 0))
            border_gradient.setColorAt(0.60, QColor(255, 255, 255, 18))
            border_gradient.setColorAt(0.82, QColor(self._theme.glow_color))
            border_gradient.setColorAt(1.00, QColor(self._theme.hover_color))
            border_brush = QBrush(border_gradient)
            border_width = 2.0

        border_pen = QPen(border_brush, border_width)
        border_pen.setCapStyle(Qt.RoundCap)
        border_pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(border_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(border_rect)

        inner_rim_alpha = 50 if self._theme.name == "APPLE" else 24
        inner_rim = QPen(QColor(255, 255, 255, inner_rim_alpha))
        inner_rim.setWidthF(0.8)
        painter.setPen(inner_rim)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(orb_rect.adjusted(4.0, 4.0, -4.0, -4.0))

        if self._debug:
            debug_pen = QPen(QColor(255, 84, 84, 200))
            debug_pen.setStyle(Qt.DashLine)
            painter.setPen(debug_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            event.ignore()
            return

        self._dragging = True
        self._drag_threshold_exceeded = False
        self._press_global = event.globalPos()
        self._press_window_pos = self.pos()
        self._stop_snap_animation()
        self._magnet_offset = QPointF(0.0, 0.0)
        self._set_hover_state(True)
        event.accept()

    def mouseMoveEvent(self, event):
        if not self._dragging:
            event.ignore()
            return

        delta = event.globalPos() - self._press_global
        if delta.manhattanLength() >= self._drag_start_distance:
            self._drag_threshold_exceeded = True

        target = self._press_window_pos + delta
        screen = self._screen_for_point(event.globalPos())
        target = self._clamp_to_screen(target, screen)
        self.move(target)
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            event.ignore()
            return

        was_dragging = self._dragging
        dragged = self._drag_threshold_exceeded
        self._dragging = False
        self._drag_threshold_exceeded = False
        self._set_hover_state(self.underMouse())

        if not dragged:
            print("orb clicked")
        elif was_dragging:
            self._snap_to_nearest_edge()

        event.accept()

    def _animate_hover(self, active: bool):
        self._hover_animation.stop()
        self._hover_animation.setStartValue(self._hover_progress)
        self._hover_animation.setEndValue(1.0 if active else 0.0)
        self._hover_animation.start()

    def _set_hover_state(self, active: bool):
        self._hover_animation.stop()
        self.hoverProgress = 1.0 if active else 0.0

    def _position_initially(self):
        if self._positioned:
            return

        screen = QApplication.primaryScreen()
        if screen is None:
            return

        geometry = screen.availableGeometry()
        x = geometry.x() + geometry.width() - self.width()
        y = geometry.y() + (geometry.height() - self.height()) // 2
        self.move(self._clamp_to_screen(QPoint(x, y), screen))
        self._positioned = True
        if self._debug:
            print(f"orb position: {self.pos().x()}, {self.pos().y()}")

    def _snap_to_nearest_edge(self):
        screen = self._screen_for_point(QCursor.pos())
        if screen is None:
            return

        geometry = screen.availableGeometry()
        current = self.pos()
        left_target = geometry.x()
        right_target = geometry.x() + geometry.width() - self.width()
        target_x = left_target if current.x() + (self.width() / 2.0) < geometry.center().x() else right_target
        target_y = self._clamp_y(current.y(), geometry)
        target = QPoint(target_x, target_y)

        self._stop_snap_animation()
        self._snap_animation = QPropertyAnimation(self, b"pos", self)
        self._snap_animation.setDuration(150)
        self._snap_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._snap_animation.setStartValue(current)
        self._snap_animation.setEndValue(target)
        self._snap_animation.finished.connect(self._on_snap_finished)
        self._snap_animation.start()

    def _on_snap_finished(self):
        self._stop_snap_animation()
        if self._debug:
            print(f"orb position: {self.pos().x()}, {self.pos().y()}")

    def _stop_snap_animation(self):
        if self._snap_animation is not None:
            self._snap_animation.stop()
            self._snap_animation.deleteLater()
            self._snap_animation = None

    def _update_magnetic_offset(self):
        self._border_phase = (self._border_phase + 0.95 + (self._cursor_proximity * 0.35)) % 360.0

        if self._dragging:
            if self._magnet_offset != QPointF(0.0, 0.0):
                self._magnet_offset = QPointF(0.0, 0.0)
        else:
            screen = self._screen_for_point(QCursor.pos())
            if screen is None:
                self.update()
                return

            cursor = QCursor.pos()
            center = self.mapToGlobal(QPoint(self.rect().width() - 50, self.rect().center().y()))
            delta = QPointF(cursor.x() - center.x(), cursor.y() - center.y())
            distance = math.hypot(delta.x(), delta.y())
            proximity_window = 140.0
            if distance <= 0.01 or distance > proximity_window:
                target = QPointF(0.0, 0.0)
                self._cursor_proximity += (0.0 - self._cursor_proximity) * 0.14
            else:
                strength = (proximity_window - distance) / proximity_window
                self._cursor_proximity += (strength - self._cursor_proximity) * 0.12
                scale = min(7.0, 7.0 * (strength ** 1.15))
                target = QPointF((delta.x() / distance) * scale, (delta.y() / distance) * scale)

            current = self._magnet_offset
            next_offset = QPointF(
                current.x() + (target.x() - current.x()) * 0.14,
                current.y() + (target.y() - current.y()) * 0.14,
            )
            if (abs(next_offset.x() - current.x()) > 0.01) or (abs(next_offset.y() - current.y()) > 0.01):
                self._magnet_offset = next_offset
        if self._dragging:
            self._cursor_proximity += (0.0 - self._cursor_proximity) * 0.18

        self.update()

    def _clamp_to_screen(self, position: QPoint, screen) -> QPoint:
        geometry = screen.availableGeometry()
        x = max(geometry.x(), min(position.x(), geometry.x() + geometry.width() - self.width()))
        y = self._clamp_y(position.y(), geometry)
        return QPoint(x, y)

    def _clamp_y(self, y_position: int, geometry) -> int:
        return max(geometry.y(), min(y_position, geometry.y() + geometry.height() - self.height()))

    def _screen_for_point(self, point: QPoint):
        screen = QGuiApplication.screenAt(point)
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        return screen
