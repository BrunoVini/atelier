# Media assets (BGM / SFX) — download on demand

To keep atelier lightweight, the background-music tracks and sound-effects library
from huashu-design are **not vendored** (they total tens of MB). The animation /
video capability degrades gracefully without them (silent export + a warning).

When a narrated animation or video export needs audio, fetch the originals from
the huashu-design assets folder (or your own library) into this directory:

- BGM: `bgm-tech.mp3`, `bgm-educational.mp3`, `bgm-tutorial.mp3`, `bgm-ad.mp3`, …
- SFX: organized by category under `sfx/`

`scripts/export_video.sh` looks here for `bgm-*.mp3` and `sfx/` and warns if they
are absent rather than failing.
