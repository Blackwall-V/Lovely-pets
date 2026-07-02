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
--
-- NOTE: the `move` value is in absolute pixels and must match your
-- screen resolution + pet size + margin. Run `python pet.py --debug`
-- to see the computed position, then update this line if needed.
-- Example: 1280x720 screen, 356x360 GIF, 32px margin → 891 327

hl.window_rule({
	name = "lovely-pet-overlay",
	match = { title = "Lovely Pet" },
	float = true,
	pin = true,
	no_focus = true,
	move = "891 327",
})
