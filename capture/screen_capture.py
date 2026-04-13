from __future__ import annotations

import cv2
import mss
import numpy as np


class ScreenCapture:
    def __init__(self, monitor_index: int = 1) -> None:
        self._sct = mss.mss()
        monitor_count = len(self._sct.monitors)

        if monitor_count <= 1:
            self._monitor = self._sct.monitors[0]
        else:
            safe_index = max(1, min(monitor_index, monitor_count - 1))
            self._monitor = self._sct.monitors[safe_index]

    def read(self) -> np.ndarray:
        shot = self._sct.grab(self._monitor)
        frame_bgra = np.asarray(shot)
        return cv2.cvtColor(frame_bgra, cv2.COLOR_BGRA2BGR)
