from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import torch
from ultralytics import YOLO
from ultralytics.nn.tasks import DetectionModel

Box = Tuple[int, int, int, int]


class PersonDetector:
    def __init__(self, model_path: str | Path) -> None:
        model_path = Path(model_path)
        model_path.parent.mkdir(parents=True, exist_ok=True)

        if hasattr(torch.serialization, "add_safe_globals"):
            torch.serialization.add_safe_globals([DetectionModel])

        self._model = YOLO(str(model_path))

    def detect(self, frame, conf: float = 0.35) -> List[Box]:
        results = self._model.predict(
            source=frame,
            classes=[0],
            conf=conf,
            verbose=False,
            device="cpu",
        )

        boxes: List[Box] = []
        for result in results:
            if result.boxes is None:
                continue

            for xyxy in result.boxes.xyxy.tolist():
                x1, y1, x2, y2 = [int(v) for v in xyxy]
                boxes.append((x1, y1, x2, y2))

        return boxes
