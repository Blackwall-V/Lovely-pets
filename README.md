# Lovely-pets

A Wayland-native desktop pet for the Hyprland compositor. Displays an
animated GIF or lightweight video as a frameless, transparent overlay
that persists across all workspaces without intercepting clicks.

## Status

Skeleton only. The build is in progress, see the project commit history.

## Planned features

- Click-through overlay via `Qt.WindowType.WindowTransparentForInput`
  plus Hyprland `passthrough` window rule
- System tray via AppIndicator3 with **Load Pet...** and **Quit**
- CLI: `python pet.py /path/to/pet.gif`
- Display-sleep detection that pauses playback to drop CPU to 0%
- Wayland enforcement with runtime assertion (never falls back to Xwayland)

## Requirements

- Python 3.10+
- PyQt6
- Hyprland compositor
- System packages (Arch names):
  - `qt6-wayland`
  - `libayatana-appindicator3`
  - `gobject-introspection` and `python-gobject`

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python pet.py
```

Full install, run, and Hyprland configuration instructions will land
in a later commit.
