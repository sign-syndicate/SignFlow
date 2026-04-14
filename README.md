# SignFlow

Minimal desktop baseline built with PyQt5.

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

## What It Does

The current project is a clean restart baseline.

It runs as a system tray application with a minimal menu:

- Start (no-op, prints to console)
- Exit (quits the app)

No floating windows, overlays, or animation systems are included in this reset.

## Architecture

```
Code/
├── core/
│   ├── config.py         # Minimal runtime config
│   └── state_manager.py  # Minimal state holder (idle baseline)
└── main.py              # PyQt5 entry point

Documents/
└── architecture.md
```

## Current Behavior

1. Launches QApplication.
2. Creates a QSystemTrayIcon.
3. Provides Start and Exit menu actions.
4. Keeps app alive in the tray until Exit.

## License

See the LICENSE file.
