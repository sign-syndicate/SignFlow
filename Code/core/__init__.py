"""Core detection and capture modules."""
from .capture import ScreenCapture
from .detection import PersonDetector
from .roi_stabilizer import ROIStabilizer, ROIStabilizerConfig
from .pipeline import VisionPipeline

__all__ = ["ScreenCapture", "PersonDetector", "ROIStabilizer", "ROIStabilizerConfig", "VisionPipeline"]
