import math

from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QConicalGradient, QPainter, QPainterPath, QPen
from PyQt5.QtCore import QRectF, Qt


class BorderAnimator(QObject):
    phase_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._phase = 0.0
        self._state = "idle"
        self._timer = QTimer(self)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    @property
    def phase(self) -> float:
        return self._phase

    @property
    def state(self) -> str:
        return self._state

    def set_state(self, state: str):
        self._state = str(state)

    def _tick(self):
        if self._state == "active":
            step = 0.009
        elif self._state == "selecting":
            step = 0.02
        elif self._state == "panel_open":
            step = 0.012
        else:
            step = 0.006
        self._phase = (self._phase + step) % 1.0
        self.phase_changed.emit()


def _rounded_path(rect, radius: float):
    path = QPainterPath()
    path.addRoundedRect(QRectF(rect), radius, radius)
    return path


def paint_border(painter: QPainter, rect, radius: float, state: str, phase: float, theme):
    path = _rounded_path(rect, radius)
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, True)

    if state == "active":
        gradient = QConicalGradient(rect.center(), phase * 360.0)
        gradient.setColorAt(0.0, QColor(*theme.active_border_a))
        gradient.setColorAt(0.33, QColor(*theme.active_border_b))
        gradient.setColorAt(0.66, QColor(*theme.active_border_c))
        gradient.setColorAt(1.0, QColor(*theme.active_border_a))
        for width, alpha in ((5.0, 32), (2.4, 110), (1.3, 210)):
            glow = QColor(*theme.active_border_a)
            glow.setAlpha(alpha)
            pen = QPen(glow, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            if width < 2.0:
                pen = QPen(gradient, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)
    elif state == "selecting":
        pulse = 0.5 + 0.5 * math.sin(phase * math.tau * 2.0)
        glow = QColor(*theme.selecting_border_glow)
        glow.setAlpha(int(34 + 42 * pulse))
        soft = QColor(*theme.selecting_border_core)
        soft.setAlpha(120)
        core = QColor(*theme.selecting_border_core)
        for width, color in ((4.5, glow), (2.0, soft), (1.3, core)):
            painter.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)
    else:
        pulse = 0.5 + 0.5 * math.sin(phase * math.tau)
        glow_alpha = int(14 + 18 * pulse)
        glow = QColor(*theme.idle_border_glow)
        glow.setAlpha(glow_alpha)
        painter.setPen(QPen(glow, 4.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)
        painter.setPen(QPen(QColor(*theme.idle_border_core), 1.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)

    painter.restore()
