from PyQt5.QtCore import QObject, pyqtSignal


class AppStateManager(QObject):
    state_changed = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = "idle"

    @property
    def state(self) -> str:
        return self._state

    def set_state(self, state: str):
        state = str(state)
        if state == self._state:
            return
        previous = self._state
        self._state = state
        self.state_changed.emit(previous, state)
