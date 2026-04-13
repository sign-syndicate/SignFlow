"""Stateful ROI stabilization and prediction for noisy person detections."""
from __future__ import annotations

from dataclasses import dataclass
from json import JSONDecodeError
import json
from math import hypot
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

# Type hints
Box = Tuple[int, int, int, int, float]
FrameBox = Tuple[int, int, int, int]
FloatBox = Tuple[float, float, float, float]
FrameSize = Tuple[int, int]


@dataclass(frozen=True)
class ROIStabilizerConfig:
    """Runtime tuning values for the ROI stabilizer."""

    enable_roi_stabilization: bool = True
    responsiveness: float = 0.20
    realignment_threshold: float = 0.16
    instant_realignment: bool = True
    padding_scale: float = 0.10
    padding_pixels: int = 6
    positional_bias_x: float = 0.0
    positional_bias_y: float = -0.03
    prediction_enable: bool = True
    debug_visualization: bool = False
    yolo_box_approximation: bool = True
    iou_weight: float = 0.7
    confidence_weight: float = 0.3
    velocity_decay: float = 0.88
    dropout_confidence_decay: float = 0.92
    association_iou_threshold: float = 0.18
    association_center_threshold: float = 0.55
    association_distance_threshold: float = 0.62
    new_track_iou_threshold: float = 0.08
    max_missed_frames: int = 12
    min_track_confidence: float = 0.10
    show_raw_boxes: bool = True
    show_stable_boxes: bool = True
    raw_box_rgb: Tuple[int, int, int] = (0, 255, 120)
    stable_box_rgb: Tuple[int, int, int] = (164, 78, 255)
    focus_mode_enabled: bool = False
    focus_dim_alpha: int = 96

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

    track_id: int
    box: FloatBox
    confidence: float
    velocity: FloatBox
    missed_frames: int = 0


@dataclass(frozen=True)
class StableROI:
    """Public stable ROI returned to the overlay and downstream consumers."""

    track_id: int
    box: Box
    confidence: float


class ROIStabilizer:
    """Maintain a stable, padded ROI from noisy per-frame detections."""

    def __init__(self, config: ROIStabilizerConfig | None = None) -> None:
        self._config = config or ROIStabilizerConfig()
        self._tracks: Dict[int, _TrackState] = {}
        self._next_track_id = 1
        self._last_frame_size: Optional[FrameSize] = None

    @property
    def config(self) -> ROIStabilizerConfig:
        """Return the active runtime configuration."""
        return self._config

    def reset(self) -> None:
        """Clear the internal ROI state."""
        self._tracks.clear()
        self._next_track_id = 1
        self._last_frame_size = None

    def get_active_rois(self) -> List[Box]:
        """Return the current stabilized ROIs in frame coordinates."""
        if self._last_frame_size is None:
            return []
        return [self._track_to_box(track, self._last_frame_size) for track in self._sorted_tracks()]

    def get_active_roi(self) -> List[Box]:
        """Compatibility alias for callers that still expect the singular name."""
        return self.get_active_rois()

    def update(self, detections: Sequence[Box], frame_size: FrameSize) -> List[Box]:
        """Update the stabilizer with a new set of detections for the current frame."""
        self._last_frame_size = frame_size
        if not self._config.enable_roi_stabilization:
            return self._update_without_stabilization(detections, frame_size)

        detections = [detection for detection in detections if detection[4] >= self._config.min_track_confidence]
        raw_detections = [tuple(float(value) for value in detection[:4]) + (float(detection[4]),) for detection in detections]

        assignments, unmatched_tracks, unmatched_detections = self._associate(raw_detections)

        for track_id, detection_index in assignments.items():
            track = self._tracks[track_id]
            detection = raw_detections[detection_index]
            self._tracks[track_id] = self._update_track(track, detection, frame_size)

        for track_id in unmatched_tracks:
            track = self._tracks[track_id]
            self._tracks[track_id] = self._predict_track(track, frame_size)

        for detection_index in unmatched_detections:
            if self._should_spawn_track(raw_detections[detection_index]):
                self._spawn_track(raw_detections[detection_index], frame_size)

        self._prune_tracks()
        return self.get_active_rois()

    def _update_without_stabilization(self, detections: Sequence[Box], frame_size: FrameSize) -> List[Box]:
        """Bypass smoothing while still applying padding and consistency checks."""
        self._tracks.clear()
        for detection in detections:
            if detection[4] < self._config.min_track_confidence:
                continue
            self._spawn_track(tuple(float(value) for value in detection[:4]) + (float(detection[4]),), frame_size)
        return self.get_active_rois()

    def _associate(self, detections: Sequence[Tuple[float, float, float, float, float]]) -> Tuple[Dict[int, int], List[int], List[int]]:
        """Greedily associate detections to existing tracks using overlap and proximity."""
        if not self._tracks:
            return {}, [], list(range(len(detections)))

        candidates: List[Tuple[float, int, int]] = []
        for track_id, track in self._tracks.items():
            predicted_box = self._predict_box(track, None)
            for detection_index, detection in enumerate(detections):
                detection_box = detection[:4]
                score = self._association_score(predicted_box, detection_box, detection[4])
                candidates.append((score, track_id, detection_index))

        assignments: Dict[int, int] = {}
        used_tracks: set[int] = set()
        used_detections: set[int] = set()

        for score, track_id, detection_index in sorted(candidates, reverse=True):
            if track_id in used_tracks or detection_index in used_detections:
                continue
            track = self._tracks[track_id]
            detection_box = detections[detection_index][:4]
            iou_score = self._intersection_over_union(track.box, detection_box)
            center_distance = self._center_distance(track.box, detection_box)
            if iou_score < self._config.association_iou_threshold and center_distance > self._config.association_center_threshold:
                continue
            assignments[track_id] = detection_index
            used_tracks.add(track_id)
            used_detections.add(detection_index)

        unmatched_tracks = [track_id for track_id in self._tracks if track_id not in used_tracks]
        unmatched_detections = [index for index in range(len(detections)) if index not in used_detections]
        return assignments, unmatched_tracks, unmatched_detections

    def _association_score(self, track_box: FloatBox, detection_box: FloatBox, confidence: float) -> float:
        iou_score = self._intersection_over_union(track_box, detection_box)
        center_distance = self._center_distance(track_box, detection_box)
        size_distance = self._size_distance(track_box, detection_box)
        return (iou_score * self._config.iou_weight) + (confidence * self._config.confidence_weight) - (center_distance * 0.14) - (size_distance * 0.10)

    def _spawn_track(self, detection: Tuple[float, float, float, float, float], frame_size: FrameSize) -> None:
        box = self._clamp_box(detection[:4], frame_size)
        confidence = float(detection[4])
        track = _TrackState(
            track_id=self._next_track_id,
            box=box,
            confidence=confidence,
            velocity=(0.0, 0.0, 0.0, 0.0),
            missed_frames=0,
        )
        self._tracks[self._next_track_id] = track
        self._next_track_id += 1

    def _should_spawn_track(self, detection: Tuple[float, float, float, float, float]) -> bool:
        """Avoid spawning a duplicate track for detections that still overlap an active track."""
        if not self._tracks:
            return True

        detection_box = detection[:4]
        for track in self._tracks.values():
            iou_score = self._intersection_over_union(track.box, detection_box)
            center_distance = self._center_distance(track.box, detection_box)
            if iou_score >= self._config.new_track_iou_threshold or center_distance <= self._config.association_distance_threshold:
                return False

        return True

    def _update_track(self, track: _TrackState, detection: Tuple[float, float, float, float, float], frame_size: FrameSize) -> _TrackState:
        target_box = self._clamp_box(detection[:4], frame_size)
        alpha = self._resolve_blend_factor(track.box, target_box)

        if self._should_hold_box(track.box, target_box):
            blended_box = track.box
        else:
            blended_box = self._blend_boxes(track.box, target_box, alpha)

        clamped_box = self._clamp_box(blended_box, frame_size)
        velocity = tuple(
            (clamped_box[index] - track.box[index]) + (track.velocity[index] * self._config.velocity_decay)
            for index in range(4)
        )
        confidence = (track.confidence * (1.0 - alpha)) + (float(detection[4]) * alpha)
        return _TrackState(
            track_id=track.track_id,
            box=clamped_box,
            confidence=confidence,
            velocity=velocity,
            missed_frames=0,
        )

    def _predict_track(self, track: _TrackState, frame_size: FrameSize) -> _TrackState:
        if not self._config.prediction_enable:
            return _TrackState(
                track_id=track.track_id,
                box=track.box,
                confidence=track.confidence,
                velocity=tuple(component * self._config.velocity_decay for component in track.velocity),
                missed_frames=track.missed_frames + 1,
            )

        predicted_box = self._predict_box(track, frame_size)
        confidence = track.confidence * self._config.dropout_confidence_decay
        velocity = tuple(component * self._config.velocity_decay for component in track.velocity)
        return _TrackState(
            track_id=track.track_id,
            box=predicted_box,
            confidence=confidence,
            velocity=velocity,
            missed_frames=track.missed_frames + 1,
        )

    def _predict_box(self, track: _TrackState, frame_size: FrameSize | None) -> FloatBox:
        predicted = tuple(track.box[index] + track.velocity[index] for index in range(4))
        if frame_size is None:
            return predicted
        return self._clamp_box(predicted, frame_size)

    def _should_hold_box(self, previous_box: FloatBox, target_box: FloatBox) -> bool:
        deviation = self._box_deviation(previous_box, target_box)
        return deviation < self._config.realignment_threshold * 0.45

    def _resolve_blend_factor(self, previous_box: FloatBox, target_box: FloatBox) -> float:
        deviation = self._box_deviation(previous_box, target_box)
        base = self._clamp01(self._config.responsiveness)

        if deviation >= self._config.realignment_threshold:
            if self._config.instant_realignment:
                return 1.0
            return min(0.9, max(base, 0.55))

        if deviation <= self._config.realignment_threshold * 0.25:
            return 0.0

        if self._config.yolo_box_approximation:
            return max(0.05, base * 0.35)

        return max(0.08, base * 0.55)

    def _expand_and_bias(self, box: FrameBox, frame_size: FrameSize) -> FloatBox:
        """Apply padding and a slight positional bias for the visual ROI output only."""
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

    def _track_to_box(self, track: _TrackState, frame_size: FrameSize) -> Box:
        x1, y1, x2, y2 = self._expand_and_bias(track.box, frame_size)
        return (int(round(x1)), int(round(y1)), int(round(x2)), int(round(y2)), float(track.confidence))

    def _sorted_tracks(self) -> List[_TrackState]:
        return sorted(self._tracks.values(), key=lambda track: (-track.confidence, track.track_id))

    def _prune_tracks(self) -> None:
        to_delete = [track_id for track_id, track in self._tracks.items() if track.missed_frames > self._config.max_missed_frames or track.confidence < self._config.min_track_confidence * 0.4]
        for track_id in to_delete:
            self._tracks.pop(track_id, None)

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
