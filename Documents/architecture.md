# SignFlow Architecture

This build centers on a single floating assistive orb plus a tray process shell.

## Current Build

The runtime is intentionally constrained:

- `Code/main.py` starts the tray controller and orb.
- `Code/core/config.py` holds the application name, debug flag, and startup theme choice.
- `Code/core/theme.py` defines the static Apple and Hacker themes.
- `Code/ui/orb.py` renders and animates the floating orb.
- `Code/ui/tray.py` creates the tray icon and Exit action.

## State Model

- Current state baseline: `idle`

No higher-level workflow state machine is active.

## Notes

- Theme selection is resolved once at startup.
- The orb uses custom painting and lightweight animations only.
- The tray menu intentionally exposes Exit and nothing else.
