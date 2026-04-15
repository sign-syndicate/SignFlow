# SignFlow Architecture

SignFlow is organized around a single-process PyQt event loop with three UI surfaces:

- Floating orb (interaction anchor)
- ROI selector overlay (capture flow)
- Morph panel (orb expansion response)

## Module Responsibilities

- [Code/main.py](Code/main.py): application bootstrap, object wiring, overlay lifecycle warm-up
- [Code/core/config.py](Code/core/config.py): runtime config dataclass
- [Code/core/constants.py](Code/core/constants.py): centralized shared defaults/tokens for states, timings, and dimensions
- [Code/core/theme.py](Code/core/theme.py): static theme catalog and color helpers
- [Code/core/state_manager.py](Code/core/state_manager.py): generic state signal helper
- [Code/ui/orb.py](Code/ui/orb.py): floating orb rendering, dock behavior, morph orchestration
- [Code/ui/panel.py](Code/ui/panel.py): panel content and edge-aware internal layout
- [Code/ui/selector.py](Code/ui/selector.py): fullscreen ROI selection and confirmation state machine
- [Code/ui/tray.py](Code/ui/tray.py): tray icon and context menu

## Centralization Strategy

The refactor moved cross-cutting literals into [Code/core/constants.py](Code/core/constants.py):

- App defaults (name/theme/debug/features)
- Runtime scheduling defaults (next tick)
- Selector states and timing values
- Orb presentation states and edge tokens
- Panel sizing/typography defaults
- Tray icon geometry ratios and size set

This keeps behavior consistent while reducing duplicated literals across modules.

## Runtime Sequence

1. Build QApplication and theme.
2. Build tray and orb.
3. Create one persistent ROI overlay instance.
4. Prime overlay once at startup.
5. User activates orb to enter ROI flow.
6. ROI confirm emits geometry and triggers orb-to-panel morph.
7. Panel close triggers reverse morph and restores orb dock state.

## State Systems

Selector states:

- idle
- selecting
- confirming_roi

Orb presentation states:

- orb
- transition_to_panel
- panel
- transition_to_orb

## Performance and Stability

- ROI first-open hitch is reduced by persistent overlay instance plus startup warm-up.
- Hover/dock behavior is driven by cursor truth in orb updates, reducing stale enter/leave state issues.
- Refactor is structural and constants-driven to preserve product behavior.
