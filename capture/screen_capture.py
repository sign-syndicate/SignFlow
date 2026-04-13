from __future__ import annotations

import cv2
import mss
import numpy as np


class ScreenCapture:
    def __init__(self, monitor_index: int = 1) -> None:
        self._monitor_index = monitor_index
        self._sct = None
        self._monitor = None

    def _ensure_initialized(self) -> None:
        if self._sct is not None and self._monitor is not None:
            return

        # mss uses thread-local handles on Windows. Initialize in the same
        # thread that performs grab() to avoid srcdc/memdc attribute errors.
        self._sct = mss.mss()
        monitor_count = len(self._sct.monitors)

        if monitor_count <= 1:
            self._monitor = self._sct.monitors[0]
        else:
            safe_index = max(1, min(self._monitor_index, monitor_count - 1))
            self._monitor = self._sct.monitors[safe_index]

    @property
    def origin(self) -> tuple[int, int]:
        self._ensure_initialized()
        return int(self._monitor["left"]), int(self._monitor["top"])

    def read(self) -> np.ndarray:
        self._ensure_initialized()
        shot = self._sct.grab(self._monitor)
        frame_bgra = np.asarray(shot)
        return cv2.cvtColor(frame_bgra, cv2.COLOR_BGRA2BGR)
