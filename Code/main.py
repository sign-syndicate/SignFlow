"""SignFlow - Main entry point."""
from __future__ import annotations

import ctypes
import sys
import threading
import time
from ctypes import wintypes
from pathlib import Path

from PyQt5.QtCore import QObject, Qt, QThread, pyqtSignal
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

# Windows API Constants
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
VK_S = 0x53
HOTKEY_ID = 1


class HotKeyBridge(QObject):
    """Bridges hotkey events from a background thread to the Qt UI thread."""

    triggered = pyqtSignal()


class HotKeyListener:
    """Listen for hotkey in background thread."""

    def __init__(self, callback):
        self._callback = callback
        self._thread = None
        self._running = False
        self._thread_id = None

    def start(self):
        """Start listening for hotkey."""
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        print("Hotkey listener thread started")

    def stop(self):
        """Stop listening."""
        self._running = False
        if self._thread_id is not None:
            # Unblock GetMessageW so the thread can exit promptly.
            ctypes.windll.user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)  # WM_QUIT
        if self._thread:
            self._thread.join(timeout=3)

    def _listen_loop(self):
        """Background thread that waits for hotkey message."""
        try:
            self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
            # Register hotkey
            result = ctypes.windll.user32.RegisterHotKey(
                None,
                HOTKEY_ID,
                MOD_CONTROL | MOD_ALT | MOD_NOREPEAT,
                VK_S,
            )
            if not result:
                print("Failed to register Ctrl+Alt+S hotkey")
                return
            print("Ctrl+Alt+S hotkey registered")

            # Create a message queue to receive hotkey events
            msg = wintypes.MSG()
            while self._running:
                # Pump messages - GetMessage blocks until a message arrives
                res = ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if res == 0:  # WM_QUIT
                    break
                if res < 0:
                    break

                if msg.message == WM_HOTKEY:
                    self._callback()
        except Exception as e:
            print(f"Hotkey listener error: {e}")
        finally:
            try:
                ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_ID)
            except Exception:
                pass


class PipelineWorker(QThread):
    """Worker thread that runs the vision pipeline."""

    result_ready = pyqtSignal(object)

    def __init__(self, model_path: Path, roi_config_path: Path) -> None:
        super().__init__()
        self._running = False
        self._pipeline = VisionPipeline(
            model_path=model_path,
            monitor_index=1,
            conf_threshold=0.35,
            roi_config_path=roi_config_path,
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
    roi_config_path = Path(__file__).parent / "config" / "roi_stabilizer.json"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    roi_config_path.parent.mkdir(parents=True, exist_ok=True)

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
    worker = PipelineWorker(model_path=model_path, roi_config_path=roi_config_path)
    worker.result_ready.connect(overlay.update_payload)

    hotkey_bridge = HotKeyBridge()

    # Setup hotkey toggle (Ctrl+Alt+S)
    last_toggle = 0.0

    def toggle_overlay():
        nonlocal last_toggle
        now = time.monotonic()
        # Guard against pathological burst input while preserving responsiveness.
        if now - last_toggle < 0.08:
            return
        last_toggle = now
        if overlay.isVisible():
            overlay.hide()
        else:
            overlay.show()
            overlay.raise_()

    hotkey_bridge.triggered.connect(toggle_overlay, Qt.QueuedConnection)

    hotkey_listener = HotKeyListener(hotkey_bridge.triggered.emit)
    hotkey_listener.start()

    # Connect menu actions
    action_show.triggered.connect(lambda: (overlay.show(), overlay.raise_()))
    action_hide.triggered.connect(overlay.hide)

    def on_exit():
        hotkey_listener.stop()
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
        "Use Ctrl+Alt+S to toggle overlay. Double-click tray to show.",
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
