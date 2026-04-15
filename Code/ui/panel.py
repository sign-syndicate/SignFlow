from __future__ import annotations

import math

from PyQt5.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPen
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
            orb_fill = QColor(255, 255, 255, 252)
            orb_border = QColor(24, 24, 24, 120)
        else:
            fill = QColor(self._theme.base_color)
            fill.setAlpha(236)
            border = QColor(self._theme.primary_color)
            border.setAlpha(96)
            orb_fill = QColor(self._theme.base_color)
            orb_fill.setAlpha(246)
            orb_border = QColor(self._theme.primary_color)
            orb_border.setAlpha(110)

        painter.setBrush(fill)
        pen = QPen(border, 1.0)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), self._radius, self._radius)

        orb_rect = self._compute_anchor_orb_rect()
        self._anchor_orb_rect = orb_rect
        shadow = QColor(0, 0, 0, PANEL_DEFAULTS.anchor_orb_shadow_alpha)
        painter.setPen(Qt.NoPen)
        painter.setBrush(shadow)
        painter.drawEllipse(orb_rect.adjusted(1.0, 1.0, 3.0, 3.0))

        orb_pen = QPen(orb_border, PANEL_DEFAULTS.anchor_orb_border_px)
        orb_pen.setCapStyle(Qt.RoundCap)
        orb_pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(orb_pen)
        painter.setBrush(orb_fill)
        painter.drawEllipse(orb_rect)

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

    def _is_on_anchor_orb(self, point) -> bool:
        if self._anchor_orb_rect is None:
            return False
        center_x = self._anchor_orb_rect.center().x()
        center_y = self._anchor_orb_rect.center().y()
        radius = self._anchor_orb_rect.width() * 0.5
        dx = point.x() - center_x
        dy = point.y() - center_y
        return math.hypot(dx, dy) <= radius
