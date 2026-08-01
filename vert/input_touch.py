"""Finger tracking, on-screen button hit-testing, and keyboard fallback.

Touch is multi-touch aware: fingers are tracked in a dict keyed by finger_id,
so two buttons (e.g. GRAB + SPIN) can be held down by two different fingers
at once. Mouse and keyboard are mapped onto the same action set so the game
is testable on desktop and driveable headlessly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import pygame

import config

ACTIONS = ("spin_left", "spin_right", "grab", "flip", "pump", "pause")

KEY_MAP = {
    pygame.K_LEFT: "spin_left",
    pygame.K_RIGHT: "spin_right",
    pygame.K_z: "grab",
    pygame.K_x: "flip",
    pygame.K_c: "pump",
    pygame.K_ESCAPE: "pause",
}


@dataclass
class Button:
    name: str
    shape: str  # "circle" or "rect"
    rect: pygame.Rect
    center: Tuple[float, float] = (0.0, 0.0)
    radius: float = 0.0
    pad: float = 20.0
    label: str = ""
    color: Tuple[int, int, int] = (255, 255, 255)

    def hit_test(self, x: float, y: float) -> bool:
        if self.shape == "circle":
            dx = x - self.center[0]
            dy = y - self.center[1]
            reach = self.radius + self.pad
            return dx * dx + dy * dy <= reach * reach
        return self.rect.inflate(self.pad * 2, self.pad * 2).collidepoint(x, y)


def build_buttons() -> Dict[str, Button]:
    """Big-thumb layout: SPIN pad bottom-left, GRAB/FLIP/PUMP bottom-right, pause top-right."""
    w, h = config.LOGICAL_WIDTH, config.LOGICAL_HEIGHT
    buttons: Dict[str, Button] = {}

    spin_w, spin_h = 190, 170
    spin_x, spin_y = 24, h - spin_h - 24
    buttons["spin_left"] = Button(
        "spin_left", "rect", pygame.Rect(spin_x, spin_y, spin_w, spin_h),
        label="<", color=config.CYAN,
    )
    buttons["spin_right"] = Button(
        "spin_right", "rect", pygame.Rect(spin_x + spin_w + 6, spin_y, spin_w, spin_h),
        label=">", color=config.CYAN,
    )

    buttons["grab"] = Button(
        "grab", "circle", pygame.Rect(0, 0, 0, 0),
        center=(w - 330, h - 140), radius=95, label="GRAB", color=config.MAGENTA,
    )
    buttons["flip"] = Button(
        "flip", "circle", pygame.Rect(0, 0, 0, 0),
        center=(w - 160, h - 320), radius=90, label="FLIP", color=config.LIME,
    )
    buttons["pump"] = Button(
        "pump", "circle", pygame.Rect(0, 0, 0, 0),
        center=(w - 110, h - 110), radius=70, label="PUMP", color=config.ORANGE,
    )

    buttons["pause"] = Button(
        "pause", "rect", pygame.Rect(w - 74, 18, 54, 54),
        pad=10, label="II", color=config.WHITE,
    )
    return buttons


@dataclass
class ActionState:
    held: bool = False
    just_pressed: bool = False
    just_released: bool = False


@dataclass
class InputState:
    spin_left: ActionState
    spin_right: ActionState
    grab: ActionState
    flip: ActionState
    pump: ActionState
    pause: ActionState


class InputManager:
    def __init__(self, buttons: Dict[str, Button]):
        self.buttons = buttons
        self.fingers: Dict[object, Tuple[float, float]] = {}
        self.keyboard: Dict[str, bool] = {name: False for name in ACTIONS}
        self._prev_held: Dict[str, bool] = {name: False for name in ACTIONS}
        self.letterbox: Tuple[float, float, float, float] = (
            0.0, 0.0, float(config.LOGICAL_WIDTH), float(config.LOGICAL_HEIGHT),
        )

    def set_letterbox(self, ox: float, oy: float, sw: float, sh: float) -> None:
        self.letterbox = (ox, oy, sw, sh)

    def window_to_logical(self, px: float, py: float) -> Tuple[float, float]:
        ox, oy, sw, sh = self.letterbox
        if sw <= 0 or sh <= 0:
            return (0.0, 0.0)
        lx = (px - ox) / sw * config.LOGICAL_WIDTH
        ly = (py - oy) / sh * config.LOGICAL_HEIGHT
        return lx, ly

    def handle_event(self, event: pygame.event.Event, window_size: Tuple[int, int]) -> None:
        if event.type == pygame.FINGERDOWN or event.type == pygame.FINGERMOTION:
            px, py = event.x * window_size[0], event.y * window_size[1]
            self.fingers[event.finger_id] = self.window_to_logical(px, py)
        elif event.type == pygame.FINGERUP:
            self.fingers.pop(event.finger_id, None)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.fingers["mouse"] = self.window_to_logical(*event.pos)
        elif event.type == pygame.MOUSEMOTION:
            if "mouse" in self.fingers:
                self.fingers["mouse"] = self.window_to_logical(*event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.fingers.pop("mouse", None)
        elif event.type == pygame.KEYDOWN:
            action = KEY_MAP.get(event.key)
            if action:
                self.keyboard[action] = True
        elif event.type == pygame.KEYUP:
            action = KEY_MAP.get(event.key)
            if action:
                self.keyboard[action] = False

    def is_held(self, name: str) -> bool:
        if self.keyboard.get(name):
            return True
        btn = self.buttons.get(name)
        if not btn:
            return False
        for pos in self.fingers.values():
            if btn.hit_test(*pos):
                return True
        return False

    def compute(self) -> InputState:
        states = {}
        for name in ACTIONS:
            held = self.is_held(name)
            prev = self._prev_held[name]
            states[name] = ActionState(
                held=held, just_pressed=held and not prev, just_released=(not held) and prev,
            )
            self._prev_held[name] = held
        return InputState(
            spin_left=states["spin_left"], spin_right=states["spin_right"],
            grab=states["grab"], flip=states["flip"], pump=states["pump"], pause=states["pause"],
        )
