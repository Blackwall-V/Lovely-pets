"""PetWindow: frameless, transparent, draggable overlay.

The window is NOT click-through. The Hyprland Lua API (0.55.4) does
not have a ``passthrough`` field, so compositor-level click-through
is impossible. Instead, the window receives mouse events directly:

* **Left-drag** moves the pet anywhere on screen.
* **Right-click** opens a context menu (resize, reposition, pause,
  load, quit) — see :func:`lovely_pet.menu.build_context_menu`.

The actual animated content is drawn by a child ``MediaCanvas``.
PetWindow's only job is to host that canvas, size it, place it, and
forward mouse interactions.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QPoint, QRect, QSize, Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QWidget

from lovely_pet.position import Corner

DEFAULT_MARGIN_PX = 32
MAX_SCREEN_FRACTION = 0.8  # Allow larger pets now that user can resize


def _anchor_position(
    screen_rect: QRect,
    window_size: QSize,
    corner: Corner,
    margin: int,
) -> QPoint:
    if corner is Corner.TOP_LEFT:
        return QPoint(screen_rect.left() + margin, screen_rect.top() + margin)
    if corner is Corner.TOP_RIGHT:
        return QPoint(
            screen_rect.right() - window_size.width() - margin,
            screen_rect.top() + margin,
        )
    if corner is Corner.BOTTOM_LEFT:
        return QPoint(
            screen_rect.left() + margin,
            screen_rect.bottom() - window_size.height() - margin,
        )
    if corner is Corner.CENTER:
        return QPoint(
            screen_rect.center().x() - window_size.width() // 2,
            screen_rect.center().y() - window_size.height() // 2,
        )
    return QPoint(
        screen_rect.right() - window_size.width() - margin,
        screen_rect.bottom() - window_size.height() - margin,
    )


class PetWindow(QWidget):
    """Frameless, transparent, draggable pet window."""

    def __init__(
        self,
        corner: Corner = Corner.BOTTOM_RIGHT,
        margin: int = DEFAULT_MARGIN_PX,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        # Frameless, on-top, no taskbar entry, no drop shadow.
        # WindowTransparentForInput is REMOVED — we need mouse events
        # for drag + right-click menu. Click-through is not possible
        # with the current Hyprland Lua API anyway (no passthrough field).
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint
        )

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

        self._corner = corner
        self._margin = margin
        self._drag_offset: Optional[QPoint] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_corner(self, corner: Corner) -> None:
        self._corner = corner
        self._reposition()

    def set_margin(self, margin: int) -> None:
        self._margin = max(0, int(margin))
        self._reposition()

    def apply_position(self) -> None:
        self._reposition()

    def resize_to(self, size: QSize) -> None:
        clamped = self._clamp_size(size)
        if clamped == self.size():
            return
        self.resize(clamped)

    # ------------------------------------------------------------------
    # Drag support
    # ------------------------------------------------------------------
    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.pos()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    # ------------------------------------------------------------------
    # Layout helpers
    # ------------------------------------------------------------------
    def _clamp_size(self, size: QSize) -> QSize:
        screen = QGuiApplication.screenAt(self.pos()) or QGuiApplication.primaryScreen()
        if screen is None:
            return size
        avail = screen.availableGeometry().size()
        max_w = int(avail.width() * MAX_SCREEN_FRACTION)
        max_h = int(avail.height() * MAX_SCREEN_FRACTION)
        w = min(max(1, size.width()), max_w)
        h = min(max(1, size.height()), max_h)
        return QSize(w, h)

    def _reposition(self) -> None:
        screen = QGuiApplication.screenAt(self.pos()) or QGuiApplication.primaryScreen()
        if screen is None:
            return
        rect = screen.availableGeometry()
        target = _anchor_position(rect, self.size(), self._corner, self._margin)
        self.move(target)
