# SignFlow

Real-time person detection overlay using YOLO and PyQt5, with a stateful ROI stabilizer for smoother tracking.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

The overlay will appear on your screen and detect everyone visible. Each person gets a stable green box that only realigns when the YOLO detection changes enough to matter. Raw detections can be shown in purple when debug visualization is enabled.

## Architecture

```
Code/
├── core/
│   ├── capture.py      # Screen capture (mss)
│   ├── detection.py    # YOLO person detection
│   ├── roi_stabilizer.py # Stateful ROI smoothing and prediction
│   └── pipeline.py     # Orchestrates capture + detection + stabilization
├── config/
│   └── roi_stabilizer.json # Runtime tuning values for ROI behavior
├── ui/
│   └── overlay.py      # PyQt5 transparent overlay
└── main.py             # Entry point + Qt event loop

Documents/
└── architecture.md     # Detailed architecture docs
```

## How It Works

1. **Capture**: Grabs frames from screen using `mss`
2. **Detect**: Runs YOLO person detection on each frame
3. **Stabilize**: Smooths detections into persistent per-person ROIs
4. **Render**: Draws stabilized boxes on transparent overlay in real-time

That's it. Simple, fast, extensible.

## Folder Guide

- **Code/** - All application logic (pure Python)
- **Documents/** - Documentation and architecture notes
- **models/** - YOLO model weights (auto-downloaded)
- **config/** - Runtime ROI stabilization config

## Development

For beginners:
- Start with `Code/main.py` - the entry point
- Then look at `Code/core/pipeline.py` - the main logic
- Each module is <100 lines and well-documented
- `Code/config/roi_stabilizer.json` controls stabilization strength, padding, prediction, and debug output

To extend:
- Add new detection modules in `Code/core/`
- Add new UI components in `Code/ui/`
- Update the pipeline to use them

## License

See LICENSE file.
