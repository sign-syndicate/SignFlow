"""SignFlow - Main entry point."""
from __future__ import annotations

import sys
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QAction, QApplication, QMenu, QStyle, QSystemTrayIcon

# Handle imports whether run from root or directly
try:
    from .core import VisionPipeline
    from .ui import DetectionOverlay
except ImportError:
    # Fallback for direct execution
    sys.path.insert(0, str(Path(__file__).parent))
    from core import VisionPipeline
    from ui import DetectionOverlay


class PipelineWorker(QThread):
    """Worker thread that runs the vision pipeline."""

    result_ready = pyqtSignal(object)

    def __init__(self, model_path: Path) -> None:
        super().__init__()
        self._running = False
        self._pipeline = VisionPipeline(
            model_path=model_path,
            monitor_index=1,
            conf_threshold=0.35,
        )

    def run(self) -> None:
        """Main worker loop."""
        self._running = True
        while self._running:
            payload = self._pipeline.process_once()
            self.result_ready.emit(payload)

    def stop(self) -> None:
        """Stop the worker."""
        self._running = False


def main() -> int:
    """Main application entry point."""
    # Setup
    model_path = Path(__file__).parent / "models" / "yolov8n.pt"
    model_path.parent.mkdir(parents=True, exist_ok=True)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Create overlay
    overlay = DetectionOverlay()
    overlay.show()

    # Create system tray
    tray = QSystemTrayIcon()
    tray.setIcon(app.style().standardIcon(QStyle.SP_ComputerIcon))

    menu = QMenu()
    action_show = QAction("Show", menu)
    action_hide = QAction("Hide", menu)
    action_exit = QAction("Exit", menu)

    menu.addAction(action_show)
    menu.addAction(action_hide)
    menu.addSeparator()
    menu.addAction(action_exit)
    tray.setContextMenu(menu)

    # Create worker thread
    worker = PipelineWorker(model_path=model_path)
    worker.result_ready.connect(overlay.update_payload)

    # Connect menu actions
    action_show.triggered.connect(lambda: (overlay.show(), overlay.raise_()))
    action_hide.triggered.connect(overlay.hide)

    def on_exit():
        worker.stop()
        worker.wait(5000)
        tray.hide()
        app.quit()

    action_exit.triggered.connect(on_exit)

    # Tray double-click shows overlay
    tray.activated.connect(
        lambda reason: (overlay.show(), overlay.raise_())
        if reason == QSystemTrayIcon.DoubleClick
        else None
    )

    # Show tray and start
    tray.show()
    tray.showMessage(
        "SignFlow Running",
        "Double-click tray to toggle overlay.",
        QSystemTrayIcon.Information,
        2500,
    )

    worker.start()
    return_code = app.exec_()

    # Cleanup
    if worker.isRunning():
        worker.stop()
        worker.wait(5000)

    return return_code


if __name__ == "__main__":
    sys.exit(main())
