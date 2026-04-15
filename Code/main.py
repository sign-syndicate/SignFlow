import sys

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication

from .core.config import AppConfig
from .core.theme import get_theme
from .ui.orb import FloatingOrb
from .ui.selector import RoiSelectorOverlay
from .ui.tray import SystemTrayController


def main():
    config = AppConfig()
    app = QApplication(sys.argv)
    app.setApplicationName(config.app_name)
    app.setQuitOnLastWindowClosed(False)

    theme = get_theme(config.current_theme)
    if config.debug:
        print(f"theme: {theme.name}")

    tray = SystemTrayController(app, theme)
    orb = FloatingOrb(theme, debug=config.debug, magnetic_effect_enabled=config.orb_magnetic_effect_enabled)
    selector = {"widget": None}

    def _on_selection_cancelled():
        if config.debug:
            print("selection cancelled")

    def _on_roi_confirmed(x: int, y: int, w: int, h: int):
        if config.debug:
            print(f"stored roi: {x}, {y}, {w}, {h}")
        orb.on_roi_confirmed(x, y, w, h)

    def _get_or_create_overlay():
        active = selector["widget"]
        if active is not None:
            return active

        overlay = RoiSelectorOverlay(theme, debug=config.debug)
        overlay.roi_confirmed.connect(_on_roi_confirmed)
        overlay.selection_cancelled.connect(_on_selection_cancelled)
        overlay.destroyed.connect(lambda *_: selector.__setitem__("widget", None))
        selector["widget"] = overlay
        return overlay

    def _open_selector_overlay():
        active_selector = selector["widget"]
        if active_selector is not None and active_selector.isVisible():
            return

        overlay = _get_or_create_overlay()
        QTimer.singleShot(0, overlay.start)

    orb.activated.connect(_open_selector_overlay)
    orb.show()

    # Pre-warm the fullscreen translucent ROI overlay once so first open is instant.
    warm_overlay = _get_or_create_overlay()
    QTimer.singleShot(0, warm_overlay.prime)

    app._signflow_orb = orb
    app._signflow_tray = tray
    app._signflow_selector = selector

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
