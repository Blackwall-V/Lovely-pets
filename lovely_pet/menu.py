"""Right-click context menu for the pet window.

Provides resize presets (25%–200%), corner repositioning,
pause/resume, load pet, and quit — all in a Qt ``QMenu`` that
works natively on Wayland (no GTK dependency for this menu).

The menu is built fresh each time the user right-clicks, so it
always reflects the current pause state and source path.
"""
from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import QFileDialog, QMenu

from lovely_pet.media import file_dialog_filter
from lovely_pet.position import Corner

if TYPE_CHECKING:
    from lovely_pet.media import MediaCanvas
    from lovely_pet.window import PetWindow

# Resize presets in percent of native source size.
SIZE_PRESETS = [25, 50, 75, 100, 125, 150, 200]


def _apply_scale(window: "PetWindow", canvas: "MediaCanvas", pct: int) -> None:
    """Resize the window to ``pct`` percent of the canvas's native size."""
    native = canvas.native_size()
    if not native.isValid():
        return
    scaled = QSize(
        max(1, int(native.width() * pct / 100)),
        max(1, int(native.height() * pct / 100)),
    )
    window.resize_to(scaled)


def _apply_corner(window: "PetWindow", corner: Corner) -> None:
    window.set_corner(corner)


def _load_pet(window: "PetWindow", canvas: "MediaCanvas") -> None:
    start_dir = os.path.expanduser("~")
    current = canvas.source_path()
    if current and os.path.isfile(current):
        start_dir = os.path.dirname(current)
    path, _ = QFileDialog.getOpenFileName(
        window,
        "Load Pet",
        start_dir,
        file_dialog_filter(),
    )
    if not path:
        return
    try:
        canvas.set_source(path)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"[lovely-pet] could not load {path!r}: {exc}", file=sys.stderr)
        return
    native = canvas.native_size()
    if native.isValid():
        window.resize_to(native)


def build_context_menu(
    window: "PetWindow",
    canvas: "MediaCanvas",
    on_quit,
) -> QMenu:
    """Build and return a context menu. Caller execs it."""
    menu = QMenu(window)
    menu.setWindowTitle("Lovely Pet")

    # --- Resize submenu ------------------------------------------------
    resize_menu = menu.addMenu("Resize")
    for pct in SIZE_PRESETS:
        action = resize_menu.addAction(f"{pct}%")
        action.triggered.connect(
            lambda checked, p=pct: _apply_scale(window, canvas, p)
        )

    # --- Position submenu ----------------------------------------------
    pos_menu = menu.addMenu("Move to corner")
    for corner in Corner:
        action = pos_menu.addAction(corner.value.replace("-", " ").title())
        action.triggered.connect(
            lambda checked, c=corner: _apply_corner(window, c)
        )

    menu.addSeparator()

    # --- Pause / Resume ------------------------------------------------
    pause_label = "Resume" if canvas.is_paused() else "Pause"
    pause_action = menu.addAction(pause_label)
    def _toggle_pause():
        if canvas.is_paused():
            canvas.resume()
        else:
            canvas.pause()
    pause_action.triggered.connect(_toggle_pause)

    # --- Load Pet ------------------------------------------------------
    load_action = menu.addAction("Load Pet...")
    load_action.triggered.connect(lambda: _load_pet(window, canvas))

    menu.addSeparator()

    # --- Quit ----------------------------------------------------------
    quit_action = menu.addAction("Quit")
    quit_action.triggered.connect(on_quit)

    return menu
