from __future__ import annotations

import time
from pathlib import Path
from typing import List, Tuple

from capture.screen_capture import ScreenCapture
from detection.person_detector import PersonDetector

Box = Tuple[int, int, int, int]


class VisionPipeline:
    def __init__(
        self,
        model_path: str | Path,
        monitor_index: int = 1,
        conf: float = 0.35,
    ) -> None:
        self._capture = ScreenCapture(monitor_index=monitor_index)
        self._detector = PersonDetector(model_path=model_path)
        self._conf = conf
        self._running = False

    def process_once(self) -> List[Box]:
        frame = self._capture.read()
        return self._detector.detect(frame=frame, conf=self._conf)

    def run(self, on_result=None, throttle_seconds: float = 0.0) -> None:
        self._running = True
        while self._running:
            boxes = self.process_once()
            if on_result is not None:
                on_result(boxes)

            if throttle_seconds > 0:
                time.sleep(throttle_seconds)

    def stop(self) -> None:
        self._running = False
