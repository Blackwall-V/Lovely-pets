"""User configuration loader.

Reads an INI file at ``~/.config/lovely-pet/config.ini`` (overridable
via the ``LOVELY_PET_CONFIG`` environment variable or the
``--config <path>`` CLI flag) and produces a :class:`PetConfig` that
the rest of the app merges with its own defaults.

Format
------
INI, flat (no sections). The shipped sample lives in
:data:`SAMPLE_CONFIG_TEXT` and is what ``--init-config`` writes to
disk. The format was chosen because every user already has an INI
editor (``vim``, ``nano``, GNOME Text Editor, etc.) and the config
is just five flat keys.

Precedence
----------
``pet.py`` resolves the effective config like so (later overrides
earlier):

1. Hard-coded :class:`PetConfig` defaults
2. ``~/.config/lovely-pet/config.ini`` (or the path the user passed)
3. Command-line arguments

This module only does step 2. Steps 1 and 3 are the caller's job.
"""
from __future__ import annotations

import configparser
import os
import sys
from dataclasses import dataclass, fields
from typing import Optional

# XDG Base Directory spec — but with a hard fallback for the rare
# user who has not set $XDG_CONFIG_HOME.
CONFIG_DIR = os.environ.get(
    "LOVELY_PET_CONFIG_DIR",
    os.path.join(
        os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"),
        "lovely-pet",
    ),
)
DEFAULT_CONFIG_PATH = os.path.join(CONFIG_DIR, "config.ini")


SAMPLE_CONFIG_TEXT = """\
# Lovely-pets configuration
# ----------------------------------------
# Edit values below, then run `python pet.py` to apply.
# CLI flags (e.g. --size 50) override this file.

# Path to the default pet (GIF or video). Leave commented to fall
# back to the bundled sample at assets/sample_pet.gif.
# source = /home/v/Downloads/yoru-chainsaw-man.gif

# Scale of the native source size, in percent. Range: 1-100.
size = 100

# Anchor corner on the screen. One of:
#   top-left, top-right, bottom-left, bottom-right, center
corner = bottom-right

# Pixels of breathing room between the pet and the screen edge.
margin = 32

# Verbose diagnostic logging on stderr. true or false.
debug = false
"""


@dataclass(frozen=True)
class PetConfig:
    """Validated user configuration.

    Every field has a sensible default; loading a missing or partial
    config file just returns the dataclass with those defaults in
    place. Validation lives in :mod:`lovely_pet.cli` so the same
    error messages apply whether a value came from the config or the
    command line.
    """

    source: Optional[str] = None
    size: int = 100
    corner: str = "bottom-right"
    margin: int = 32
    debug: bool = False


# Field types used for coercion of the raw INI string values.
_INT_FIELDS = {"size", "margin"}
_BOOL_FIELDS = {"debug"}


def _coerce(name: str, raw: str):
    """Coerce a raw string from the INI file to the right Python type.

    Raises ``ValueError`` on a value the field cannot accept; the
    caller turns that into a stderr warning and falls back to the
    default for that single key.
    """
    if name in _INT_FIELDS:
        return int(raw)
    if name in _BOOL_FIELDS:
        return raw.strip().lower() in ("1", "true", "yes", "on")
    return raw


def load_config(path: Optional[str] = None) -> PetConfig:
    """Load a :class:`PetConfig` from ``path`` (or the default location).

    Returns the default :class:`PetConfig` if the file does not exist,
    cannot be parsed, or has no recognised keys. A bad value on a
    single key is logged and that key falls back to its default — we
    do not refuse to launch over a single typo in the config.

    The file is read as flat ``key = value`` lines by default — no
    ``[section]`` header is required. If the user *does* add a
    section header, the loader picks it up too; sections are
    flattened into the same key namespace.
    """
    config_path = path or DEFAULT_CONFIG_PATH
    if not os.path.isfile(config_path):
        return PetConfig()

    try:
        with open(config_path, encoding="utf-8") as fh:
            content = fh.read()
    except OSError as exc:
        print(
            f"[lovely-pet] could not read {config_path}: {exc}",
            file=sys.stderr,
        )
        return PetConfig()

    # configparser requires a section header; a flat key=value file
    # is rejected. If the file has no [section] line, we treat the
    # whole file as the [DEFAULT] section.
    if not any(
        line.lstrip().startswith("[") and line.rstrip().endswith("]")
        for line in content.splitlines()
    ):
        content = "[DEFAULT]\n" + content

    parser = configparser.ConfigParser()
    try:
        parser.read_string(content)
    except configparser.Error as exc:
        print(
            f"[lovely-pet] could not parse {config_path}: {exc}",
            file=sys.stderr,
        )
        return PetConfig()

    # Flatten the parser: top-level defaults + any section contents.
    raw: dict[str, str] = {}
    raw.update(parser.defaults())
    for section in parser.sections():
        raw.update(dict(parser[section]))

    valid = {f.name for f in fields(PetConfig)}
    kwargs: dict = {}
    for key, value in raw.items():
        if key not in valid:
            print(
                f"[lovely-pet] ignoring unknown config key: {key!r}",
                file=sys.stderr,
            )
            continue
        try:
            kwargs[key] = _coerce(key, value)
        except (ValueError, TypeError) as exc:
            print(
                f"[lovely-pet] invalid value for {key!r} in "
                f"{config_path}: {exc}. Using default.",
                file=sys.stderr,
            )

    return PetConfig(**kwargs)


def write_sample_config(path: Optional[str] = None) -> str:
    """Write :data:`SAMPLE_CONFIG_TEXT` to ``path`` and return the path.

    Creates parent directories if they do not exist. Refuses to
    overwrite an existing file unless the caller passes an explicit
    path; the user should delete the old one first.
    """
    target = os.path.expanduser(path) if path else DEFAULT_CONFIG_PATH
    if os.path.exists(target):
        raise FileExistsError(
            f"Refusing to overwrite existing config: {target}. "
            "Delete it first or pass a different path."
        )
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(SAMPLE_CONFIG_TEXT)
    return target


__all__ = [
    "CONFIG_DIR",
    "DEFAULT_CONFIG_PATH",
    "PetConfig",
    "SAMPLE_CONFIG_TEXT",
    "load_config",
    "write_sample_config",
]
