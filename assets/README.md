# assets/

Bundled media files for Lovely-pets.

## sample_pet.gif

A 64×64 animated GIF used as the default pet when the app launches
without a `--source` argument. Pink circle tracing a figure-8 path
over a fully transparent background. Regenerate it with:

```bash
python tools/make_sample_pet.py
```

The generator script is a one-off; it has no runtime role. It is
shipped in `tools/` so the asset can be reproduced without reverse
engineering the GIF.

## Adding your own pets

Drop a `.gif`, `.mp4`, `.webm`, `.mov`, `.mkv`, or `.avi` file in
this directory and pass it on the command line:

```bash
python pet.py assets/your_pet.gif
```

…or via the **Load Pet...** entry in the system tray at runtime.
