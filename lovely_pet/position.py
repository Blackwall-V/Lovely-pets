"""Position enum shared between CLI parsing and the window widget.

Lives in its own module so :mod:`lovely_pet.cli` can import it
without dragging in PyQt6 (the CLI must be runnable in a headless
terminal, e.g. for ``python pet.py --help``).
"""
from __future__ import annotations

from enum import Enum
from typing import Optional


class Corner(str, Enum):
    """Anchor corner for the pet window on its screen."""

    TOP_LEFT = "top-left"
    TOP_RIGHT = "top-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_RIGHT = "bottom-right"
    CENTER = "center"

    @classmethod
    def parse(cls, value: Optional[str]) -> "Corner":
        if value is None:
            return cls.BOTTOM_RIGHT
        try:
            return cls(value.lower())
        except ValueError as exc:
            raise ValueError(
                f"Unknown corner '{value}'. Valid: "
                f"{', '.join(c.value for c in cls)}"
            ) from exc


__all__ = ["Corner"]
