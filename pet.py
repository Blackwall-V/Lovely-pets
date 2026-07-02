#!/usr/bin/env python3
"""Entry point for the Lovely-pets desktop pet.

Usage:
    python pet.py                       # launch with bundled sample
    python pet.py /path/to/pet.gif      # launch with a specific pet
    python pet.py --size 50             # scale to 50% of native size
"""
import sys

from lovely_pet.app import build_application, install_signal_handlers
from lovely_pet.window import Corner, PetWindow


def main() -> int:
    app = build_application(sys.argv)
    install_signal_handlers(app)

    window = PetWindow(corner=Corner.BOTTOM_RIGHT, margin=32)
    window.setWindowTitle("Lovely Pet")
    window.resize(128, 128)  # Placeholder size until media is wired up
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
