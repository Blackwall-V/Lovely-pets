"""System tray integration via AppIndicator3 (StatusNotifierItem).

Why not ``QSystemTrayIcon``?
----------------------------
Qt's ``QSystemTrayIcon`` ships an XEmbed / freedesktop legacy tray
protocol implementation that Wayland compositors generally ignore.
On Hyprland, only the StatusNotifierItem D-Bus interface (the SNI
spec) is wired up. AppIndicator3 is the canonical C/GLib
implementation of that spec; we use it through PyGObject so the
whole stack is GTK-on-the-tray-side, Qt-on-the-everything-else-side.

GTK ↔ Qt bridging
-----------------
GTK has its own main loop. We pump pending GTK events from a
``QTimer`` at 100 ms; the latency is invisible for a click-to-open
menu, and it avoids the much more involved ``QSocketNotifier`` +
``Glib.MainContext`` integration that a real-time bridge would need.
"""
from __future__ import annotations

import os
import sys
from typing import Callable, Optional, TYPE_CHECKING

from PyQt6.QtCore import QTimer

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget

# Theme icon candidates, tried in order. We try several because
# distros ship wildly different icon sets.
_ICON_CANDIDATES = (
    "preferences-system",
    "applications-multimedia",
    "multimedia",
    "video-display",
    "emblem-system",
    "image-x-generic",
    "applications-other",
)

# Required GLib main loop pump interval in ms.
_GTK_PUMP_INTERVAL_MS = 100


class TrayIcon:
    """AppIndicator3-backed system tray for Lovely-pets.

    All callbacks are invoked on the Qt main thread (the GTK pump
    timer fires from ``QTimer.timeout``).

    If AppIndicator3 is unavailable (missing system packages), the
    tray degrades to a no-op: no exception is raised, the app still
    runs and is killable via Ctrl-C. A warning is printed to stderr
    on first use.
    """

    def __init__(
        self,
        on_load: Callable[[], None],
        on_pause_resume: Callable[[], None],
        on_quit: Callable[[], None],
        parent: Optional["QWidget"] = None,
    ) -> None:
        self._on_load = on_load
        self._on_pause_resume = on_pause_resume
        self._on_quit = on_quit
        self._parent = parent
        self._available: bool = False

        self._indicator = None
        self._menu = None
        self._pause_item = None  # type: ignore[var-annotated]
        self._pump_timer: Optional[QTimer] = None

        self._init_indicator()
        self._init_gtk_pump()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def is_available(self) -> bool:
        """True if a real AppIndicator is in use; False if we degraded."""
        return self._available

    def update_pause_label(self, paused: bool) -> None:
        """Refresh the Pause/Resume menu item label without a rebuild."""
        if not self._available or self._pause_item is None:
            return
        self._pause_item.set_label("Resume" if paused else "Pause")

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def _init_indicator(self) -> None:
        try:
            import gi

            gi.require_version("AppIndicator3", "0.1")
            gi.require_version("Gtk", "3.0")
            from gi.repository import AppIndicator3, Gtk  # noqa: F401
        except (ImportError, ValueError) as exc:
            print(
                "[lovely-pet] AppIndicator3 not available: "
                f"{exc}. The tray icon will not appear; use Ctrl-C to quit.",
                file=sys.stderr,
            )
            return

        # gi is importable; we re-import here to keep the
        # type-only references out of the runtime path.
        from gi.repository import AppIndicator3, Gtk  # type: ignore[no-redef]

        try:
            icon_name = self._pick_icon_name()
            self._indicator = AppIndicator3.Indicator.new(
                "lovely-pet",
                icon_name,
                AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
            )
            self._indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        except Exception as exc:  # noqa: BLE001 — libappindicator raises broadly
            print(
                f"[lovely-pet] could not create AppIndicator3: {exc}",
                file=sys.stderr,
            )
            return

        self._menu = Gtk.Menu()

        load_item = Gtk.MenuItem(label="Load Pet...")
        load_item.connect("activate", self._handle_load)
        self._menu.append(load_item)

        self._pause_item = Gtk.MenuItem(label="Pause")
        self._pause_item.connect("activate", self._handle_pause_resume)
        self._menu.append(self._pause_item)

        # Visual separator.
        sep = Gtk.SeparatorMenuItem()
        self._menu.append(sep)

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", self._handle_quit)
        self._menu.append(quit_item)

        # show_all() recurses through children.
        self._menu.show_all()
        self._indicator.set_menu(self._menu)
        self._available = True

    def _init_gtk_pump(self) -> None:
        """Process pending GTK events from the Qt event loop.

        Without this, GTK menu clicks would never be observed because
        Qt owns the main loop. 100 ms is a fine cadence: tray menus
        are user-initiated, not latency-sensitive.
        """
        if not self._available:
            return
        self._pump_timer = QTimer()
        self._pump_timer.setInterval(_GTK_PUMP_INTERVAL_MS)
        self._pump_timer.timeout.connect(self._pump_gtk)
        self._pump_timer.start()

    def _pump_gtk(self) -> None:
        try:
            from gi.repository import Gtk

            # events_pending() is a static method on Gtk in PyGObject.
            while Gtk.events_pending():
                Gtk.main_iteration_do(False)
        except Exception:  # noqa: BLE001
            # If GTK ever goes away (it shouldn't, but…), stop pumping.
            if self._pump_timer is not None:
                self._pump_timer.stop()

    def _pick_icon_name(self) -> str:
        """Return the first icon name that exists in the icon theme.

        We probe via ``Gtk.IconTheme`` because passing a non-existent
        icon name to AppIndicator3 makes the indicator render as a
        blank square.
        """
        try:
            from gi.repository import Gtk

            theme = Gtk.IconTheme.get_default()
            for name in _ICON_CANDIDATES:
                if theme.has_icon(name):
                    return name
        except Exception:  # noqa: BLE001
            pass
        return _ICON_CANDIDATES[0]

    # ------------------------------------------------------------------
    # Menu callbacks
    # ------------------------------------------------------------------
    def _handle_load(self, _item) -> None:
        try:
            self._on_load()
        except Exception as exc:  # noqa: BLE001
            print(f"[lovely-pet] load failed: {exc}", file=sys.stderr)

    def _handle_pause_resume(self, _item) -> None:
        try:
            self._on_pause_resume()
        except Exception as exc:  # noqa: BLE001
            print(f"[lovely-pet] pause toggle failed: {exc}", file=sys.stderr)

    def _handle_quit(self, _item) -> None:
        try:
            self._on_quit()
        except Exception as exc:  # noqa: BLE001
            print(f"[lovely-pet] quit failed: {exc}", file=sys.stderr)


__all__ = ["TrayIcon"]
