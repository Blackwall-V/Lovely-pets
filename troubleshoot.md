# Troubleshooting

Three recurring issues, what causes them, and how to debug.

## 1. Black background instead of transparency

**Symptom:** The pet appears with a solid black or solid window-grey
rectangle behind the GIF, hiding the desktop.

**Cause:** `WA_TranslucentBackground` is not actually taking effect.
This is almost always one of:

- The widget's `paintEvent` is filling the rect with a brush before
  drawing the GIF. PetWindow is just a positioning shell and never
  paints, so this only happens if you embed `MediaCanvas` somewhere
  with its own background.
- The source GIF has no transparent index in its palette. Re-export
  with `gifsicle -O3 --lossy=80 input.gif -o output.gif` to force a
  palette with transparency.
- Hyprland is drawing a server-side shadow or blur because the
  `noshadow` / `noblur` rules did not match. Verify with
  `hyprctl clients | grep lovely-pet` and confirm the rules are
  listed.

**Debug:** Run with `QT_DEBUG_PLUGINS=1 python pet.py` and check
that the Qt platform is `wayland`, not `xcb`. If it fell back, the
whole compositor stack is Xwayland and transparency is impossible.

## 2. Tray icon does not appear

**Symptom:** The app runs, the pet is visible, but no icon shows up
in the system tray.

**Cause:** Hyprland does not provide a built-in StatusNotifier
watcher. The SNI protocol needs a registered D-Bus watcher
(`org.kde.StatusNotifierWatcher`) for icons to render. Common
solutions:

- Run `waybar` and add a `tray` module — it registers as the SNI
  watcher.
- Run `walker` (default Hyprland app launcher) with the tray plugin
  enabled.
- Install `snixembed` as a stand-alone SNI watcher if you want a
  minimal tray with no bar.

**Debug:** Verify a watcher is registered:

```bash
dbus-send --session --print-reply \
  --dest=org.freedesktop.DBus /org/freedesktop/DBus \
  org.freedesktop.DBus.ListNames | grep -i StatusNotifier
```

If that command prints nothing, no SNI watcher is running and tray
icons will not appear regardless of which app registered them.

**Fallback:** Lovely-pets still runs and is killable via Ctrl-C
when the tray is unavailable; the app prints a warning to stderr on
startup.

## 3. App silently falls back to Xwayland

**Symptom:** `hyprctl clients` shows the window with a class that
contains `xwayland` instead of `lovely-pet`. Mouse clicks are
intercepted, transparency is broken, performance is poor.

**Cause:** The `qt6-wayland` system package is missing. Qt then loads
the `xcb` platform plugin, which uses Xwayland, which is a deal
breaker for the click-through overlay.

**Debug:** Confirm Qt is on Wayland:

```bash
python pet.py --debug
```

The first line of stderr after the parsed-args banner should read
`Qt platform: wayland`. If it reads `xcb` or `minimal`, Qt is on
the wrong plugin.

**Fix:** Install `qt6-wayland` (Arch) or `qml6-module-qtquick`
(Debian, which pulls in `qt6-wayland` as a dependency). The
runtime assert in `lovely_pet/app.py` will also catch this and
exit with an error message that names the missing package.

**Verify:** `hyprctl clients | grep lovely-pet` should show
`xwayland: false` in the output.
