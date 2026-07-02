"""PetWindow: frameless, transparent, click-through overlay.

The window flag combination is what makes a Wayland compositor treat
this as a non-interactive overlay. Hyprland's windowrulev2 directives
in ``hyprland/windowrulev2.conf`` then pin the window across all
workspaces, float it above tiled clients, and enable ``passthrough``
so the compositor itself ignores mouse hits on this surface.

The actual animated content is drawn by a child ``MediaCanvas``
(see :mod:`lovely_pet.media`). PetWindow's only job is to host that
canvas, size it, and place it on the right monitor at the right
corner.

Position strategy
-----------------
Default placement is the bottom-right corner of the primary screen
with a configurable margin. The compositor's ``availableGeometry``
excludes taskbars / docks so the pet always sits on visible pixels.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QPoint, QRect, QSize, Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QWidget

from lovely_pet.position import Corner

DEFAULT_MARGIN_PX = 32
MAX_SCREEN_FRACTION = 0.5  # Cap pet size at half the screen


def _anchor_position(
    screen_rect: QRect,
    window_size: QSize,
    corner: Corner,
    margin: int,
) -> QPoint:
    """Return the top-left QPoint for a window of ``window_size`` anchored
    at ``corner`` inside ``screen_rect`` with ``margin`` pixels of breathing
    room from the screen edges.
    """
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
    # BOTTOM_RIGHT
    return QPoint(
        screen_rect.right() - window_size.width() - margin,
        screen_rect.bottom() - window_size.height() - margin,
    )


class PetWindow(QWidget):
    """A frameless, transparent, click-through overlay window.

    Set the media content by populating this window with a single
    child widget (typically ``MediaCanvas``) that fills the entire
    rect. The window itself never paints; it is a positioning shell.
    """

    def __init__(
        self,
        corner: Corner = Corner.BOTTOM_RIGHT,
        margin: int = DEFAULT_MARGIN_PX,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        # --- Window flags ------------------------------------------------
        # FramelessWindowHint: no title bar, no borders.
        # WindowStaysOnTopHint: above all normal windows.
        # Tool: not in the taskbar / pager; not part of the task switcher.
        # WindowTransparentForInput: Qt-level click-through. On Wayland
        #   this works on the Wayland-EGL / QtWayland backend in
        #   conjunction with the Hyprland ``passthrough`` rule.
        # WindowDoesNotAcceptFocus: never takes keyboard focus.
        # NoDropShadowWindowHint: we have transparent pixels, a server-
        #   side shadow would draw a black box around the pet.
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.NoDropShadowWindowHint
        )

        # --- Per-pixel alpha --------------------------------------------
        # Without this Qt fills the widget rect with the palette base
        # colour (usually black) and we lose the GIF's transparency.
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        # No system background; we paint our own (transparent) pixels.
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        # Don't accept focus via Tab navigation.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._corner = corner
        self._margin = margin

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_corner(self, corner: Corner) -> None:
        """Move the pet to a different anchor corner of the active screen."""
        self._corner = corner
        self._reposition()

    def set_margin(self, margin: int) -> None:
        """Change the distance from the screen edge in pixels."""
        self._margin = max(0, int(margin))
        self._reposition()

    def apply_position(self) -> None:
        """Public alias for the internal anchor calculation.

        Call this after ``show()`` to re-anchor the window — some
        Wayland compositors reposition mapped windows before they
        become visible, and a no-op reposition after show is the
        cheapest way to recover the bottom-right corner.
        """
        self._reposition()

    def resize_to(self, size: QSize) -> None:
        """Resize the window while honouring the screen-size cap."""
        clamped = self._clamp_size(size)
        if clamped == self.size():
            return
        self.resize(clamped)
        self._reposition()

    # ------------------------------------------------------------------
    # Layout helpers
    # ------------------------------------------------------------------
    def _clamp_size(self, size: QSize) -> QSize:
        """Cap the pet at MAX_SCREEN_FRACTION of the screen so a giant
        source image cannot cover the entire desktop.
        """
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
        """Move the window to its anchored position on the active screen.

        Safe to call before ``show()`` — the move is buffered and
        applied at the next expose. The previous implementation
        early-returned on ``not self.isVisible()``, which left the
        window at Qt's default (0, 0) on first launch and made the
        pet look like a normal top-left app window.
        """
        screen = QGuiApplication.screenAt(self.pos()) or QGuiApplication.primaryScreen()
        if screen is None:
            return
        rect = screen.availableGeometry()
        target = _anchor_position(rect, self.size(), self._corner, self._margin)
        self.move(target)

    # ------------------------------------------------------------------
    # Event filters
    # ------------------------------------------------------------------
    def moveEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().moveEvent(event)
        # If the user moves us between monitors (e.g. via a Hyprland
        # window rule or a future drag handle), re-clamp to the new
        # screen's geometry.
        screen = QGuiApplication.screenAt(self.pos())
        if screen is not None and screen != QGuiApplication.primaryScreen():
            avail = screen.availableGeometry()
            new_pos = _anchor_position(avail, self.size(), self._corner, self._margin)
            if self.pos() != new_pos:
                self.move(new_pos)
