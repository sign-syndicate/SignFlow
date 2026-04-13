"""PyQt5 transparent overlay for drawing detections."""
from __future__ import annotations

from typing import Dict, List, Tuple

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
        self._boxes: List[Box] = []
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

    def update_payload(self, payload: Dict[str, List[Box]]) -> None:
        """
        Update overlay with new detections.
        
        Args:
            payload: Dictionary with "boxes" key containing detection list.
        """
        self._boxes = payload.get("boxes", [])
        self.update()

    def paintEvent(self, event) -> None:
        """Paint detection boxes on the overlay."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw each detection box
        pen = QPen(QColor(0, 255, 120), 2)  # Bright green
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        for x1, y1, x2, y2, confidence in self._boxes:
            # Convert from screen space to widget local space
            lx1 = x1 - self._origin_x
            ly1 = y1 - self._origin_y
            width = max(1, x2 - x1)
            height = max(1, y2 - y1)

            # Draw rectangle
            painter.drawRect(lx1, ly1, width, height)

            # Draw confidence label
            label = f"person {confidence:.2f}"
            painter.setPen(QPen(QColor(30, 240, 140), 1))
            painter.drawText(lx1 + 4, max(12, ly1 - 6), label)

        painter.end()
