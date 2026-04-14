# SignFlow

Minimal desktop shell built with PyQt5.

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

## What It Does

SignFlow now starts as a static-theme tray app with one floating orb:

- System tray icon with an Exit action only
- Floating orb anchored to a stable edge distance
- Subtle breathing, hover, magnetic, and snap motion
- Idle auto-hide with partial edge docking and smooth reveal
- Hidden-state translucency with animated fade during dock transitions
- Static theme selection at startup only

## Architecture

```
Code/
├── core/
│   ├── config.py         # App constants and static theme choice
│   ├── theme.py          # Theme definitions and resolver
│   └── state_manager.py  # Minimal state holder
├── ui/
│   ├── orb.py            # Floating orb widget
│   └── tray.py           # System tray controller
└── main.py              # PyQt5 entry point

Documents/
└── architecture.md
```

## Current Behavior

1. Launches QApplication.
2. Resolves the configured theme once at startup.
3. Creates a QSystemTrayIcon with only Exit in the menu.
4. Shows a draggable floating orb with stable edge attachment and consistent snap distance.
5. Auto-hides the orb after idle by docking it partially into the attached edge.
6. Reveals the orb immediately when cursor enters the activation region.
7. Keeps opacity and position transitions synchronized during hide/reveal.
8. Keeps the app alive in the tray until Exit.

## License

See the LICENSE file.
