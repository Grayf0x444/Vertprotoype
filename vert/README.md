# VERT

A single-level 2D vert (halfpipe) skateboarding game in Python + pygame-ce,
inspired by the vert levels of the Game Boy Color *Tony Hawk's Pro Skater*.
Built landscape-first for touchscreens, with mouse and keyboard fallbacks for
desktop development.

Pump for speed, launch off the coping, stack GRAB / FLIP / SPIN into a named
trick combo, and land it clean before the 90-second timer runs out.

## Running it

```bash
pip install -r requirements.txt
python main.py
```

The window is resizable; the 1280x720 logical scene is scaled and letterboxed
to fit whatever size or aspect ratio the window/screen actually is.

## Controls

**Touch (primary):**
- **Bottom-left pad** — split LEFT / RIGHT halves. Hold to SPIN (rotate on
  the vertical axis) while airborne.
- **Bottom-right** — GRAB (hold), FLIP (tap), PUMP (tap). All three fit
  under a right thumb without repositioning.
- **Top-right** — small pause button.
- Multi-touch is required: hold GRAB with one thumb and SPIN with the other
  to stack a combo (e.g. INDY 360).

**Mouse:** left-click/drag over a button acts as a single "finger" — good
for smoke-testing on desktop, but only one button at a time.

**Keyboard fallback:**
| Key | Action |
|---|---|
| `←` / `→` | Spin left / right |
| `Z` | Grab |
| `X` | Flip |
| `C` | Pump |
| `Esc` | Pause |
| `Space` / `Enter` | Confirm on title / results / pause screens |

## How to play

- On the flat bottom and in the transitions, tap **PUMP** while descending
  through a transition to add speed (pumping while climbing does nothing —
  it's rhythm-based, like a real halfpipe).
- Carry enough speed past the coping and you launch into the air.
- While airborne, combine the three inputs:
  - **GRAB** (hold) — reach down and grab the board. Release it before you
    land, or the trick doesn't count.
  - **FLIP** (tap) — queue a kickflip. Each tap adds one rotation; the flip
    animation has to finish before you land.
  - **SPIN** (hold left/right) — rotate your whole body. Degrees accumulate
    the whole time it's held.
- The trick name pops up and updates live as you build the combo — watch it
  to see what you're about to land.
- Land within ±35° of a clean 180° multiple, with grab released and all
  flips finished, to bank the score. Miss that window and you bail: the
  stick figure ragdolls, the combo resets, and you respawn on the ramp at
  reduced speed after ~1.5s.
- Chain clean landings without bailing to build a combo multiplier.
- Score, combo, and the timer are in the HUD; a results screen shows your
  best trick and total score when the run ends, and the high score persists
  to `vert_highscore.json` next to the game files.

## Project layout

```
vert/
  main.py          # async main loop, state machine (TITLE / PLAY / PAUSED / RESULTS)
  config.py         # tuning constants, colors, logical resolution
  ramp.py            # Ramp geometry, height_at/slope_at, ramp+fence+graffiti drawing
  skater.py          # Skater physics, state machine, stick-figure rendering, ragdoll
  tricks.py          # trick state, TRICK_NAMES resolver, scoring
  input_touch.py      # finger tracking, button defs, hit testing, keyboard mapping
  ui.py               # HUD, animated trick text, score popups, buttons, screens
  fx.py                # camera + screen shake, trail, speed lines, procedural sfx
  test_headless.py     # scripted no-display smoke test (see below)
  requirements.txt
```

## Tuning

All gameplay-feel constants live in the `# --- TUNING ---` block at the top
of `config.py`. Notable ones:

- `GRAVITY_GROUND` / `GRAVITY_AIR` — how hard gravity pulls while on the
  ramp vs. in the air.
- `FRICTION` — constant speed bleed; higher values make pumping more
  necessary to maintain speed.
- `PUMP_BOOST`, `MIN_LAUNCH_SPEED`, `LAUNCH_VY_FACTOR`, `POP_VELOCITY` —
  control how much a pump adds, how much speed you need at the coping to
  launch, and how high you fly.
- `LANDING_ANGLE_TOLERANCE` — how forgiving landings are (degrees off a
  clean 180° multiple).
- `SPIN_RATE`, `FLIP_DURATION`, `GRAB_HELD_THRESHOLD` — trick input pacing.
- `TRANSITION_RADIUS`, `DECK_WIDTH`, `FLAT_WIDTH`, `DECK_Y` — ramp geometry.
  If you change `TRANSITION_RADIUS` or `GRAVITY_GROUND` a lot, sanity-check
  that a few pumps can still get the skater to `MIN_LAUNCH_SPEED` at the
  coping (energy needed scales with `2 * GRAVITY_GROUND * TRANSITION_RADIUS`).

Trick names and their base scores are defined in `tricks.py`, in
`resolve_trick()` — extend the branches there to add new named combos.

## Testing headlessly

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python test_headless.py
```

This drives the real `Game` object for 900 simulated frames with scripted
pump/grab/spin input (no display or audio device required), and asserts
that the skater launches, lands a trick cleanly, and that `resolve_trick()`
correctly names a couple of combo tricks.

## Packaging for mobile (pygbag)

[pygbag](https://github.com/pygame-web/pygbag) compiles a pygame-ce project
to WebAssembly so it runs in a mobile browser. The main loop is already
structured for it (`async def main()`, no blocking waits, yields every
frame via `await asyncio.sleep(0)`).

```bash
pip install pygbag
pygbag .
```

Run from inside the `vert/` folder (the one containing `main.py`). pygbag
serves the packaged build locally by default — open the printed `localhost`
URL on a phone on the same network, or run `pygbag --build .` to produce a
static `build/web` bundle you can host anywhere. `pygame.FINGERDOWN` /
`FINGERMOTION` / `FINGERUP` map to real touch events in the browser build, so
no code changes are needed for touch to work there.
