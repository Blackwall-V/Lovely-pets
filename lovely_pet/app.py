"""QApplication setup with strict Wayland enforcement.

The order of operations here is deliberate:

1. Set ``QT_QPA_PLATFORM=wayland`` and friends via ``os.environ`` *before*
   importing any PyQt6 module. Qt reads these at import time and locks
   the platform plugin in place; mutating them later is a no-op.
2. Build the ``QApplication`` and assign the metadata Hyprland uses to
   match window rules (``WM_CLASS`` derives from ``applicationName``).
3. Assert that the chosen platform plugin really is Wayland. If a user
   is missing ``qt6-wayland`` Qt silently falls back to ``xcb`` and
   Xwayland is launched, defeating the entire point of this app.
"""
from __future__ import annotations

import os
import sys
from typing import Sequence

# These names are also used by Hyprland windowrulev2 directives; keep
# them in sync with hyprland/windowrulev2.conf.
APP_NAME = "lovely-pet"
ORG_NAME = "lovely-pet"
APP_DISPLAY_NAME = "Lovely Pet"


def configure_wayland_env() -> None:
    """Force the Wayland platform plugin.

    ``setdefault`` is used (not assignment) so a user who already
    exported ``QT_QPA_PLATFORM=wayland`` from their compositor session
    is left alone, and a user running inside a nested X session gets a
    clear error from the runtime assert below rather than a silent
    override.
    """
    os.environ.setdefault("QT_QPA_PLATFORM", "wayland")
    # Suppress server-side window decoration; we draw our own frameless
    # window in lovely_pet.window.PetWindow.
    os.environ.setdefault("QT_WAYLAND_DISABLE_WINDOWDECORATION", "1")
    # Disable Qt's automatic high-DPI scaling of raster bitmaps, which
    # can shred alpha edges on transparent GIFs. We resize via QPainter.
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "0")


def _assert_wayland(app) -> None:
    """Fail fast if Qt silently fell back to Xwayland.

    A missing ``qt6-wayland`` system package is the usual cause. The
    error message tells the user exactly what to install.
    """
    name = app.platformName().lower()
    if name != "wayland":
        raise RuntimeError(
            f"Lovely-pets requires Wayland but Qt loaded the '{name}' "
            "platform plugin (Xwayland fallback). Install qt6-wayland "
            "and ensure QT_QPA_PLATFORM=wayland is honored by your "
            "compositor. On Arch: 'pacman -S qt6-wayland'. On Debian: "
            "'apt install qml6-module-qtquick' (pulls qt6-wayland)."
        )


def build_application(argv: Sequence[str]) -> "QApplication":
    """Build and return a fully configured QApplication.

    Importing PyQt6 here (rather than at module top) guarantees the
    env-var configuration runs first.
    """
    configure_wayland_env()

    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QGuiApplication
    from PyQt6.QtWidgets import QApplication

    # QApplication (not QGuiApplication) is required for QSystemTrayIcon
    # and other widgets we will add in later phases.
    app = QApplication(list(argv))
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)
    # High-DPI pixmaps off; we render via QPainter at the size we want.
    app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, False)

    _assert_wayland(app)
    return app


def install_signal_handlers(app) -> None:
    """Wire SIGINT and SIGTERM to QApplication.quit for clean shutdown."""
    import signal

    signal.signal(signal.SIGINT, lambda *_: app.quit())
    signal.signal(signal.SIGTERM, lambda *_: app.quit())
