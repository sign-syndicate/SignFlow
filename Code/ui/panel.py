from __future__ import annotations

from PyQt5.QtCore import QEasingCurve, QPropertyAnimation, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import QGraphicsOpacityEffect, QLabel, QPushButton, QWidget

from ..core.theme import Theme


class OrbPanelContent(QWidget):
    collapse_requested = pyqtSignal()

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self._theme = theme
        self._edge = "right"
        self._morph = 0.0
        self._radius = 14.0
        self._padding = 14

        self._caption_label = QLabel("Listening...", self)
        self._caption_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        self._caption_opacity = QGraphicsOpacityEffect(self._caption_label)
        self._caption_opacity.setOpacity(1.0)
        self._caption_label.setGraphicsEffect(self._caption_opacity)

        self._caption_anim = QPropertyAnimation(self._caption_opacity, b"opacity", self)
        self._caption_anim.setDuration(100)
        self._caption_anim.setEasingCurve(QEasingCurve.OutCubic)

        self._collapse_button = QPushButton("X", self)
        self._collapse_button.setFocusPolicy(Qt.NoFocus)
        self._collapse_button.setCursor(Qt.PointingHandCursor)
        self._collapse_button.setFixedSize(24, 24)
        self._collapse_button.clicked.connect(self.collapse_requested.emit)

        self._apply_theme()

    def set_edge(self, edge: str):
        edge = "left" if str(edge).lower() == "left" else "right"
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
        self._collapse_button.setVisible(visible)
        self._apply_layout()

    def set_caption(self, text: str):
        safe_text = str(text).strip() if text is not None else ""
        if not safe_text:
            safe_text = "Listening..."
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

    def _apply_theme(self):
        if self._theme.name == "APPLE":
            caption_color = "#101010"
            btn_color = "rgba(20, 20, 20, 230)"
            btn_bg = "rgba(255, 255, 255, 0)"
            btn_bg_hover = "rgba(0, 0, 0, 8)"
            btn_bg_pressed = "rgba(0, 0, 0, 12)"
            btn_border = "rgba(0, 0, 0, 34)"
        else:
            caption_color = "#ECECEF"
            btn_color = "rgba(236, 236, 236, 220)"
            btn_bg = "rgba(255, 255, 255, 12)"
            btn_bg_hover = "rgba(255, 255, 255, 18)"
            btn_bg_pressed = "rgba(255, 255, 255, 24)"
            btn_border = "rgba(255, 255, 255, 26)"

        self._caption_label.setStyleSheet(
            "color: " + caption_color + ";"
            "font-size: 16px;"
            "font-weight: 600;"
            "background: transparent;"
            "border: none;"
        )

        self._collapse_button.setStyleSheet(
            "QPushButton {"
            "color: " + btn_color + ";"
            "font-size: 12px;"
            "font-weight: 700;"
            "background: " + btn_bg + ";"
            "border: 1px solid " + btn_border + ";"
            "border-radius: 12px;"
            "padding: 0px;"
            "}"
            "QPushButton:hover {"
            "background: " + btn_bg_hover + ";"
            "}"
            "QPushButton:pressed {"
            "background: " + btn_bg_pressed + ";"
            "}"
        )

    def _apply_layout(self):
        panel_w = self.width()
        panel_h = self.height()
        if panel_w <= 0 or panel_h <= 0:
            return

        padding = max(0, self._padding)
        button_size = self._collapse_button.width()
        button_y = max(0, (panel_h - button_size) // 2)

        if self._edge == "right":
            button_x = max(0, panel_w - padding - button_size)
            caption_left = max(0, padding)
            caption_right = max(caption_left + 120, button_x - 8)
        else:
            button_x = max(0, padding)
            caption_left = min(panel_w, button_x + button_size + 8)
            caption_right = max(caption_left + 120, panel_w - padding)

        self._collapse_button.move(button_x, button_y)

        caption_width = max(8, caption_right - caption_left)
        self._caption_label.setGeometry(caption_left, 0, caption_width, panel_h)
