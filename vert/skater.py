"""Skater physics, state machine, stick-figure rendering, and bail ragdoll."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

import pygame

import config
from ramp import Ramp
from tricks import TrickSession, resolve_trick

GROUNDED = "GROUNDED"
AIRBORNE = "AIRBORNE"
BAILING = "BAILING"


@dataclass
class RagdollLimb:
    x: float
    y: float
    vx: float
    vy: float
    angle: float
    va: float
    length: float


class Skater:
    def __init__(self, ramp: Ramp) -> None:
        self.ramp = ramp
        self.facing = 1
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.state = GROUNDED
        self.lean_angle = 0.0
        self.air_time = 0.0
        self.trick: Optional[TrickSession] = None
        self.bail_timer = 0.0
        self.pre_bail_speed = 0.0
        self.ragdoll: List[RagdollLimb] = []
        self.pump_flash = 0.0

        self.just_launched = False
        self.just_landed = False
        self.just_bailed = False
        self.last_trick_result: Optional[Tuple[str, int, float, float]] = None

        self.reset_position(speed_mult=1.0)

    def reset_position(self, speed_mult: float = 1.0) -> None:
        self.x = (self.ramp.flat_bottom_left + self.ramp.flat_bottom_right) / 2
        self.y = self.ramp.height_at(self.x)
        self.vx = 260.0 * speed_mult * (self.facing or 1)
        self.vy = 0.0
        self.state = GROUNDED
        self.trick = None
        self.ragdoll = []
        self.lean_angle = 0.0

    def update(self, dt: float, inp) -> None:
        self.just_launched = False
        self.just_landed = False
        self.just_bailed = False
        self.pump_flash = max(0.0, self.pump_flash - dt * 3.0)

        if self.state == GROUNDED:
            self._update_grounded(dt, inp)
        elif self.state == AIRBORNE:
            self._update_airborne(dt, inp)
        elif self.state == BAILING:
            self._update_bailing(dt)

    # --- grounded ---
    def _update_grounded(self, dt: float, inp) -> None:
        slope = self.ramp.slope_at(self.x)
        self.vx += config.GRAVITY_GROUND * slope * dt
        self.vx -= self.vx * config.FRICTION * dt
        self.vx = max(-config.MAX_SPEED, min(config.MAX_SPEED, self.vx))

        if inp.pump.just_pressed:
            descending = (self.vx * slope) > 0.0
            if self.ramp.in_transition(self.x) and descending and abs(self.vx) > 5.0:
                self.vx += config.PUMP_BOOST * (1.0 if self.vx >= 0 else -1.0)
                self.vx = max(-config.MAX_SPEED, min(config.MAX_SPEED, self.vx))
                self.pump_flash = 1.0

        new_x = self.x + self.vx * dt
        new_x = max(0.0, min(self.ramp.total_width, new_x))

        crossing_left = self.x >= self.ramp.left_coping_x and new_x < self.ramp.left_coping_x
        crossing_right = self.x <= self.ramp.right_coping_x and new_x > self.ramp.right_coping_x

        if (crossing_left or crossing_right) and abs(self.vx) >= config.MIN_LAUNCH_SPEED:
            self._launch()
            return

        self.x = new_x
        self.y = self.ramp.height_at(self.x)
        self.lean_angle = math.degrees(math.atan(self.ramp.slope_at(self.x)))
        if self.vx != 0:
            self.facing = 1 if self.vx > 0 else -1

    def _launch(self) -> None:
        self.state = AIRBORNE
        self.y = self.ramp.height_at(self.x)
        self.vy = -abs(self.vx) * config.LAUNCH_VY_FACTOR - config.POP_VELOCITY
        self.trick = TrickSession()
        self.air_time = 0.0
        self.just_launched = True

    # --- airborne ---
    def _update_airborne(self, dt: float, inp) -> None:
        self.vy += config.GRAVITY_AIR * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.air_time += dt
        # The level is a single closed halfpipe: treat its outer edges as
        # invisible walls so a big air can never carry the skater off past
        # the decks into empty space.
        self.x = max(0.0, min(self.ramp.total_width, self.x))

        if self.trick is not None:
            self.trick.update(dt, inp)

        surface_y = self.ramp.height_at(self.x)
        if self.vy >= 0.0 and self.y >= surface_y:
            self._attempt_landing(surface_y)

    def _attempt_landing(self, surface_y: float) -> None:
        t = self.trick
        if t is not None:
            nearest_180 = round(t.spin_degrees / 180.0) * 180.0
            rotation_ok = abs(t.spin_degrees - nearest_180) <= config.LANDING_ANGLE_TOLERANCE
            tricks_complete = t.tricks_complete
        else:
            rotation_ok = True
            tricks_complete = True

        if rotation_ok and tricks_complete:
            self.state = GROUNDED
            self.y = surface_y
            self.lean_angle = math.degrees(math.atan(self.ramp.slope_at(self.x)))
            self.vy = 0.0
            self.vx = max(-config.MAX_SPEED, min(config.MAX_SPEED, self.vx))
            self.just_landed = True
            if t is not None:
                name, base = resolve_trick(t.grab_held, t.grab_time, t.flip_count, t.spin_degrees)
                self.last_trick_result = (name, base, t.grab_time, t.spin_degrees)
            else:
                self.last_trick_result = None
            self.trick = None
        else:
            self._bail()

    def _bail(self) -> None:
        self.pre_bail_speed = self.vx
        self.state = BAILING
        self.bail_timer = config.BAIL_RESPAWN_DELAY
        self.just_bailed = True
        self.trick = None
        self._spawn_ragdoll()

    def _spawn_ragdoll(self) -> None:
        self.ragdoll = []
        for _ in range(5):
            ang = random.uniform(0.0, 360.0)
            speed = random.uniform(80.0, 260.0)
            self.ragdoll.append(RagdollLimb(
                x=self.x, y=self.y,
                vx=math.cos(math.radians(ang)) * speed + self.vx * 0.3,
                vy=math.sin(math.radians(ang)) * speed - 100.0,
                angle=random.uniform(0.0, 360.0),
                va=random.uniform(-360.0, 360.0),
                length=random.uniform(18.0, 34.0),
            ))

    def _update_bailing(self, dt: float) -> None:
        for limb in self.ragdoll:
            limb.vy += config.GRAVITY_AIR * 0.6 * dt
            limb.x += limb.vx * dt
            limb.y += limb.vy * dt
            limb.angle += limb.va * dt
        self.bail_timer -= dt
        if self.bail_timer <= 0.0:
            speed = max(120.0, abs(self.pre_bail_speed) * config.BAIL_SPEED_MULT)
            self.reset_position(speed_mult=1.0)
            self.vx = speed * (self.facing or 1)

    # --- drawing ---
    def draw(self, surface: pygame.Surface, camera, t: float) -> None:
        scale = 46.0 * camera.zoom
        if self.state == BAILING:
            draw_ragdoll(surface, camera, self.ragdoll, config.LIME, config.BLACK)
            return

        pos = camera.to_screen(self.x, self.y)
        if self.state == GROUNDED:
            lean = self.lean_angle
            board_angle = 0.0
            grab = False
        else:
            tr = self.trick
            lean = tr.spin_degrees if tr else 0.0
            flip_progress = tr.flip_in_progress_ratio if tr else 0.0
            board_angle = flip_progress * 360.0 * (1 if self.facing > 0 else -1)
            grab = bool(tr and tr.grab_held)

        draw_stick_figure(surface, pos, scale, lean, board_angle, grab, self.facing, config.LIME, config.BLACK)


def draw_stick_figure(
    surface: pygame.Surface,
    pos: Tuple[float, float],
    scale: float,
    lean_angle: float,
    board_angle: float,
    grab: bool,
    facing: int,
    color: Tuple[int, int, int],
    outline: Tuple[int, int, int],
) -> None:
    """Draws a simple articulated stick-figure skater on a board.

    All poses funnel through this one function so they stay easy to tweak:
    `pos` is the board-center screen position, `lean_angle` rotates the whole
    body/board (ramp slope while grounded, spin rotation while airborne),
    `board_angle` is the board's rotation relative to the body (flip
    tricks), `grab` reaches the trailing arm down to the board, and
    `facing` (+1/-1) mirrors the pose left-to-right.
    """
    x, y = pos
    ang = math.radians(lean_angle)
    up = (-math.sin(ang), -math.cos(ang))
    right = (math.cos(ang), -math.sin(ang))

    def pt(along_up: float, along_right: float) -> Tuple[float, float]:
        return (
            x + up[0] * along_up * scale + right[0] * along_right * scale * facing,
            y + up[1] * along_up * scale + right[1] * along_right * scale * facing,
        )

    board_ang = math.radians(lean_angle + board_angle)
    bright = (math.cos(board_ang), -math.sin(board_ang))
    board_len = 0.9
    b0 = (x - bright[0] * board_len * scale * facing, y - bright[1] * board_len * scale * facing)
    b1 = (x + bright[0] * board_len * scale * facing, y + bright[1] * board_len * scale * facing)
    pygame.draw.line(surface, outline, b0, b1, max(3, int(scale * 0.16)))

    hip = pt(0.9, 0.0)
    shoulder = pt(1.9, 0.05)
    head_c = pt(2.35, 0.05)
    front_foot = pt(0.05, 0.5)
    back_foot = pt(0.05, -0.5)
    front_hand = pt(0.4, 0.55) if grab else pt(1.4, 0.9)
    back_hand = pt(1.5, -0.7)

    limbs = [
        (hip, shoulder), (shoulder, front_hand), (shoulder, back_hand),
        (hip, front_foot), (hip, back_foot),
    ]
    w = max(3, int(scale * 0.14))
    for a, b in limbs:
        pygame.draw.line(surface, outline, a, b, w + 2)
        pygame.draw.line(surface, color, a, b, w)

    r = max(4, int(scale * 0.32))
    head_pos = (int(head_c[0]), int(head_c[1]))
    pygame.draw.circle(surface, outline, head_pos, r + 2)
    pygame.draw.circle(surface, color, head_pos, r)


def draw_ragdoll(surface: pygame.Surface, camera, limbs: List[RagdollLimb], color, outline) -> None:
    for limb in limbs:
        p = camera.to_screen(limb.x, limb.y)
        ang = math.radians(limb.angle)
        half_len = limb.length * camera.zoom / 2.0
        dx = math.cos(ang) * half_len
        dy = math.sin(ang) * half_len
        a = (p[0] - dx, p[1] - dy)
        b = (p[0] + dx, p[1] + dy)
        pygame.draw.line(surface, outline, a, b, 7)
        pygame.draw.line(surface, color, a, b, 4)
