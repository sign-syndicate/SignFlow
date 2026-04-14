from PyQt5.QtCore import QEasingCurve, QPoint, QRect, QRectF, QPropertyAnimation, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PyQt5.QtWidgets import QWidget


class RegionSelector(QWidget):
    selection_finished = pyqtSignal(QRect)
    selection_cancelled = pyqtSignal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self._dragging = False
        self._origin = QPoint()
        self._current = QPoint()
        self._selection = QRect()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.CrossCursor)
        self.setWindowOpacity(0.0)

        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(config.dim_fade_ms)
        self._fade.setEasingCurve(QEasingCurve.OutCubic)

    def show_with_fade(self):
        screen = self.screen()
        if screen is None:
            return
        self.setGeometry(screen.virtualGeometry())
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.ActiveWindowFocusReason)
        self._fade.stop()
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.start()

    def hide_overlay(self):
        self.hide()
        self._dragging = False
        self._selection = QRect()

    def _has_selection(self) -> bool:
        return self._selection.width() > 0 and self._selection.height() > 0

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.selection_cancelled.emit()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        self._dragging = True
        self._origin = event.pos()
        self._current = event.pos()
        self._selection = QRect(self._origin, self._current).normalized()
        self.update()

    def mouseMoveEvent(self, event):
        if not self._dragging:
            return
        self._current = event.pos()
        self._selection = QRect(self._origin, self._current).normalized()
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        self._dragging = False
        self._current = event.pos()
        self._selection = QRect(self._origin, self._current).normalized()
        self.update()
        if self._has_selection():
            top_left = self.geometry().topLeft() + self._selection.topLeft()
            roi = QRect(top_left, self._selection.size()).normalized()
            self.selection_finished.emit(roi)
        else:
            self.selection_cancelled.emit()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        full_rect = self.rect()
        dim_color = QColor(*self._config.theme.dim_color)
        painter.fillRect(full_rect, dim_color)

        chip_text = self._config.selection_text
        font = QFont("Segoe UI", 10)
        font.setBold(True)
        metrics = QFontMetrics(font)
        chip_width = metrics.horizontalAdvance(chip_text) + 34
        chip_height = metrics.height() + 18
        chip_rect = QRectF((self.width() - chip_width) / 2.0, 18, chip_width, chip_height)
        painter.setPen(QPen(QColor(*self._config.theme.selector_chip_border), 1.0))
        painter.setBrush(QColor(*self._config.theme.selector_chip_bg))
        painter.drawRoundedRect(chip_rect, 12, 12)
        painter.setFont(font)
        painter.setPen(QColor(*self._config.theme.selector_chip_text))
        painter.drawText(chip_rect, Qt.AlignCenter, chip_text)

        if self._has_selection():
            selection = QRectF(self._selection)
            fill = QColor(*self._config.theme.selector_fill)
            border = QColor(*self._config.theme.selector_border)
            painter.setPen(Qt.NoPen)
            painter.setBrush(fill)
            painter.drawRoundedRect(selection, 10, 10)
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(border, self._config.selection_border_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawRoundedRect(selection, 10, 10)
