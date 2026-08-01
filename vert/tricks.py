"""Trick state tracking, the TRICK_NAMES resolver, and scoring.

There are exactly three air inputs: GRAB (hold), FLIP (tap, queues a board
rotation), and SPIN (hold left/right, rotates the whole skater). TrickSession
tracks the raw inputs for a single hang time; resolve_trick() turns the raw
state into a display name and a base score.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import config


@dataclass
class TrickSession:
    """Accumulated trick inputs for one continuous airborne period."""

    grab_held: bool = False
    grab_time: float = 0.0
    flip_queue: int = 0     # flips queued but still mid-animation
    flip_count: int = 0     # flips that have finished animating
    flip_anim_timer: float = 0.0
    spin_degrees: float = 0.0

    def update(self, dt: float, inp) -> None:
        if inp.grab.held:
            self.grab_held = True
            self.grab_time += dt
        else:
            self.grab_held = False

        if inp.flip.just_pressed:
            self.flip_queue += 1

        if self.flip_queue > 0:
            self.flip_anim_timer += dt
            if self.flip_anim_timer >= config.FLIP_DURATION:
                self.flip_anim_timer -= config.FLIP_DURATION
                self.flip_queue -= 1
                self.flip_count += 1

        if inp.spin_left.held and not inp.spin_right.held:
            self.spin_degrees -= config.SPIN_RATE * dt
        elif inp.spin_right.held and not inp.spin_left.held:
            self.spin_degrees += config.SPIN_RATE * dt

    @property
    def tricks_complete(self) -> bool:
        """Landing is only legal once the grab is released and no flip is mid-animation."""
        return (not self.grab_held) and self.flip_queue == 0

    @property
    def flip_in_progress_ratio(self) -> float:
        if self.flip_queue == 0:
            return 0.0
        return self.flip_anim_timer / config.FLIP_DURATION


def flip_name(flip_count: int) -> str:
    if flip_count <= 1:
        return "KICKFLIP"
    if flip_count == 2:
        return "DOUBLE KICKFLIP"
    if flip_count == 3:
        return "TRIPLE KICKFLIP"
    return "QUAD KICKFLIP"


def _spin_solo_name(spin: float) -> Tuple[str, int]:
    if spin >= 900:
        return "900", 1900
    if spin >= 720:
        return "720 SPIN", 1500
    if spin >= 540:
        return "540", 1100
    if spin >= 360:
        return "FRONTSIDE 360", 700
    return "FRONTSIDE 180", 350


def resolve_trick(grab_held: bool, grab_time: float, flip_count: int, spin_degrees: float) -> Tuple[str, int]:
    """The TRICK_NAMES resolver: raw trick state in, (display name, base score) out.

    `grab_held` is true while the grab button is currently down; `grab_time`
    is total seconds the grab has been held this air (used so the name
    doesn't vanish the instant the button is released before landing).
    """
    spin = abs(spin_degrees)
    has_grab = grab_held or grab_time > 0.05
    has_flip = flip_count > 0
    has_spin = spin >= 150.0

    if has_grab and has_flip and spin >= 540:
        return "CHRIST AIR", 5000

    if has_grab and has_spin:
        if spin >= 540:
            return "MADONNA 540", 2200
        if spin >= 360:
            return "INDY 360", 1600
        # Grabbed with a partial spin that hasn't hit a named combo yet.
        _, base = _spin_solo_name(spin)
        return "INDY GRAB + FRONTSIDE SPIN", base + 300

    if has_flip and has_spin:
        if spin >= 540:
            return "MCTWIST", 2400
        if spin >= 360:
            return "360 KICKFLIP", 1700
        return f"{flip_name(flip_count)} + SPIN", 900

    if has_spin:
        return _spin_solo_name(spin)

    if has_flip:
        return flip_name(flip_count), 200 + 150 * min(flip_count, 4)

    if has_grab:
        if grab_time > config.GRAB_HELD_THRESHOLD:
            mult = 1.0 + (grab_time - config.GRAB_HELD_THRESHOLD) * 0.5
            return f"INDY GRAB (HELD x{mult:.1f})", int(300 * mult)
        return "INDY GRAB", 300

    return "", 0


def score_trick(base_score: int, grab_time: float, spin_degrees: float, combo_count: int) -> int:
    """Scale a trick's base score by grab duration, spin magnitude, and combo chain length."""
    grab_mult = 1.0 + min(grab_time, 4.0) * 0.25
    spin_mult = 1.0 + abs(spin_degrees) / 720.0
    combo_mult = 1.0 + combo_count * 0.15
    return int(base_score * grab_mult * spin_mult * combo_mult)
