from __future__ import annotations

from typing import List, Tuple

import cv2
import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPainter, QPixmap
from PyQt5.QtWidgets import QWidget

Box = Tuple[int, int, int, int]


class MiniPlayer(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SignFlow Mini Player")
        self.resize(720, 420)
        self._pixmap: QPixmap | None = None

    def update_frame(self, frame_bgr: np.ndarray, boxes: List[Box]) -> None:
        frame = frame_bgr.copy()
        for x1, y1, x2, y2 in boxes:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, c = frame_rgb.shape
        bytes_per_line = c * w
        image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
        self._pixmap = QPixmap.fromImage(image)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.black)

        if self._pixmap is None:
            painter.end()
            return

        scaled = self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)
        painter.end()

    def closeEvent(self, event) -> None:
        # Hide instead of closing, so app stays in system tray.
        event.ignore()
        self.hide()
