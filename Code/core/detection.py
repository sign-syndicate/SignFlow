"""YOLO person detection module."""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import torch
from ultralytics import YOLO
from ultralytics.nn.tasks import DetectionModel

# Type hints
Box = Tuple[int, int, int, int]
ScoredBox = Tuple[int, int, int, int, float]


class PersonDetector:
    """Detects people in images using YOLOv8n."""

    def __init__(self, model_path: str | Path) -> None:
        """
        Initialize YOLO detector.
        
        Args:
            model_path: Path to yolov8n.pt model file.
        """
        model_path = Path(model_path)
        model_path.parent.mkdir(parents=True, exist_ok=True)

        # Add safe globals for torch deserialization
        if hasattr(torch.serialization, "add_safe_globals"):
            torch.serialization.add_safe_globals([DetectionModel])

        self._model = YOLO(str(model_path))

    def detect_with_scores(self, frame, conf: float = 0.35) -> List[ScoredBox]:
        """
        Detect people in a frame.
        
        Args:
            frame: Image frame (BGR numpy array).
            conf: Confidence threshold (0.0 - 1.0).
            
        Returns:
            List of (x1, y1, x2, y2, confidence) tuples for each detected person.
        """
        results = self._model.predict(
            source=frame,
            classes=[0],  # COCO class 0 = person
            conf=conf,
            verbose=False,
            device="cpu",
        )

        boxes: List[ScoredBox] = []
        for result in results:
            if result.boxes is None:
                continue

            xyxy_list = result.boxes.xyxy.tolist()
            conf_list = result.boxes.conf.tolist()

            for (x1, y1, x2, y2), score in zip(xyxy_list, conf_list):
                boxes.append((int(x1), int(y1), int(x2), int(y2), float(score)))

        return boxes
