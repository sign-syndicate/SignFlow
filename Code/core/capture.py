"""Screen capture module - grabs frames from the screen."""
from __future__ import annotations

import cv2
import mss
import numpy as np


class ScreenCapture:
    """Captures frames from the screen using mss."""

    def __init__(self, monitor_index: int = 1) -> None:
        """
        Initialize screen capture.
        
        Args:
            monitor_index: Which monitor to capture from (1-indexed, 1 = primary).
        """
        self._monitor_index = monitor_index
        self._sct = None
        self._monitor = None

    def _ensure_initialized(self) -> None:
        """Initialize mss in the correct thread (lazy init)."""
        if self._sct is not None and self._monitor is not None:
            return

        self._sct = mss.mss()
        monitor_list = self._sct.monitors
        monitor_count = len(monitor_list)

        # Select monitor: fallback to primary if index out of bounds
        if monitor_count <= 1:
            self._monitor = monitor_list[0]
        else:
            safe_index = max(1, min(self._monitor_index, monitor_count - 1))
            self._monitor = monitor_list[safe_index]

    @property
    def origin(self) -> tuple[int, int]:
        """Get the top-left corner of the captured monitor (for coordinate mapping)."""
        self._ensure_initialized()
        return int(self._monitor["left"]), int(self._monitor["top"])

    def read(self) -> np.ndarray:
        """
        Capture one frame from the screen.
        
        Returns:
            Frame as BGR numpy array (compatible with OpenCV).
        """
        self._ensure_initialized()
        frame_bgra = np.asarray(self._sct.grab(self._monitor))
        return cv2.cvtColor(frame_bgra, cv2.COLOR_BGRA2BGR)
