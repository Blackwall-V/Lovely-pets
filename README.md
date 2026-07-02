# Lovely-pets

A Wayland-native desktop pet for the Hyprland compositor. Displays an
animated GIF or lightweight video as a frameless, transparent overlay
that persists across all workspaces without intercepting clicks.

## Features

- **Click-through overlay** — `Qt.WindowType.WindowTransparentForInput`
  combined with Hyprland's `passthrough` window rule.
- **Pinned to all workspaces** — uses `windowrulev2 = pin`.
- **Multi-format media** — animated GIFs via `QMovie`, `.mp4`/`.webm`/
  `.mov`/`.mkv`/`.avi` via `QMediaPlayer` + `QVideoSink`. Audio is muted
  by default.
- **System tray** — AppIndicator3 menu with **Load Pet...**, **Pause**,
  and **Quit**. Tray degrades gracefully to a no-op if AppIndicator3
  is not installed; the app stays killable via Ctrl-C.
- **Sleep-aware** — listens on the D-Bus session bus for
  `org.freedesktop.ScreenSaver.ActiveChanged` and pauses the canvas
  while the display is blank, resuming on wake. CPU drops to 0% while
  asleep.
- **CLI configurable** — `python pet.py --size 50 --corner top-left
  /path/to/pet.gif` works without restarting the app.
- **Strict Wayland** — refuses to fall back to Xwayland. The runtime
  assert in `lovely_pet/app.py` aborts with a clear install hint if Qt
  is not on the `wayland` platform plugin.

## Requirements

- Python 3.10 or newer
- Hyprland (the Hyprland window rules match `class:^(lovely-pet)$`)
- See `requirements.txt` for the full Python + system package list

## Install

```bash
git clone https://github.com/Blackwall-V/Lovely-pets.git
cd Lovely-pets
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### System packages

The `qt6-wayland`, `libayatana-appindicator3`, and `python-gobject`
packages are **not** pip-installable on most distros. Pick the
correct line for your distro from `requirements.txt`. A summary:

| Distro    | Command |
|-----------|---------|
| Arch      | `sudo pacman -S --needed qt6-wayland libayatana-appindicator3 python-gobject gst-libav gst-plugins-good gst-plugins-bad` |
| Debian    | `sudo apt install qml6-module-qtquick libayatana-appindicator3-1 gir1.2-ayatanaappindicator3-0.1 python3-gi gir1.2-gtk-3.0 ffmpeg` |
| Fedora    | `sudo dnf install qt6-qtwayland libayatana-appindicator-gtk3 python3-gobject gstreamer1-plugins-good gstreamer1-plugins-bad-free ffmpeg` |

## Hyprland configuration

Append the `windowrulev2` rules to your Hyprland config and reload:

```bash
cat hyprland/windowrulev2.conf >> ~/.config/hypr/hyprland.conf
hyprctl reload
```

Verify they took effect:

```bash
hyprctl clients | grep lovely-pet
```

You should see `floating: true`, `pinned: true`, `fullscreen: 0`.

## Run

```bash
python pet.py                              # launches the bundled sample
python pet.py /path/to/my_pet.gif          # launch with a custom GIF
python pet.py --size 50                    # 50% of native size
python pet.py --corner top-left --margin 8 # pin to top-left, 8px from edge
python pet.py --debug                      # verbose logging to stderr
python pet.py --help                       # full CLI reference
```

Once running:

- Click anywhere on the pet — the click passes through to the window
  beneath.
- Right-click the **tray icon** → **Load Pet...** to swap media at
  runtime.
- Right-click the **tray icon** → **Pause** to halt the animation.
- Right-click the **tray icon** → **Quit** to exit. (Ctrl-C in the
  terminal works too.)

## Configuration

Lovely-pets reads an INI file at
`~/.config/lovely-pet/config.ini` (overridable via the
`LOVELY_PET_CONFIG` environment variable) and uses its values as
the defaults for every CLI flag. **CLI flags always win over the
file.**

Bootstrap a sample config:

```bash
python pet.py --init-config   # writes ~/.config/lovely-pet/config.ini
```

Inspect the effective config (config + CLI overrides, after merge):

```bash
python pet.py --print-config
```

Sample file:

```ini
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
```

Lines starting with `#` are comments. Unknown keys are logged and
ignored — a typo in one key will not stop the app from launching.

Use a non-default config file (e.g. for testing):

```bash
LOVELY_PET_CONFIG=/path/to/test.ini python pet.py
```

## CLI reference

```
usage: pet.py [-h] [--source SOURCE] [--size PCT]
              [--corner {top-left,top-right,bottom-left,bottom-right,center}]
              [--margin PX] [--debug] [--init-config] [--print-config]
              [source_pos]
```

| Flag            | Description |
|-----------------|-------------|
| `source_pos`    | Positional: path to a `.gif` or video file |
| `--source`      | Same as positional, explicit form wins if both given |
| `--size`        | Scale 1–100% of native dimensions (default: 100, from config) |
| `--corner`      | Anchor corner on the screen (default: `bottom-right`, from config) |
| `--margin`      | Pixels of breathing room from the screen edge (default: 32, from config) |
| `--debug`       | Verbose diagnostic logging on stderr (default: false, from config) |
| `--init-config` | Write a sample config to `~/.config/lovely-pet/config.ini` and exit |
| `--print-config`| Print the effective config (after merging config + CLI) and exit |

## Project layout

```
Lovely-pets/
├── pet.py                       # entry point
├── lovely_pet/
│   ├── __init__.py
│   ├── app.py                   # Wayland-enforcing QApplication
│   ├── cli.py                   # argparse wrapper
│   ├── config.py                # INI config loader + sample generator
│   ├── media.py                 # GIF + video canvas
│   ├── position.py              # Corner enum (Qt-free for headless CLI)
│   ├── sleep_watcher.py         # D-Bus ScreenSaver listener
│   ├── tray.py                  # AppIndicator3 system tray
│   └── window.py                # Frameless, transparent, click-through
├── hyprland/
│   └── windowrulev2.conf        # Hyprland window rules
├── assets/
│   └── sample_pet.gif           # bundled sample
├── requirements.txt
├── troubleshoot.md              # 3-bullet debug guide
└── README.md
```

## Troubleshooting

See [`troubleshoot.md`](troubleshoot.md) for the 3 most common issues
and how to debug them. If you hit something not covered there, run
`python pet.py --debug` and include the stderr output in your bug
report.

## License

TBD. Project is in active development; license selection is a
follow-up commit.
