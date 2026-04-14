from PyQt5.QtCore import QObject, QRect, pyqtSignal

from .config import AppConfig


class AppStateManager(QObject):
    state_changed = pyqtSignal(str, str)
    roi_changed = pyqtSignal(object)
    caption_changed = pyqtSignal(str)
    dock_edge_changed = pyqtSignal(str)

    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self._config = config
        self._state = "idle"
        self._roi = None
        self._dock_edge = "right"
        self._caption = config.idle_caption
        self._caption_index = 0

    @property
    def state(self) -> str:
        return self._state

    @property
    def roi(self):
        return self._roi

    @property
    def dock_edge(self) -> str:
        return self._dock_edge

    @property
    def caption(self) -> str:
        return self._caption

    def set_state(self, state: str):
        state = str(state)
        if state == self._state:
            return
        previous = self._state
        self._state = state
        self.state_changed.emit(previous, state)

    def set_roi(self, roi):
        if roi is None:
            self._roi = None
            self.roi_changed.emit(None)
            return
        if isinstance(roi, QRect):
            value = QRect(roi)
        else:
            left, top, width, height = roi
            value = QRect(int(left), int(top), int(width), int(height))
        self._roi = value
        self.roi_changed.emit(QRect(value))

    def set_dock_edge(self, dock_edge: str):
        dock_edge = str(dock_edge)
        if dock_edge == self._dock_edge:
            return
        self._dock_edge = dock_edge
        self.dock_edge_changed.emit(dock_edge)

    def set_caption(self, caption: str):
        caption = str(caption)
        if caption == self._caption:
            return
        self._caption = caption
        self.caption_changed.emit(caption)

    def reset_caption_cycle(self):
        self._caption_index = 0

    def next_caption(self) -> str:
        captions = self._config.active_caption_cycle
        if not captions:
            return self._caption
        caption = captions[self._caption_index % len(captions)]
        self._caption_index += 1
        self.set_caption(caption)
        return caption
