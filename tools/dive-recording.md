# Manual asciinema recording of `hardwood dive`

## One-time setup

```bash
$ brew install asciinema           # or: dnf/apt install asciinema
$ brew install agg                 # optional, for GIF rendering
```

iTerm2: create a "Recording" profile once, used for every take.
- `Settings → Profiles → Colors → Color Presets…`: pick **Dark Background**
  for a neutral, high-contrast look that survives the GIF/SVG render step.

Open a window with the profile via `Profiles` menu → "Recording" → `⌘N`.

Window size is set per-recording via an xterm CSI 8 sequence (see below),
so leave **Disable session-initiated resizing** *off* in this profile — it
would otherwise block that resize.

## Per-recording

```bash
# 1. Env (in the outer shell — before asciinema)
$ export HARDWOOD_BIN="$PWD/hardwood-cli-early-access-macos-aarch64/bin/hardwood"

# 2. Configure file access on local s3proxy (see TESTING.md)
$ export AWS_ENDPOINT_URL=http://localhost:9090
$ ...

# 3. Resize the window to the target geometry (rows ; cols)
$ printf '\e[8;35;120t'

# 4. Record (no shell, just dive — exits cleanly when you press q)
$ asciinema rec dive-demo.cast \
      --rows 35 --cols 120 --idle-time-limit 5 \
      --title "hardwood dive — Overture Places" \
      -c "$HARDWOOD_BIN dive --file s3://test-bucket/overture_places.zstd.parquet"

# 5. Drive the UI by hand. Quit with q to stop the recording.

# 6. Review
$ asciinema play dive-demo.cast
$ asciinema play -s 2 dive-demo.cast       # 2× to scrub
```

## Re-recording

```bash
$ rm dive-demo.cast        # bad take? just delete and rerun the asciinema rec line
```

## Share / export

```bash
$ asciinema upload dive-demo.cast                  # asciinema.org URL
$ agg dive-demo.cast dive-demo.gif                 # GIF
$ agg --theme monokai --font-size 14 dive-demo.cast dive-demo.gif
```

## Tips for clean takes

- Pause ~1.5s on each screen — `--idle-time-limit 2` compresses long pauses on
  playback, so don't rush.
- Don't backspace typos; restart the take.
- Mute notifications, close chat apps that auto-focus the terminal.
