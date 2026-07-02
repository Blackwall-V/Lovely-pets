#!/usr/bin/env python3
"""Entry point for the Lovely-pets desktop pet.

Usage:
    python pet.py                       # launch with bundled sample
    python pet.py /path/to/pet.gif      # launch with a specific pet
    python pet.py --size 50             # scale to 50% of native size
    python pet.py --corner top-left     # pin to a different corner
    python pet.py --init-config         # write a sample config and exit
    python pet.py --print-config        # print effective config and exit
    python pet.py --help                # show full options
"""
import os
import sys

from lovely_pet.cli import parse_args
from lovely_pet.config import (
    DEFAULT_CONFIG_PATH,
    PetConfig,
    load_config,
    write_sample_config,
)

DEFAULT_SAMPLE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "assets", "sample_pet.gif"
)


def _debug_log(enabled: bool, *parts) -> None:
    if not enabled:
        return
    print("[lovely-pet]", *parts, file=sys.stderr)


def _tray_load(window, canvas) -> None:
    """Open a QFileDialog and load the picked file into the canvas."""
    from PyQt6.QtWidgets import QFileDialog

    from lovely_pet.media import file_dialog_filter

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
        return  # user cancelled
    try:
        canvas.set_source(path)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"[lovely-pet] could not load {path!r}: {exc}", file=sys.stderr)
        return
    native = canvas.native_size()
    if native.isValid():
        window.resize_to(native)


def _tray_toggle_pause(tray, canvas) -> None:
    """Flip the canvas pause state and update the tray menu label."""
    if canvas.is_paused():
        canvas.resume()
    else:
        canvas.pause()
    tray.update_pause_label(canvas.is_paused())


def main() -> int:
    # --- Load config (CLI defaults) and parse args -------------------
    config_path = os.environ.get("LOVELY_PET_CONFIG") or DEFAULT_CONFIG_PATH
    config = load_config(config_path)

    args = parse_args(sys.argv[1:], config=config, config_path=config_path)
    _debug_log(args.debug, f"loaded config from {config_path}")
    _debug_log(args.debug, f"effective args: {args}")

    # --- Handle --init-config -----------------------------------------
    # No Qt needed; do this first so it works in a headless terminal.
    if args.init_config:
        try:
            path = write_sample_config()
        except FileExistsError as exc:
            print(f"[lovely-pet] {exc}", file=sys.stderr)
            return 1
        print(f"[lovely-pet] wrote sample config to {path}")
        return 0

    # --- Handle --print-config ----------------------------------------
    if args.print_config:
        print("[lovely-pet] effective configuration:")
        print(f"  source       = {args.source!r}")
        print(f"  size_percent = {args.size_percent}")
        print(f"  corner       = {args.corner.value}")
        print(f"  margin       = {args.margin}")
        print(f"  debug        = {args.debug}")
        return 0

    # Defer Qt imports until we actually want to build a window.
    from lovely_pet.app import build_application, install_signal_handlers
    from lovely_pet.media import MediaCanvas
    from lovely_pet.sleep_watcher import SleepWatcher
    from lovely_pet.tray import TrayIcon
    from lovely_pet.window import PetWindow

    app = build_application(sys.argv)
    install_signal_handlers(app)
    _debug_log(args.debug, f"Qt platform: {app.platformName()}")
    _debug_log(
        args.debug,
        f"Hyprland WM_CLASS match: applicationName={app.applicationName()!r} "
        f"(must equal 'lovely-pet' for windowrulev2 to apply)",
    )

    window = PetWindow(corner=args.corner, margin=args.margin)
    window.setWindowTitle("Lovely Pet")

    canvas = MediaCanvas(window)
    source = args.source if args.source is not None else DEFAULT_SAMPLE
    _debug_log(args.debug, f"loading source: {source!r}")

    if os.path.isfile(source):
        try:
            canvas.set_source(source)
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            print(
                f"[lovely-pet] could not load {source!r}: {exc}",
                file=sys.stderr,
            )
    else:
        print(
            f"[lovely-pet] no source file at {source!r}. "
            "Provide a path on the command line, set `source =` in "
            "~/.config/lovely-pet/config.ini, or use the tray "
            "'Load Pet...' menu to pick one.",
            file=sys.stderr,
        )
        window.resize(128, 128)  # visible placeholder for empty state

    native = canvas.native_size()
    if native.isValid():
        if args.size_percent != 100:
            scaled = native * (args.size_percent / 100.0)
            scaled.setWidth(max(1, int(scaled.width())))
            scaled.setHeight(max(1, int(scaled.height())))
            window.resize_to(scaled)
        else:
            window.resize_to(native)

    # --- System tray ---------------------------------------------------
    # The tray degrades gracefully if AppIndicator3 is missing; the app
    # is still killable via Ctrl-C.
    tray = TrayIcon(
        on_load=lambda: _tray_load(window, canvas),
        on_pause_resume=lambda: _tray_toggle_pause(tray, canvas),
        on_quit=app.quit,
    )
    if not tray.is_available():
        print(
            "[lovely-pet] running without tray icon. Use Ctrl-C to quit.",
            file=sys.stderr,
        )

    # --- Sleep-aware pausing -----------------------------------------
    # Subscribes to org.freedesktop.ScreenSaver.ActiveChanged over the
    # session bus. Pauses the canvas on display sleep, resumes on
    # wake. If the user manually paused via the tray, we leave them
    # alone.
    sleep_watcher = SleepWatcher(canvas)
    if not sleep_watcher.is_connected():
        _debug_log(
            args.debug,
            "sleep watcher offline: ActiveChanged subscription failed",
        )

    window.show()
    canvas.show()
    # Defensive: if the Wayland compositor repositioned us at show
    # time (some compositors clamp windows to visible regions), force
    # the anchor corner again. This is a no-op when we're already
    # where we want to be.
    window.apply_position()

    _debug_log(
        args.debug,
        f"window: {window.size().width()}x{window.size().height()} "
        f"at {window.pos().x()},{window.pos().y()}, "
        f"corner={args.corner.value}, margin={args.margin}",
    )

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
