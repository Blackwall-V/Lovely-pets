"""D-Bus ScreenSaver.ActiveChanged listener.

Pauses media playback when the display sleeps, resumes when it wakes.
Bridges the GLib main loop into Qt via QSocketNotifier.
"""
