# SignFlow

Minimal assistive desktop UI built with PyQt5.

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

## What It Does

SignFlow presents a floating orb that expands into a clean caption panel, dims the desktop, and lets the user select a region of interest. The current build focuses only on UI behavior and interaction polish.

## Architecture

```
Code/
├── core/
│   ├── config.py        # UI tuning values and shared copy
│   └── state_manager.py  # Single source of truth for UI state
├── ui/
│   ├── border.py         # Animated border rendering helpers
│   ├── orb.py           # Floating docked orb widget
│   ├── panel.py         # Caption panel and morph animation
│   ├── selector.py      # Full-screen region selector overlay
│   ├── tray.py          # System tray controller
│   └── overlay.py       # Top-level UI coordinator
└── main.py              # PyQt5 entry point

Documents/
└── architecture.md
```

## Behavior

1. The orb sits on the screen edge and can be dragged or clicked.
2. Clicking the orb expands it into a rounded caption panel.
3. The desktop dims and the user selects a region.
4. On selection, the app enters an active captioning state.
5. The tray menu provides Open and Exit.

## License

See the LICENSE file.
