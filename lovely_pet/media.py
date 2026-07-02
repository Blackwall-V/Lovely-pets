"""MediaCanvas: unified QMovie (GIF) and QMediaPlayer (video) renderer.

The public API (``set_source``, ``native_size``, ``pause``, ``resume``)
stays identical for both file types so the rest of the app never has
to know which backend is in use. Internally:

* GIFs go through ``QMovie``. We cache the current pixmap on the
  ``frameChanged`` signal (cheaper than calling
  ``QMovie.currentPixmap()`` from inside ``paintEvent``).
* Videos go through ``QMediaPlayer`` + ``QVideoSink``. Each new
  frame is converted to a ``QImage`` and we ``update()`` to schedule
  a repaint. ``mediaStatusChanged`` loops the clip forever.
* Audio is muted unconditionally; a desktop pet is visual only.

Resource notes
--------------
* ``QMovie`` is configured with ``CacheNone`` because most desktop
  pets loop a short animation forever; caching every frame is wasted
  RAM.
* The sleep watcher in phase 8 calls ``pause()`` to drop the
  per-frame paint cost to zero when the display blanks.
"""
from __future__ import annotations

import os
import sys
from typing import Optional, Union

from PyQt6.QtCore import QRect, QSize, QUrl, Qt
from PyQt6.QtGui import QImage, QPainter, QPixmap
from PyQt6.QtWidgets import QWidget

# Phase 4 landed GIFs. Phase 6 added the video suffixes.
GIF_SUFFIXES = (".gif",)
VIDEO_SUFFIXES = (".mp4", ".webm", ".mov", ".mkv", ".avi", ".m4v")


def is_gif(path: str) -> bool:
    """True if ``path`` looks like an animated GIF we can hand to QMovie."""
    return os.path.splitext(path)[1].lower() in GIF_SUFFIXES


def is_video(path: str) -> bool:
    """True if ``path`` looks like a video file ``QMediaPlayer`` can decode."""
    return os.path.splitext(path)[1].lower() in VIDEO_SUFFIXES


def is_media(path: str) -> bool:
    """True if ``path`` is any media type :class:`MediaCanvas` can load."""
    return is_gif(path) or is_video(path)


def file_dialog_filter() -> str:
    """A ``QFileDialog``-compatible filter string for the supported types."""
    patterns = " ".join(f"*{ext}" for ext in GIF_SUFFIXES + VIDEO_SUFFIXES)
    return f"Pet media ({patterns});;All files (*)"


class MediaCanvas(QWidget):
    """A widget that paints an animated media source centered and
    aspect-fit inside its rect.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

        # --- GIF backend state -----------------------------------------
        self._movie: Optional["QMovie"] = None  # type: ignore[name-defined]
        self._current_pixmap: Optional[QPixmap] = None

        # --- Video backend state ---------------------------------------
        self._player: Optional["QMediaPlayer"] = None  # type: ignore[name-defined]
        self._sink: Optional["QVideoSink"] = None  # type: ignore[name-defined]
        self._audio_output: Optional["QAudioOutput"] = None  # type: ignore[name-defined]
        self._current_frame: Optional[QImage] = None
        self._looping: bool = True  # desktop pets loop forever

        self._current_source: Optional[str] = None
        self._paused: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_source(self, path: str) -> None:
        """Load a media file. Supports GIFs and the common video formats.

        Raises ``FileNotFoundError`` if the path is missing, ``ValueError``
        if the suffix is unrecognised, and whatever Qt raises on a
        malformed source file.
        """
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        if not is_media(path):
            raise ValueError(
                f"Unsupported media type: {os.path.splitext(path)[1]}. "
                f"Supported: {GIF_SUFFIXES + VIDEO_SUFFIXES}."
            )

        # Tear down whatever was loaded before.
        self._stop_movie()
        self._stop_player()
        self._current_pixmap = None
        self._current_frame = None
        self._paused = False

        if is_gif(path):
            self._load_gif(path)
        else:
            self._load_video(path)

        self._current_source = path

    def native_size(self) -> QSize:
        """Return the source media's native pixel size, or QSize() if no
        media is loaded yet.
        """
        if self._movie is not None:
            return self._movie.frameRect().size()
        if self._current_frame is not None and not self._current_frame.isNull():
            return self._current_frame.size()
        if self._player is not None and self._player.isAvailable():
            # QMediaPlayer doesn't expose a size before first frame;
            # fall back to a sensible default.
            return QSize(320, 240)
        return QSize()

    def source_path(self) -> Optional[str]:
        return self._current_source

    def pause(self) -> None:
        """Halt playback. Idempotent. No-op if no media is loaded."""
        if self._paused:
            return
        if self._movie is not None:
            self._movie.setPaused(True)
        if self._player is not None:
            self._player.pause()
        self._paused = True

    def resume(self) -> None:
        """Resume playback after a ``pause()``. Idempotent."""
        if not self._paused:
            return
        if self._movie is not None:
            self._movie.setPaused(False)
        if self._player is not None:
            self._player.play()
        self._paused = False

    def is_paused(self) -> bool:
        return self._paused

    # ------------------------------------------------------------------
    # GIF backend
    # ------------------------------------------------------------------
    def _load_gif(self, path: str) -> None:
        from PyQt6.QtGui import QMovie

        self._movie = QMovie(path)
        self._movie.setCacheMode(QMovie.CacheMode.CacheNone)
        self._movie.setSpeed(100)
        self._movie.frameChanged.connect(self._on_frame_changed)
        self._movie.errorOccurred.connect(self._on_movie_error)
        self._movie.start()

    def _on_frame_changed(self, _frame_number: int) -> None:
        if self._movie is None:
            return
        self._current_pixmap = self._movie.currentPixmap()
        self.update()

    def _on_movie_error(self, _error) -> None:
        if self._movie is None:
            return
        print(
            f"[lovely-pet] QMovie error on {self._current_source!r}: "
            f"{self._movie.errorString()}",
            file=sys.stderr,
        )

    def _stop_movie(self) -> None:
        if self._movie is None:
            return
        try:
            self._movie.stop()
            self._movie.frameChanged.disconnect(self._on_frame_changed)
        except (TypeError, RuntimeError):
            pass
        try:
            self._movie.errorOccurred.disconnect(self._on_movie_error)
        except (TypeError, RuntimeError):
            pass
        self._movie = None
        self._current_pixmap = None

    # ------------------------------------------------------------------
    # Video backend
    # ------------------------------------------------------------------
    def _load_video(self, path: str) -> None:
        from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer, QVideoSink

        self._sink = QVideoSink(self)
        self._sink.videoFrameChanged.connect(self._on_video_frame)

        # Mute: a desktop pet is visual only; audio would be obnoxious
        # when the user is coding or gaming. We hold a reference to the
        # QAudioOutput so the volume setting sticks for the player's
        # lifetime; otherwise Qt may garbage-collect it.
        self._audio_output = QAudioOutput(self)
        self._audio_output.setVolume(0.0)

        self._player = QMediaPlayer(self)
        self._player.setVideoOutput(self._sink)
        self._player.setAudioOutput(self._audio_output)
        self._player.mediaStatusChanged.connect(self._on_media_status)
        self._player.errorOccurred.connect(self._on_player_error)
        self._player.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
        self._player.play()

    def _on_video_frame(self, frame) -> None:
        """Cache the most recent frame and schedule a repaint.

        ``frame.toImage()`` is the supported way to get a paintable
        QImage; we accept the conversion cost here (off the paint path)
        and re-use the same QImage until the next frame arrives.
        """
        if not frame.isValid():
            return
        image = frame.toImage()
        if image.isNull():
            return
        self._current_frame = image
        self.update()

    def _on_media_status(self, status) -> None:
        """Loop the video forever by seeking to 0 on end-of-media."""
        from PyQt6.QtMultimedia import QMediaPlayer

        if (
            self._looping
            and self._player is not None
            and status == QMediaPlayer.MediaStatus.EndOfMedia
        ):
            self._player.setPosition(0)
            self._player.play()

    def _on_player_error(self, error, error_string: str = "") -> None:
        print(
            f"[lovely-pet] QMediaPlayer error on "
            f"{self._current_source!r}: {error_string!r} ({error})",
            file=sys.stderr,
        )

    def _stop_player(self) -> None:
        if self._player is None:
            return
        try:
            self._player.stop()
            self._player.mediaStatusChanged.disconnect(self._on_media_status)
        except (TypeError, RuntimeError):
            pass
        try:
            self._player.errorOccurred.disconnect(self._on_player_error)
        except (TypeError, RuntimeError):
            pass
        self._player = None
        self._sink = None
        self._audio_output = None
        self._current_frame = None

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        # Prefer the most recently decoded GIF pixmap, fall back to the
        # most recent video frame. Only one backend is ever active at a
        # time so this if/else is a cheap, hot-path branch.
        if self._current_pixmap is not None and not self._current_pixmap.isNull():
            self._draw_pixmap(self._current_pixmap)
            return
        if self._current_frame is not None and not self._current_frame.isNull():
            self._draw_image(self._current_frame)

    def _draw_pixmap(self, pix: QPixmap) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.drawPixmap(self._aspect_fit_rect(pix.size()), pix)
        painter.end()

    def _draw_image(self, image: QImage) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.drawImage(self._aspect_fit_rect(image.size()), image)
        painter.end()

    def _aspect_fit_rect(self, source_size: QSize) -> QRect:
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


__all__ = [
    "GIF_SUFFIXES",
    "VIDEO_SUFFIXES",
    "MediaCanvas",
    "file_dialog_filter",
    "is_gif",
    "is_media",
    "is_video",
]
