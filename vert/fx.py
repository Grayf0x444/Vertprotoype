"""Camera (with screen shake), the air trail, speed lines, and procedural SFX."""
from __future__ import annotations

import random
from typing import List, Tuple

import pygame

import config


class Camera:
    """Follows the skater with damping and zooms out for big airs."""

    def __init__(self) -> None:
        self.x = config.TOTAL_WIDTH / 2
        self.y = config.FLAT_Y
        self.zoom = 1.0
        self._shake_mag = 0.0
        self._shake_time = 0.0
        self._shake_total = 1.0
        self._shake_offset = (0.0, 0.0)

    def shake(self, magnitude: float, duration: float) -> None:
        self._shake_mag = magnitude
        self._shake_time = duration
        self._shake_total = max(0.0001, duration)

    def update(self, target_x: float, target_y: float, target_zoom: float, dt: float) -> None:
        damp = min(1.0, 6.0 * dt)
        self.x += (target_x - self.x) * damp
        self.y += (target_y - self.y) * damp
        self.zoom += (target_zoom - self.zoom) * damp
        if self._shake_time > 0:
            self._shake_time -= dt
            t = max(0.0, self._shake_time / self._shake_total)
            m = self._shake_mag * t
            self._shake_offset = (random.uniform(-m, m), random.uniform(-m, m))
        else:
            self._shake_offset = (0.0, 0.0)

    def to_screen(self, x: float, y: float) -> Tuple[float, float]:
        sx = (x - self.x) * self.zoom + config.LOGICAL_WIDTH / 2 + self._shake_offset[0]
        sy = (y - self.y) * self.zoom + config.LOGICAL_HEIGHT * 0.60 + self._shake_offset[1]
        return sx, sy


class TrailFX:
    """A chunky, fading trail arc showing the skater's recent air path."""

    def __init__(self) -> None:
        self.points: List[List[float]] = []

    def add(self, x: float, y: float) -> None:
        self.points.append([x, y, 1.0])

    def update(self, dt: float) -> None:
        for p in self.points:
            p[2] -= dt * 0.7
        self.points = [p for p in self.points if p[2] > 0]

    def clear(self) -> None:
        self.points.clear()

    def draw(self, surface: pygame.Surface, camera: Camera, color: Tuple[int, int, int]) -> None:
        if len(self.points) < 2:
            return
        layer = pygame.Surface((config.LOGICAL_WIDTH, config.LOGICAL_HEIGHT), pygame.SRCALPHA)
        for i in range(1, len(self.points)):
            a = self.points[i - 1]
            b = self.points[i]
            alpha = max(0, min(255, int(b[2] * 220)))
            width = max(2, int(9 * b[2]))
            p0 = camera.to_screen(a[0], a[1])
            p1 = camera.to_screen(b[0], b[1])
            pygame.draw.line(layer, (*color, alpha), p0, p1, width)
        surface.blit(layer, (0, 0))


def draw_speed_lines(surface: pygame.Surface, camera: Camera, skater) -> None:
    if skater.state != "GROUNDED" or abs(skater.vx) < 380:
        return
    sx, sy = camera.to_screen(skater.x, skater.y)
    direction = -1 if skater.vx > 0 else 1
    for i in range(4):
        offset = 30 + i * 16
        length = 34 + i * 12
        y0 = sy - 6 + i * 7
        x0 = sx + direction * offset
        x1 = x0 + direction * length
        pygame.draw.line(surface, config.WHITE, (x0, y0), (x1, y0), 3)


class SfxBank:
    """Tiny procedurally generated sound effects. Silently disables itself if audio fails."""

    def __init__(self) -> None:
        self.enabled = False
        self.pop = None
        self.thud = None
        self.buzz = None
        try:
            import numpy as np

            pygame.mixer.init(frequency=22050, size=-16, channels=1)
            self.pop = self._tone(np, 620.0, 1500.0, 0.10)
            self.thud = self._tone(np, 160.0, 55.0, 0.18)
            self.buzz = self._noise(np, 0.28)
            self.enabled = True
        except Exception:
            self.enabled = False

    @staticmethod
    def _tone(np, freq_start: float, freq_end: float, duration: float):
        rate = 22050
        n = max(1, int(rate * duration))
        t = np.linspace(0.0, duration, n, endpoint=False)
        freq = np.linspace(freq_start, freq_end, n)
        wave = np.sin(2.0 * np.pi * freq * t)
        env = np.linspace(1.0, 0.0, n) ** 1.5
        arr = (wave * env * 32767 * 0.5).astype(np.int16)
        return pygame.sndarray.make_sound(arr)

    @staticmethod
    def _noise(np, duration: float):
        rate = 22050
        n = max(1, int(rate * duration))
        env = np.linspace(1.0, 0.0, n)
        arr = (np.random.uniform(-1.0, 1.0, n) * env * 32767 * 0.4).astype(np.int16)
        return pygame.sndarray.make_sound(arr)

    def _play(self, sound) -> None:
        if not self.enabled or sound is None:
            return
        try:
            sound.play()
        except Exception:
            pass

    def play_pop(self) -> None:
        self._play(self.pop)

    def play_thud(self) -> None:
        self._play(self.thud)

    def play_buzz(self) -> None:
        self._play(self.buzz)
