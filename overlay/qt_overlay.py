from __future__ import annotations

from typing import List, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import QApplication, QWidget

Box = Tuple[int, int, int, int]


class DetectionOverlay(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._boxes: List[Box] = []
        self._origin_x = 0
        self._origin_y = 0

        self.setWindowTitle("SignFlow Overlay")
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        screen = QApplication.primaryScreen()
        if screen is not None:
            rect = screen.virtualGeometry()
            self._origin_x = rect.left()
            self._origin_y = rect.top()
            self.setGeometry(rect)

    def update_boxes(self, boxes: List[Box]) -> None:
        self._boxes = boxes
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        box_pen = QPen(QColor(0, 255, 120), 3)
        painter.setPen(box_pen)
        painter.setBrush(Qt.NoBrush)

        for x1, y1, x2, y2 in self._boxes:
            lx1 = x1 - self._origin_x
            ly1 = y1 - self._origin_y
            painter.drawRect(lx1, ly1, max(1, x2 - x1), max(1, y2 - y1))

        painter.end()
