# SignFlow Architecture

This build centers on a single floating assistive orb plus a tray process shell.

## Current Build

The runtime is intentionally constrained:

- `Code/main.py` starts the tray controller and orb.
- `Code/core/config.py` holds the application name, debug flag, and startup theme choice.
- `Code/core/theme.py` defines static `APPLE` and `DARK` themes (with `HACKER` legacy alias support).
- `Code/ui/orb.py` renders and animates the floating orb.
- `Code/ui/tray.py` creates a minimalist tray icon and Exit action.

## State Model

- Current state baseline: `idle`

No higher-level workflow state machine is active.

## Notes

- Theme selection is resolved once at startup.
- The orb uses custom painting and lightweight animations only.
- Edge attach distance is single-source and stable across startup, snap, and reveal paths.
- Idle handling docks the orb partially into the active edge, with region-aware reveal behavior.
- Hidden-state translucency is animated in sync with docking movement.
- Border animation uses uniformly colored moving segments for a balanced ring.
- The tray menu intentionally exposes Exit and nothing else.
