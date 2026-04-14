from __future__ import annotations

import math

from PyQt5.QtCore import QEasingCurve, QPoint, QPointF, QPropertyAnimation, QRectF, Qt, QTimer, pyqtProperty, pyqtSignal
from PyQt5.QtGui import QColor, QBrush, QCursor, QGuiApplication, QLinearGradient, QPainter, QPen, QRadialGradient
from PyQt5.QtWidgets import QApplication, QWidget

from ..core.theme import Theme


class FloatingOrb(QWidget):
    activated = pyqtSignal()

    BASE_DIAMETER = 56.0
    WIDGET_DIAMETER = 124
    AUTO_HIDE_DELAY_MS = 2600
    DOCK_ANIMATION_MS = 260
    HIDDEN_VISIBLE_RATIO = 0.5
    VISIBLE_OVERHANG_PX = 24
    REVEAL_DISTANCE = 120.0
    HIDDEN_OPACITY = 0.70

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
        self._dock_animation = None
        self._opacity_animation = None
        self._border_phase = 0.0
        self._cursor_proximity = 0.0
        self._click_flash = 0.0
        self._display_opacity = 1.0
        self._dock_side = "right"
        self._dock_hidden = False
        self._forced_hidden_mode = False
        self._idle_timer = QTimer(self)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.setInterval(self.AUTO_HIDE_DELAY_MS)
        self._idle_timer.timeout.connect(self._auto_hide_if_idle)

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

        self._click_flash_animation = QPropertyAnimation(self, b"clickFlash", self)
        self._click_flash_animation.setEasingCurve(QEasingCurve.OutCubic)

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

    def getClickFlash(self) -> float:
        return self._click_flash

    def setClickFlash(self, value: float):
        self._click_flash = max(0.0, min(1.0, float(value)))
        self.update()

    clickFlash = pyqtProperty(float, fget=getClickFlash, fset=setClickFlash)

    def getDisplayOpacity(self) -> float:
        return self._display_opacity

    def setDisplayOpacity(self, value: float):
        self._display_opacity = max(self.HIDDEN_OPACITY, min(1.0, float(value)))
        self.update()

    def animateDisplayOpacity(self, target_opacity: float, duration: int | None = None):
        self._animate_display_opacity(target_opacity, duration)

    def enterHiddenDockMode(self):
        self._cancel_idle_timer()
        self._dock_hidden = True
        self._animate_dock_visibility(False)

    def setForcedHiddenMode(self, enabled: bool):
        enabled = bool(enabled)
        if enabled == self._forced_hidden_mode:
            return

        self._forced_hidden_mode = enabled
        if enabled:
            self._dragging = False
            self._drag_threshold_exceeded = False
            self._set_hover_state(False)
            self._cursor_proximity = 0.0
            self._magnet_offset = QPointF(0.0, 0.0)
            self.enterHiddenDockMode()
            self.update()
            return

        self._reset_idle_timer()

    displayOpacity = pyqtProperty(float, fget=getDisplayOpacity, fset=setDisplayOpacity)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._positioned:
            self._position_initially()
        self._dock_hidden = False
        self._reset_idle_timer()
        if self._debug:
            print(f"orb theme: {self._theme.name}")
            print(f"orb position: {self.pos().x()}, {self.pos().y()}")

    def enterEvent(self, event):
        if self._forced_hidden_mode:
            super().enterEvent(event)
            return
        self._animate_hover(True)
        self._reveal_from_edge()
        self._reset_idle_timer()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._forced_hidden_mode:
            super().leaveEvent(event)
            return
        self._animate_hover(False)
        self._reset_idle_timer()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.fillRect(self.rect(), Qt.transparent)
        painter.setOpacity(self._display_opacity)

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

        if self._click_flash > 0.0:
            flash = QColor(self._theme.hover_color if self._theme.name != "APPLE" else "#FFFFFF")
            flash_alpha = 0.22 if self._theme.name == "APPLE" else 0.30
            flash.setAlphaF(flash_alpha * self._click_flash)
            flash_gradient = QRadialGradient(center, radius * 1.08)
            flash_gradient.setColorAt(0.0, flash)
            flash_gradient.setColorAt(0.45, QColor(flash.red(), flash.green(), flash.blue(), 0))
            flash_gradient.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setPen(Qt.NoPen)
            painter.setBrush(flash_gradient)
            painter.drawEllipse(orb_rect.adjusted(-2.0, -2.0, 2.0, 2.0))

        painter.setBrush(fill_gradient)
        painter.drawEllipse(orb_rect)

        sheen = QLinearGradient(orb_rect.topLeft(), orb_rect.bottomRight())
        sheen_color = QColor(255, 255, 255, 36 if self._theme.name == "APPLE" else 14)
        sheen.setColorAt(0.0, sheen_color)
        sheen.setColorAt(0.4, QColor(255, 255, 255, 0))
        sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(sheen)
        painter.drawEllipse(orb_rect.adjusted(radius * 0.08, radius * 0.08, -radius * 0.12, -radius * 0.12))

        self._draw_border_segments(painter, orb_rect, center)

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
        if self._forced_hidden_mode:
            event.ignore()
            return
        if event.button() != Qt.LeftButton:
            event.ignore()
            return

        self._dragging = True
        self._drag_threshold_exceeded = False
        self._press_global = event.globalPos()
        self._press_window_pos = self.pos()
        self._stop_snap_animation()
        self._stop_dock_animation()
        self._magnet_offset = QPointF(0.0, 0.0)
        self._reveal_from_edge()
        self._dock_hidden = False
        self._cancel_idle_timer()
        self._trigger_click_flash()
        event.accept()

    def mouseMoveEvent(self, event):
        if self._forced_hidden_mode:
            event.ignore()
            return
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
        self._dock_hidden = False
        self._reset_idle_timer()
        event.accept()

    def mouseReleaseEvent(self, event):
        if self._forced_hidden_mode:
            event.ignore()
            return
        if event.button() != Qt.LeftButton:
            event.ignore()
            return

        was_dragging = self._dragging
        dragged = self._drag_threshold_exceeded
        self._dragging = False
        self._drag_threshold_exceeded = False

        if not dragged:
            self.activated.emit()
            self._reveal_from_edge()
        elif was_dragging:
            self._snap_to_nearest_edge()
        self._reset_idle_timer()

        event.accept()

    def _animate_hover(self, active: bool):
        self._hover_animation.stop()
        self._hover_animation.setStartValue(self._hover_progress)
        self._hover_animation.setEndValue(1.0 if active else 0.0)
        self._hover_animation.start()

    def _set_hover_state(self, active: bool):
        self._hover_animation.stop()
        self.hoverProgress = 1.0 if active else 0.0

    def _trigger_click_flash(self):
        self._click_flash_animation.stop()
        self._click_flash_animation.setDuration(0)
        self.clickFlash = 0.0
        self._click_flash_animation.setDuration(110)
        self._click_flash_animation.setStartValue(0.0)
        self._click_flash_animation.setKeyValueAt(0.45, 1.0)
        self._click_flash_animation.setEndValue(0.0)
        self._click_flash_animation.start()

    def _position_initially(self):
        if self._positioned:
            return

        screen = QApplication.primaryScreen()
        if screen is None:
            return

        geometry = screen.availableGeometry()
        y = geometry.y() + (geometry.height() - self.height()) // 2
        self._dock_side = "right"
        self._dock_hidden = False
        start_position = self._dock_visible_target(screen)
        self.move(QPoint(start_position.x(), self._clamp_y(y, geometry)))
        self._positioned = True
        self._reset_idle_timer()
        if self._debug:
            print(f"orb position: {self.pos().x()}, {self.pos().y()}")

    def _snap_to_nearest_edge(self):
        screen = self._screen_for_point(QCursor.pos())
        if screen is None:
            return

        geometry = screen.availableGeometry()
        current = self.pos()
        self._dock_side = "left" if current.x() + (self.width() / 2.0) < geometry.center().x() else "right"
        target = self._dock_visible_target(screen)
        target.setY(self._clamp_y(current.y(), geometry))

        self._stop_snap_animation()
        self._animate_to_position(target, self.DOCK_ANIMATION_MS, QEasingCurve.OutCubic, use_snap_animation=True)

    def _on_snap_finished(self):
        self._stop_snap_animation()
        self._reset_idle_timer()
        if self._debug:
            print(f"orb position: {self.pos().x()}, {self.pos().y()}")

    def _stop_snap_animation(self):
        if self._snap_animation is not None:
            self._snap_animation.stop()
            self._snap_animation.deleteLater()
            self._snap_animation = None

    def _stop_dock_animation(self):
        if self._dock_animation is not None:
            self._dock_animation.stop()
            self._dock_animation.deleteLater()
            self._dock_animation = None

    def _stop_opacity_animation(self):
        if self._opacity_animation is not None:
            self._opacity_animation.stop()
            self._opacity_animation.deleteLater()
            self._opacity_animation = None

    def _animate_to_position(self, target: QPoint, duration: int, easing, use_snap_animation: bool = False):
        if use_snap_animation:
            self._stop_snap_animation()
            animation = QPropertyAnimation(self, b"pos", self)
            self._snap_animation = animation
        else:
            self._stop_dock_animation()
            animation = QPropertyAnimation(self, b"pos", self)
            self._dock_animation = animation

        animation.setDuration(duration)
        animation.setEasingCurve(easing)
        animation.setStartValue(self.pos())
        animation.setEndValue(target)

        if use_snap_animation:
            animation.finished.connect(self._on_snap_finished)
        else:
            animation.finished.connect(self._on_dock_animation_finished)
        animation.start()

    def _on_dock_animation_finished(self):
        self._stop_dock_animation()
        self._reset_idle_timer()

    def _cancel_idle_timer(self):
        if self._idle_timer.isActive():
            self._idle_timer.stop()

    def _reset_idle_timer(self):
        if self._forced_hidden_mode:
            return
        if self._dragging:
            return
        if self._under_active_interaction():
            self._idle_timer.start(self.AUTO_HIDE_DELAY_MS)
            return
        self._idle_timer.start(self.AUTO_HIDE_DELAY_MS)

    def _under_active_interaction(self) -> bool:
        return self.underMouse() or self._hover_progress > 0.01

    def _auto_hide_if_idle(self):
        if self._forced_hidden_mode:
            return
        if self._dragging or self._under_active_interaction() or self._cursor_near_orb():
            self._reset_idle_timer()
            return
        if self._dock_hidden:
            return
        self._dock_hidden = True
        self._animate_dock_visibility(False)

    def _reveal_from_edge(self):
        if self._forced_hidden_mode:
            return
        if self._dragging:
            return
        if not self._dock_hidden:
            return
        self._dock_hidden = False
        self._animate_dock_visibility(True)

    def _animate_dock_visibility(self, visible: bool):
        screen = self._screen_for_point(QCursor.pos())
        if screen is None:
            return

        target = self._dock_visible_target(screen) if visible else self._dock_hidden_target(screen)
        self._animate_to_position(target, self.DOCK_ANIMATION_MS, QEasingCurve.OutCubic)
        self._animate_display_opacity(1.0 if visible else self.HIDDEN_OPACITY)

    def _animate_display_opacity(self, target_opacity: float, duration: int | None = None):
        self._stop_opacity_animation()
        self._opacity_animation = QPropertyAnimation(self, b"displayOpacity", self)
        self._opacity_animation.setDuration(self.DOCK_ANIMATION_MS if duration is None else int(duration))
        self._opacity_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._opacity_animation.setStartValue(self._display_opacity)
        self._opacity_animation.setEndValue(float(target_opacity))
        self._opacity_animation.finished.connect(self._on_opacity_animation_finished)
        self._opacity_animation.start()

    def _on_opacity_animation_finished(self):
        self._stop_opacity_animation()

    def _dock_visible_target(self, screen) -> QPoint:
        geometry = screen.availableGeometry()
        y = self._clamp_y(self.pos().y(), geometry)
        if self._dock_side == "left":
            x = geometry.x() - self.VISIBLE_OVERHANG_PX
        else:
            x = geometry.x() + geometry.width() - self.width() + self.VISIBLE_OVERHANG_PX
        return QPoint(x, y)

    def _dock_hidden_target(self, screen) -> QPoint:
        geometry = screen.availableGeometry()
        y = self._clamp_y(self.pos().y(), geometry)
        visible_width = max(18, int(round(self.width() * self.HIDDEN_VISIBLE_RATIO)))
        if self._dock_side == "left":
            x = geometry.x() - (self.width() - visible_width)
        else:
            x = geometry.x() + geometry.width() - visible_width
        return QPoint(x, y)

    def _cursor_near_orb(self) -> bool:
        cursor = QCursor.pos()
        reference = self._interaction_reference_point()
        delta = QPointF(cursor.x() - reference.x(), cursor.y() - reference.y())
        return math.hypot(delta.x(), delta.y()) <= self.REVEAL_DISTANCE

    def _interaction_reference_point(self) -> QPoint:
        center_y = self.pos().y() + self.height() // 2
        if not self._dock_hidden:
            return QPoint(self.pos().x() + self.width() // 2, center_y)

        visible_width = max(18, int(round(self.width() * self.HIDDEN_VISIBLE_RATIO)))
        if self._dock_side == "left":
            x = self.pos().x() + self.width() - visible_width // 2
        else:
            x = self.pos().x() + visible_width // 2
        return QPoint(x, center_y)

    def _update_magnetic_offset(self):
        if self._forced_hidden_mode:
            if self._magnet_offset != QPointF(0.0, 0.0):
                self._magnet_offset = QPointF(0.0, 0.0)
            if abs(self._cursor_proximity) > 0.001:
                self._cursor_proximity = 0.0
            self.update()
            return

        self._border_phase = (self._border_phase + 0.42 + (self._cursor_proximity * 0.18)) % 360.0

        if self._dragging:
            if self._magnet_offset != QPointF(0.0, 0.0):
                self._magnet_offset = QPointF(0.0, 0.0)
        else:
            if self._dock_hidden and self._cursor_near_orb():
                self._reveal_from_edge()

            screen = self._screen_for_point(QCursor.pos())
            if screen is None:
                self.update()
                return

            cursor = QCursor.pos()
            center = self._interaction_reference_point()
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

            # Never allow magnetic motion to push the orb closer into its docked edge.
            if self._dock_side == "right":
                target.setX(min(0.0, target.x()))
            else:
                target.setX(max(0.0, target.x()))

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

    def _draw_border_segments(self, painter: QPainter, orb_rect: QRectF, center: QPointF):
        border_rect = orb_rect.adjusted(-4.2, -4.2, 4.2, 4.2)
        ring_width = 2.3 if self._theme.name == "APPLE" else 2.05
        segment_span = 13.0
        slots = 8
        phase = self._border_phase % 360.0
        interaction_level = max(self._hover_progress, self._cursor_proximity, self._click_flash)
        alpha_multiplier = 0.50 + (interaction_level * 0.72)
        if self._dock_hidden:
            alpha_multiplier *= 0.84

        if self._theme.name == "APPLE":
            border_color = QColor(221, 221, 221, 232)
        else:
            border_color = QColor(self._theme.glow_color)
            border_color.setAlpha(236)

        painter.setBrush(Qt.NoBrush)
        for index in range(slots):
            angle = (phase + index * (360.0 / slots)) % 360.0
            distance_to_primary = min(abs(angle - phase), 360.0 - abs(angle - phase))
            distance_to_secondary = min(abs(angle - ((phase + 180.0) % 360.0)), 360.0 - abs(angle - ((phase + 180.0) % 360.0)))
            primary_mix = max(0.0, 1.0 - (distance_to_primary / 54.0))
            secondary_mix = max(0.0, 1.0 - (distance_to_secondary / 54.0))
            brightness = min(1.0, 0.50 + (primary_mix * 0.50) + (secondary_mix * 0.18))

            color = QColor(border_color)
            color.setAlphaF(max(0.22, min(1.0, color.alphaF() * brightness * alpha_multiplier)))
            pen = QPen(color, ring_width)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.drawArc(border_rect, int((90.0 - (angle + segment_span * 0.5)) * 16), int(segment_span * 16))

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
