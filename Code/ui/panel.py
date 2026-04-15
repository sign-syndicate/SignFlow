from __future__ import annotations

import math

from PyQt5.QtCore import QEasingCurve, QPoint, QPointF, QPropertyAnimation, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QLinearGradient, QPainter, QPen, QRadialGradient
from PyQt5.QtCore import QRectF
from PyQt5.QtWidgets import QGraphicsOpacityEffect, QLabel, QWidget

from ..core.constants import ORB_PRESENTATION_DEFAULTS, PANEL_DEFAULTS
from ..core.theme import Theme


class OrbPanelContent(QWidget):
    collapse_requested = pyqtSignal()
    drag_started = pyqtSignal(QPoint)
    drag_moved = pyqtSignal(QPoint)
    drag_released = pyqtSignal(QPoint)

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self._theme = theme
        self._edge = ORB_PRESENTATION_DEFAULTS.edge_right
        self._morph = 0.0
        self._radius = 14.0
        self._padding = 14
        self._dragging = False
        self._anchor_orb_rect = None
        self._border_phase = 0.0

        self._caption_label = QLabel(PANEL_DEFAULTS.caption_placeholder, self)
        self._caption_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        self._caption_opacity = QGraphicsOpacityEffect(self._caption_label)
        self._caption_opacity.setOpacity(1.0)
        self._caption_label.setGraphicsEffect(self._caption_opacity)

        self._caption_anim = QPropertyAnimation(self._caption_opacity, b"opacity", self)
        self._caption_anim.setDuration(PANEL_DEFAULTS.caption_update_ms)
        self._caption_anim.setEasingCurve(QEasingCurve.OutCubic)

        self._apply_theme()

    def set_edge(self, edge: str):
        edge = ORB_PRESENTATION_DEFAULTS.edge_left if str(edge).lower() == ORB_PRESENTATION_DEFAULTS.edge_left else ORB_PRESENTATION_DEFAULTS.edge_right
        if edge == self._edge:
            return
        self._edge = edge
        self._apply_layout()

    def set_radius(self, radius: float):
        self._radius = max(0.0, float(radius))
        self.update()

    def set_padding(self, padding: int):
        self._padding = max(0, int(padding))
        self._apply_layout()

    def set_morph(self, morph: float):
        self._morph = max(0.0, min(1.0, float(morph)))
        visible = self._morph > 0.20
        self._caption_label.setVisible(visible)
        self._apply_layout()
        self.update()

    def set_border_phase(self, phase: float):
        self._border_phase = float(phase) % 360.0
        if self._morph > 0.001:
            self.update()

    def set_caption(self, text: str):
        safe_text = str(text).strip() if text is not None else ""
        if not safe_text:
            safe_text = PANEL_DEFAULTS.caption_placeholder
        self._caption_label.setText(safe_text)

    def animate_caption_update(self, text: str):
        self.set_caption(text)
        self._caption_anim.stop()
        self._caption_anim.setStartValue(0.70)
        self._caption_anim.setEndValue(1.0)
        self._caption_anim.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_layout()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._is_on_anchor_orb(event.pos()):
                self.collapse_requested.emit()
                event.accept()
                return
            self._dragging = True
            self.drag_started.emit(event.globalPos())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging:
            self.drag_moved.emit(event.globalPos())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._dragging and event.button() == Qt.LeftButton:
            self._dragging = False
            self.drag_released.emit(event.globalPos())
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        if self._theme.name == "APPLE":
            fill = QColor(255, 255, 255, 250)
            border = QColor(24, 24, 24, 120)
        else:
            fill = QColor(self._theme.base_color)
            fill.setAlpha(236)
            border = QColor(self._theme.primary_color)
            border.setAlpha(96)

        painter.setBrush(fill)
        pen = QPen(border, 1.0)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), self._radius, self._radius)

        orb_rect = self._compute_anchor_orb_rect()
        self._anchor_orb_rect = orb_rect
        self._draw_anchor_orb(painter, orb_rect)

    def _apply_theme(self):
        if self._theme.name == "APPLE":
            caption_color = "#101010"
        else:
            caption_color = "#ECECEF"

        self._caption_label.setStyleSheet(
            "color: " + caption_color + ";"
            "font-size: " + str(PANEL_DEFAULTS.caption_font_px) + "px;"
            "font-weight: " + str(PANEL_DEFAULTS.caption_weight) + ";"
            "background: transparent;"
            "border: none;"
        )

    def _apply_layout(self):
        panel_w = self.width()
        panel_h = self.height()
        if panel_w <= 0 or panel_h <= 0:
            return

        padding = max(0, self._padding)
        orb_diameter = PANEL_DEFAULTS.anchor_orb_diameter_px
        orb_radius = orb_diameter * 0.5

        if self._edge == ORB_PRESENTATION_DEFAULTS.edge_right:
            orb_center_x = panel_w - PANEL_DEFAULTS.edge_overhang_px
            caption_left = max(0, padding)
            caption_right = max(caption_left + PANEL_DEFAULTS.min_caption_width_px, int(round(orb_center_x - orb_radius - PANEL_DEFAULTS.caption_button_gap_px)))
        else:
            orb_center_x = PANEL_DEFAULTS.edge_overhang_px
            caption_left = min(panel_w, int(round(orb_center_x + orb_radius + PANEL_DEFAULTS.caption_button_gap_px)))
            caption_right = max(caption_left + PANEL_DEFAULTS.min_caption_width_px, panel_w - padding)

        caption_width = max(8, caption_right - caption_left)
        self._caption_label.setGeometry(caption_left, 0, caption_width, panel_h)

    def _compute_anchor_orb_rect(self):
        panel_h = self.height()
        diameter = float(PANEL_DEFAULTS.anchor_orb_diameter_px)
        radius = diameter * 0.5
        center_y = panel_h * 0.5
        if self._edge == ORB_PRESENTATION_DEFAULTS.edge_right:
            center_x = self.width() - float(PANEL_DEFAULTS.edge_overhang_px)
        else:
            center_x = float(PANEL_DEFAULTS.edge_overhang_px)
        return QRectF(center_x - radius, center_y - radius, diameter, diameter)

    def _draw_anchor_orb(self, painter: QPainter, orb_rect: QRectF):
        center = orb_rect.center()
        radius = orb_rect.width() * 0.5

        glow_color = QColor(self._theme.glow_color)
        glow_color.setAlphaF(0.22 + (self._theme.shadow_strength * 0.22))
        glow = QRadialGradient(center, radius * 1.48)
        glow.setColorAt(0.0, glow_color)
        glow_soft = QColor(glow_color)
        glow_soft.setAlphaF(glow_color.alphaF() * 0.22)
        glow.setColorAt(0.70, glow_soft)
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(orb_rect.adjusted(-radius * 0.44, -radius * 0.44, radius * 0.44, radius * 0.44))

        fill_gradient = QRadialGradient(orb_rect.topLeft() + QPointF(radius * 0.28, radius * 0.24), radius * 1.2)
        highlight = QColor(self._theme.hover_color)
        highlight.setAlphaF(0.96 if self._theme.name == "APPLE" else 0.52)
        base = QColor(self._theme.base_color)
        base_darker = QColor(self._theme.base_color).darker(112 if self._theme.name == "APPLE" else 128)
        fill_gradient.setColorAt(0.0, highlight)
        fill_gradient.setColorAt(0.5, base)
        fill_gradient.setColorAt(1.0, base_darker)
        painter.setPen(Qt.NoPen)
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
        ring_width = 2.3 if self._theme.name == "APPLE" else 2.05
        segment_span = 13.0
        slots = 8
        phase = self._border_phase
        if self._theme.name == "APPLE":
            border_color = QColor(221, 221, 221, 232)
        else:
            border_color = QColor(self._theme.glow_color)
            border_color.setAlpha(236)

        for index in range(slots):
            angle = (phase + index * (360.0 / slots)) % 360.0
            color = QColor(border_color)
            pen = QPen(color, ring_width)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawArc(border_rect, int((90.0 - (angle + segment_span * 0.5)) * 16), int(segment_span * 16))

        inner_rim_alpha = 50 if self._theme.name == "APPLE" else 24
        inner_rim = QPen(QColor(255, 255, 255, inner_rim_alpha))
        inner_rim.setWidthF(0.8)
        painter.setPen(inner_rim)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(orb_rect.adjusted(4.0, 4.0, -4.0, -4.0))

        inner_rect = QRectF(
            center.x() - (radius * 0.82),
            center.y() - (radius * 0.82),
            radius * 1.64,
            radius * 1.64,
        )
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#F7F7F7"))
        painter.drawEllipse(inner_rect)

        ring_pen = QPen(QColor("#2A2A2F"), 2.5)
        ring_pen.setCapStyle(Qt.RoundCap)
        ring_pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(ring_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(inner_rect)

    def _is_on_anchor_orb(self, point) -> bool:
        if self._anchor_orb_rect is None:
            return False
        center_x = self._anchor_orb_rect.center().x()
        center_y = self._anchor_orb_rect.center().y()
        radius = self._anchor_orb_rect.width() * 0.5
        dx = point.x() - center_x
        dy = point.y() - center_y
        return math.hypot(dx, dy) <= radius
