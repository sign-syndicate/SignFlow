"""Vision pipeline - orchestrates capture and detection."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .capture import ScreenCapture
from .detection import PersonDetector
from .roi_stabilizer import ROIStabilizer, ROIStabilizerConfig

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
        roi_config_path: str | Path | None = None,
    ) -> None:
        """
        Initialize the vision pipeline.
        
        Args:
            model_path: Path to yolov8n.pt.
            monitor_index: Which monitor to capture (1-indexed).
            conf_threshold: YOLO confidence threshold (0-1).
            roi_config_path: Optional JSON config path for ROI stabilization.
        """
        self._capture = ScreenCapture(monitor_index=monitor_index)
        self._detector = PersonDetector(model_path=model_path)
        self._conf = conf_threshold
        self._roi_config = ROIStabilizerConfig.from_file(roi_config_path)
        self._stabilizer = ROIStabilizer(self._roi_config)

    def process_once(self) -> Dict[str, object]:
        """
        Process one frame.
        
        Returns:
            Dictionary containing raw detections, stabilized ROI, and debug flags.
        """
        frame = self._capture.read()
        detections = self._detector.detect_with_scores(frame, conf=self._conf)
        left, top = self._capture.origin
        frame_height, frame_width = frame.shape[:2]

        active_rois = self._stabilizer.update(detections, (frame_width, frame_height))

        # Convert box coordinates from frame-space to screen-space.
        raw_screen_boxes = [
            (x1 + left, y1 + top, x2 + left, y2 + top, conf)
            for x1, y1, x2, y2, conf in detections
        ]

        stable_screen_boxes: List[Box] = [
            (x1 + left, y1 + top, x2 + left, y2 + top, confidence)
            for x1, y1, x2, y2, confidence in active_rois
        ]

        return {
            "raw_boxes": raw_screen_boxes,
            "stable_boxes": stable_screen_boxes,
            "active_rois": active_rois,
            "debug_visualization": self._roi_config.debug_visualization,
            "stabilization_enabled": self._roi_config.enable_roi_stabilization,
            "show_raw_boxes": self._roi_config.show_raw_boxes,
            "show_stable_boxes": self._roi_config.show_stable_boxes,
            "raw_box_rgb": self._roi_config.raw_box_rgb,
            "stable_box_rgb": self._roi_config.stable_box_rgb,
            "focus_mode_enabled": self._roi_config.focus_mode_enabled,
            "focus_dim_alpha": self._roi_config.focus_dim_alpha,
        }

    def get_active_roi(self) -> List[Box]:
        """Expose the current stabilized ROIs for downstream consumers."""
        return self._stabilizer.get_active_rois()
