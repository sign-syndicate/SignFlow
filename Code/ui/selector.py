from __future__ import annotations

from PyQt5.QtCore import (
    QEasingCurve,
    QEvent,
    QPropertyAnimation,
    QRect,
    Qt,
    pyqtProperty,
    pyqtSignal,
)
from PyQt5.QtGui import QColor, QGuiApplication, QPainter, QPen
from PyQt5.QtWidgets import QWidget

from ..core.theme import Theme, resolve_primary_light_color


class RoiSelectorOverlay(QWidget):
    roi_confirmed = pyqtSignal(int, int, int, int)
    selection_cancelled = pyqtSignal()

    CONFIRMATION_MS = 3000
    FADE_IN_MS = 180
    COMPLETION_INSET_MS = 180
    COMPLETION_FADE_MS = 180
    CONFIRM_PADDING_PX = 4.0

    def __init__(self, theme: Theme, debug: bool = False, parent=None):
        super().__init__(parent)
        self._theme = theme
        self._debug = debug

        self._state = "idle"
        self._origin = None
        self._current = None
        self._roi_rect = QRect()
        self._locked_rect = QRect()
        self._inset = 0.0
        self._overlay_opacity = 0.0
        self._confirm_progress = 0.0

        self._primary_color = QColor(self._theme.primary_color)
        self._primary_light_color = QColor(resolve_primary_light_color(self._theme))
        self._overlay_color = QColor(self._theme.overlay_color)

        self._confirm_animation = QPropertyAnimation(self, b"confirmProgress", self)
        self._confirm_animation.setDuration(self.CONFIRMATION_MS)
        self._confirm_animation.setEasingCurve(QEasingCurve.Linear)

        self._fade_in_anim = QPropertyAnimation(self, b"overlayOpacity", self)
        self._fade_in_anim.setDuration(self.FADE_IN_MS)
        self._fade_in_anim.setEasingCurve(QEasingCurve.OutCubic)

        self._completion_inset_anim = QPropertyAnimation(self, b"roiInset", self)
        self._completion_inset_anim.setDuration(self.COMPLETION_INSET_MS)
        self._completion_inset_anim.setEasingCurve(QEasingCurve.InOutCubic)

        self._completion_fade_anim = QPropertyAnimation(self, b"overlayOpacity", self)
        self._completion_fade_anim.setDuration(self.COMPLETION_FADE_MS)
        self._completion_fade_anim.setEasingCurve(QEasingCurve.InOutCubic)

        self._confirm_animation.finished.connect(self._on_confirmation_complete)
        self._completion_inset_anim.finished.connect(self._on_completion_inset_finished)
        self._completion_fade_anim.finished.connect(self._finish_confirmed_selection)

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.CrossCursor)
        app = QGuiApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def getOverlayOpacity(self) -> float:
        return self._overlay_opacity

    def setOverlayOpacity(self, value: float):
        self._overlay_opacity = max(0.0, min(1.0, float(value)))
        self.update()

    overlayOpacity = pyqtProperty(float, fget=getOverlayOpacity, fset=setOverlayOpacity)

    def getRoiInset(self) -> float:
        return self._inset

    def setRoiInset(self, value: float):
        self._inset = max(0.0, float(value))
        self.update()

    roiInset = pyqtProperty(float, fget=getRoiInset, fset=setRoiInset)

    def getConfirmProgress(self) -> float:
        return self._confirm_progress

    def setConfirmProgress(self, value: float):
        self._confirm_progress = max(0.0, min(1.0, float(value)))
        self.update()

    confirmProgress = pyqtProperty(float, fget=getConfirmProgress, fset=setConfirmProgress)

    @property
    def state(self) -> str:
        return self._state

    def start(self):
        self._set_fullscreen_geometry()
        self._set_state("idle")
        self._fade_in_anim.stop()
        self.overlayOpacity = 0.0
        self.roiInset = 0.0
        self._fade_in_anim.setStartValue(0.0)
        self._fade_in_anim.setEndValue(1.0)
        self.show()
        self.raise_()
        self.activateWindow()
        self.grabKeyboard()
        self.setFocus(Qt.ActiveWindowFocusReason)
        self._fade_in_anim.start()

    def showEvent(self, event):
        super().showEvent(event)
        self._set_fullscreen_geometry()

    def closeEvent(self, event):
        self._confirm_animation.stop()
        self._completion_inset_anim.stop()
        self._completion_fade_anim.stop()
        self._fade_in_anim.stop()
        app = QGuiApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        self.releaseKeyboard()
        super().closeEvent(event)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.KeyPress:
            self._cancel_selection()
            return True
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self._cancel_selection()
            event.accept()
            return

        if event.button() != Qt.LeftButton:
            event.ignore()
            return

        self._begin_selection(event.pos())
        event.accept()

    def mouseMoveEvent(self, event):
        if self._state != "selecting" or self._origin is None:
            event.ignore()
            return

        self._current = event.pos()
        self._roi_rect = QRect(self._origin, self._current).normalized()
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            event.ignore()
            return

        if self._state != "selecting":
            event.accept()
            return

        self._current = event.pos()
        self._roi_rect = QRect(self._origin, self._current).normalized()

        if self._is_valid_rect(self._roi_rect):
            self._enter_confirmation()
        else:
            self._clear_roi()
            self._set_state("idle")

        self.update()
        event.accept()

    def keyPressEvent(self, event):
        self._cancel_selection()
        event.accept()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        content_alpha = max(0.0, min(1.0, self._overlay_opacity))

        dim = QColor(self._overlay_color)
        overlay_alpha = int(round(255 * self._theme.overlay_opacity * self._overlay_opacity * self._theme.opacity_idle))
        dim.setAlpha(max(0, min(255, overlay_alpha)))
        painter.fillRect(self.rect(), dim)

        if not self._is_valid_rect(self._roi_rect):
            return

        draw_rect = self._roi_rect.adjusted(int(self._inset), int(self._inset), -int(self._inset), -int(self._inset))
        if draw_rect.width() <= 0 or draw_rect.height() <= 0:
            return

        if self._state == "confirming_roi":
            inner_pen = QPen(self._primary_light_color, 1.9)
            inner_pen.setStyle(Qt.CustomDashLine)
            inner_pen.setDashPattern([6.0, 5.0])
            inner_pen.setCapStyle(Qt.RoundCap)
            inner_pen.setJoinStyle(Qt.RoundJoin)
            inner_pen_color = QColor(self._primary_light_color)
            inner_pen_color.setAlpha(int(96 * content_alpha))
            inner_pen.setColor(inner_pen_color)
            painter.setPen(inner_pen)

            inner_fill = QColor(self._primary_light_color)
            inner_fill.setAlpha(int(12 * content_alpha))
            painter.setBrush(inner_fill)
            painter.drawRect(draw_rect)

            confirm_color = self._interpolate_color(self._primary_light_color, QColor(255, 255, 255), self._confirm_progress)
            confirm_color.setAlpha(int((180 + (60 * self._confirm_progress)) * content_alpha))
            glow_color = QColor(confirm_color)
            glow_color.setAlpha(min(255, glow_color.alpha() // 5 + 34))
            glow_pen = QPen(glow_color, 3.0)
            glow_pen.setStyle(Qt.SolidLine)
            glow_pen.setCapStyle(Qt.RoundCap)
            glow_pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(glow_pen)
            self._draw_progressive_solid_rect(painter, draw_rect, self._confirm_progress, glow_pen)

            confirm_pen = QPen(confirm_color, 1.4)
            confirm_pen.setStyle(Qt.SolidLine)
            confirm_pen.setCapStyle(Qt.RoundCap)
            confirm_pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(confirm_pen)
            self._draw_progressive_solid_rect(painter, draw_rect, self._confirm_progress, confirm_pen)
        else:
            pen = QPen(self._primary_light_color, 2.0)
            pen.setStyle(Qt.CustomDashLine)
            pen.setDashPattern([6.0, 6.0])
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            pen_color = QColor(self._primary_light_color)
            pen_color.setAlpha(int(86 * content_alpha))
            pen.setColor(pen_color)
            painter.setPen(pen)

            fill = QColor(self._primary_light_color)
            fill.setAlpha(int(8 * content_alpha))
            painter.setBrush(fill)
            painter.drawRect(draw_rect)

        if self._debug:
            coords = f"{self._roi_rect.x()}, {self._roi_rect.y()}, {self._roi_rect.width()}, {self._roi_rect.height()}"
            label_color = QColor(self._primary_color)
            label_color.setAlpha(230)
            painter.setPen(label_color)
            text_x = max(6, draw_rect.x())
            text_y = max(16, draw_rect.y() - 6)
            painter.drawText(text_x, text_y, coords)

    def _begin_selection(self, point):
        self._confirm_animation.stop()
        self._completion_inset_anim.stop()
        self._completion_fade_anim.stop()
        self._fade_in_anim.stop()
        self.roiInset = 0.0
        self.confirmProgress = 0.0

        self._origin = point
        self._current = point
        self._roi_rect = QRect(point, point)

        self._set_state("selecting")
        self.update()

    def _enter_confirmation(self):
        self._confirm_animation.stop()
        self.confirmProgress = 0.0
        self._set_state("confirming_roi")
        self._confirm_animation.setStartValue(0.0)
        self._confirm_animation.setEndValue(1.0)
        self._confirm_animation.start()

    def _on_confirmation_complete(self):
        if self._state != "confirming_roi" or not self._is_valid_rect(self._roi_rect):
            return
        self._locked_rect = QRect(self._roi_rect)
        print(
            f"ROI confirmed: {self._locked_rect.x()}, {self._locked_rect.y()}, "
            f"{self._locked_rect.width()}, {self._locked_rect.height()}"
        )
        self._completion_inset_anim.stop()
        self._completion_fade_anim.stop()
        self._completion_inset_anim.setStartValue(0.0)
        self._completion_inset_anim.setEndValue(2.0)
        self._completion_fade_anim.setStartValue(self._overlay_opacity)
        self._completion_fade_anim.setEndValue(0.0)
        self._completion_inset_anim.start()
        self._completion_fade_anim.start()

    def _on_completion_inset_finished(self):
        if not self._is_valid_rect(self._locked_rect):
            return
        self.update()

    def _finish_confirmed_selection(self):
        if self._is_valid_rect(self._locked_rect):
            self.roi_confirmed.emit(
                self._locked_rect.x(),
                self._locked_rect.y(),
                self._locked_rect.width(),
                self._locked_rect.height(),
            )
        self.close()

    def _cancel_selection(self):
        self._confirm_animation.stop()
        self._completion_inset_anim.stop()
        self._completion_fade_anim.stop()
        self._fade_in_anim.stop()
        self._clear_roi()
        self._set_state("idle")
        self.selection_cancelled.emit()
        self.close()

    def _clear_roi(self):
        self._origin = None
        self._current = None
        self._roi_rect = QRect()
        self._locked_rect = QRect()
        self.roiInset = 0.0
        self.confirmProgress = 0.0

    def _set_fullscreen_geometry(self):
        screens = QGuiApplication.screens()
        if not screens:
            self.setGeometry(QRect(0, 0, 1280, 720))
            return

        geometry = screens[0].geometry()
        for screen in screens[1:]:
            geometry = geometry.united(screen.geometry())
        self.setGeometry(geometry)

    def _set_state(self, new_state: str):
        new_state = str(new_state)
        if new_state == self._state:
            return
        previous = self._state
        self._state = new_state
        if self._debug:
            print(f"selector state: {previous} -> {new_state}")

    @staticmethod
    def _interpolate_color(start: QColor, end: QColor, progress: float) -> QColor:
        progress = max(0.0, min(1.0, float(progress)))
        return QColor(
            int(start.red() + ((end.red() - start.red()) * progress)),
            int(start.green() + ((end.green() - start.green()) * progress)),
            int(start.blue() + ((end.blue() - start.blue()) * progress)),
            int(start.alpha() + ((end.alpha() - start.alpha()) * progress)),
        )

    @staticmethod
    def _is_valid_rect(rect: QRect) -> bool:
        return rect.width() >= 4 and rect.height() >= 4

    @staticmethod
    def _rect_perimeter_points(rect: QRect):
        left = float(rect.left())
        top = float(rect.top())
        right = float(rect.right())
        bottom = float(rect.bottom())

        if right <= left or bottom <= top:
            return []

        return [
            (left, top, right, top),
            (right, top, right, bottom),
            (right, bottom, left, bottom),
            (left, bottom, left, top),
        ]

    def _draw_progressive_dashed_rect(self, painter: QPainter, rect: QRect, progress: float, pen: QPen):
        progress = max(0.0, min(1.0, float(progress)))
        if progress <= 0.0:
            return

        segments = self._rect_perimeter_points(rect)
        if not segments:
            return

        dash_len = 12.0
        gap_len = 7.0
        reveal_length = self._rect_perimeter_length(rect) * progress

        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        distance_cursor = 0.0
        for start_x, start_y, end_x, end_y in segments:
            side_length = abs(end_x - start_x) + abs(end_y - start_y)
            if side_length <= 0.0:
                continue

            segment_cursor = 0.0
            while segment_cursor < side_length:
                dash_start = max(0.0, distance_cursor + segment_cursor)
                if dash_start >= reveal_length:
                    return
                dash_end = min(distance_cursor + segment_cursor + dash_len, distance_cursor + side_length, reveal_length)
                if dash_end > dash_start:
                    self._draw_line_slice(painter, rect, dash_start, dash_end)
                segment_cursor += dash_len + gap_len

            distance_cursor += side_length

    def _draw_progressive_solid_rect(self, painter: QPainter, rect: QRect, progress: float, pen: QPen):
        progress = max(0.0, min(1.0, float(progress)))
        if progress <= 0.0:
            return

        perimeter_length = self._rect_perimeter_length(rect)
        if perimeter_length <= 0.0:
            return

        reveal_length = perimeter_length * progress
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        self._draw_line_slice(painter, rect, 0.0, reveal_length)

    def _rect_perimeter_length(self, rect: QRect) -> float:
        return float(max(0, rect.width()) * 2 + max(0, rect.height()) * 2)

    def _draw_line_slice(self, painter: QPainter, rect: QRect, start_distance: float, end_distance: float):
        left = float(rect.left())
        top = float(rect.top())
        right = float(rect.right())
        bottom = float(rect.bottom())

        perimeter = self._rect_perimeter_length(rect)
        if perimeter <= 0.0:
            return

        def point_at(distance: float):
            distance = max(0.0, min(perimeter, float(distance)))
            width = right - left
            height = bottom - top

            if distance <= width:
                return left + distance, top
            distance -= width
            if distance <= height:
                return right, top + distance
            distance -= height
            if distance <= width:
                return right - distance, bottom
            distance -= width
            return left, bottom - min(height, distance)

        width = right - left
        height = bottom - top
        edge_boundaries = [
            width,
            width + height,
            (width * 2.0) + height,
            perimeter,
        ]

        def edge_index_at(distance: float) -> int:
            if distance < edge_boundaries[0]:
                return 0
            if distance < edge_boundaries[1]:
                return 1
            if distance < edge_boundaries[2]:
                return 2
            return 3

        start_distance = max(0.0, min(perimeter, float(start_distance)))
        end_distance = max(0.0, min(perimeter, float(end_distance)))
        if end_distance <= start_distance:
            return

        cursor = start_distance
        while cursor < end_distance:
            edge_index = edge_index_at(cursor)
            edge_limit = edge_boundaries[edge_index]
            segment_end = min(end_distance, edge_limit)
            start_point = point_at(cursor)
            end_point = point_at(segment_end)
            painter.drawLine(
                int(round(start_point[0])),
                int(round(start_point[1])),
                int(round(end_point[0])),
                int(round(end_point[1])),
            )

            # Guard against potential no-progress loops due to float rounding.
            if segment_end <= cursor:
                break
            cursor = segment_end
