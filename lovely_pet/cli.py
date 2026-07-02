"""Command-line interface: argparse wrapper.

Deliberately has **no** Qt import so it can run before the QApplication
exists. ``python pet.py --help`` should work in a headless terminal.

Contract
--------
* :func:`parse_args` returns a :class:`PetArgs` dataclass with
  validated, typed fields.
* Unknown options and missing positional args produce a friendly
  argparse error and exit code 2, *not* a Qt crash.
* A user config (see :mod:`lovely_pet.config`) is loaded before
  parsing and used as the argparse defaults; CLI flags still
  override the file.
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Optional, Sequence

from lovely_pet.config import PetConfig
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
    # Path the effective config was loaded from, for debug logging.
    config_path: Optional[str]
    # Action flags: --init-config and --print-config cause main() to
    # exit before launching the GUI.
    init_config: bool
    print_config: bool


def _build_parser(defaults: PetConfig) -> argparse.ArgumentParser:
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
            "Path to a .gif (or .mp4/.webm/.mov) file. "
            "Mutually compatible with --source; --source wins if both are "
            "given. Falls back to the config file's `source` key."
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
        default=defaults.size,
        metavar="PCT",
        help=(
            "Scale the pet to PCT percent of the source's native size. "
            f"Range: {MIN_SIZE_PERCENT}-{MAX_SIZE_PERCENT}. "
            f"Default from config: {defaults.size}."
        ),
    )
    parser.add_argument(
        "--corner",
        dest="corner",
        type=str,
        default=defaults.corner,
        choices=[c.value for c in Corner],
        help=(
            "Which corner of the screen to anchor the pet to. "
            f"Default from config: {defaults.corner}."
        ),
    )
    parser.add_argument(
        "--margin",
        dest="margin",
        type=int,
        default=defaults.margin,
        metavar="PX",
        help=(
            "Pixels of breathing room between the pet and the screen edge. "
            f"Default from config: {defaults.margin}."
        ),
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=defaults.debug,
        help=(
            "Emit verbose diagnostic logging on stderr. "
            f"Default from config: {str(defaults.debug).lower()}."
        ),
    )
    parser.add_argument(
        "--init-config",
        action="store_true",
        help=(
            "Write a sample config file to "
            "~/.config/lovely-pet/config.ini and exit. "
            "Refuses to overwrite an existing file."
        ),
    )
    parser.add_argument(
        "--print-config",
        action="store_true",
        help=(
            "Print the effective configuration (config + CLI overrides) "
            "to stdout and exit."
        ),
    )
    return parser


def parse_args(
    argv: Optional[Sequence[str]] = None,
    config: Optional[PetConfig] = None,
    config_path: Optional[str] = None,
) -> PetArgs:
    """Parse argv and return a :class:`PetArgs`.

    ``config`` provides the argparse defaults; values supplied on
    the command line still win. ``config_path`` is recorded in the
    returned ``PetArgs`` for the debug logger.
    """
    if config is None:
        config = PetConfig()

    if argv is None:
        argv = sys.argv[1:]

    parser = _build_parser(config)
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

    # --- Resolve source: --source > positional > config -------------
    if raw.source is not None:
        source = raw.source
    elif raw.source_pos is not None:
        source = raw.source_pos
    else:
        source = config.source
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
        config_path=config_path,
        init_config=raw.init_config,
        print_config=raw.print_config,
    )


__all__ = [
    "DEFAULT_MARGIN_PX",
    "DEFAULT_SIZE_PERCENT",
    "PetArgs",
    "parse_args",
]
