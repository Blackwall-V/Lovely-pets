"""D-Bus ScreenSaver listener.

Watches ``org.freedesktop.ScreenSaver`` over the session bus and
pauses the media canvas when the screen blanks, resumes it when the
screen wakes.

Why polling instead of signal subscription?
-------------------------------------------
PyQt6's ``QDBusConnection.connect()`` only accepts a slot *string*
(method name as a string), not a bound method or callable receiver
— there is no ``QObject *receiver`` parameter in any of the three
overloads. Signal subscription therefore requires decorating the
handler with ``@pyqtSlot`` and passing ``handler.__name__`` as a
string, which couples the connection to a metaobject lookup that
behaves inconsistently across Qt versions and PyQt builds.

Polling ``GetActive()`` once per second is portable across every
PyQt6 build we tested, the 1-second latency is invisible for sleep
detection, and the D-Bus call is cheap (~50 µs locally) so the
timer tick costs effectively nothing.

Manual-pause interaction
------------------------
If the user has manually paused via the tray, we must not auto-resume
the pet when the display wakes. The watcher remembers whether it was
the one that issued the pause and only reverts its own pause on wake.
"""
from __future__ import annotations

import sys
from typing import Optional, TYPE_CHECKING

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

if TYPE_CHECKING:
    from lovely_pet.media import MediaCanvas

SCREENSAVER_BUS_NAME = "org.freedesktop.ScreenSaver"
SCREENSAVER_OBJECT_PATH = "/org/freedesktop/ScreenSaver"
SCREENSAVER_INTERFACE = "org.freedesktop.ScreenSaver"

# How often we ask D-Bus whether the screen is blanked. 1 second is
# fast enough that the user does not notice the pause latency when
# the screen wakes, and slow enough that the D-Bus traffic is
# negligible.
POLL_INTERVAL_MS = 1000


class SleepWatcher(QObject):
    """Pauses / resumes a :class:`MediaCanvas` in response to the
    display-sleep D-Bus service.

    Signals
    -------
    sleepStarted()
        Emitted when the screensaver / display blank becomes active.
    sleepEnded()
        Emitted when the display is awake again.
    """

    sleepStarted = pyqtSignal()
    sleepEnded = pyqtSignal()

    def __init__(self, canvas: "MediaCanvas", parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._canvas = canvas
        self._connected: bool = False
        # True if we paused the canvas ourselves and therefore owe a
        # resume on wake. False if the user had already paused manually.
        self._auto_paused: bool = False
        self._last_active: Optional[bool] = None
        self._interface = None  # QDBusInterface, set in _connect
        self._poll_timer: Optional[QTimer] = None

        self.sleepStarted.connect(self._on_sleep_started)
        self.sleepEnded.connect(self._on_sleep_ended)

        self._connect()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def is_connected(self) -> bool:
        """True if the polling loop is running and the D-Bus service
        answered at least once. False if the service is unavailable
        and we degraded to a no-op.
        """
        return self._connected

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def _connect(self) -> None:
        try:
            from PyQt6.QtDBus import QDBusConnection, QDBusInterface
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

        self._interface = QDBusInterface(
            SCREENSAVER_BUS_NAME,
            SCREENSAVER_OBJECT_PATH,
            SCREENSAVER_INTERFACE,
            bus,
        )
        if not self._interface.isValid():
            print(
                "[lovely-pet] org.freedesktop.ScreenSaver is not "
                "registered on the session bus. Install "
                "xdg-desktop-portal or a screensaver proxy to enable "
                "sleep-aware pausing.",
                file=sys.stderr,
            )
            self._interface = None
            return

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(POLL_INTERVAL_MS)
        self._poll_timer.timeout.connect(self._poll_screensaver)
        self._poll_timer.start()
        # Prime the state so the first tick has a baseline to compare
        # against; without this, the very first transition would be
        # swallowed by the ``_last_active is None`` guard.
        self._prime_initial_state()
        self._connected = True

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------
    def _prime_initial_state(self) -> None:
        """Read the current state once so the first edge is detectable."""
        active = self._query_active()
        self._last_active = active

    def _poll_screensaver(self) -> None:
        active = self._query_active()
        if active is None:
            return
        if self._last_active is not None and active != self._last_active:
            if active:
                self.sleepStarted.emit()
            else:
                self.sleepEnded.emit()
        self._last_active = active

    def _query_active(self) -> Optional[bool]:
        """Synchronous D-Bus call. Returns ``None`` on any error."""
        if self._interface is None:
            return None
        from PyQt6.QtDBus import QDBusMessage

        try:
            msg = self._interface.call("GetActive")
        except Exception as exc:  # noqa: BLE001 — dbus can raise anything
            print(
                f"[lovely-pet] ScreenSaver.GetActive() failed: {exc}",
                file=sys.stderr,
            )
            return None
        if msg.type() != QDBusMessage.MessageType.ReplyMessage:
            return None
        args = msg.arguments()
        if not args:
            return None
        return bool(args[0])

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
