#!/usr/bin/env python3
"""Entry point for the Lovely-pets desktop pet.

Usage:
    python pet.py                       # launch with config/bundled sample
    python pet.py /path/to/pet.gif      # launch with a specific pet
    python pet.py --size 150            # 150% of native size
    python pet.py --corner top-left     # pin to a different corner
    python pet.py --help                # show full options
"""
import os
import sys

from lovely_pet.cli import parse_args
from lovely_pet.config import DEFAULT_CONFIG_PATH, load_config, write_sample_config

DEFAULT_SAMPLE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "assets", "sample_pet.gif"
)


def _debug_log(enabled: bool, *parts) -> None:
    if not enabled:
        return
    print("[lovely-pet]", *parts, file=sys.stderr)


def main() -> int:
    config_path = os.environ.get("LOVELY_PET_CONFIG") or DEFAULT_CONFIG_PATH
    config = load_config(config_path)
    args = parse_args(sys.argv[1:], config=config, config_path=config_path)
    _debug_log(args.debug, f"effective args: {args}")

    if args.init_config:
        try:
            path = write_sample_config()
        except FileExistsError as exc:
            print(f"[lovely-pet] {exc}", file=sys.stderr)
            return 1
        print(f"[lovely-pet] wrote sample config to {path}")
        return 0

    if args.print_config:
        print("[lovely-pet] effective configuration:")
        print(f"  source       = {args.source!r}")
        print(f"  size_percent = {args.size_percent}")
        print(f"  corner       = {args.corner.value}")
        print(f"  margin       = {args.margin}")
        print(f"  debug        = {args.debug}")
        return 0

    from PyQt6.QtCore import Qt
    from lovely_pet.app import build_application, install_signal_handlers
    from lovely_pet.media import MediaCanvas
    from lovely_pet.menu import build_context_menu
    from lovely_pet.window import PetWindow

    app = build_application(sys.argv)
    install_signal_handlers(app)
    _debug_log(args.debug, f"Qt platform: {app.platformName()}")

    window = PetWindow(corner=args.corner, margin=args.margin)
    window.setWindowTitle("Lovely Pet")

    canvas = MediaCanvas(window)
    source = args.source if args.source is not None else DEFAULT_SAMPLE
    _debug_log(args.debug, f"loading source: {source!r}")

    if os.path.isfile(source):
        try:
            canvas.set_source(source)
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            print(f"[lovely-pet] could not load {source!r}: {exc}", file=sys.stderr)
    else:
        print(f"[lovely-pet] no source at {source!r}.", file=sys.stderr)
        window.resize(200, 200)

    # Size the window to the GIF's native size, scaled by --size
    native = canvas.native_size()
    if native.isValid():
        from PyQt6.QtCore import QSize
        w = max(1, int(native.width() * args.size_percent / 100))
        h = max(1, int(native.height() * args.size_percent / 100))
        window.resize_to(QSize(w, h))

    # Right-click context menu (resize, move, pause, load, quit)
    def _show_context_menu(pos):
        menu = build_context_menu(window, canvas, app.quit)
        menu.exec(window.mapToGlobal(pos))

    window.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    window.customContextMenuRequested.connect(_show_context_menu)

    window.show()
    canvas.show()
    window.apply_position()

    _debug_log(
        args.debug,
        f"window: {window.size().width()}x{window.size().height()} "
        f"at {window.pos().x()},{window.pos().y()}",
    )

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
