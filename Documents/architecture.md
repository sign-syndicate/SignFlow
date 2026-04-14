# SignFlow Architecture

This repository is currently in a hard-reset baseline state.

## Current Build

The runtime is intentionally minimal:

- `Code/main.py` starts a tray-only application.
- `Code/core/config.py` contains minimal app configuration.
- `Code/core/state_manager.py` contains minimal state handling.

## State Model

- Current state baseline: `idle`

No UI transition graph is active in this reset.

## Notes

- All previous UI modules under `Code/ui/` were removed as part of hard reset.
- This baseline exists to support incremental rebuild from a stable tray runtime.
