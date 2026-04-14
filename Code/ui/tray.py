from PyQt5.QtCore import QObject, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QIcon, QPainter, QPainterPath, QPixmap
from PyQt5.QtWidgets import QAction, QMenu, QSystemTrayIcon


class SystemTrayController(QObject):
    open_requested = pyqtSignal()
    exit_requested = pyqtSignal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self._tray = None
        self._menu = None
        self._build()

    def _build_icon(self) -> QIcon:
        pixmap = QPixmap(QSize(64, 64))
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        path = QPainterPath()
        path.addEllipse(6, 6, 52, 52)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(*self._config.theme.tray_outer))
        painter.drawPath(path)
        painter.setBrush(QColor(*self._config.theme.tray_inner))
        painter.drawEllipse(12, 12, 40, 40)
        painter.setBrush(QColor(255, 255, 255, 210))
        painter.drawEllipse(25, 25, 14, 14)
        painter.end()
        return QIcon(pixmap)

    def _build(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self._tray = QSystemTrayIcon(self._build_icon(), self)
        self._menu = QMenu()
        open_action = QAction("Open", self._menu)
        exit_action = QAction("Exit", self._menu)
        open_action.triggered.connect(self.open_requested.emit)
        exit_action.triggered.connect(self.exit_requested.emit)
        self._menu.addAction(open_action)
        self._menu.addSeparator()
        self._menu.addAction(exit_action)
        self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(self._on_activated)
        self._tray.setToolTip(self._config.app_name)
        self._tray.show()

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.open_requested.emit()
