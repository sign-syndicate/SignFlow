# SignFlow Architecture

This document explains the codebase structure and how each part works.

## Directory Structure

```
SignFlow/
├── Code/                    # All application code
│   ├── core/               # Detection and capture logic
│   │   ├── __init__.py
│   │   ├── capture.py      # Screen capture module
│   │   ├── detection.py    # YOLO detection module
│   │   ├── roi_stabilizer.py # ROI smoothing and prediction
│   │   └── pipeline.py     # Main orchestrator
│   ├── config/
│   │   └── roi_stabilizer.json # Runtime tuning file
│   ├── ui/                 # User interface
│   │   ├── __init__.py
│   │   └── overlay.py      # PyQt5 overlay
│   ├── __init__.py
│   └── main.py             # Qt app entry point
├── Documents/              # Documentation
│   └── architecture.md     # This file
├── main.py                 # Root entry point
├── requirements.txt        # Python dependencies
├── LICENSE                 # License
├── .gitignore              # Git ignore
└── README.md               # Quick start guide
```

## Module Breakdown

### Core Modules (`Code/core/`)

#### `capture.py` - ScreenCapture
- **Purpose**: Grab frames from the screen
- **Key Class**: `ScreenCapture`
- **How it works**:
  1. Uses `mss` library for efficient screen capture
  2. Lazy initialization (waits until first read to init mss)
  3. Handles multi-monitor setups
  4. Returns frames as BGR numpy arrays (OpenCV compatible)

**Usage**:
```python
capture = ScreenCapture(monitor_index=1)
frame = capture.read()  # BGR numpy array
origin = capture.origin  # (left, top) for coordinate mapping
```

#### `detection.py` - PersonDetector
- **Purpose**: Detect people using YOLO
- **Key Class**: `PersonDetector`
- **How it works**:
  1. Loads `yolov8n.pt` (nano YOLO model)
  2. Runs inference on frame
  3. Filters for COCO class 0 (person only)
  4. Returns boxes as (x1, y1, x2, y2, confidence)

**Usage**:
```python
detector = PersonDetector(model_path="models/yolov8n.pt")
boxes = detector.detect_with_scores(frame, conf=0.35)
# Returns: [(x1, y1, x2, y2, conf), ...]
```

#### `pipeline.py` - VisionPipeline
- **Purpose**: Orchestrate capture + detection + stabilization
- **Key Class**: `VisionPipeline`
- **How it works**:
  1. Captures frame via `ScreenCapture`
  2. Runs detection via `PersonDetector`
  3. Stabilizes detections using `ROIStabilizer`
  4. Maintains one stabilized track per person when possible
  5. Converts raw and stabilized box coordinates to screen space
  6. Returns payload dict for rendering and downstream consumption

**Usage**:
```python
pipeline = VisionPipeline(model_path="models/yolov8n.pt")
payload = pipeline.process_once()
# Returns raw and stabilized streams plus active ROI metadata for all tracked people
```

#### `roi_stabilizer.py` - ROIStabilizer
- **Purpose**: Maintain stable ROIs from noisy detections, one track per person
- **Key Classes**: `ROIStabilizer`, `ROIStabilizerConfig`
- **How it works**:
  1. Greedily matches detections to existing tracks by overlap and position
  2. Applies padding and a configurable upward bias per track
  3. Smooths motion with deadband and threshold-based realignment
  4. Predicts through dropouts with a simple velocity model

**Usage**:
```python
stabilizer = ROIStabilizer()
stable_roi = stabilizer.update(detections, frame_size=(1920, 1080))
active_roi = stabilizer.get_active_roi()
```

### UI Modules (`Code/ui/`)

#### `overlay.py` - DetectionOverlay
- **Purpose**: Draw raw and stabilized detections on transparent overlay
- **Key Class**: `DetectionOverlay(QWidget)`
- **How it works**:
  1. Creates frameless, transparent, click-through window
  2. Stays on top of all other windows
  3. Receives payloads with raw and stabilized box streams
  4. Draws raw detections in purple when debug mode is enabled
  5. Draws stabilized boxes in green for the active overlay

**Usage**:
```python
overlay = DetectionOverlay()
overlay.show()

# In a loop:
payload = pipeline.process_once()
overlay.update_payload(payload)
```

### Entry Point (`Code/main.py`)

- **Purpose**: Qt application setup and event loop
- **Key Components**:
  - `PipelineWorker`: QThread that runs pipeline in background
  - `main()`: Creates Qt app, setups UI, connects signals/slots
  - System tray integration

**Flow**:
1. Create QApplication
2. Create DetectionOverlay (renders detections)
3. Create system tray (minimize/exit)
4. Create PipelineWorker thread (runs pipeline)
5. Connect pipeline.result_ready → overlay.update_payload
6. Start Qt event loop

## Data Flow

```
Screen
  ↓
ScreenCapture.read() → BGR frame
  ↓
PersonDetector.detect_with_scores() → boxes in frame-space
  ↓
ROIStabilizer.update() → stable active ROI in frame-space
   ↓
VisionPipeline.process_once() → convert raw and stabilized boxes to screen-space
  ↓
payload = {"raw_boxes": [...], "stable_boxes": [...], "active_roi": ...}
  ↓
overlay.update_payload(payload)
  ↓
DetectionOverlay.paintEvent() → draw stabilized ROI, and raw boxes in debug mode
  ↓
User sees a stable green ROI on overlay
```

## Coordinate Spaces

There are two coordinate spaces:

1. **Frame Space**: (0, 0) is top-left of captured area
   - YOLO returns boxes in this space
   - E.g., frame is 1920x1080, box is (100, 100, 200, 200)

2. **Screen Space**: (0, 0) is top-left of entire screen
   - Overlay lives in this space
   - Accounts for multi-monitor offsets
   - Conversion: `screen_x = frame_x + capture_origin_x`

Example with multi-monitor:
- Monitor 1: 1920x1080, origin (0, 0)
- Monitor 2: 1920x1080, origin (1920, 0)
- If capturing from Monitor 2:
  - Frame box: (100, 100, 200, 200)
  - Screen box: (2020, 100, 2120, 200)

## Performance

- **Capture**: ~1-2ms per frame (mss is fast)
- **Detection**: ~50-100ms per frame (YOLO nano, CPU)
- **Render**: <1ms per frame (PyQt)
- **Total**: ~50-100ms, or ~10-20 FPS

To improve:
- Use GPU for detection: `device="cuda"`
- Skip frames: only run detection every Nth frame
- Use `yolov8s` instead of `yolov8n` (faster but heavier)

## Extending the Code

### Adding a new detector:

Create `Code/core/my_detector.py`:
```python
class MyDetector:
    def detect(self, frame):
        # Your detection logic
        return [(x1, y1, x2, y2, conf), ...]
```

Update `Code/core/pipeline.py` to use it:
```python
from .my_detector import MyDetector

class VisionPipeline:
    def __init__(self, ...):
        self._detector = MyDetector()
```

### Adding new rendering:

Create `Code/ui/my_renderer.py`:
```python
class MyRenderer(QWidget):
    def update_payload(self, payload):
        self._data = payload
        self.update()
    
    def paintEvent(self, event):
        # Your rendering logic
        pass
```

Update `Code/main.py` to use it.

### Adding a new data source:

Create `Code/core/my_source.py`:
```python
class MySource:
    def read(self):
        # Return frame as BGR numpy array
        return frame
```

Use it instead of ScreenCapture in pipeline.

## Testing

Each module is independent and testable:

```python
# Test capture
capture = ScreenCapture()
frame = capture.read()
assert frame is not None

# Test detection
detector = PersonDetector("models/yolov8n.pt")
boxes = detector.detect_with_scores(frame)
assert isinstance(boxes, list)

# Test pipeline
pipeline = VisionPipeline("models/yolov8n.pt")
payload = pipeline.process_once()
assert "boxes" in payload
```

## Dependencies

See `requirements.txt`:
- `torch`: PyTorch (for YOLO)
- `torchvision`: Computer vision utilities
- `ultralytics`: YOLO library
- `opencv-python`: Image processing
- `mss`: Fast screen capture
- `PyQt5`: GUI framework

## License

See LICENSE file for details.
