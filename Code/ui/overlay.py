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
        self._active_roi: Optional[Box] = None
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
        self._active_roi = payload.get("active_roi_screen") or payload.get("active_roi")
        self._debug_visualization = bool(payload.get("debug_visualization", False))
        self.update()

    def paintEvent(self, event) -> None:
        """Paint the stabilized ROI and optional raw detections on the overlay."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setBrush(Qt.NoBrush)

        if self._debug_visualization:
            self._draw_boxes(
                painter,
                self._raw_boxes,
                box_color=QColor(164, 78, 255),
                text_color=QColor(220, 180, 255),
                pen_width=1,
                label_prefix="raw",
            )

        self._draw_boxes(
            painter,
            self._stable_boxes,
            box_color=QColor(0, 255, 120),
            text_color=QColor(30, 240, 140),
            pen_width=2,
            label_prefix="stable",
        )

        if self._active_roi is not None and not self._stable_boxes:
            self._draw_boxes(
                painter,
                [self._active_roi],
                box_color=QColor(0, 255, 120),
                text_color=QColor(30, 240, 140),
                pen_width=2,
                label_prefix="roi",
            )

        painter.end()

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
