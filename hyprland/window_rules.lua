-- Hyprland window rules for Lovely-pets (Lua config format)
--
-- Match by **title** (not class). Qt 6.11 derives the xdg-shell
-- app_id from the executable's path basename, so when launched as
-- `python pet.py` the class resolves to `python3`. The window
-- title is set explicitly via `QWidget.setWindowTitle("Lovely Pet")`
-- in pet.py, so a title-based match is reliable.
--
-- To install (Hyprland 0.46+ with Lua config):
--   cat hyprland/window_rules.lua >> ~/.config/hypr/hyprland.lua
--   hyprctl reload
--
-- To verify:
--   hyprctl clients | grep -A2 "Lovely Pet"
--   hyprctl configerrors   (should be empty)
--
-- Field name reference (verified on Hyprland 0.55.4 Lua API):
--   float, pin, no_focus, no_anim, no_shadow, no_blur,
--   no_max_size, border_size, rounding, move
--
-- NOTE: `passthrough` (click-through) does NOT exist in the Lua
-- API. Click-through is handled at the Qt level via
-- Qt.WindowType.WindowTransparentForInput in lovely_pet/window.py.
--
-- NOTE: the `move` value is in logical pixels (accounting for the
-- monitor scale factor). Run `python pet.py --debug` to see the
-- computed position, then update this line if you change your
-- GIF, screen, or margin.
-- Example: 1920x1080 @ 1.5x scale → 1280x720 logical
--          356x360 GIF, 32px margin → move = "891 327"

hl.window_rule({
	name = "lovely-pet-overlay",
	match = { title = "Lovely Pet" },
	float = true,
	pin = true,
	no_focus = true,
	no_anim = true,
	no_shadow = true,
	no_blur = true,
	no_max_size = true,
	border_size = 0,
	rounding = 0,
	move = "891 327",
})
