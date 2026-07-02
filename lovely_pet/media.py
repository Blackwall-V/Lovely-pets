"""MediaCanvas: unified QMovie (GIF) and QMediaPlayer (video) renderer.

Both paths emit a single painted frame per Qt paintEvent so positioning
and click-through behaviour stay identical regardless of media type.
"""
