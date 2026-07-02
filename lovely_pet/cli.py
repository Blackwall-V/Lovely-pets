"""Command-line interface: argparse wrapper.

Deliberately has **no** Qt import so it can run before the QApplication
exists. ``python pet.py --help`` should work in a headless terminal.

Contract
--------
* ``parse_args(argv)`` returns a :class:`PetArgs` dataclass with
  validated, typed fields. Default values match the documented "just
  run it" behaviour.
* Unknown options and missing positional args produce a friendly
  argparse error and exit code 2, *not* a Qt crash.
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Optional, Sequence

from lovely_pet.position import Corner

DEFAULT_MARGIN_PX = 32
DEFAULT_SIZE_PERCENT = 100
MIN_SIZE_PERCENT = 1
MAX_SIZE_PERCENT = 100


@dataclass(frozen=True)
class PetArgs:
    """Validated, parsed command-line arguments."""

    source: Optional[str]
    size_percent: int
    corner: Corner
    margin: int
    debug: bool


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pet.py",
        description=(
            "A Wayland-native desktop pet for Hyprland. "
            "Displays an animated GIF or video as a click-through "
            "overlay pinned across all workspaces."
        ),
        # Keep error messages short; the full help is rarely useful.
        add_help=True,
    )
    parser.add_argument(
        "source_pos",
        nargs="?",
        default=None,
        help=(
            "Path to a .gif (or, after phase 6, .mp4/.webm/.mov) file. "
            "Mutually compatible with --source; --source wins if both are "
            "given."
        ),
    )
    parser.add_argument(
        "--source",
        dest="source",
        default=None,
        help="Same as the positional SOURCE_POS, but explicit. Overrides the positional.",
    )
    parser.add_argument(
        "--size",
        dest="size_percent",
        type=int,
        default=DEFAULT_SIZE_PERCENT,
        metavar="PCT",
        help=(
            "Scale the pet to PCT percent of the source's native size. "
            f"Range: {MIN_SIZE_PERCENT}-{MAX_SIZE_PERCENT}. "
            f"Default: {DEFAULT_SIZE_PERCENT}."
        ),
    )
    parser.add_argument(
        "--corner",
        dest="corner",
        type=str,
        default=Corner.BOTTOM_RIGHT.value,
        choices=[c.value for c in Corner],
        help=(
            "Which corner of the screen to anchor the pet to. "
            "Default: bottom-right."
        ),
    )
    parser.add_argument(
        "--margin",
        dest="margin",
        type=int,
        default=DEFAULT_MARGIN_PX,
        metavar="PX",
        help=(
            "Pixels of breathing room between the pet and the screen edge. "
            f"Default: {DEFAULT_MARGIN_PX}."
        ),
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Emit verbose diagnostic logging to stderr.",
    )
    return parser


def parse_args(argv: Optional[Sequence[str]] = None) -> PetArgs:
    """Parse argv and return a :class:`PetArgs`.

    Validates the size range and converts the corner string to a
    :class:`Corner` enum.
    """
    if argv is None:
        argv = sys.argv[1:]

    parser = _build_parser()
    raw = parser.parse_args(list(argv))

    # --- Validate size -----------------------------------------------
    if not (MIN_SIZE_PERCENT <= raw.size_percent <= MAX_SIZE_PERCENT):
        parser.error(
            f"--size must be between {MIN_SIZE_PERCENT} and "
            f"{MAX_SIZE_PERCENT} (got {raw.size_percent})"
        )

    # --- Validate margin ---------------------------------------------
    if raw.margin < 0:
        parser.error(f"--margin must be >= 0 (got {raw.margin})")

    # --- Resolve source: --source wins over positional --------------
    source = raw.source if raw.source is not None else raw.source_pos
    if source is not None:
        source = os.path.expanduser(source)

    # --- Convert corner ----------------------------------------------
    try:
        corner = Corner.parse(raw.corner)
    except ValueError as exc:
        parser.error(str(exc))

    return PetArgs(
        source=source,
        size_percent=raw.size_percent,
        corner=corner,
        margin=raw.margin,
        debug=raw.debug,
    )


__all__ = [
    "DEFAULT_MARGIN_PX",
    "DEFAULT_SIZE_PERCENT",
    "PetArgs",
    "parse_args",
]
