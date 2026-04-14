import sys

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
    orb = FloatingOrb(theme, debug=config.debug)
    selector = {"widget": None}

    def _on_selection_cancelled():
        if config.debug:
            print("selection cancelled")
        orb.setForcedHiddenMode(False)
        selector["widget"] = None

    def _on_roi_confirmed(x: int, y: int, w: int, h: int):
        if config.debug:
            print(f"stored roi: {x}, {y}, {w}, {h}")
        orb.setForcedHiddenMode(False)
        selector["widget"] = None

    def _open_selector_overlay():
        active_selector = selector["widget"]
        if active_selector is not None and active_selector.isVisible():
            return

        orb.show()
        orb.raise_()
        orb.setForcedHiddenMode(True)
        overlay = RoiSelectorOverlay(theme, debug=config.debug)
        overlay.roi_confirmed.connect(_on_roi_confirmed)
        overlay.selection_cancelled.connect(_on_selection_cancelled)
        overlay.release_orb_lock.connect(lambda: orb.setForcedHiddenMode(False))
        overlay.destroyed.connect(lambda *_: selector.__setitem__("widget", None))
        overlay.destroyed.connect(lambda *_: orb.setForcedHiddenMode(False))
        selector["widget"] = overlay
        overlay.start()

    orb.activated.connect(_open_selector_overlay)
    orb.show()

    app._signflow_orb = orb
    app._signflow_tray = tray
    app._signflow_selector = selector

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
