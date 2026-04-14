from PyQt5.QtCore import QEasingCurve, QParallelAnimationGroup, QPropertyAnimation, QRect, QRectF, Qt, pyqtProperty, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .border import BorderAnimator, paint_border


class CaptionPanel(QWidget):
    collapse_requested = pyqtSignal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self._dock_edge = "right"
        self._corner_radius = float(config.panel_corner_radius)
        self._panel_state = "idle"
        self._title_text = config.open_caption
        self._target_geometry = QRect()
        self._close_anchor_global_y = None
        self._border_animator = BorderAnimator(self)
        self._border_animator.phase_changed.connect(self.update)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumSize(config.panel_min_size)
        self.setWindowOpacity(0.0)

        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(32)
        self._shadow.setOffset(0, 12)
        self._shadow.setColor(QColor(0, 0, 0, 110))
        self.setGraphicsEffect(self._shadow)

        self._content = QWidget(self)
        self._content.setAttribute(Qt.WA_TranslucentBackground, True)

        self.caption_label = QLabel(config.open_caption, self._content)
        self.caption_label.setWordWrap(True)
        self.caption_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.caption_label.setFont(QFont("Segoe UI", 10))
        self.caption_label.setStyleSheet(
            "color: rgba(%d, %d, %d, %d);"
            % config.theme.panel_text
        )

        self.close_button = QPushButton("X", self._content)
        self.close_button.setCursor(Qt.PointingHandCursor)
        self.close_button.setFixedSize(config.orb_diameter, config.orb_diameter)
        self.close_button.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
        self.close_button.setStyleSheet(
            "QPushButton {"
            " background: rgba(%d, %d, %d, %d);"
            " color: rgba(%d, %d, %d, %d);"
            " border: 1px solid rgba(%d, %d, %d, %d);"
            " border-radius: %dpx;"
            " }"
            "QPushButton:hover { background: rgba(%d, %d, %d, %d); }"
            "QPushButton:pressed { background: rgba(%d, %d, %d, %d); }"
            % (
                *config.theme.panel_button_bg,
                *config.theme.panel_button_text,
                *config.theme.panel_button_border,
                int(config.orb_diameter / 2),
                *config.theme.panel_button_hover,
                *config.theme.panel_button_pressed,
            )
        )
        self.close_button.clicked.connect(self.collapse_requested.emit)

        layout = QVBoxLayout(self._content)
        layout.setContentsMargins(
            config.panel_padding_x,
            config.panel_padding_y,
            config.panel_padding_x,
            config.panel_padding_y,
        )
        layout.setSpacing(8)
        row = QHBoxLayout()
        row.setSpacing(10)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.caption_label, 1)
        layout.addLayout(row)

        self._geometry_anim = QPropertyAnimation(self, b"geometry", self)
        self._geometry_anim.setDuration(config.open_duration_ms)
        self._geometry_anim.setEasingCurve(QEasingCurve.OutCubic)

        self._opacity_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._opacity_anim.setDuration(config.open_duration_ms)
        self._opacity_anim.setEasingCurve(QEasingCurve.OutCubic)

        self._radius_anim = QPropertyAnimation(self, b"cornerRadius", self)
        self._radius_anim.setDuration(config.open_duration_ms)
        self._radius_anim.setEasingCurve(QEasingCurve.OutCubic)

        self._animation_group = QParallelAnimationGroup(self)
        self._animation_group.addAnimation(self._geometry_anim)
        self._animation_group.addAnimation(self._opacity_anim)
        self._animation_group.addAnimation(self._radius_anim)

        self._close_group = QParallelAnimationGroup(self)
        self._close_geometry_anim = QPropertyAnimation(self, b"geometry", self)
        self._close_geometry_anim.setDuration(config.close_duration_ms)
        self._close_geometry_anim.setEasingCurve(QEasingCurve.InCubic)
        self._close_opacity_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._close_opacity_anim.setDuration(config.close_duration_ms)
        self._close_opacity_anim.setEasingCurve(QEasingCurve.InCubic)
        self._close_radius_anim = QPropertyAnimation(self, b"cornerRadius", self)
        self._close_radius_anim.setDuration(config.close_duration_ms)
        self._close_radius_anim.setEasingCurve(QEasingCurve.InCubic)
        self._close_group.addAnimation(self._close_geometry_anim)
        self._close_group.addAnimation(self._close_opacity_anim)
        self._close_group.addAnimation(self._close_radius_anim)
        self._close_group.finished.connect(self._finalize_close)

    def set_dock_edge(self, dock_edge: str):
        self._dock_edge = dock_edge
        self._position_close_button()

    def set_close_anchor(self, global_center_y: int):
        self._close_anchor_global_y = int(global_center_y)
        self._position_close_button()

    def set_panel_state(self, state: str):
        self._panel_state = str(state)
        self._border_animator.set_state(self._panel_state)
        self.update()

    def set_caption(self, text: str):
        self._title_text = str(text)
        self.caption_label.setText(self._title_text)

    def set_cornerRadius(self, value):
        self._corner_radius = max(0.0, float(value))
        self.update()

    def cornerRadius(self):
        return self._corner_radius

    cornerRadius = pyqtProperty(float, fget=cornerRadius, fset=set_cornerRadius)

    def prepare_for_open(self, from_geometry: QRect, to_geometry: QRect):
        self._target_geometry = QRect(to_geometry)
        self.setGeometry(from_geometry)
        self.setWindowOpacity(0.0)
        self.set_cornerRadius(min(from_geometry.width(), from_geometry.height()) / 2.0)
        self.show()
        self.raise_()
        self._geometry_anim.stop()
        self._opacity_anim.stop()
        self._radius_anim.stop()
        self._geometry_anim.setStartValue(QRect(from_geometry))
        self._geometry_anim.setEndValue(QRect(to_geometry))
        self._opacity_anim.setStartValue(0.0)
        self._opacity_anim.setEndValue(1.0)
        self._radius_anim.setStartValue(min(from_geometry.width(), from_geometry.height()) / 2.0)
        self._radius_anim.setEndValue(float(self._config.panel_corner_radius))
        self._animation_group.start()

    def animate_collapse(self, to_geometry: QRect):
        self._target_geometry = QRect(to_geometry)
        self._close_group.stop()
        self._close_geometry_anim.setStartValue(QRect(self.geometry()))
        self._close_geometry_anim.setEndValue(QRect(to_geometry))
        self._close_opacity_anim.setStartValue(float(self.windowOpacity()))
        self._close_opacity_anim.setEndValue(0.0)
        self._close_radius_anim.setStartValue(float(self._corner_radius))
        self._close_radius_anim.setEndValue(min(to_geometry.width(), to_geometry.height()) / 2.0)
        self._close_group.start()

    def _finalize_close(self):
        self.hide()
        self.set_cornerRadius(float(self._config.panel_corner_radius))

    def closeEvent(self, event):
        event.ignore()
        self.collapse_requested.emit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._content.setGeometry(self.rect())
        self._position_close_button()

    def moveEvent(self, event):
        super().moveEvent(event)
        self._position_close_button()

    def _position_close_button(self):
        size = self.close_button.width()
        if self._close_anchor_global_y is None:
            center_y = int(self.height() / 2)
        else:
            center_y = int(self._close_anchor_global_y - self.y())
            center_y = max(int(size / 2), min(center_y, int(self.height() - (size / 2))))
        if self._dock_edge == "left":
            center_x = int(self._config.orb_diameter / 2)
        else:
            center_x = int(self.width() - (self._config.orb_diameter / 2))
        self.close_button.move(int(center_x - (size / 2)), int(center_y - (size / 2)))

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        path = rect

        base = QColor(*self._config.theme.panel_base)
        accent_top = QColor(*self._config.theme.panel_top)
        accent_bottom = QColor(*self._config.theme.panel_bottom)
        painter.setPen(Qt.NoPen)
        painter.setBrush(base)
        painter.drawRoundedRect(path, self._corner_radius, self._corner_radius)

        painter.setBrush(QColor(accent_top))
        upper_rect = QRectF(rect)
        upper_rect.adjust(1, 1, -1, -(rect.height() * 0.45))
        painter.drawRoundedRect(upper_rect, self._corner_radius, self._corner_radius)
        painter.setBrush(QColor(accent_bottom))
        lower_rect = QRectF(rect)
        lower_rect.adjust(1, rect.height() * 0.45, -1, -1)
        painter.drawRoundedRect(lower_rect, self._corner_radius, self._corner_radius)

        paint_border(
            painter,
            rect,
            self._corner_radius,
            self._panel_state,
            self._border_animator.phase,
            self._config.theme,
        )
