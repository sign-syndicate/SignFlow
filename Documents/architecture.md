# SignFlow Architecture

This build centers on a floating assistive orb, a full-screen ROI selector, and a tray process shell.

## Current Build

The runtime is intentionally constrained:

- `Code/main.py` starts the tray controller and orb.
- `Code/core/config.py` holds the application name, debug flag, and startup theme choice.
- `Code/core/config.py` also holds the orb magnetic-effect toggle, which is currently disabled by default.
- `Code/core/theme.py` defines static `APPLE` and `DARK` themes (with `HACKER` legacy alias support).
- `Code/ui/orb.py` renders and animates the floating orb.
- `Code/ui/selector.py` handles full-screen ROI rendering, mouse/key interaction, and confirmation timing.
- `Code/ui/tray.py` creates a minimalist tray icon and Exit action.

`Code/main.py` also keeps a persistent `RoiSelectorOverlay` instance and primes it once on startup to reduce first-entry transition hitching.

## State Model

The ROI subsystem currently uses:

- `idle`
- `selecting`
- `confirming_roi`

The orb keeps its own interaction state (hover, drag, dock hidden/visible) independently.

## Notes

- Theme selection is resolved once at startup.
- The orb uses custom painting and lightweight animations only.
- Edge attach distance is single-source and stable across startup, snap, and reveal paths.
- Idle handling docks the orb partially into the active edge, with region-aware reveal behavior that still responds to cursor proximity even when magnetic pull is disabled.
- Hidden-state translucency is animated in sync with docking movement.
- Cursor-driven magnetic offset is feature-flagged off by default; only the positional pull is disabled, not the proximity-triggered reveal or hover/scale rendering.
- Border animation uses uniformly colored moving segments for a balanced ring.
- ROI overlay supports animated entry/exit, drag selection, 3-second confirmation, and immediate keyboard confirmation (Enter/Space).
- ROI cancel operations (ESC/right-click/non-drag click) route through animated fade-out rather than abrupt close.
- ROI overlay is persistent across activations and state is cleared on each `start()` call so prior selections do not carry over.
- The tray menu intentionally exposes Exit and nothing else.
