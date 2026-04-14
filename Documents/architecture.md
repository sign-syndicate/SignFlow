# SignFlow Architecture

This rebuild is a minimal UI-only desktop shell for an assistive captioning app.

## Current Build

The application is organized around a small state-driven PyQt5 UI stack:

- `Code/core/config.py` stores shared UI constants and copy.
- `Code/core/state_manager.py` is the single source of truth for UI state, ROI, dock edge, and caption text.
- `Code/ui/orb.py` implements the floating docked orb.
- `Code/ui/panel.py` implements the morphing caption panel.
- `Code/ui/selector.py` implements the dimmed region selection overlay.
- `Code/ui/border.py` renders the animated state border.
- `Code/ui/tray.py` provides the system tray entry points.
- `Code/ui/overlay.py` coordinates widget transitions and state reactions.
- `Code/main.py` launches the Qt application.

## State Flow

1. `idle`
2. `panel_open`
3. `selecting`
4. `active`

The state manager emits changes, and the UI reacts through signals and slots. The widgets never own the source of truth for state.

## Notes

- No ML, MediaPipe, or inference pipeline is included in this layer.
- The tray menu should close the application fully only through Exit.
- The panel close button collapses back to the orb instead of quitting.
