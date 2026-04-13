"""Vision pipeline - orchestrates capture and detection."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

from .capture import ScreenCapture
from .detection import PersonDetector

# Type hints
Box = Tuple[int, int, int, int, float]  # x1, y1, x2, y2, confidence


class VisionPipeline:
    """
    Main vision pipeline.
    
    Flow:
    1. Capture frame from screen
    2. Run YOLO person detection
    3. Convert box coordinates to screen space
    4. Return payload for rendering
    """

    def __init__(
        self,
        model_path: str | Path,
        monitor_index: int = 1,
        conf_threshold: float = 0.35,
    ) -> None:
        """
        Initialize the vision pipeline.
        
        Args:
            model_path: Path to yolov8n.pt.
            monitor_index: Which monitor to capture (1-indexed).
            conf_threshold: YOLO confidence threshold (0-1).
        """
        self._capture = ScreenCapture(monitor_index=monitor_index)
        self._detector = PersonDetector(model_path=model_path)
        self._conf = conf_threshold

    def process_once(self) -> Dict[str, List[Box]]:
        """
        Process one frame.
        
        Returns:
            Dictionary with "boxes" key containing list of detected boxes.
            Example: {"boxes": [(x1, y1, x2, y2, conf), ...]}
        """
        frame = self._capture.read()
        detections = self._detector.detect_with_scores(frame, conf=self._conf)
        left, top = self._capture.origin

        # Convert box coordinates from frame-space to screen-space
        screen_boxes = [
            (x1 + left, y1 + top, x2 + left, y2 + top, conf)
            for x1, y1, x2, y2, conf in detections
        ]

        return {"boxes": screen_boxes}
