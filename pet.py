#!/usr/bin/env python3
"""Entry point for the Lovely-pets desktop pet.

Usage:
    python pet.py                       # launch with bundled sample
    python pet.py /path/to/pet.gif      # launch with a specific pet
    python pet.py --size 50             # scale to 50% of native size
    python pet.py --corner top-left     # pin to a different corner
    python pet.py --help                # show full options
"""
import os
import sys

from lovely_pet.cli import parse_args

DEFAULT_SAMPLE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "assets", "sample_pet.gif"
)


def _debug_log(enabled: bool, *parts) -> None:
    if not enabled:
        return
    print("[lovely-pet]", *parts, file=sys.stderr)


def main() -> int:
    # Parse CLI first so --help works without PyQt6 installed.
    args = parse_args(sys.argv[1:])
    _debug_log(args.debug, f"parsed args: {args}")

    # Defer Qt imports until we actually want to build a window.
    from lovely_pet.app import build_application, install_signal_handlers
    from lovely_pet.media import MediaCanvas
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
            print(
                f"[lovely-pet] could not load {source!r}: {exc}",
                file=sys.stderr,
            )
    else:
        print(
            f"[lovely-pet] no source file at {source!r}. "
            "Provide a GIF path on the command line, e.g. "
            "'python pet.py /path/to/pet.gif'.",
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

    _debug_log(
        args.debug,
        f"window size: {window.size().width()}x{window.size().height()} "
        f"at {window.pos().x()},{window.pos().y()}",
    )

    window.show()
    canvas.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
