"""Headless smoke test.

Drives the real Game object (physics, tricks, scoring, rendering) for several
hundred frames with scripted synthetic input, using the SDL dummy video/audio
drivers so it runs with no display. Verifies:

  1. No crashes over the run.
  2. The skater actually launches (GROUNDED -> AIRBORNE) and lands back
     (AIRBORNE -> GROUNDED) at least once.
  3. At least one combo trick name resolves correctly via resolve_trick().

Run with:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python test_headless.py
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import main as vert_main  # noqa: E402
from skater import AIRBORNE, GROUNDED  # noqa: E402
from tricks import resolve_trick  # noqa: E402


def run() -> int:
    game = vert_main.Game()
    game.state = vert_main.PLAY

    dt = 1.0 / 60.0
    saw_air = False
    saw_clean_landing = False
    was_air = False
    air_frames = 0
    max_vx = 0.0

    for frame in range(900):
        kb = game.input.keyboard
        for key in kb:
            kb[key] = False

        if game.skater.state == GROUNDED:
            if frame % 4 < 2:
                kb["pump"] = True
            air_frames = 0

        if game.skater.state == AIRBORNE:
            was_air = True
            saw_air = True
            # Hold grab only briefly, then release it so the trick actually
            # completes (grab released) before landing. Spin only until
            # close to a clean 180 so the landing-angle check passes
            # regardless of exact hang time.
            if air_frames < 12:
                kb["grab"] = True
            if game.skater.trick is not None and game.skater.trick.spin_degrees < 170.0:
                kb["spin_right"] = True
            air_frames += 1

        game.update(dt)
        game.draw()

        max_vx = max(max_vx, abs(game.skater.vx))
        if was_air and game.skater.state == GROUNDED and game.skater.just_landed:
            saw_clean_landing = True
            was_air = False

    assert saw_air, "skater never launched into the air over 900 frames"
    assert saw_clean_landing, "skater launched but never landed a trick cleanly"

    name, base = resolve_trick(True, 0.4, 0, 360.0)
    assert name == "INDY 360", f"expected INDY 360, got {name!r}"
    assert base > 0

    name2, base2 = resolve_trick(False, 0.0, 2, 0.0)
    assert name2 == "DOUBLE KICKFLIP", f"expected DOUBLE KICKFLIP, got {name2!r}"
    assert base2 > 0

    print("HEADLESS TEST PASSED")
    print(f"  frames run: 900, max vx reached: {max_vx:.0f}, final score: {game.score}, high_score: {game.high_score}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
