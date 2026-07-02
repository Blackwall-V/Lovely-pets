#!/usr/bin/env python3
"""Entry point for the Lovely-pets desktop pet.

Usage:
    python pet.py                       # launch with bundled sample
    python pet.py /path/to/pet.gif      # launch with a specific pet
    python pet.py --size 50             # scale to 50% of native size
"""
import os
import sys

from lovely_pet.app import build_application, install_signal_handlers
from lovely_pet.media import MediaCanvas
from lovely_pet.window import Corner, PetWindow

DEFAULT_SAMPLE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "assets", "sample_pet.gif"
)


def _resolve_source(argv: list[str]) -> str:
    """Pick a GIF to load. CLI arg wins; otherwise the bundled sample.

    Positional argv[1] is treated as a path. The full argparse wrapper
    arrives in phase 5; this stub keeps phase 4 runnable.
    """
    for arg in argv[1:]:
        if not arg.startswith("-"):
            return arg
    return DEFAULT_SAMPLE


def main() -> int:
    app = build_application(sys.argv)
    install_signal_handlers(app)

    window = PetWindow(corner=Corner.BOTTOM_RIGHT, margin=32)
    window.setWindowTitle("Lovely Pet")

    canvas = MediaCanvas(window)
    source = _resolve_source(sys.argv)
    if os.path.isfile(source):
        try:
            canvas.set_source(source)
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            print(f"[lovely-pet] could not load {source!r}: {exc}", file=sys.stderr)
    else:
        print(
            f"[lovely-pet] no source file at {source!r}. "
            "Provide a GIF path on the command line, e.g. "
            "'python pet.py /path/to/pet.gif'.",
            file=sys.stderr,
        )
        # Resize to a small placeholder so the window is visible for
        # verifying the click-through overlay even with no media.
        window.resize(128, 128)

    if canvas.native_size().isValid():
        window.resize_to(canvas.native_size())
    window.show()
    canvas.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
