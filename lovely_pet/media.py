"""MediaCanvas: unified QMovie (GIF) and QMediaPlayer (video) renderer.

Phase 4 lands the GIF path. Phase 6 extends :class:`MediaCanvas` with
``QMediaPlayer`` so the public API (``setSource``, ``nativeSize``,
``pause``, ``resume``) stays the same for both file types.

Both renderers emit a single ``QImage``/``QPixmap`` per Qt frame; the
``paintEvent`` here is the only place we ever draw to the screen, so
positioning, scaling, and click-through behaviour are identical
regardless of media type.

Resource notes
--------------
* ``QMovie`` is configured with ``CacheNone`` because most desktop
  pets loop a short animation forever; caching every frame is wasted
  RAM.
* ``setSpeed(100)`` is the default (real-time). The sleep watcher in
  phase 8 calls ``pause()`` to drop the per-frame paint cost to zero
  when the display blanks.
* The current pixmap is cached on the ``QMovie.frameChanged`` signal
  rather than fetched in ``paintEvent``; calling
  ``QMovie.currentPixmap()`` from a paint handler is documented as
  expensive and triggers a fresh image conversion.
"""
from __future__ import annotations

import os
from typing import Optional

from PyQt6.QtCore import QRect, QSize, Qt
from PyQt6.QtGui import QImage, QPainter, QPixmap
from PyQt6.QtWidgets import QWidget

# Phase 6 will extend this with video suffixes.
GIF_SUFFIXES = (".gif",)


def is_gif(path: str) -> bool:
    """True if ``path`` looks like an animated GIF we can hand to QMovie."""
    return os.path.splitext(path)[1].lower() in GIF_SUFFIXES


class MediaCanvas(QWidget):
    """A widget that paints an animated media source centered and
    aspect-fit inside its rect.

    Subclass or use directly; the parent :class:`PetWindow` resizes us
    to the media's native dimensions and then we paint however large
    the window grows.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # Transparent fill: required for WA_TranslucentBackground to
        # actually show transparency. WA_NoSystemBackground prevents Qt
        # from overwriting our paint with the default palette colour.
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

        self._movie: Optional["QMovie"] = None  # type: ignore[name-defined]
        self._current_pixmap: Optional[QPixmap] = None
        self._current_source: Optional[str] = None
        self._paused: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_source(self, path: str) -> None:
        """Load a media file. Currently only GIFs are supported.

        Raises ``FileNotFoundError`` if the path is missing, ``ValueError``
        if the suffix is unrecognised, and whatever Qt raises on a
        malformed GIF (typically ``RuntimeError``).
        """
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        if not is_gif(path):
            raise ValueError(
                f"Unsupported media type: {os.path.splitext(path)[1]}. "
                f"Phase 4 only supports {GIF_SUFFIXES}."
            )

        self._stop_movie()

        from PyQt6.QtGui import QMovie

        self._movie = QMovie(path)
        # Don't cache every decoded frame: pet animations are short
        # loops and we only ever display one frame at a time.
        self._movie.setCacheMode(QMovie.CacheMode.CacheNone)
        # Real-time playback. Phase 8 may scale this on load.
        self._movie.setSpeed(100)
        self._movie.frameChanged.connect(self._on_frame_changed)
        self._movie.errorOccurred.connect(self._on_movie_error)

        self._current_source = path
        self._paused = False
        self._movie.start()

    def native_size(self) -> QSize:
        """Return the source media's native pixel size, or QSize() if no
        media is loaded."""
        if self._movie is None:
            return QSize()
        return self._movie.frameRect().size()

    def source_path(self) -> Optional[str]:
        """Return the path most recently passed to ``set_source``, or None."""
        return self._current_source

    def pause(self) -> None:
        """Halt playback. Idempotent."""
        if self._movie is not None and not self._paused:
            self._movie.setPaused(True)
            self._paused = True

    def resume(self) -> None:
        """Resume playback after a ``pause()``. Idempotent."""
        if self._movie is not None and self._paused:
            self._movie.setPaused(False)
            self._paused = False

    def is_paused(self) -> bool:
        return self._paused

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _stop_movie(self) -> None:
        if self._movie is not None:
            self._movie.stop()
            self._movie.frameChanged.disconnect(self._on_frame_changed)
            try:
                self._movie.errorOccurred.disconnect(self._on_movie_error)
            except (TypeError, RuntimeError):
                # disconnect() raises if the connection was already gone;
                # safe to ignore.
                pass
            self._movie = None
        self._current_pixmap = None
        self._current_source = None
        self._paused = False
        self.update()

    def _on_frame_changed(self, _frame_number: int) -> None:
        # Cache the pixmap here (not inside paintEvent) — currentPixmap
        # does a format conversion that is cheaper to do off the paint
        # path.
        if self._movie is None:
            return
        self._current_pixmap = self._movie.currentPixmap()
        self.update()

    def _on_movie_error(self, _error) -> None:
        # We deliberately do not crash on bad GIFs. The window simply
        # stays empty and a debug log line is emitted.
        import sys

        print(
            f"[lovely-pet] QMovie error on {self._current_source!r}: "
            f"{self._movie.errorString() if self._movie else 'unknown'}",
            file=sys.stderr,
        )

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        pix = self._current_pixmap
        if pix is None or pix.isNull():
            return

        painter = QPainter(self)
        # Smooth scaling avoids jagged edges when the window is sized
        # larger than the GIF's native dimensions.
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        target = self._aspect_fit_rect(pix.size())
        painter.drawPixmap(target, pix)
        painter.end()

    def _aspect_fit_rect(self, source_size: QSize) -> QRect:
        """Compute the centered, aspect-fit rect for ``source_size`` inside
        ``self.rect()``.
        """
        widget_rect = self.rect()
        if widget_rect.isEmpty() or source_size.isEmpty():
            return widget_rect
        scaled = source_size.scaled(
            widget_rect.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (widget_rect.width() - scaled.width()) // 2
        y = (widget_rect.height() - scaled.height()) // 2
        return QRect(x, y, scaled.width(), scaled.height())


__all__ = ["GIF_SUFFIXES", "MediaCanvas", "is_gif"]
