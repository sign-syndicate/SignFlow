# SignFlow

SignFlow is a PyQt5 desktop shell with a floating orb, ROI capture overlay, and panel morph interaction.

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

## Product Surface

- Floating orb with dock/snap, hover motion, and idle edge hide/reveal
- ROI selector overlay with instant fade-in, confirmation animation, and cancel/confirm paths
- Orb to panel morph with reversible close, caption placeholder, and edge-aware layout
- System tray process shell with Exit action

## Refactor Highlights

- Centralized shared constants in [Code/core/constants.py](Code/core/constants.py)
- Runtime config stays in [Code/core/config.py](Code/core/config.py), sourced from shared defaults
- Panel UI extracted into [Code/ui/panel.py](Code/ui/panel.py)
- Selector and tray now consume shared tokens (timings, states, sizes) instead of scattered literals
- Overlay warm-up persists and is pre-primed at startup for first-open responsiveness

## Project Layout

```
Code/
├── core/
│   ├── __init__.py
│   ├── config.py
│   ├── constants.py
│   ├── state_manager.py
│   └── theme.py
├── ui/
│   ├── __init__.py
│   ├── orb.py
│   ├── panel.py
│   ├── selector.py
│   └── tray.py
└── main.py

Documents/
└── architecture.md
```

## Runtime Flow

1. Start QApplication and resolve theme.
2. Build tray icon/controller.
3. Build floating orb.
4. Create one persistent ROI overlay instance.
5. Prime overlay once on startup to avoid first-open hitch.
6. On orb activation, open overlay with immediate fade-in.
7. On ROI confirm, emit coordinates and transition orb to panel mode.
8. On panel close, reverse morph back to orb and restore dock behavior.

## ROI Controls

- Left drag: draw selection rectangle
- Release: start confirmation countdown
- Enter/Space: immediate confirm
- Escape or right click: cancel

## Stability Notes

- State names and timing values are centralized and reused across modules.
- Widget creation paths avoid repeated heavyweight overlay construction.
- Behavior-preserving refactor focused on structure and maintainability, not feature changes.

## License

See [LICENSE](LICENSE).
