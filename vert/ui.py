"""HUD, animated trick text, score popups, on-screen buttons, and screens."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List

import pygame

import config
from input_touch import Button

_FONT_CACHE: Dict[tuple, pygame.font.Font] = {}


def get_font(size: int, bold: bool = True) -> pygame.font.Font:
    key = (size, bold)
    if key not in _FONT_CACHE:
        try:
            font = pygame.font.SysFont("arialblack,arial,dejavusans", size, bold=bold)
        except Exception:
            font = pygame.font.Font(None, size)
        _FONT_CACHE[key] = font
    return _FONT_CACHE[key]


def ease_out_back(t: float) -> float:
    c1 = 1.70158
    c3 = c1 + 1.0
    t = max(0.0, min(1.0, t))
    return 1.0 + c3 * (t - 1.0) ** 3 + c1 * (t - 1.0) ** 2


def draw_outlined_text(
    surface: pygame.Surface, text: str, size: int, pos, color, outline=config.BLACK,
    center: bool = True, bold: bool = True, outline_w: int = 3, alpha: int = 255,
) -> pygame.Rect:
    if not text or size < 4:
        return pygame.Rect(pos[0], pos[1], 0, 0)
    font = get_font(size, bold)
    base = font.render(text, True, color)
    outline_s = font.render(text, True, outline)
    w = base.get_width() + outline_w * 2
    h = base.get_height() + outline_w * 2
    layer = pygame.Surface((w, h), pygame.SRCALPHA)
    base_rect = base.get_rect(center=(w // 2, h // 2))
    for dx, dy in ((-outline_w, 0), (outline_w, 0), (0, -outline_w), (0, outline_w),
                   (-outline_w, -outline_w), (outline_w, -outline_w), (-outline_w, outline_w), (outline_w, outline_w)):
        layer.blit(outline_s, base_rect.move(dx, dy))
    layer.blit(base, base_rect)
    if alpha < 255:
        layer.set_alpha(max(0, alpha))
    rect = layer.get_rect(center=pos) if center else layer.get_rect(topleft=pos)
    surface.blit(layer, rect)
    return rect


class HUD:
    def draw(self, surface: pygame.Surface, score: int, combo: int, time_left: float, high_score: int) -> None:
        draw_outlined_text(surface, f"{score:06d}", 46, (170, 50), config.WHITE)
        if combo > 1:
            draw_outlined_text(surface, f"COMBO x{combo}", 30, (170, 96), config.ORANGE)
        secs = max(0, int(math.ceil(time_left)))
        col = config.HOT_PINK if secs <= 10 else config.CYAN
        draw_outlined_text(surface, f"{secs:02d}", 50, (config.LOGICAL_WIDTH / 2, 44), col)
        draw_outlined_text(surface, f"BEST {high_score}", 22, (config.LOGICAL_WIDTH - 150, 40), config.LIME)


@dataclass
class TrickText:
    active: bool = False
    text: str = ""
    age: float = 0.0
    x: float = 0.0

    def __post_init__(self) -> None:
        self.x = config.LOGICAL_WIDTH / 2

    def show(self, text: str) -> None:
        if text != self.text:
            self.age = 0.0
        self.active = True
        self.text = text

    def update(self, dt: float) -> None:
        if self.active:
            self.age += dt

    def hide(self) -> None:
        self.active = False
        self.text = ""

    def draw(self, surface: pygame.Surface) -> None:
        if not self.active or not self.text:
            return
        pop_t = min(1.0, self.age / 0.18)
        scale = 0.35 + 0.65 * ease_out_back(pop_t)
        drift = self.age * 34.0
        alpha = 255
        if self.age > 1.2:
            alpha = max(0, int(255 * (1.0 - (self.age - 1.2) / 0.5)))
        size = max(10, int(60 * max(0.1, scale)))
        y = config.LOGICAL_HEIGHT * 0.30 - drift
        is_rare = "CHRIST" in self.text
        col = config.YELLOW if not is_rare else config.HOT_PINK
        draw_outlined_text(surface, self.text, size, (self.x, y), col, outline_w=4, alpha=alpha)


@dataclass
class ScorePopup:
    x: float
    y: float
    text: str
    age: float = 0.0
    life: float = 1.2


class ScorePopups:
    def __init__(self) -> None:
        self.items: List[ScorePopup] = []

    def add(self, x: float, y: float, points: int) -> None:
        self.items.append(ScorePopup(x, y, f"+{points}"))

    def update(self, dt: float) -> None:
        for p in self.items:
            p.age += dt
        self.items = [p for p in self.items if p.age < p.life]

    def draw(self, surface: pygame.Surface, camera) -> None:
        for p in self.items:
            t = p.age / p.life
            sx, sy = camera.to_screen(p.x, p.y)
            sy -= t * 70.0
            alpha = int(255 * (1.0 - t))
            draw_outlined_text(surface, p.text, 32, (sx, sy), config.LIME, outline_w=3, alpha=alpha)


def draw_buttons(surface: pygame.Surface, buttons: Dict[str, Button], input_mgr) -> None:
    overlay = pygame.Surface((config.LOGICAL_WIDTH, config.LOGICAL_HEIGHT), pygame.SRCALPHA)
    for name, btn in buttons.items():
        pressed = input_mgr.is_held(name)
        fill = (*btn.color, 150 if pressed else 80)
        outline = (255, 255, 255, 255) if pressed else (*config.BLACK, 220)
        if btn.shape == "circle":
            c = (int(btn.center[0]), int(btn.center[1]))
            r = int(btn.radius) + (6 if pressed else 0)
            pygame.draw.circle(overlay, fill, c, r)
            pygame.draw.circle(overlay, outline, c, r, 5)
        else:
            r = btn.rect.inflate(6, 6) if pressed else btn.rect
            pygame.draw.rect(overlay, fill, r, border_radius=18)
            pygame.draw.rect(overlay, outline, r, 5, border_radius=18)
    surface.blit(overlay, (0, 0))
    for name, btn in buttons.items():
        label_pos = btn.center if btn.shape == "circle" else btn.rect.center
        size = 30 if btn.shape == "circle" else 38
        draw_outlined_text(surface, btn.label, size, label_pos, config.WHITE, outline_w=3)


def draw_title_screen(surface: pygame.Surface, t: float) -> None:
    bob = math.sin(t * 2.0) * 8.0
    draw_outlined_text(
        surface, "VERT", 150, (config.LOGICAL_WIDTH / 2, 250 + bob), config.HOT_PINK, outline_w=7,
    )
    draw_outlined_text(
        surface, "TAP OR PRESS SPACE TO DROP IN", 36, (config.LOGICAL_WIDTH / 2, 410), config.WHITE, outline_w=3,
    )
    draw_outlined_text(
        surface, "SPIN: bottom-left pad    GRAB / FLIP / PUMP: bottom-right",
        22, (config.LOGICAL_WIDTH / 2, 460), config.CYAN, outline_w=2,
    )
    draw_outlined_text(
        surface, "KEYBOARD: <- -> spin   Z grab   X flip   C pump   ESC pause",
        20, (config.LOGICAL_WIDTH / 2, 495), config.LIME, outline_w=2,
    )


def draw_results_screen(
    surface: pygame.Surface, score: int, best_trick: str, best_trick_score: int,
    high_score: int, retry_rect: pygame.Rect,
) -> None:
    overlay = pygame.Surface((config.LOGICAL_WIDTH, config.LOGICAL_HEIGHT), pygame.SRCALPHA)
    overlay.fill((10, 0, 20, 150))
    surface.blit(overlay, (0, 0))
    draw_outlined_text(surface, "RUN COMPLETE", 66, (config.LOGICAL_WIDTH / 2, 150), config.YELLOW, outline_w=5)
    draw_outlined_text(surface, f"SCORE  {score}", 50, (config.LOGICAL_WIDTH / 2, 240), config.WHITE)
    trick_label = best_trick if best_trick else "-"
    draw_outlined_text(
        surface, f"BEST TRICK  {trick_label} ({best_trick_score})", 32,
        (config.LOGICAL_WIDTH / 2, 300), config.LIME,
    )
    draw_outlined_text(surface, f"HIGH SCORE  {high_score}", 28, (config.LOGICAL_WIDTH / 2, 350), config.CYAN)
    pygame.draw.rect(surface, config.ORANGE, retry_rect, border_radius=20)
    pygame.draw.rect(surface, config.BLACK, retry_rect, 5, border_radius=20)
    draw_outlined_text(surface, "RETRY", 40, retry_rect.center, config.WHITE)


def draw_pause_overlay(surface: pygame.Surface, resume_rect: pygame.Rect) -> None:
    overlay = pygame.Surface((config.LOGICAL_WIDTH, config.LOGICAL_HEIGHT), pygame.SRCALPHA)
    overlay.fill((10, 0, 20, 170))
    surface.blit(overlay, (0, 0))
    draw_outlined_text(surface, "PAUSED", 68, (config.LOGICAL_WIDTH / 2, 260), config.WHITE, outline_w=5)
    pygame.draw.rect(surface, config.LIME, resume_rect, border_radius=20)
    pygame.draw.rect(surface, config.BLACK, resume_rect, 5, border_radius=20)
    draw_outlined_text(surface, "RESUME", 34, resume_rect.center, config.BLACK)
