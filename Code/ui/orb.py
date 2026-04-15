from __future__ import annotations

import math

from PyQt5.QtCore import QAbstractAnimation, QEasingCurve, QEvent, QPoint, QPointF, QPropertyAnimation, QRectF, Qt, QTimer, pyqtProperty, pyqtSignal
from PyQt5.QtGui import QColor, QBrush, QCursor, QGuiApplication, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from ..core.constants import ORB_PRESENTATION_DEFAULTS, PANEL_DEFAULTS
from ..core.theme import Theme
from .panel import OrbPanelContent


class OrbSettingsWindow(QWidget):
    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(260, 132)
        self.setAttribute(Qt.WA_DeleteOnClose, False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        label = QLabel("Settings coming soon", self)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(
            "color: #EAEAEA;"
            "font-size: 14px;"
            "font-weight: 500;"
            "background: transparent;"
        )
        layout.addStretch(1)
        layout.addWidget(label)
        layout.addStretch(1)

        base = QColor(theme.base_color)
        border = QColor(theme.primary_color)
        border.setAlpha(140)
        self.setStyleSheet(
            f"background-color: rgba({base.red()}, {base.green()}, {base.blue()}, 232);"
            f"border: 1px solid rgba({border.red()}, {border.green()}, {border.blue()}, {border.alpha()});"
            "border-radius: 10px;"
        )


class FloatingOrb(QWidget):
    activated = pyqtSignal()

    BASE_DIAMETER = 56.0
    DOCK_WIDGET_DIAMETER = 124
    MENU_CANVAS_PADDING = 48
    WIDGET_DIAMETER = DOCK_WIDGET_DIAMETER + (MENU_CANVAS_PADDING * 2)
    AUTO_HIDE_DELAY_MS = 1000
    DOCK_ANIMATION_MS = 260
    HIDDEN_VISIBLE_RATIO = 0.5
    VISIBLE_OVERHANG_PX = 24
    REVEAL_DISTANCE = 120.0
    HIDDEN_OPACITY = 0.70
    MENU_SPINE_MS = 120
    MENU_NODE_MS = 80
    MENU_SPINE_RATIO = 1.35
    MENU_NODE_RATIO = 0.75
    MENU_ICON_BOX_RATIO = 1.24
    MENU_ICON_STROKE_RATIO = 0.16
    MENU_COMMON_STROKE_WIDTH = 2.5
    MENU_NODE_HOVER_SCALE = 0.08
    MENU_NODE_HOVER_LERP = 0.24
    QUIT_EXIT_MS = 190
    QUIT_EXIT_DROP_PX = 8
    QUIT_EXIT_OPACITY = 0.74
    STARTUP_ENTRY_MARGIN_PX = 12
    STARTUP_UNLOCK_GRACE_MS = 40
    PANEL_TRANSITION_DELAY_MS = 100
    PANEL_TRANSITION_MS = 250
    PANEL_TARGET_WIDTH = 312.0
    PANEL_TARGET_HEIGHT = 96.0
    PANEL_TARGET_RADIUS = 14.0
    PANEL_PADDING = 14.0
    PANEL_CAPTION_MIN_WIDTH = 180

    def __init__(self, theme: Theme, debug: bool = False, magnetic_effect_enabled: bool = True, parent=None):
        super().__init__(parent)
        self._theme = theme
        self._debug = debug
        self._magnetic_effect_enabled = magnetic_effect_enabled
        self._scale = 1.0
        self._hover_progress = 0.0
        self._inner_ring_progress = 0.0
        self._magnet_offset = QPointF(0.0, 0.0)
        self._dragging = False
        self._pressing = False
        self._press_global = QPoint()
        self._press_window_pos = QPoint()
        self._panel_press_global = QPoint()
        self._panel_press_window_pos = QPoint()
        self._drag_threshold_exceeded = False
        self._panel_dragging = False
        self._panel_drag_threshold_exceeded = False
        self._drag_start_distance = QApplication.startDragDistance()
        self._positioned = False
        self._snap_animation = None
        self._dock_animation = None
        self._opacity_animation = None
        self._quit_move_animation = None
        self._startup_move_animation = None
        self._border_phase = 0.0
        self._cursor_proximity = 0.0
        self._click_flash = 0.0
        self._display_opacity = 1.0
        self._dock_side = ORB_PRESENTATION_DEFAULTS.edge_right
        self._dock_hidden = False
        self._menu_open = False
        self._menu_spine_progress = 0.0
        self._menu_node_progress = 0.0
        self._menu_animating = False
        self._menu_animating_open = False
        self._menu_mouse_grabbed = False
        self._pending_quit = False
        self._quitting = False
        self._starting_up = False
        self._menu_hover_top = 0.0
        self._menu_hover_bottom = 0.0
        self._menu_hover_top_target = 0.0
        self._menu_hover_bottom_target = 0.0
        self._settings_window = None
        self._presentation_state = ORB_PRESENTATION_DEFAULTS.state_orb
        self._panel_morph = 0.0
        self._panel_anchor_edge_x = 0.0
        self._panel_anchor_center_y = 0.0
        self._panel_rect = QRectF()
        self._panel_caption_text = PANEL_DEFAULTS.caption_placeholder
        self._hover_target_active = False
        self._idle_timer = QTimer(self)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.setInterval(self.AUTO_HIDE_DELAY_MS)
        self._idle_timer.timeout.connect(self._auto_hide_if_idle)

        self.resize(self.WIDGET_DIAMETER, self.WIDGET_DIAMETER)
        self.setMinimumSize(int(self.BASE_DIAMETER), int(self.BASE_DIAMETER))
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_Hover, True)

        self._panel_content = OrbPanelContent(self._theme, self)
        self._panel_content.set_caption(self._panel_caption_text)
        self._panel_content.set_edge(self._dock_side)
        self._panel_content.collapse_requested.connect(self.panel_to_orb_transition)
        self._panel_content.drag_started.connect(self._on_panel_drag_started)
        self._panel_content.drag_moved.connect(self._on_panel_drag_moved)
        self._panel_content.drag_released.connect(self._on_panel_drag_released)
        self._panel_content.hide()

        self._breathing_animation = QPropertyAnimation(self, b"scale", self)
        self._breathing_animation.setDuration(2800)
        self._breathing_animation.setLoopCount(-1)
        self._breathing_animation.setEasingCurve(QEasingCurve.InOutSine)
        self._breathing_animation.setStartValue(0.98)
        self._breathing_animation.setKeyValueAt(0.5, 1.02)
        self._breathing_animation.setEndValue(0.98)
        self._breathing_animation.start()

        self._hover_animation = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_animation.setDuration(120)
        self._hover_animation.setEasingCurve(QEasingCurve.OutCubic)

        self._click_flash_animation = QPropertyAnimation(self, b"clickFlash", self)
        self._click_flash_animation.setEasingCurve(QEasingCurve.OutCubic)

        self._panel_morph_animation = QPropertyAnimation(self, b"panelMorph", self)
        self._panel_morph_animation.setDuration(self.PANEL_TRANSITION_MS)
        self._panel_morph_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._panel_morph_animation.finished.connect(self._on_panel_morph_finished)

        self._menu_spine_animation = QPropertyAnimation(self, b"menuSpineProgress", self)
        self._menu_spine_animation.setDuration(self.MENU_SPINE_MS)
        self._menu_spine_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._menu_spine_animation.finished.connect(self._on_menu_spine_animation_finished)

        self._menu_node_animation = QPropertyAnimation(self, b"menuNodeProgress", self)
        self._menu_node_animation.setDuration(self.MENU_NODE_MS)
        self._menu_node_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._menu_node_animation.finished.connect(self._on_menu_node_animation_finished)

        self._magnet_timer = QTimer(self)
        self._magnet_timer.setInterval(16)
        self._magnet_timer.timeout.connect(self._update_magnetic_offset)
        self._magnet_timer.start()

        app = QApplication.instance()
        if app is not None:
            app.applicationStateChanged.connect(self._on_application_state_changed)

        QTimer.singleShot(0, self._position_initially)

    def getMenuSpineProgress(self) -> float:
        return self._menu_spine_progress

    def setMenuSpineProgress(self, value: float):
        self._menu_spine_progress = max(0.0, min(1.0, float(value)))
        self.update()

    menuSpineProgress = pyqtProperty(float, fget=getMenuSpineProgress, fset=setMenuSpineProgress)

    def getMenuNodeProgress(self) -> float:
        return self._menu_node_progress

    def setMenuNodeProgress(self, value: float):
        self._menu_node_progress = max(0.0, min(1.0, float(value)))
        self.update()

    menuNodeProgress = pyqtProperty(float, fget=getMenuNodeProgress, fset=setMenuNodeProgress)

    def theme(self) -> Theme:
        return self._theme

    def getScale(self) -> float:
        return self._scale

    def setScale(self, value: float):
        self._scale = float(value)
        self.update()

    scale = pyqtProperty(float, fget=getScale, fset=setScale)

    def getHoverProgress(self) -> float:
        return self._hover_progress

    def setHoverProgress(self, value: float):
        self._hover_progress = max(0.0, min(1.0, float(value)))
        self.update()

    hoverProgress = pyqtProperty(float, fget=getHoverProgress, fset=setHoverProgress)

    def getClickFlash(self) -> float:
        return self._click_flash

    def setClickFlash(self, value: float):
        self._click_flash = max(0.0, min(1.0, float(value)))
        self.update()

    clickFlash = pyqtProperty(float, fget=getClickFlash, fset=setClickFlash)

    def getDisplayOpacity(self) -> float:
        return self._display_opacity

    def setDisplayOpacity(self, value: float):
        self._display_opacity = max(self.HIDDEN_OPACITY, min(1.0, float(value)))
        self.update()

    def animateDisplayOpacity(self, target_opacity: float, duration: int | None = None):
        self._animate_display_opacity(target_opacity, duration)

    displayOpacity = pyqtProperty(float, fget=getDisplayOpacity, fset=setDisplayOpacity)

    def getPanelMorph(self) -> float:
        return self._panel_morph

    def setPanelMorph(self, value: float):
        self._panel_morph = max(0.0, min(1.0, float(value)))
        self._sync_panel_geometry_from_morph()
        self.update()

    panelMorph = pyqtProperty(float, fget=getPanelMorph, fset=setPanelMorph)

    def orb_to_panel_transition(self):
        if self._presentation_state in (
            ORB_PRESENTATION_DEFAULTS.state_panel,
            ORB_PRESENTATION_DEFAULTS.state_transition_to_panel,
        ):
            return
        if self._quitting or self._starting_up:
            return

        self._stop_snap_animation()
        self._stop_dock_animation()
        self._cancel_idle_timer()
        self._dock_hidden = False
        if self._menu_interactions_blocked() and self._menu_open:
            self._close_menu()
        self._remove_global_click_filter()
        self._menu_open = False
        self._menu_animating = False
        self._menu_animating_open = False
        self._menu_spine_animation.stop()
        self._menu_node_animation.stop()
        self._menu_spine_progress = 0.0
        self._menu_node_progress = 0.0

        center_global = self.mapToGlobal(self.rect().center())
        screen = self._screen_for_point(center_global)
        if screen is None:
            return

        geometry = screen.availableGeometry()
        min_panel_y = geometry.top()
        max_panel_y = max(min_panel_y, (geometry.bottom() + 1) - self.WIDGET_DIAMETER)
        panel_y = max(min_panel_y, min(int(round(center_global.y() - (self.PANEL_TARGET_HEIGHT * 0.5))), max_panel_y))
        self._panel_anchor_center_y = float(panel_y + (self.PANEL_TARGET_HEIGHT * 0.5))
        panel_overhang = float(PANEL_DEFAULTS.edge_overhang_px)
        if self._dock_side == ORB_PRESENTATION_DEFAULTS.edge_right:
            self._panel_anchor_edge_x = float(center_global.x()) + panel_overhang
        else:
            self._panel_anchor_edge_x = float(center_global.x()) - panel_overhang

        self._presentation_state = ORB_PRESENTATION_DEFAULTS.state_transition_to_panel
        self._panel_content.set_edge(self._dock_side)
        self._panel_content.show()
        self._panel_content.raise_()

        self._panel_morph_animation.stop()
        self._panel_morph_animation.setStartValue(self._panel_morph)
        self._panel_morph_animation.setEndValue(1.0)
        self._panel_morph_animation.start()

    def panel_to_orb_transition(self):
        if self._presentation_state in (
            ORB_PRESENTATION_DEFAULTS.state_orb,
            ORB_PRESENTATION_DEFAULTS.state_transition_to_orb,
        ):
            return
        if self._quitting:
            return

        self._presentation_state = ORB_PRESENTATION_DEFAULTS.state_transition_to_orb
        self._panel_morph_animation.stop()
        self._panel_morph_animation.setStartValue(self._panel_morph)
        self._panel_morph_animation.setEndValue(0.0)
        self._panel_morph_animation.start()

    def update_caption(self, text: str):
        safe_text = str(text).strip() if text is not None else ""
        if not safe_text:
            safe_text = PANEL_DEFAULTS.caption_placeholder
        self._panel_caption_text = safe_text
        self._panel_content.animate_caption_update(self._panel_caption_text)

    def on_roi_confirmed(self, _x: int, _y: int, _w: int, _h: int):
        QTimer.singleShot(self.PANEL_TRANSITION_DELAY_MS, self.orb_to_panel_transition)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._positioned:
            self._position_initially()
        elif self._starting_up and self._startup_move_animation is None:
            # Defensive fallback: never leave startup interaction lock active.
            self._starting_up = False
        self._dock_hidden = False
        self._reset_idle_timer()
        if self._debug:
            print(f"orb theme: {self._theme.name}")
            print(f"orb position: {self.pos().x()}, {self.pos().y()}")

    def closeEvent(self, event):
        self._stop_startup_move_animation()
        self._stop_quit_move_animation()
        self._release_menu_mouse_grab()
        self._remove_global_click_filter()
        self._panel_morph_animation.stop()
        self._menu_spine_animation.stop()
        self._menu_node_animation.stop()
        app = QApplication.instance()
        if app is not None:
            try:
                app.applicationStateChanged.disconnect(self._on_application_state_changed)
            except TypeError:
                pass
        super().closeEvent(event)

    def enterEvent(self, event):
        if self._quitting or self._starting_up:
            super().enterEvent(event)
            return
        if self._panel_visual_active():
            super().enterEvent(event)
            return
        if self._menu_interactions_blocked():
            super().enterEvent(event)
            return
        self._animate_hover(True)
        self._reveal_from_edge()
        self._reset_idle_timer()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._quitting or self._starting_up:
            super().leaveEvent(event)
            return
        if self._panel_visual_active():
            super().leaveEvent(event)
            return
        if self._menu_interactions_blocked():
            super().leaveEvent(event)
            return
        self._animate_hover(False)
        self._reset_idle_timer()
        super().leaveEvent(event)

    def eventFilter(self, watched, event):
        if not self._menu_interactions_blocked():
            return super().eventFilter(watched, event)
        if event.type() != QEvent.MouseButtonPress:
            return super().eventFilter(watched, event)

        global_pos = event.globalPos()
        local = self.mapFromGlobal(global_pos)
        if self.rect().contains(local):
            return super().eventFilter(watched, event)

        self._close_menu()
        return super().eventFilter(watched, event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.fillRect(self.rect(), Qt.transparent)
        painter.setOpacity(self._display_opacity)

        if self._panel_visual_active():
            self._draw_panel_morph(painter)
            return

        menu_visible = self._menu_visual_active()
        effective_hover = self._hover_progress
        effective_proximity = 0.0 if menu_visible else self._cursor_proximity

        center = QPointF(self.rect().center())
        if not menu_visible:
            center += self._magnet_offset
        effective_scale = self._scale * (1.0 + 0.05 * effective_hover)
        effective_scale += 0.012 * effective_proximity
        diameter = self.BASE_DIAMETER * effective_scale
        radius = diameter / 2.0
        orb_rect = QRectF(center.x() - radius, center.y() - radius, diameter, diameter)

        if menu_visible:
            self._draw_menu_spines(painter, center, diameter)

        glow_color = QColor(self._theme.glow_color)
        glow_strength = 0.17 + (self._theme.shadow_strength * 0.28) + (0.08 * effective_hover) + (0.06 * effective_proximity)
        glow_color.setAlphaF(max(0.0, min(1.0, glow_strength)))
        glow_gradient = QRadialGradient(center, radius * (1.45 + (0.12 * effective_hover) + (0.08 * effective_proximity)))
        glow_gradient.setColorAt(0.0, glow_color)
        glow_soft = QColor(glow_color)
        glow_soft.setAlphaF(glow_color.alphaF() * 0.22)
        glow_gradient.setColorAt(0.7, glow_soft)
        glow_gradient.setColorAt(1.0, QColor(0, 0, 0, 0))

        painter.setPen(Qt.NoPen)
        painter.setBrush(glow_gradient)
        painter.drawEllipse(orb_rect.adjusted(-radius * 0.45, -radius * 0.45, radius * 0.45, radius * 0.45))

        fill_gradient = QRadialGradient(orb_rect.topLeft() + QPointF(radius * 0.28, radius * 0.24), radius * 1.2)
        highlight = QColor(self._theme.hover_color)
        highlight.setAlphaF(0.96 if self._theme.name == "APPLE" else 0.52)
        base = QColor(self._theme.base_color)
        base_darker = QColor(self._theme.base_color).darker(112 if self._theme.name == "APPLE" else 128)
        fill_gradient.setColorAt(0.0, highlight)
        fill_gradient.setColorAt(0.5, base)
        fill_gradient.setColorAt(1.0, base_darker)

        if self._click_flash > 0.0:
            flash = QColor(self._theme.hover_color if self._theme.name != "APPLE" else "#FFFFFF")
            flash_alpha = 0.22 if self._theme.name == "APPLE" else 0.30
            flash.setAlphaF(flash_alpha * self._click_flash)
            flash_gradient = QRadialGradient(center, radius * 1.08)
            flash_gradient.setColorAt(0.0, flash)
            flash_gradient.setColorAt(0.45, QColor(flash.red(), flash.green(), flash.blue(), 0))
            flash_gradient.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setPen(Qt.NoPen)
            painter.setBrush(flash_gradient)
            painter.drawEllipse(orb_rect.adjusted(-2.0, -2.0, 2.0, 2.0))

        painter.setBrush(fill_gradient)
        painter.drawEllipse(orb_rect)

        sheen = QLinearGradient(orb_rect.topLeft(), orb_rect.bottomRight())
        sheen_color = QColor(255, 255, 255, 36 if self._theme.name == "APPLE" else 14)
        sheen.setColorAt(0.0, sheen_color)
        sheen.setColorAt(0.4, QColor(255, 255, 255, 0))
        sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(sheen)
        painter.drawEllipse(orb_rect.adjusted(radius * 0.08, radius * 0.08, -radius * 0.12, -radius * 0.12))

        self._draw_border_segments(painter, orb_rect, center)

        inner_rim_alpha = 50 if self._theme.name == "APPLE" else 24
        inner_rim = QPen(QColor(255, 255, 255, inner_rim_alpha))
        inner_rim.setWidthF(0.8)
        painter.setPen(inner_rim)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(orb_rect.adjusted(4.0, 4.0, -4.0, -4.0))

        self._draw_center_accent(painter, center, radius)

        if menu_visible:
            self._draw_menu_nodes(painter, center, diameter)

        if self._debug:
            debug_pen = QPen(QColor(255, 84, 84, 200))
            debug_pen.setStyle(Qt.DashLine)
            painter.setPen(debug_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

    def _draw_panel_morph(self, painter: QPainter):
        panel_rect = QRectF(self._panel_rect)
        if panel_rect.width() <= 0.0 or panel_rect.height() <= 0.0:
            return

        morph = self._panel_morph
        shadow_alpha = int(round(48 + (56 * morph)))
        shadow_color = QColor(0, 0, 0, max(0, min(140, shadow_alpha)))
        shadow_radius = 14.0 + (6.0 * morph)
        shadow_rect = panel_rect.adjusted(-shadow_radius, -shadow_radius, shadow_radius, shadow_radius)

        shadow_gradient = QRadialGradient(shadow_rect.center(), max(shadow_rect.width(), shadow_rect.height()) * 0.56)
        shadow_gradient.setColorAt(0.0, shadow_color)
        shadow_gradient.setColorAt(0.72, QColor(0, 0, 0, 24))
        shadow_gradient.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(shadow_gradient)
        painter.drawRoundedRect(shadow_rect, panel_rect.height() * 0.5 + 8.0, panel_rect.height() * 0.5 + 8.0)

    def _panel_visual_active(self) -> bool:
        return self._presentation_state != ORB_PRESENTATION_DEFAULTS.state_orb or self._panel_morph > 0.001

    def _panel_width_phase(self) -> float:
        return max(0.0, min(1.0, self._panel_morph / 0.70))

    def _panel_refine_phase(self) -> float:
        return max(0.0, min(1.0, (self._panel_morph - 0.34) / 0.66))

    def _panel_current_width(self) -> float:
        return self._lerp(self.BASE_DIAMETER, self.PANEL_TARGET_WIDTH, self._ease_out_cubic(self._panel_width_phase()))

    def _panel_current_height(self) -> float:
        return self._lerp(self.BASE_DIAMETER, self.PANEL_TARGET_HEIGHT, self._ease_out_cubic(self._panel_refine_phase()))

    def _panel_current_radius(self) -> float:
        orb_radius = self.BASE_DIAMETER * 0.5
        return self._lerp(orb_radius, self.PANEL_TARGET_RADIUS, self._ease_out_cubic(self._panel_refine_phase()))

    def _panel_current_padding(self) -> float:
        return self._lerp(0.0, self.PANEL_PADDING, self._ease_out_cubic(self._panel_refine_phase()))

    def _sync_panel_geometry_from_morph(self):
        if not self._panel_visual_active():
            return

        width = max(2.0, self._panel_current_width())
        height = max(2.0, self._panel_current_height())
        left = (
            self._panel_anchor_edge_x - width
            if self._dock_side == ORB_PRESENTATION_DEFAULTS.edge_right
            else self._panel_anchor_edge_x
        )
        top = self._panel_anchor_center_y - (height * 0.5)

        new_x = int(round(left))
        new_y = int(round(top))
        new_w = int(round(width))
        new_h = int(round(height))
        self.setGeometry(new_x, new_y, new_w, new_h)

        self._panel_rect = QRectF(0.0, 0.0, float(new_w), float(new_h))
        self._update_panel_chrome_geometry()

    def _on_panel_drag_started(self, global_pos: QPoint):
        if self._presentation_state != ORB_PRESENTATION_DEFAULTS.state_panel:
            return
        self._panel_dragging = False
        self._panel_drag_threshold_exceeded = False
        self._panel_press_global = QPoint(global_pos)
        self._panel_press_window_pos = QPoint(self.pos())
        self._stop_snap_animation()
        self._stop_dock_animation()

    def _on_panel_drag_moved(self, global_pos: QPoint):
        if self._presentation_state != ORB_PRESENTATION_DEFAULTS.state_panel:
            return

        delta = global_pos - self._panel_press_global
        if delta.manhattanLength() >= self._drag_start_distance:
            self._panel_drag_threshold_exceeded = True

        if not self._panel_drag_threshold_exceeded:
            return

        self._panel_dragging = True
        target = self._panel_press_window_pos + delta
        screen = self._screen_for_point(global_pos)
        if screen is None:
            return

        clamped = self._clamp_panel_to_screen(target, screen)
        self.move(clamped)

        geometry = screen.availableGeometry()
        panel_center_x = self.x() + (self.width() * 0.5)
        next_side = (
            ORB_PRESENTATION_DEFAULTS.edge_left
            if panel_center_x < geometry.center().x()
            else ORB_PRESENTATION_DEFAULTS.edge_right
        )
        if next_side != self._dock_side:
            self._dock_side = next_side
            self._panel_content.set_edge(self._dock_side)

    def _on_panel_drag_released(self, global_pos: QPoint):
        if self._presentation_state != ORB_PRESENTATION_DEFAULTS.state_panel:
            return

        dragged = self._panel_drag_threshold_exceeded
        self._panel_dragging = False
        self._panel_drag_threshold_exceeded = False
        if not dragged:
            return
        self._snap_panel_to_nearest_edge(global_pos)

    def _clamp_panel_to_screen(self, position: QPoint, screen) -> QPoint:
        geometry = screen.availableGeometry()
        overhang = int(PANEL_DEFAULTS.edge_overhang_px)
        min_x = geometry.left() - overhang
        max_x = (geometry.right() + 1) - self.width() + overhang
        x = max(min_x, min(position.x(), max_x))
        min_y = geometry.top()
        max_y = max(min_y, (geometry.bottom() + 1) - self.WIDGET_DIAMETER)
        y = max(min_y, min(position.y(), max_y))
        return QPoint(x, y)

    def _snap_panel_to_nearest_edge(self, global_pos: QPoint):
        screen = self._screen_for_point(global_pos)
        if screen is None:
            return

        geometry = screen.availableGeometry()
        panel_center_x = self.x() + (self.width() * 0.5)
        self._dock_side = (
            ORB_PRESENTATION_DEFAULTS.edge_left
            if panel_center_x < geometry.center().x()
            else ORB_PRESENTATION_DEFAULTS.edge_right
        )
        self._panel_content.set_edge(self._dock_side)

        overhang = int(PANEL_DEFAULTS.edge_overhang_px)
        if self._dock_side == ORB_PRESENTATION_DEFAULTS.edge_left:
            target_x = geometry.left() - overhang
            self._panel_anchor_edge_x = float(geometry.left()) - float(overhang)
        else:
            target_x = (geometry.right() + 1) - self.width() + overhang
            self._panel_anchor_edge_x = float(geometry.right() + 1) + float(overhang)

        min_y = geometry.top()
        max_y = max(min_y, (geometry.bottom() + 1) - self.WIDGET_DIAMETER)
        target_y = max(min_y, min(self.y(), max_y))
        self._panel_anchor_center_y = float(target_y + (self.height() * 0.5))
        self._animate_to_position(QPoint(target_x, target_y), self.DOCK_ANIMATION_MS, QEasingCurve.OutCubic, use_snap_animation=True)

    def _update_panel_chrome_geometry(self):
        if not self._panel_visual_active():
            self._panel_content.hide()
            return

        self._panel_content.show()
        self._panel_content.raise_()

        panel_w = int(round(self._panel_rect.width()))
        panel_h = int(round(self._panel_rect.height()))
        padding = int(round(self._panel_current_padding()))
        self._panel_content.setGeometry(0, 0, panel_w, panel_h)
        self._panel_content.set_edge(self._dock_side)
        self._panel_content.set_padding(padding)
        self._panel_content.set_radius(self._panel_current_radius())
        self._panel_content.set_morph(self._panel_morph)

    @staticmethod
    def _lerp(start: float, end: float, t: float) -> float:
        return start + ((end - start) * max(0.0, min(1.0, float(t))))

    @staticmethod
    def _ease_out_cubic(t: float) -> float:
        t = max(0.0, min(1.0, float(t)))
        return 1.0 - ((1.0 - t) ** 3)

    def mousePressEvent(self, event):
        if self._quitting or self._starting_up:
            event.accept()
            return
        if self._panel_visual_active():
            event.accept()
            return

        if event.button() == Qt.RightButton:
            if self._menu_interactions_blocked():
                self._close_menu()
                event.accept()
                return
            if self._can_open_menu():
                self._open_menu()
                event.accept()
                return
            event.ignore()
            return

        if event.button() != Qt.LeftButton:
            event.ignore()
            return

        if self._menu_interactions_blocked():
            action = self._menu_action_for_point(event.pos())
            if action == "settings":
                self._open_settings_window()
                self._close_menu()
            elif action == "quit":
                self._request_quit_sequence()
            else:
                self._close_menu()
            event.accept()
            return

        self._dragging = False
        self._drag_threshold_exceeded = False
        self._pressing = True
        self._press_global = event.globalPos()
        self._press_window_pos = self.pos()
        self._stop_snap_animation()
        self._stop_dock_animation()
        self._magnet_offset = QPointF(0.0, 0.0)
        self._cancel_idle_timer()
        event.accept()

    def mouseMoveEvent(self, event):
        if self._panel_visual_active():
            event.accept()
            return
        if self._menu_interactions_blocked():
            self._update_menu_hover_state(event.pos())
            event.accept()
            return

        if not self._pressing:
            event.ignore()
            return

        delta = event.globalPos() - self._press_global
        if delta.manhattanLength() >= self._drag_start_distance:
            self._drag_threshold_exceeded = True

        if not self._drag_threshold_exceeded:
            event.accept()
            return

        self._dragging = True
        target = self._press_window_pos + delta
        screen = self._screen_for_point(event.globalPos())
        target = self._clamp_to_screen(target, screen)
        self.move(target)
        self._dock_hidden = False
        self._reset_idle_timer()
        event.accept()

    def mouseReleaseEvent(self, event):
        if self._panel_visual_active():
            event.accept()
            return
        if self._menu_interactions_blocked():
            event.accept()
            return

        if event.button() != Qt.LeftButton:
            event.ignore()
            return

        was_dragging = self._dragging
        dragged = self._drag_threshold_exceeded
        self._dragging = False
        self._pressing = False
        self._drag_threshold_exceeded = False

        if not dragged:
            QTimer.singleShot(0, self.activated.emit)
        elif was_dragging:
            self._snap_to_nearest_edge()
        self._reset_idle_timer()

        event.accept()

    def _animate_hover(self, active: bool):
        if self._menu_interactions_blocked() or self._panel_visual_active():
            return
        if active == self._hover_target_active and self._hover_animation.state() == QAbstractAnimation.Running:
            return
        self._hover_target_active = bool(active)
        self._hover_animation.stop()
        self._hover_animation.setStartValue(self._hover_progress)
        self._hover_animation.setEndValue(1.0 if active else 0.0)
        self._hover_animation.start()

    def _set_hover_state(self, active: bool):
        self._hover_animation.stop()
        self._hover_target_active = bool(active)
        self.hoverProgress = 1.0 if active else 0.0

    def _menu_visual_active(self) -> bool:
        return self._menu_spine_progress > 0.001 or self._menu_node_progress > 0.001

    def _menu_interactions_blocked(self) -> bool:
        return self._menu_open or self._menu_animating or self._menu_visual_active() or self._panel_visual_active()

    def _on_panel_morph_finished(self):
        if self._presentation_state == ORB_PRESENTATION_DEFAULTS.state_transition_to_panel:
            self._presentation_state = ORB_PRESENTATION_DEFAULTS.state_panel
            self._hover_animation.stop()
            self.hoverProgress = 0.0
            self._cursor_proximity = 0.0
            self._magnet_offset = QPointF(0.0, 0.0)
            self._breathing_animation.pause()
            self.update()
            return

        if self._presentation_state == ORB_PRESENTATION_DEFAULTS.state_transition_to_orb:
            self._presentation_state = ORB_PRESENTATION_DEFAULTS.state_orb
            self._panel_morph = 0.0
            self._panel_content.hide()
            self._restore_orb_canvas_geometry()
            if self._breathing_animation.state() != QAbstractAnimation.Running:
                self._breathing_animation.start()
            self._reset_idle_timer()
            self.update()

    def _restore_orb_canvas_geometry(self):
        panel_overhang = float(PANEL_DEFAULTS.edge_overhang_px)
        if self._dock_side == ORB_PRESENTATION_DEFAULTS.edge_right:
            orb_center_x = self._panel_anchor_edge_x - panel_overhang
        else:
            orb_center_x = self._panel_anchor_edge_x + panel_overhang

        center_point = QPoint(int(round(orb_center_x)), int(round(self._panel_anchor_center_y)))
        screen = self._screen_for_point(center_point)
        if screen is None:
            return

        x = int(round(orb_center_x - (self.WIDGET_DIAMETER * 0.5)))
        y = int(round(self._panel_anchor_center_y - (self.WIDGET_DIAMETER * 0.5)))
        self.setGeometry(x, y, self.WIDGET_DIAMETER, self.WIDGET_DIAMETER)

        self._dock_hidden = False
        self.displayOpacity = 1.0

    def _install_global_click_filter(self):
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
        self._grab_menu_mouse()

    def _remove_global_click_filter(self):
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        self._release_menu_mouse_grab()

    def _grab_menu_mouse(self):
        if self._menu_mouse_grabbed:
            return
        try:
            self.grabMouse()
            self._menu_mouse_grabbed = True
        except Exception:
            self._menu_mouse_grabbed = False

    def _release_menu_mouse_grab(self):
        if not self._menu_mouse_grabbed:
            return
        try:
            self.releaseMouse()
        except Exception:
            pass
        self._menu_mouse_grabbed = False

    def _is_roi_active(self) -> bool:
        app = QApplication.instance()
        selector = getattr(app, "_signflow_selector", None)
        if isinstance(selector, dict):
            widget = selector.get("widget")
            return bool(widget is not None and widget.isVisible())
        return False

    def _can_open_menu(self) -> bool:
        return (
            not self._quitting
            and not self._starting_up
            and not self._dragging
            and not self._pressing
            and not self._is_roi_active()
            and not self._panel_visual_active()
        )

    def _open_menu(self):
        if self._menu_open and not self._menu_animating:
            return
        if not self._can_open_menu():
            return

        self._menu_open = True
        self._menu_animating = True
        self._menu_animating_open = True
        self._set_hover_state(True)
        self._cursor_proximity = 0.0
        self._magnet_offset = QPointF(0.0, 0.0)
        self._menu_hover_top = 0.0
        self._menu_hover_bottom = 0.0
        self._menu_hover_top_target = 0.0
        self._menu_hover_bottom_target = 0.0
        self._cancel_idle_timer()
        self._install_global_click_filter()

        self._menu_node_animation.stop()
        self._menu_spine_animation.stop()
        self._menu_spine_animation.setStartValue(self._menu_spine_progress)
        self._menu_spine_animation.setEndValue(1.0)
        self._menu_spine_animation.start()

    def _close_menu(self):
        if not (self._menu_open or self._menu_animating or self._menu_visual_active()):
            return

        self._menu_open = False
        self._menu_animating = True
        self._menu_animating_open = False
        self._menu_hover_top_target = 0.0
        self._menu_hover_bottom_target = 0.0
        self._menu_spine_animation.stop()
        self._menu_node_animation.stop()
        self._menu_node_animation.setStartValue(self._menu_node_progress)
        self._menu_node_animation.setEndValue(0.0)
        self._menu_node_animation.start()

    def _request_quit_sequence(self):
        if self._quitting:
            return
        self._pending_quit = True
        if self._menu_interactions_blocked():
            self._close_menu()
            return
        self._start_quit_exit_animation()

    def _start_quit_exit_animation(self):
        if self._quitting:
            return

        self._pending_quit = False
        self._quitting = True
        self._remove_global_click_filter()
        self._cancel_idle_timer()
        self._stop_snap_animation()
        self._stop_dock_animation()
        self._stop_quit_move_animation()

        screen = self._screen_for_point(self._orb_center_point())
        if screen is None:
            QApplication.quit()
            return

        geometry = screen.availableGeometry()
        current = self.pos()
        margin = 12
        if self._dock_side == ORB_PRESENTATION_DEFAULTS.edge_left:
            target_x = geometry.left() - self.width() - margin
        else:
            target_x = geometry.right() + 1 + margin
        target_y = self._clamp_y(current.y() + self.QUIT_EXIT_DROP_PX, geometry)

        self._quit_move_animation = QPropertyAnimation(self, b"pos", self)
        self._quit_move_animation.setDuration(self.QUIT_EXIT_MS)
        self._quit_move_animation.setEasingCurve(QEasingCurve.InCubic)
        self._quit_move_animation.setStartValue(current)
        self._quit_move_animation.setEndValue(QPoint(target_x, target_y))
        self._quit_move_animation.finished.connect(self._on_quit_exit_animation_finished)
        self._quit_move_animation.start()
        self._animate_display_opacity(self.QUIT_EXIT_OPACITY, duration=self.QUIT_EXIT_MS)

    def _on_application_state_changed(self, state):
        if self._quitting:
            return
        if state != Qt.ApplicationActive and (self._menu_open or self._menu_animating or self._menu_visual_active()):
            self._close_menu()

    def _on_menu_spine_animation_finished(self):
        if self._menu_animating_open:
            self._menu_node_animation.stop()
            self._menu_node_animation.setStartValue(self._menu_node_progress)
            self._menu_node_animation.setEndValue(1.0)
            self._menu_node_animation.start()
            return

        self._menu_animating = False
        self._menu_animating_open = False
        self._remove_global_click_filter()
        if self._pending_quit:
            self._start_quit_exit_animation()
            return
        self._sync_hover_after_menu_close()
        self._reset_idle_timer()

    def _on_menu_node_animation_finished(self):
        if self._menu_animating_open:
            self._menu_animating = False
            self._menu_open = True
            self._reset_idle_timer()
            return

        self._menu_spine_animation.stop()
        self._menu_spine_animation.setStartValue(self._menu_spine_progress)
        self._menu_spine_animation.setEndValue(0.0)
        self._menu_spine_animation.start()

    def _stop_quit_move_animation(self):
        if self._quit_move_animation is not None:
            self._quit_move_animation.stop()
            self._quit_move_animation.deleteLater()
            self._quit_move_animation = None

    def _on_quit_exit_animation_finished(self):
        self._stop_quit_move_animation()
        QApplication.quit()

    def _sync_hover_after_menu_close(self):
        local_cursor = self.mapFromGlobal(QCursor.pos())
        is_inside = self.rect().contains(local_cursor)
        self._set_hover_state(is_inside)

    def _menu_geometry(self, center: QPointF, diameter: float) -> dict:
        direction_x = 1.0 if self._dock_side == ORB_PRESENTATION_DEFAULTS.edge_left else -1.0
        angle = math.radians(45.0)
        full_length = diameter * self.MENU_SPINE_RATIO
        length = full_length * self._menu_spine_progress

        dx = math.cos(angle) * length * direction_x
        dy = math.sin(angle) * length
        top_center = QPointF(center.x() + dx, center.y() - dy)
        bottom_center = QPointF(center.x() + dx, center.y() + dy)

        node_radius_full = (diameter * self.MENU_NODE_RATIO) * 0.5
        node_radius_draw = node_radius_full * self._menu_node_progress
        node_radius_hit = node_radius_full if self._menu_open else node_radius_draw

        return {
            "top": top_center,
            "bottom": bottom_center,
            "node_radius_draw": node_radius_draw,
            "node_radius_hit": node_radius_hit,
        }

    def _draw_menu_spines(self, painter: QPainter, center: QPointF, diameter: float):
        if self._menu_spine_progress <= 0.001:
            return
        geometry = self._menu_geometry(center, diameter)
        line_color = QColor(self._theme.primary_color)
        line_color.setAlpha(214)
        pen = QPen(line_color, 2.0)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawLine(center, geometry["top"])
        painter.drawLine(center, geometry["bottom"])

    def _draw_center_accent(self, painter: QPainter, center: QPointF, orb_radius: float):
        interaction_boost = self._inner_ring_progress
        inner_rect = QRectF(
            center.x() - (orb_radius * 0.82),
            center.y() - (orb_radius * 0.82),
            orb_radius * 1.64,
            orb_radius * 1.64,
        )

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#F7F7F7"))
        painter.drawEllipse(inner_rect)

        ring_pen = QPen(self._menu_icon_color("settings"), self.MENU_COMMON_STROKE_WIDTH)
        ring_pen.setCapStyle(Qt.RoundCap)
        ring_pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(ring_pen)
        painter.setBrush(Qt.NoBrush)

        # Shrink the ring on hover to create a subtle pupil-dilation cue.
        ring_shrink = orb_radius * (0.12 * interaction_boost)
        ring_rect = inner_rect.adjusted(ring_shrink, ring_shrink, -ring_shrink, -ring_shrink)
        painter.drawEllipse(ring_rect)

    def _draw_menu_nodes(self, painter: QPainter, center: QPointF, diameter: float):
        if self._menu_node_progress <= 0.001:
            return

        geometry = self._menu_geometry(center, diameter)
        node_radius = geometry["node_radius_draw"]
        if node_radius <= 0.05:
            return

        top_scale = 1.0 + (self.MENU_NODE_HOVER_SCALE * self._menu_hover_top)
        bottom_scale = 1.0 + (self.MENU_NODE_HOVER_SCALE * self._menu_hover_bottom)

        self._draw_mini_orb(painter, geometry["top"], node_radius * top_scale, self._menu_hover_top)
        self._draw_mini_orb(painter, geometry["bottom"], node_radius * bottom_scale, self._menu_hover_bottom)
        self._draw_settings_icon(painter, geometry["top"], node_radius * top_scale)
        self._draw_quit_icon(painter, geometry["bottom"], node_radius * bottom_scale)

    def _draw_mini_orb(self, painter: QPainter, node_center: QPointF, radius: float, hover_amount: float = 0.0):
        rect = QRectF(node_center.x() - radius, node_center.y() - radius, radius * 2.0, radius * 2.0)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(self._theme.base_color))
        painter.drawEllipse(rect)

        border = QPen(QColor(255, 255, 255, 38), 0.8)
        border.setCapStyle(Qt.RoundCap)
        border.setJoinStyle(Qt.RoundJoin)
        painter.setPen(border)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(rect.adjusted(2.0, 2.0, -2.0, -2.0))

    def _draw_settings_icon(self, painter: QPainter, node_center: QPointF, radius: float):
        color = self._menu_icon_color("settings")
        color.setAlpha(int(255 * self._menu_node_progress))
        pen = QPen(color, self.MENU_COMMON_STROKE_WIDTH)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        painter.drawPath(self._build_gear_outline(node_center, radius))

        hole_radius = radius * 0.20
        painter.drawEllipse(
            QRectF(
                node_center.x() - hole_radius,
                node_center.y() - hole_radius,
                hole_radius * 2.0,
                hole_radius * 2.0,
            )
        )

    def _draw_quit_icon(self, painter: QPainter, node_center: QPointF, radius: float):
        color = self._menu_icon_color("quit")
        color.setAlpha(int(255 * self._menu_node_progress))
        pen = QPen(color, self.MENU_COMMON_STROKE_WIDTH)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        inset = radius * 0.36
        painter.drawLine(
            QPointF(node_center.x() - inset, node_center.y() - inset),
            QPointF(node_center.x() + inset, node_center.y() + inset),
        )
        painter.drawLine(
            QPointF(node_center.x() + inset, node_center.y() - inset),
            QPointF(node_center.x() - inset, node_center.y() + inset),
        )

    def _menu_icon_color(self, role: str) -> QColor:
        return QColor("#2A2A2F")

    def _update_menu_hover_state(self, local_pos: QPoint | None = None):
        if not self._menu_visual_active():
            self._menu_hover_top_target = 0.0
            self._menu_hover_bottom_target = 0.0
        else:
            if local_pos is None:
                local_pos = self.mapFromGlobal(QCursor.pos())

            action = "close"
            if self.rect().contains(local_pos):
                action = self._menu_action_for_point(local_pos)

            self._menu_hover_top_target = 1.0 if action == "settings" else 0.0
            self._menu_hover_bottom_target = 1.0 if action == "quit" else 0.0

        prev_top = self._menu_hover_top
        prev_bottom = self._menu_hover_bottom
        self._menu_hover_top += (self._menu_hover_top_target - self._menu_hover_top) * self.MENU_NODE_HOVER_LERP
        self._menu_hover_bottom += (self._menu_hover_bottom_target - self._menu_hover_bottom) * self.MENU_NODE_HOVER_LERP

        if abs(self._menu_hover_top - prev_top) > 0.001 or abs(self._menu_hover_bottom - prev_bottom) > 0.001:
            self.update()

    def _build_gear_outline(self, node_center: QPointF, radius: float) -> QPainterPath:
        icon_radius = radius * self.MENU_ICON_BOX_RATIO * 0.5
        bump_radius = icon_radius * 0.18
        path = QPainterPath()

        steps = 128
        for index in range(steps + 1):
            theta = (math.tau * index / steps) - (math.pi / 2.0)
            wave = math.cos(theta * 8.0)
            r = icon_radius + (bump_radius * wave)
            x = node_center.x() + math.cos(theta) * r
            y = node_center.y() + math.sin(theta) * r
            if index == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)

        path.closeSubpath()
        return path

    def _menu_action_for_point(self, local_point: QPoint) -> str:
        center = QPointF(self.rect().center())
        diameter = self.BASE_DIAMETER * self._scale
        geometry = self._menu_geometry(center, diameter)
        node_radius = geometry["node_radius_hit"]
        point = QPointF(local_point)

        top_delta = QPointF(point.x() - geometry["top"].x(), point.y() - geometry["top"].y())
        if math.hypot(top_delta.x(), top_delta.y()) <= node_radius:
            return "settings"

        bottom_delta = QPointF(point.x() - geometry["bottom"].x(), point.y() - geometry["bottom"].y())
        if math.hypot(bottom_delta.x(), bottom_delta.y()) <= node_radius:
            return "quit"
        return "close"

    def _open_settings_window(self):
        if self._settings_window is None:
            self._settings_window = OrbSettingsWindow(self._theme)

        self._settings_window.show()
        self._settings_window.raise_()
        self._settings_window.activateWindow()

    def _trigger_click_flash(self):
        self._click_flash_animation.stop()
        self._click_flash_animation.setDuration(0)
        self.clickFlash = 0.0
        self._click_flash_animation.setDuration(110)
        self._click_flash_animation.setStartValue(0.0)
        self._click_flash_animation.setKeyValueAt(0.45, 1.0)
        self._click_flash_animation.setEndValue(0.0)
        self._click_flash_animation.start()

    def _position_initially(self):
        if self._positioned:
            return

        screen = QApplication.primaryScreen()
        if screen is None:
            return

        geometry = screen.availableGeometry()
        y = geometry.y() + (geometry.height() - self.height()) // 2
        self._dock_side = ORB_PRESENTATION_DEFAULTS.edge_right
        self._dock_hidden = False
        visible_position = self._dock_visible_target(screen)
        visible_position.setY(self._clamp_y(y, geometry))

        # Mirror the quit motion so launch feels intentional: enter from the dock edge while fading in.
        margin = int(self.STARTUP_ENTRY_MARGIN_PX)
        if self._dock_side == ORB_PRESENTATION_DEFAULTS.edge_left:
            start_x = geometry.left() - self.width() - margin
        else:
            start_x = geometry.right() + 1 + margin
        start_y = self._clamp_y(visible_position.y() + self.QUIT_EXIT_DROP_PX, geometry)
        self.move(QPoint(start_x, start_y))
        self.displayOpacity = self.QUIT_EXIT_OPACITY

        self._positioned = True
        self._start_startup_entry_animation(visible_position)
        self._reset_idle_timer()
        if self._debug:
            print(f"orb position: {self.pos().x()}, {self.pos().y()}")

    def _start_startup_entry_animation(self, target: QPoint):
        self._stop_startup_move_animation()
        self._starting_up = True
        self._startup_move_animation = QPropertyAnimation(self, b"pos", self)
        self._startup_move_animation.setDuration(self.QUIT_EXIT_MS)
        self._startup_move_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._startup_move_animation.setStartValue(self.pos())
        self._startup_move_animation.setEndValue(target)
        self._startup_move_animation.finished.connect(self._on_startup_entry_animation_finished)
        self._startup_move_animation.start()
        self._animate_display_opacity(1.0, duration=self.QUIT_EXIT_MS)
        QTimer.singleShot(self.QUIT_EXIT_MS + self.STARTUP_UNLOCK_GRACE_MS, self._ensure_startup_entry_unlocked)

    def _stop_startup_move_animation(self):
        if self._startup_move_animation is not None:
            self._startup_move_animation.stop()
            self._startup_move_animation.deleteLater()
            self._startup_move_animation = None

    def _on_startup_entry_animation_finished(self):
        self._stop_startup_move_animation()
        self._starting_up = False
        self._reset_idle_timer()

    def _ensure_startup_entry_unlocked(self):
        if not self._starting_up:
            return
        if self._startup_move_animation is not None and self._startup_move_animation.state() == QAbstractAnimation.Running:
            return
        self._on_startup_entry_animation_finished()

    def _snap_to_nearest_edge(self):
        screen = self._screen_for_point(QCursor.pos())
        if screen is None:
            return

        geometry = screen.availableGeometry()
        current = self.pos()
        canvas_shift = (self.width() - self.DOCK_WIDGET_DIAMETER) / 2.0
        dock_center_x = current.x() + canvas_shift + (self.DOCK_WIDGET_DIAMETER / 2.0)
        self._dock_side = (
            ORB_PRESENTATION_DEFAULTS.edge_left
            if dock_center_x < geometry.center().x()
            else ORB_PRESENTATION_DEFAULTS.edge_right
        )
        target = self._dock_visible_target(screen)
        target.setY(self._clamp_y(current.y(), geometry))

        self._stop_snap_animation()
        self._animate_to_position(target, self.DOCK_ANIMATION_MS, QEasingCurve.OutCubic, use_snap_animation=True)

    def _on_snap_finished(self):
        self._stop_snap_animation()
        self._reset_idle_timer()
        if self._debug:
            print(f"orb position: {self.pos().x()}, {self.pos().y()}")

    def _stop_snap_animation(self):
        if self._snap_animation is not None:
            self._snap_animation.stop()
            self._snap_animation.deleteLater()
            self._snap_animation = None

    def _stop_dock_animation(self):
        if self._dock_animation is not None:
            self._dock_animation.stop()
            self._dock_animation.deleteLater()
            self._dock_animation = None

    def _stop_opacity_animation(self):
        if self._opacity_animation is not None:
            self._opacity_animation.stop()
            self._opacity_animation.deleteLater()
            self._opacity_animation = None

    def _animate_to_position(self, target: QPoint, duration: int, easing, use_snap_animation: bool = False):
        if use_snap_animation:
            self._stop_snap_animation()
            animation = QPropertyAnimation(self, b"pos", self)
            self._snap_animation = animation
        else:
            self._stop_dock_animation()
            animation = QPropertyAnimation(self, b"pos", self)
            self._dock_animation = animation

        animation.setDuration(duration)
        animation.setEasingCurve(easing)
        animation.setStartValue(self.pos())
        animation.setEndValue(target)

        if use_snap_animation:
            animation.finished.connect(self._on_snap_finished)
        else:
            animation.finished.connect(self._on_dock_animation_finished)
        animation.start()

    def _on_dock_animation_finished(self):
        self._stop_dock_animation()
        self._reset_idle_timer()

    def _cancel_idle_timer(self):
        if self._idle_timer.isActive():
            self._idle_timer.stop()

    def _reset_idle_timer(self):
        if self._is_roi_active():
            self._cancel_idle_timer()
            return
        if self._panel_visual_active():
            self._cancel_idle_timer()
            return
        if self._menu_interactions_blocked():
            self._cancel_idle_timer()
            return
        if self._dragging:
            return
        if self._under_active_interaction():
            self._idle_timer.start(self.AUTO_HIDE_DELAY_MS)
            return
        self._idle_timer.start(self.AUTO_HIDE_DELAY_MS)

    def _under_active_interaction(self) -> bool:
        if self._menu_interactions_blocked():
            return True
        if self._pressing or self._dragging:
            return True
        return self.rect().contains(self.mapFromGlobal(QCursor.pos()))

    def _auto_hide_if_idle(self):
        if self._is_roi_active():
            return
        if self._panel_visual_active():
            return
        if self._menu_interactions_blocked():
            return
        if self._dragging or self._under_active_interaction() or self._cursor_near_orb():
            self._reset_idle_timer()
            return
        if self._dock_hidden:
            return
        self._dock_hidden = True
        self._animate_dock_visibility(False)

    def _reveal_from_edge(self):
        if self._panel_visual_active():
            return
        if self._dragging or self._menu_interactions_blocked():
            return
        if not self._dock_hidden:
            return
        self._dock_hidden = False
        self._animate_dock_visibility(True)

    def _animate_dock_visibility(self, visible: bool):
        if self._panel_visual_active():
            return
        screen = self._screen_for_point(self._orb_center_point())
        if screen is None:
            return

        target = self._dock_visible_target(screen) if visible else self._dock_hidden_target(screen)
        self._animate_to_position(target, self.DOCK_ANIMATION_MS, QEasingCurve.OutCubic)
        self._animate_display_opacity(1.0 if visible else self.HIDDEN_OPACITY)

    def _animate_display_opacity(self, target_opacity: float, duration: int | None = None):
        self._stop_opacity_animation()
        self._opacity_animation = QPropertyAnimation(self, b"displayOpacity", self)
        self._opacity_animation.setDuration(self.DOCK_ANIMATION_MS if duration is None else int(duration))
        self._opacity_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._opacity_animation.setStartValue(self._display_opacity)
        self._opacity_animation.setEndValue(float(target_opacity))
        self._opacity_animation.finished.connect(self._on_opacity_animation_finished)
        self._opacity_animation.start()

    def _on_opacity_animation_finished(self):
        self._stop_opacity_animation()

    def _dock_visible_target(self, screen) -> QPoint:
        geometry = screen.availableGeometry()
        y = self._clamp_y(self.pos().y(), geometry)
        overhang = int(self.VISIBLE_OVERHANG_PX)
        canvas_shift = int((self.width() - self.DOCK_WIDGET_DIAMETER) / 2)
        if self._dock_side == ORB_PRESENTATION_DEFAULTS.edge_left:
            x = geometry.left() - overhang - canvas_shift
        else:
            # right() is inclusive; add +1 to convert to width-style boundary before applying overhang.
            x = geometry.right() - self.width() + 1 + overhang + canvas_shift
        return QPoint(x, y)

    def _dock_hidden_target(self, screen) -> QPoint:
        geometry = screen.availableGeometry()
        y = self._clamp_y(self.pos().y(), geometry)
        visible_width = self._visible_width_for_hidden_state()
        canvas_shift = int((self.width() - self.DOCK_WIDGET_DIAMETER) / 2)
        x = self._docked_x_for_visible_width(geometry, visible_width)
        x += canvas_shift if self._dock_side == ORB_PRESENTATION_DEFAULTS.edge_left else -canvas_shift
        return QPoint(x, y)

    def _cursor_near_orb(self) -> bool:
        if self._panel_visual_active():
            return False
        if self._menu_interactions_blocked():
            return False
        cursor = QCursor.pos()
        reference = self._interaction_reference_point()
        delta = QPointF(cursor.x() - reference.x(), cursor.y() - reference.y())
        return math.hypot(delta.x(), delta.y()) <= self.REVEAL_DISTANCE

    def _interaction_reference_point(self) -> QPoint:
        center_y = self.pos().y() + self.height() // 2
        if not self._dock_hidden:
            return QPoint(self.pos().x() + self.width() // 2, center_y)

        visible_width = self._visible_width_for_hidden_state()
        if self._dock_side == ORB_PRESENTATION_DEFAULTS.edge_left:
            x = self.pos().x() + self.width() - visible_width // 2
        else:
            x = self.pos().x() + visible_width // 2
        return QPoint(x, center_y)

    def _visible_width_for_hidden_state(self) -> int:
        return max(18, int(round(self.DOCK_WIDGET_DIAMETER * self.HIDDEN_VISIBLE_RATIO)))

    def _docked_x_for_visible_width(self, geometry, visible_width: int) -> int:
        visible_width = max(1, min(int(visible_width), self.width()))
        if self._dock_side == ORB_PRESENTATION_DEFAULTS.edge_left:
            return geometry.x() - (self.width() - visible_width)
        return geometry.x() + geometry.width() - visible_width

    def _update_magnetic_offset(self):
        if self._is_roi_active() and not self._panel_visual_active():
            if self._dock_hidden:
                self._dock_hidden = False
                self._animate_dock_visibility(True)
            if self._magnet_offset != QPointF(0.0, 0.0):
                self._magnet_offset = QPointF(0.0, 0.0)
            self._cursor_proximity += (0.0 - self._cursor_proximity) * 0.25
            self._hover_target_active = False
            self.update()
            return

        if self._panel_visual_active():
            self._border_phase = (self._border_phase + 0.42) % 360.0
            self._cursor_proximity += (0.0 - self._cursor_proximity) * 0.22
            if self._magnet_offset != QPointF(0.0, 0.0):
                self._magnet_offset = QPointF(0.0, 0.0)
            self._menu_hover_top += (0.0 - self._menu_hover_top) * self.MENU_NODE_HOVER_LERP
            self._menu_hover_bottom += (0.0 - self._menu_hover_bottom) * self.MENU_NODE_HOVER_LERP
            self._hover_target_active = False
            self.update()
            return

        phase_step = 1.08 if self._starting_up else 0.42
        self._border_phase = (self._border_phase + phase_step + (self._cursor_proximity * 0.18)) % 360.0

        ring_target = max(0.0, min(1.0, float(self._hover_progress)))
        self._inner_ring_progress += (ring_target - self._inner_ring_progress) * 0.18

        if self._quitting:
            self.update()
            return

        if self._starting_up:
            # Startup interaction is blocked, so skip cursor/screen math to keep entry smooth.
            if self._magnet_offset != QPointF(0.0, 0.0):
                self._magnet_offset = QPointF(0.0, 0.0)
            if self._cursor_proximity > 0.0:
                self._cursor_proximity += (0.0 - self._cursor_proximity) * 0.25
            self.update()
            return

        if self._menu_interactions_blocked():
            self._update_menu_hover_state()
            if self._magnet_offset != QPointF(0.0, 0.0):
                self._magnet_offset = QPointF(0.0, 0.0)
            if self._cursor_proximity > 0.0:
                self._cursor_proximity += (0.0 - self._cursor_proximity) * 0.25
            self.update()
            return

        cursor_inside = self.rect().contains(self.mapFromGlobal(QCursor.pos()))
        if not self._dragging and not self._pressing:
            if cursor_inside and not self._hover_target_active:
                self._animate_hover(True)
            elif not cursor_inside and self._hover_target_active:
                self._animate_hover(False)

        if self._menu_hover_top > 0.001 or self._menu_hover_bottom > 0.001:
            self._menu_hover_top += (0.0 - self._menu_hover_top) * self.MENU_NODE_HOVER_LERP
            self._menu_hover_bottom += (0.0 - self._menu_hover_bottom) * self.MENU_NODE_HOVER_LERP

        if self._pressing and not self._dragging:
            self.update()
            return

        if self._dragging:
            if self._magnet_offset != QPointF(0.0, 0.0):
                self._magnet_offset = QPointF(0.0, 0.0)
        else:
            if self._dock_hidden and self._cursor_near_orb():
                self._reveal_from_edge()

            screen = self._screen_for_point(QCursor.pos())
            if screen is None:
                self.update()
                return

            cursor = QCursor.pos()
            center = self._interaction_reference_point()
            delta = QPointF(cursor.x() - center.x(), cursor.y() - center.y())
            distance = math.hypot(delta.x(), delta.y())
            proximity_window = 140.0
            if distance <= 0.01 or distance > proximity_window:
                target = QPointF(0.0, 0.0)
                self._cursor_proximity += (0.0 - self._cursor_proximity) * 0.14
            else:
                strength = (proximity_window - distance) / proximity_window
                self._cursor_proximity += (strength - self._cursor_proximity) * 0.12
                if self._magnetic_effect_enabled:
                    scale = min(7.0, 7.0 * (strength ** 1.15))
                    target = QPointF((delta.x() / distance) * scale, (delta.y() / distance) * scale)
                else:
                    target = QPointF(0.0, 0.0)

            # Never allow magnetic motion to push the orb closer into its docked edge.
            if self._magnetic_effect_enabled:
                if self._dock_side == ORB_PRESENTATION_DEFAULTS.edge_right:
                    target.setX(min(0.0, target.x()))
                else:
                    target.setX(max(0.0, target.x()))

                current = self._magnet_offset
                next_offset = QPointF(
                    current.x() + (target.x() - current.x()) * 0.14,
                    current.y() + (target.y() - current.y()) * 0.14,
                )
                if (abs(next_offset.x() - current.x()) > 0.01) or (abs(next_offset.y() - current.y()) > 0.01):
                    self._magnet_offset = next_offset
            elif self._magnet_offset != QPointF(0.0, 0.0):
                self._magnet_offset = QPointF(0.0, 0.0)
        if self._dragging:
            self._cursor_proximity += (0.0 - self._cursor_proximity) * 0.18

        self.update()

    def _draw_border_segments(self, painter: QPainter, orb_rect: QRectF, center: QPointF):
        border_rect = orb_rect.adjusted(-4.2, -4.2, 4.2, 4.2)
        ring_width = 2.3 if self._theme.name == "APPLE" else 2.05
        segment_span = 13.0
        slots = 8
        phase = self._border_phase % 360.0
        interaction_level = max(self._hover_progress, self._cursor_proximity, self._click_flash)
        alpha_multiplier = 0.50 + (interaction_level * 0.72)
        if self._dock_hidden:
            alpha_multiplier *= 0.84

        if self._theme.name == "APPLE":
            border_color = QColor(221, 221, 221, 232)
        else:
            border_color = QColor(self._theme.glow_color)
            border_color.setAlpha(236)

        painter.setBrush(Qt.NoBrush)
        for index in range(slots):
            angle = (phase + index * (360.0 / slots)) % 360.0
            distance_to_primary = min(abs(angle - phase), 360.0 - abs(angle - phase))
            distance_to_secondary = min(abs(angle - ((phase + 180.0) % 360.0)), 360.0 - abs(angle - ((phase + 180.0) % 360.0)))
            primary_mix = max(0.0, 1.0 - (distance_to_primary / 54.0))
            secondary_mix = max(0.0, 1.0 - (distance_to_secondary / 54.0))
            brightness = min(1.0, 0.50 + (primary_mix * 0.50) + (secondary_mix * 0.18))

            color = QColor(border_color)
            color.setAlphaF(max(0.22, min(1.0, color.alphaF() * brightness * alpha_multiplier)))
            pen = QPen(color, ring_width)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.drawArc(border_rect, int((90.0 - (angle + segment_span * 0.5)) * 16), int(segment_span * 16))

    def _clamp_to_screen(self, position: QPoint, screen) -> QPoint:
        geometry = screen.availableGeometry()
        canvas_shift = int((self.width() - self.DOCK_WIDGET_DIAMETER) / 2)
        min_x = geometry.left() - int(self.VISIBLE_OVERHANG_PX) - canvas_shift
        max_x = geometry.right() - self.DOCK_WIDGET_DIAMETER + 1 + int(self.VISIBLE_OVERHANG_PX) - canvas_shift
        x = max(min_x, min(position.x(), max_x))
        y = self._clamp_y(position.y(), geometry)
        return QPoint(x, y)

    def _clamp_y(self, y_position: int, geometry) -> int:
        return max(geometry.y(), min(y_position, geometry.y() + geometry.height() - self.height()))

    def _screen_for_point(self, point: QPoint):
        screen = QGuiApplication.screenAt(point)
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        return screen

    def _orb_center_point(self) -> QPoint:
        return QPoint(self.pos().x() + (self.width() // 2), self.pos().y() + (self.height() // 2))
