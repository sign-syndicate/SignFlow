# SignFlow

Minimal desktop shell built with PyQt5.

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

## What It Does

SignFlow starts as a static-theme tray app with one floating orb and a full-screen ROI selector:

- System tray icon with an Exit action only
- Floating orb anchored to a stable edge distance
- Subtle breathing, hover, magnetic, and snap motion
- Idle auto-hide with partial edge docking and smooth reveal
- Hidden-state translucency with animated fade during dock transitions
- Full-screen ROI selection overlay with animated confirmation
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
│   ├── selector.py       # Full-screen ROI selector overlay
│   └── tray.py           # System tray controller
└── main.py              # PyQt5 entry point

Documents/
└── architecture.md
```

## Current Behavior

1. Launches QApplication.
2. Resolves the configured theme once at startup.
3. Creates a QSystemTrayIcon with only Exit in the menu.
4. Creates and primes the ROI selector once (warm-up) so first-entry transition is smoother.
5. Shows a draggable floating orb with stable edge attachment and consistent snap distance.
6. Auto-hides the orb after idle by docking it partially into the attached edge.
7. Reveals the orb when cursor enters the activation region, even when magnetic pull is disabled.
8. Clicking the orb opens ROI mode with a dimmed full-screen overlay and a fade-in transition.
9. Dragging defines a selection rectangle; release starts a 3-second confirmation animation.
10. Enter/Space can skip the confirmation timer and finalize immediately.
11. Cancel paths (ESC, right-click, or non-drag click in ROI) use animated fade-out and emit cancellation.
12. Confirm path emits ROI coordinates and exits with the same polished fade-out timing.
13. Keeps the app alive in the tray until Exit.

The orb's cursor-driven magnetic motion is controlled by `Code/core/config.py` via `ORB_MAGNETIC_EFFECT_ENABLED`, and is currently disabled. Hover, click, scale, and cursor-proximity reveal still remain active.

## ROI Controls

- Left click + drag: select region.
- Release after drag: begin confirmation timer.
- Enter or Space: confirm immediately (skip timer).
- ESC: cancel selection.
- Right click: cancel selection.
- Left click without a valid drag: cancel and exit ROI.

## License

See the LICENSE file.
