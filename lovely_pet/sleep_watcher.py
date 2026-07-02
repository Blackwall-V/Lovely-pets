"""D-Bus ScreenSaver listener.

NOTE: Currently a no-op. The synchronous D-Bus call froze the app
when no screensaver service was registered, and the async
``callWithCallback`` crashed because PyQt6 requires ``@pyqtSlot``
decoration with exact argument types that we can't know at
runtime. The feature will be re-enabled when a reliable D-Bus
binding is available.

The user can pause/resume manually via the right-click context
menu or the system tray.
"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from PyQt6.QtCore import QObject

if TYPE_CHECKING:
    from lovely_pet.media import MediaCanvas


class SleepWatcher(QObject):
    """No-op placeholder. Always reports disconnected."""

    def __init__(self, canvas: "MediaCanvas", parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._canvas = canvas

    def is_connected(self) -> bool:
        return False


__all__ = ["SleepWatcher"]
