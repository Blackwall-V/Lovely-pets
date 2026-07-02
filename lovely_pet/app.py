"""QApplication setup with strict Wayland enforcement.

This module must set the Wayland environment variables BEFORE any Qt
import so that QApplication() cannot accidentally pick xcb.
"""
