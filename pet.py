#!/usr/bin/env python3
"""Entry point for the Lovely-pets desktop pet.

Usage:
    python pet.py                       # launch with bundled sample
    python pet.py /path/to/pet.gif      # launch with a specific pet
    python pet.py --size 50             # scale to 50% of native size
"""
import sys

from lovely_pet.app import build_application


def main() -> int:
    app = build_application(sys.argv)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
