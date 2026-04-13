"""Stateful ROI stabilization and prediction for noisy person detections."""
from __future__ import annotations

from dataclasses import dataclass
from json import JSONDecodeError
import json
from math import hypot
from pathlib import Path
from typing import Optional, Sequence, Tuple

# Type hints
Box = Tuple[int, int, int, int, float]
FrameBox = Tuple[int, int, int, int]
FloatBox = Tuple[float, float, float, float]
FrameSize = Tuple[int, int]


@dataclass(frozen=True)
class ROIStabilizerConfig:
    """Runtime tuning values for the ROI stabilizer."""

    enable_roi_stabilization: bool = True
    responsiveness: float = 0.35
    realignment_threshold: float = 0.35
    padding_scale: float = 0.18
    padding_pixels: int = 12
    positional_bias_x: float = 0.0
    positional_bias_y: float = -0.08
    prediction_enable: bool = True
    debug_visualization: bool = False
    yolo_box_approximation: bool = True
    iou_weight: float = 0.7
    confidence_weight: float = 0.3
    velocity_decay: float = 0.88
    dropout_confidence_decay: float = 0.92

    @classmethod
    def from_file(cls, config_path: str | Path | None) -> "ROIStabilizerConfig":
        """Load configuration from JSON, falling back to defaults when unavailable."""
        if config_path is None:
            return cls()

        path = Path(config_path)
        if not path.exists():
            return cls()

        try:
            with path.open("r", encoding="utf-8") as handle:
                raw_config = json.load(handle)
        except (OSError, JSONDecodeError):
            return cls()

        if not isinstance(raw_config, dict):
            return cls()

        default_config = cls()
        values = {}
        for field_name in default_config.__dataclass_fields__:
            values[field_name] = raw_config.get(field_name, getattr(default_config, field_name))

        return cls(**values)


@dataclass
class _TrackState:
    """Internal state for the stabilized ROI."""

    box: FloatBox
    confidence: float
    velocity: FloatBox


class ROIStabilizer:
    """Maintain a stable, padded ROI from noisy per-frame detections."""

    def __init__(self, config: ROIStabilizerConfig | None = None) -> None:
        self._config = config or ROIStabilizerConfig()
        self._state: Optional[_TrackState] = None

    @property
    def config(self) -> ROIStabilizerConfig:
        """Return the active runtime configuration."""
        return self._config

    def reset(self) -> None:
        """Clear the internal ROI state."""
        self._state = None

    def get_active_roi(self) -> Optional[Box]:
        """Return the current stabilized ROI in frame coordinates."""
        if self._state is None:
            return None
        x1, y1, x2, y2 = self._state.box
        return (int(round(x1)), int(round(y1)), int(round(x2)), int(round(y2)), float(self._state.confidence))

    def update(self, detections: Sequence[Box], frame_size: FrameSize) -> Optional[Box]:
        """Update the stabilizer with a new set of detections for the current frame."""
        if not self._config.enable_roi_stabilization:
            return self._update_without_stabilization(detections, frame_size)

        best_detection = self._select_detection(detections)

        if best_detection is None:
            return self._handle_dropout(frame_size)

        target_box = self._expand_and_bias(best_detection[:4], frame_size)
        target_confidence = float(best_detection[4])

        if self._state is None:
            self._state = _TrackState(
                box=target_box,
                confidence=target_confidence,
                velocity=(0.0, 0.0, 0.0, 0.0),
            )
            return self._state_to_box()

        predicted_box = self._predict_box(frame_size)
        blend_factor = self._resolve_blend_factor(predicted_box, target_box)

        blended_box = self._blend_boxes(predicted_box, target_box, blend_factor)
        clamped_box = self._clamp_box(blended_box, frame_size)

        previous_box = self._state.box
        velocity = tuple(
            (clamped_box[index] - previous_box[index]) + (self._state.velocity[index] * self._config.velocity_decay)
            for index in range(4)
        )
        confidence = (self._state.confidence * (1.0 - blend_factor)) + (target_confidence * blend_factor)

        self._state = _TrackState(box=clamped_box, confidence=confidence, velocity=velocity)
        return self._state_to_box()

    def _update_without_stabilization(self, detections: Sequence[Box], frame_size: FrameSize) -> Optional[Box]:
        """Bypass smoothing while still applying padding and consistency checks."""
        best_detection = self._select_detection(detections)
        if best_detection is None:
            self._state = None
            return None

        padded_box = self._expand_and_bias(best_detection[:4], frame_size)
        self._state = _TrackState(box=padded_box, confidence=float(best_detection[4]), velocity=(0.0, 0.0, 0.0, 0.0))
        return self._state_to_box()

    def _handle_dropout(self, frame_size: FrameSize) -> Optional[Box]:
        """Advance the ROI using prediction when detections disappear."""
        if self._state is None:
            return None

        if not self._config.prediction_enable:
            return self._state_to_box()

        predicted_box = self._predict_box(frame_size)
        confidence = self._state.confidence * self._config.dropout_confidence_decay
        velocity = tuple(component * self._config.velocity_decay for component in self._state.velocity)
        self._state = _TrackState(box=predicted_box, confidence=confidence, velocity=velocity)
        return self._state_to_box()

    def _predict_box(self, frame_size: FrameSize) -> FloatBox:
        """Project the current box forward using a simple velocity model."""
        if self._state is None:
            return (0.0, 0.0, 0.0, 0.0)

        predicted = tuple(self._state.box[index] + self._state.velocity[index] for index in range(4))
        return self._clamp_box(predicted, frame_size)

    def _resolve_blend_factor(self, predicted_box: FloatBox, target_box: FloatBox) -> float:
        """Determine how aggressively the stable ROI should move toward the new detection."""
        if self._state is None:
            return 1.0

        deviation = self._box_deviation(predicted_box, target_box)
        base = self._clamp01(self._config.responsiveness)

        if deviation >= self._config.realignment_threshold:
            return min(0.95, max(base, 0.7))

        if self._config.yolo_box_approximation:
            return max(0.08, base * 0.45)

        return max(0.12, base * 0.7)

    def _select_detection(self, detections: Sequence[Box]) -> Optional[Box]:
        """Select the detection most consistent with the current stabilized ROI."""
        if not detections:
            return None

        if self._state is None:
            return max(detections, key=lambda detection: (detection[4], self._area(detection[:4])))

        current_box = self._state.box

        def score_detection(detection: Box) -> float:
            detection_box = tuple(float(value) for value in detection[:4])
            iou_score = self._intersection_over_union(current_box, detection_box)
            center_distance = self._center_distance(current_box, detection_box)
            size_distance = self._size_distance(current_box, detection_box)
            confidence = float(detection[4])
            return (
                iou_score * self._config.iou_weight
                + confidence * self._config.confidence_weight
                - center_distance * 0.12
                - size_distance * 0.08
            )

        return max(detections, key=score_detection)

    def _expand_and_bias(self, box: FrameBox, frame_size: FrameSize) -> FloatBox:
        """Apply padding and a slight positional bias before stabilization."""
        x1, y1, x2, y2 = (float(value) for value in box)
        width = max(1.0, x2 - x1)
        height = max(1.0, y2 - y1)

        padding_x = width * self._config.padding_scale + float(self._config.padding_pixels)
        padding_y = height * self._config.padding_scale + float(self._config.padding_pixels)

        x1 -= padding_x
        x2 += padding_x
        y1 -= padding_y
        y2 += padding_y

        x_shift = width * self._config.positional_bias_x
        y_shift = height * self._config.positional_bias_y
        x1 += x_shift
        x2 += x_shift
        y1 += y_shift
        y2 += y_shift

        return self._clamp_box((x1, y1, x2, y2), frame_size)

    def _blend_boxes(self, previous_box: FloatBox, target_box: FloatBox, alpha: float) -> FloatBox:
        """Linearly blend two boxes coordinate-by-coordinate."""
        beta = 1.0 - alpha
        return tuple((previous_box[index] * beta) + (target_box[index] * alpha) for index in range(4))

    def _state_to_box(self) -> Optional[Box]:
        if self._state is None:
            return None

        x1, y1, x2, y2 = self._state.box
        return (int(round(x1)), int(round(y1)), int(round(x2)), int(round(y2)), float(self._state.confidence))

    def _clamp_box(self, box: FloatBox, frame_size: FrameSize) -> FloatBox:
        """Clamp a box to the current frame and preserve a minimum size."""
        frame_width, frame_height = frame_size
        x1, y1, x2, y2 = box

        x1 = max(0.0, min(x1, float(frame_width - 1)))
        y1 = max(0.0, min(y1, float(frame_height - 1)))
        x2 = max(x1 + 1.0, min(x2, float(frame_width)))
        y2 = max(y1 + 1.0, min(y2, float(frame_height)))

        return (x1, y1, x2, y2)

    def _box_deviation(self, box_a: FloatBox, box_b: FloatBox) -> float:
        """Compute a normalized deviation score between two boxes."""
        iou_gap = 1.0 - self._intersection_over_union(box_a, box_b)
        center_gap = self._center_distance(box_a, box_b)
        size_gap = self._size_distance(box_a, box_b)
        return max(iou_gap, center_gap, size_gap)

    def _center_distance(self, box_a: FloatBox, box_b: FloatBox) -> float:
        center_a_x = (box_a[0] + box_a[2]) / 2.0
        center_a_y = (box_a[1] + box_a[3]) / 2.0
        center_b_x = (box_b[0] + box_b[2]) / 2.0
        center_b_y = (box_b[1] + box_b[3]) / 2.0

        width = max(1.0, max(box_a[2] - box_a[0], box_b[2] - box_b[0]))
        height = max(1.0, max(box_a[3] - box_a[1], box_b[3] - box_b[1]))
        diagonal = max(1.0, hypot(width, height))
        return hypot(center_a_x - center_b_x, center_a_y - center_b_y) / diagonal

    def _size_distance(self, box_a: FloatBox, box_b: FloatBox) -> float:
        width_a = max(1.0, box_a[2] - box_a[0])
        height_a = max(1.0, box_a[3] - box_a[1])
        width_b = max(1.0, box_b[2] - box_b[0])
        height_b = max(1.0, box_b[3] - box_b[1])

        width_gap = abs(width_a - width_b) / max(width_a, width_b)
        height_gap = abs(height_a - height_b) / max(height_a, height_b)
        return max(width_gap, height_gap)

    def _intersection_over_union(self, box_a: FloatBox, box_b: FloatBox) -> float:
        x1 = max(box_a[0], box_b[0])
        y1 = max(box_a[1], box_b[1])
        x2 = min(box_a[2], box_b[2])
        y2 = min(box_a[3], box_b[3])

        intersection_width = max(0.0, x2 - x1)
        intersection_height = max(0.0, y2 - y1)
        intersection_area = intersection_width * intersection_height

        area_a = self._area(box_a)
        area_b = self._area(box_b)
        union_area = max(1.0, area_a + area_b - intersection_area)
        return intersection_area / union_area

    def _area(self, box: FrameBox | FloatBox) -> float:
        return max(1.0, (box[2] - box[0]) * (box[3] - box[1]))

    def _clamp01(self, value: float) -> float:
        return max(0.0, min(1.0, value))
