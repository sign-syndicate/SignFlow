"""PyQt5 transparent overlay for drawing detections."""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import QApplication, QWidget

# Type hints
Box = Tuple[int, int, int, int, float]  # x1, y1, x2, y2, confidence


class DetectionOverlay(QWidget):
    """
    Transparent topmost overlay window.
    
    - Stays on top of all windows
    - Click-through (mouse events pass through)
    - Draws detection boxes
    """

    def __init__(self) -> None:
        """Initialize the overlay widget."""
        super().__init__()
        self._raw_boxes: List[Box] = []
        self._stable_boxes: List[Box] = []
        self._active_rois: List[Box] = []
        self._config_show_raw_boxes = True
        self._config_show_stable_boxes = True
        self._show_raw_boxes = True
        self._show_stable_boxes = True
        self._user_raw_override = False
        self._user_stable_override = False
        self._focus_mode_enabled = False
        self._user_focus_override = False
        self._focus_dim_alpha = 90
        self._raw_box_color = QColor(0, 255, 120)
        self._stable_box_color = QColor(164, 78, 255)
        self._debug_visualization = False
        self._origin_x = 0
        self._origin_y = 0

        self.setWindowTitle("SignFlow")
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        # Get screen geometry
        screen = QApplication.primaryScreen()
        if screen is not None:
            rect = screen.virtualGeometry()
            self._origin_x = rect.left()
            self._origin_y = rect.top()
            self.setGeometry(rect)

    def update_payload(self, payload: Dict[str, object]) -> None:
        """
        Update overlay with new detections and stabilized ROI data.
        
        Args:
            payload: Dictionary with raw and stabilized box lists.
        """
        self._raw_boxes = list(payload.get("raw_boxes", []))
        self._stable_boxes = list(payload.get("stable_boxes", []))
        self._active_rois = list(payload.get("active_rois", []))
        self._config_show_raw_boxes = bool(payload.get("show_raw_boxes", True))
        self._config_show_stable_boxes = bool(payload.get("show_stable_boxes", True))
        if not self._user_raw_override:
            self._show_raw_boxes = self._config_show_raw_boxes
        if not self._user_stable_override:
            self._show_stable_boxes = self._config_show_stable_boxes
        config_focus_enabled = bool(payload.get("focus_mode_enabled", False))
        if not self._user_focus_override:
            self._focus_mode_enabled = config_focus_enabled
        self._focus_dim_alpha = max(0, min(220, int(payload.get("focus_dim_alpha", 90))))
        self._raw_box_color = self._parse_color(payload.get("raw_box_rgb"), QColor(0, 255, 120))
        self._stable_box_color = self._parse_color(payload.get("stable_box_rgb"), QColor(164, 78, 255))
        self._debug_visualization = bool(payload.get("debug_visualization", False))
        self.update()

    def paintEvent(self, event) -> None:
        """Paint the stabilized ROI and optional raw detections on the overlay."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setBrush(Qt.NoBrush)

        if self._focus_mode_enabled and self._stable_boxes:
            self._draw_focus_dim_layer(painter, self._stable_boxes)

        if self._show_raw_boxes:
            self._draw_boxes(
                painter,
                self._raw_boxes,
                box_color=self._raw_box_color,
                text_color=self._raw_box_color.lighter(150),
                pen_width=1,
                label_prefix="raw",
            )

        if self._show_stable_boxes:
            self._draw_boxes(
                painter,
                self._stable_boxes,
                box_color=self._stable_box_color,
                text_color=self._stable_box_color.lighter(150),
                pen_width=2,
                label_prefix="stable",
            )

        painter.end()

    def toggle_raw_boxes(self) -> None:
        """Toggle rendering of raw YOLO boxes."""
        self._user_raw_override = True
        self._show_raw_boxes = not self._show_raw_boxes
        self.update()

    def toggle_stable_boxes(self) -> None:
        """Toggle rendering of stabilized boxes."""
        self._user_stable_override = True
        self._show_stable_boxes = not self._show_stable_boxes
        self.update()

    def toggle_focus_mode(self) -> None:
        """Toggle dimming outside stabilized ROI boxes."""
        self._user_focus_override = True
        self._focus_mode_enabled = not self._focus_mode_enabled
        self.update()

    def _draw_boxes(
        self,
        painter: QPainter,
        boxes: List[Box],
        box_color: QColor,
        text_color: QColor,
        pen_width: int,
        label_prefix: str,
    ) -> None:
        """Draw a list of boxes using a specific visual style."""
        painter.setPen(QPen(box_color, pen_width))

        for x1, y1, x2, y2, confidence in boxes:
            painter.setPen(QPen(box_color, pen_width))
            lx1 = x1 - self._origin_x
            ly1 = y1 - self._origin_y
            width = max(1, x2 - x1)
            height = max(1, y2 - y1)

            painter.drawRect(lx1, ly1, width, height)

            label = f"{label_prefix} {confidence:.2f}"
            painter.setPen(QPen(text_color, 1))
            painter.drawText(lx1 + 4, max(12, ly1 - 6), label)

    def _parse_color(self, value, fallback: QColor) -> QColor:
        """Convert a config color value into a QColor."""
        if isinstance(value, (list, tuple)) and len(value) == 3:
            try:
                red, green, blue = (int(channel) for channel in value)
                return QColor(red, green, blue)
            except (TypeError, ValueError):
                return fallback
        return fallback

    def _draw_focus_dim_layer(self, painter: QPainter, focus_boxes: List[Box]) -> None:
        """Darken non-ROI regions while leaving ROI windows transparent."""
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, self._focus_dim_alpha))
        painter.drawRect(self.rect())

        painter.setCompositionMode(QPainter.CompositionMode_Clear)
        for x1, y1, x2, y2, _ in focus_boxes:
            lx1 = x1 - self._origin_x
            ly1 = y1 - self._origin_y
            width = max(1, x2 - x1)
            height = max(1, y2 - y1)
            painter.drawRoundedRect(lx1, ly1, width, height, 8.0, 8.0)

        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
