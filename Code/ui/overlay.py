from PyQt5.QtCore import QObject, Qt, QTimer, QRect
from PyQt5.QtGui import QKeySequence, QGuiApplication
from PyQt5.QtWidgets import QApplication, QShortcut

from ..core.state_manager import AppStateManager
from .orb import FloatingOrb
from .panel import CaptionPanel
from .selector import RegionSelector


class SignFlowOverlay(QObject):
    def __init__(self, config, state_manager: AppStateManager, parent=None):
        super().__init__(parent)
        self._config = config
        self._state = state_manager
        self.orb = FloatingOrb(config)
        self.panel = CaptionPanel(config)
        self.selector = RegionSelector(config)
        self._caption_timer = QTimer(self)
        self._caption_timer.setInterval(config.caption_timer_ms)
        self._caption_timer.timeout.connect(self._advance_caption)
        self._shortcut_hosts = []
        self._transition_guard = False
        self._orb_position_initialized = False

        self.orb.activated.connect(self.open_panel)
        self.orb.dock_changed.connect(self._state.set_dock_edge)
        self.panel.collapse_requested.connect(self.collapse_to_orb)
        self.selector.selection_finished.connect(self._selection_finished)
        self.selector.selection_cancelled.connect(self.collapse_to_orb)

        self._state.state_changed.connect(self._on_state_changed)
        self._state.caption_changed.connect(self.panel.set_caption)
        self._state.dock_edge_changed.connect(self._apply_dock_edge)
        self._state.roi_changed.connect(self._apply_roi)

        self._install_shortcuts()
        self._state.set_caption(config.idle_caption)
        self._apply_dock_edge(self._state.dock_edge)
        self._ensure_orb_position()
        self.orb.show()
        self.orb.raise_()
        self.panel.hide()
        self.selector.hide_overlay()

    def _install_shortcuts(self):
        for widget in (self.orb, self.panel):
            shortcut = QShortcut(QKeySequence(self._config.shortcut_sequence), widget)
            shortcut.setContext(Qt.ApplicationShortcut)
            shortcut.activated.connect(self.toggle)
            self._shortcut_hosts.append(shortcut)

    def _screen_geometry(self):
        screen = self.orb.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            return None
        return screen.availableGeometry()

    def _place_orb(self):
        self.orb.place_default()
        self._orb_position_initialized = True

    def _ensure_orb_position(self):
        if not self._orb_position_initialized:
            self._place_orb()

    def _panel_target_geometry(self):
        geo = self._screen_geometry()
        if geo is None:
            return self.panel.geometry()
        size = self._config.panel_size
        orb_geo = self.orb.geometry()
        y = max(
            geo.y() + self._config.panel_margin,
            min(
                orb_geo.center().y() - int(size.height() / 2),
                geo.y() + geo.height() - size.height() - self._config.panel_margin,
            ),
        )
        if self._state.dock_edge == "left":
            x = geo.x() + self._config.panel_margin
        else:
            x = geo.x() + geo.width() - size.width() - self._config.panel_margin
        return QRect(int(x), int(y), int(size.width()), int(size.height()))

    def _orb_geometry_for_panel(self):
        return self.orb.geometry()

    def _set_caption_mode(self, text: str):
        self._state.set_caption(text)
        self.panel.set_caption(text)

    def _on_state_changed(self, previous: str, current: str):
        self.panel.set_panel_state(current)
        if current == "idle":
            self._caption_timer.stop()
            self.selector.hide_overlay()
            self._set_caption_mode(self._config.idle_caption)
            self._animate_close_to_orb()
        elif current == "panel_open":
            self._caption_timer.stop()
            self._set_caption_mode(self._config.open_caption)
            self._animate_open_panel()
            self.selector.show_with_fade()
            QTimer.singleShot(self._config.open_duration_ms, self._enter_selecting_if_needed)
        elif current == "selecting":
            self._caption_timer.stop()
            self._set_caption_mode(self._config.open_caption)
            if not self.selector.isVisible():
                self.selector.show_with_fade()
        elif current == "active":
            self.selector.hide_overlay()
            self._caption_timer.start()
            self._state.reset_caption_cycle()
            self._set_caption_mode(self._state.next_caption())
            if not self.panel.isVisible():
                self._animate_open_panel()

    def _enter_selecting_if_needed(self):
        if self._state.state == "panel_open":
            self._state.set_state("selecting")

    def _apply_dock_edge(self, dock_edge: str):
        self.orb.set_dock_edge(dock_edge)
        self.panel.set_dock_edge(dock_edge)

    def _apply_roi(self, roi):
        if roi is None:
            return

    def _animate_open_panel(self):
        self._ensure_orb_position()
        from_geometry = self._orb_geometry_for_panel()
        to_geometry = self._panel_target_geometry()
        self.panel.set_close_anchor(from_geometry.center().y())
        self.panel.prepare_for_open(from_geometry, to_geometry)
        self.orb.setWindowOpacity(0.0)

    def _animate_close_to_orb(self):
        if not self.panel.isVisible():
            self.orb.setWindowOpacity(self._config.orb_opacity_idle)
            self.orb.show()
            self.orb.raise_()
            return
        target = self._orb_geometry_for_panel()
        self.panel.animate_collapse(target)
        self.orb.show()
        self.orb.raise_()
        self.orb.setWindowOpacity(self._config.orb_opacity_idle)

    def _selection_finished(self, roi):
        self._state.set_roi(roi)
        self._state.set_state("active")

    def _advance_caption(self):
        if self._state.state != "active":
            return
        self._set_caption_mode(self._state.next_caption())

    def open_panel(self):
        if self._transition_guard:
            return
        self._transition_guard = True
        try:
            if self._state.state == "idle":
                self._state.set_state("panel_open")
            elif self._state.state == "active":
                self._state.set_state("panel_open")
            else:
                self._state.set_state("panel_open")
        finally:
            self._transition_guard = False

    def collapse_to_orb(self):
        self._state.set_state("idle")

    def toggle(self):
        if self._state.state == "idle":
            self.open_panel()
        else:
            self.collapse_to_orb()

    def show(self):
        self._ensure_orb_position()
        self.orb.show()
        self.orb.raise_()

    def exit_application(self):
        QApplication.instance().quit()
