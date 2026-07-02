"""D-Bus ScreenSaver listener.

Listens on the **session bus** for ``org.freedesktop.ScreenSaver``'s
``ActiveChanged`` signal and pauses the media canvas when the screen
blanks, resumes it when the screen wakes.

Why QtDBus and not dbus-python / pydbus / jeepney?
-------------------------------------------------
We are already inside a Qt event loop. QtDBus integrates with that
loop natively — there is no GLib-to-Qt bridge to maintain, no
``QSocketNotifier`` plumbing, and no second event loop to spin. The
trade-off is a slightly more verbose Qt-style API, which is fine for
a single signal we only ever subscribe to.

What "ActiveChanged" means on a typical Wayland session
--------------------------------------------------------
GNOME / KDE ship a real ``org.freedesktop.ScreenSaver`` service.
On Hyprland the service is provided by ``xdg-desktop-portal``'s
``Screensaver`` portal or, if no portal is running, by
``gsd-screensaver-proxy`` from GNOME Settings Daemon. If no
service is registered the signal simply never fires; we treat that
as a no-op and the user can still pause via the tray.

User-pause vs auto-pause
------------------------
If the user has manually paused via the tray, we must not auto-resume
the pet when the display wakes. The watcher remembers the canvas
state at sleep-start and only reverts its own pause on wake.
"""
from __future__ import annotations

import sys
from typing import Optional, TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal

if TYPE_CHECKING:
    from lovely_pet.media import MediaCanvas

SCREENSAVER_BUS_NAME = "org.freedesktop.ScreenSaver"
SCREENSAVER_OBJECT_PATH = "/org/freedesktop/ScreenSaver"
SCREENSAVER_INTERFACE = "org.freedesktop.ScreenSaver"


class SleepWatcher(QObject):
    """Pauses / resumes a :class:`MediaCanvas` in response to the
    display-sleep D-Bus signal.

    Signals
    -------
    sleepStarted()
        Emitted when the screensaver / display blank is active.
    sleepEnded()
        Emitted when the display is awake again.
    """

    sleepStarted = pyqtSignal()
    sleepEnded = pyqtSignal()

    def __init__(self, canvas: "MediaCanvas", parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._canvas = canvas
        self._connected: bool = False
        # True if we paused the canvas ourselves on sleep and therefore
        # owe a resume on wake. False if the user had already paused
        # manually — in which case we leave them alone.
        self._auto_paused: bool = False

        self.sleepStarted.connect(self._on_sleep_started)
        self.sleepEnded.connect(self._on_sleep_ended)

        self._connect()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def is_connected(self) -> bool:
        """True if the D-Bus signal subscription actually went through."""
        return self._connected

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def _connect(self) -> None:
        try:
            from PyQt6.QtDBus import QDBusConnection
        except ImportError as exc:
            print(
                f"[lovely-pet] QtDBus not available: {exc}. "
                "Sleep-aware pausing is disabled.",
                file=sys.stderr,
            )
            return

        bus = QDBusConnection.sessionBus()
        if not bus.isConnected():
            print(
                "[lovely-pet] no D-Bus session bus available; "
                "sleep-aware pausing is disabled.",
                file=sys.stderr,
            )
            return

        ok = bus.connect(
            SCREENSAVER_BUS_NAME,
            SCREENSAVER_OBJECT_PATH,
            SCREENSAVER_INTERFACE,
            "ActiveChanged",
            self,                          # receiver (must be a QObject)
            self._handle_active_changed,   # slot (bound method)
        )
        if not ok:
            print(
                "[lovely-pet] could not subscribe to "
                "org.freedesktop.ScreenSaver.ActiveChanged; "
                "sleep-aware pausing is disabled.",
                file=sys.stderr,
            )
            return

        self._connected = True

    # ------------------------------------------------------------------
    # D-Bus callback
    # ------------------------------------------------------------------
    def _handle_active_changed(self, active: bool) -> None:
        if bool(active):
            self.sleepStarted.emit()
        else:
            self.sleepEnded.emit()

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------
    def _on_sleep_started(self) -> None:
        # If the user had already paused, don't touch it; the canvas
        # was paused by their choice, not by us, and we must not
        # "resume" something we didn't pause.
        if self._canvas.is_paused():
            self._auto_paused = False
            return
        self._canvas.pause()
        self._auto_paused = True

    def _on_sleep_ended(self) -> None:
        if self._auto_paused:
            self._canvas.resume()
        self._auto_paused = False


__all__ = ["SleepWatcher"]
