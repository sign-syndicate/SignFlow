from __future__ import annotations

import sys
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QAction, QApplication, QMenu, QStyle, QSystemTrayIcon

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from core.pipeline import VisionPipeline
from overlay.qt_overlay import DetectionOverlay


class PipelineWorker(QThread):
	result_ready = pyqtSignal(object)

	def __init__(self, model_path: Path) -> None:
		super().__init__()
		self._running = False
		self._pipeline = VisionPipeline(model_path=model_path, monitor_index=1, conf=0.35)

	def run(self) -> None:
		self._running = True
		while self._running:
			boxes = self._pipeline.process_once()
			self.result_ready.emit(boxes)

	def stop(self) -> None:
		self._running = False


def main() -> int:
	model_path = PROJECT_ROOT / "models" / "yolov8n.pt"
	model_path.parent.mkdir(parents=True, exist_ok=True)

	app = QApplication(sys.argv)
	app.setQuitOnLastWindowClosed(False)

	overlay = DetectionOverlay()
	overlay.show()

	tray = QSystemTrayIcon()
	tray.setIcon(app.style().standardIcon(QStyle.SP_ComputerIcon))

	menu = QMenu()
	action_open = QAction("Show Overlay", menu)
	action_hide = QAction("Hide Overlay", menu)
	action_exit = QAction("Exit", menu)

	menu.addAction(action_open)
	menu.addAction(action_hide)
	menu.addSeparator()
	menu.addAction(action_exit)
	tray.setContextMenu(menu)

	worker = PipelineWorker(model_path=model_path)
	worker.result_ready.connect(overlay.update_boxes)

	def open_player() -> None:
		overlay.show()
		overlay.raise_()

	def hide_player() -> None:
		overlay.hide()

	def exit_app() -> None:
		worker.stop()
		worker.wait(5000)
		tray.hide()
		app.quit()

	action_open.triggered.connect(open_player)
	action_hide.triggered.connect(hide_player)
	action_exit.triggered.connect(exit_app)

	tray.activated.connect(lambda reason: open_player() if reason == QSystemTrayIcon.DoubleClick else None)
	tray.show()
	tray.showMessage(
		"SignFlow Running",
		"SignFlow overlay is running. Press Win+B to focus tray icons.",
		QSystemTrayIcon.Information,
		2500,
	)

	worker.start()
	rc = app.exec_()

	if worker.isRunning():
		worker.stop()
		worker.wait(5000)

	return rc


if __name__ == "__main__":
	raise SystemExit(main())