"""VERT - async main loop and state machine (TITLE / PLAY / PAUSED / RESULTS).

Structured to stay pygbag-compatible: no blocking waits anywhere, and the
frame loop yields with `await asyncio.sleep(0)`.
"""
from __future__ import annotations

import asyncio
import json
import os

import pygame

import config
import ui
from fx import Camera, SfxBank, TrailFX, draw_speed_lines
from input_touch import InputManager, build_buttons
from ramp import Ramp
from skater import AIRBORNE, Skater
from tricks import resolve_trick, score_trick

TITLE, PLAY, PAUSED, RESULTS = "TITLE", "PLAY", "PAUSED", "RESULTS"

HERE = os.path.dirname(os.path.abspath(__file__))
HIGH_SCORE_PATH = os.path.join(HERE, config.HIGH_SCORE_FILE)

CLOUD_POSITIONS = [(150, 120), (500, 90), (900, 140), (1300, 100), (1700, 130), (-250, 110)]
HILL_POINTS_LOCAL = [(-400, 80), (-100, 40), (250, 70), (600, 30), (950, 65), (1300, 35), (1650, 75), (1800, 80)]


def load_high_score() -> int:
    try:
        with open(HIGH_SCORE_PATH, "r") as f:
            return int(json.load(f).get("high_score", 0))
    except Exception:
        return 0


def save_high_score(value: int) -> None:
    try:
        with open(HIGH_SCORE_PATH, "w") as f:
            json.dump({"high_score": value}, f)
    except Exception:
        pass


def draw_background(surface: pygame.Surface, camera: Camera) -> None:
    w, h = config.LOGICAL_WIDTH, config.LOGICAL_HEIGHT
    top, bottom = config.SKY_TOP, config.SKY_BOTTOM
    band = 6
    for y in range(0, h, band):
        t = y / h
        col = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        pygame.draw.rect(surface, col, (0, y, w, band))

    par1 = camera.x * 0.25
    for cx, cy in CLOUD_POSITIONS:
        sx = (cx - par1) % (w + 600) - 300
        pygame.draw.ellipse(surface, config.WHITE, (sx, cy, 140, 50))
        pygame.draw.ellipse(surface, config.WHITE, (sx + 50, cy - 20, 110, 50))
        pygame.draw.ellipse(surface, config.BLACK, (sx, cy, 140, 50), 3)

    par2 = camera.x * 0.45
    hill_y_base = 560
    pts = [((hx - par2) % (w + 400) - 200, hill_y_base - hy) for hx, hy in HILL_POINTS_LOCAL]
    poly = pts + [(pts[-1][0], h), (pts[0][0], h)]
    pygame.draw.polygon(surface, config.PURPLE, poly)


class Game:
    def __init__(self) -> None:
        pygame.init()
        try:
            pygame.mixer.pre_init(22050, -16, 1, 512)
        except Exception:
            pass
        self.window = pygame.display.set_mode((1152, 648), pygame.RESIZABLE)
        pygame.display.set_caption("VERT")
        self.logical = pygame.Surface((config.LOGICAL_WIDTH, config.LOGICAL_HEIGHT))
        self.clock = pygame.time.Clock()

        self.ramp = Ramp()
        self.buttons = build_buttons()
        self.input = InputManager(self.buttons)
        self.camera = Camera()
        self.trail = TrailFX()
        self.sfx = SfxBank()
        self.hud = ui.HUD()
        self.trick_text = ui.TrickText()
        self.popups = ui.ScorePopups()

        self.state = TITLE
        self.high_score = load_high_score()
        self.title_t = 0.0

        self.retry_rect = pygame.Rect(0, 0, 220, 80)
        self.retry_rect.center = (config.LOGICAL_WIDTH // 2, 440)
        self.resume_rect = pygame.Rect(0, 0, 240, 80)
        self.resume_rect.center = (config.LOGICAL_WIDTH // 2, 420)

        self.score = 0
        self.combo = 0
        self.timer = config.RUN_DURATION
        self.best_trick_name = ""
        self.best_trick_score = 0
        self.skater = Skater(self.ramp)

        self._new_run()

    def _new_run(self) -> None:
        self.skater = Skater(self.ramp)
        self.score = 0
        self.combo = 0
        self.timer = config.RUN_DURATION
        self.best_trick_name = ""
        self.best_trick_score = 0
        self.trail.clear()
        self.trick_text.hide()

    def _letterbox(self):
        ww, wh = self.window.get_size()
        if ww <= 0 or wh <= 0:
            return 0, 0, 1, 1
        target_aspect = config.LOGICAL_WIDTH / config.LOGICAL_HEIGHT
        if ww / wh > target_aspect:
            sh = wh
            sw = int(sh * target_aspect)
        else:
            sw = ww
            sh = int(sw / target_aspect)
        sw = max(1, sw)
        sh = max(1, sh)
        ox = (ww - sw) // 2
        oy = (wh - sh) // 2
        return ox, oy, sw, sh

    def _event_logical_pos(self, event):
        if event.type == pygame.FINGERDOWN:
            ww, wh = self.window.get_size()
            return self.input.window_to_logical(event.x * ww, event.y * wh)
        return self.input.window_to_logical(*event.pos)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type in (
            pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP,
            pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP,
            pygame.KEYDOWN, pygame.KEYUP,
        ):
            self.input.handle_event(event, self.window.get_size())

        if event.type in (pygame.FINGERDOWN, pygame.MOUSEBUTTONDOWN):
            lx, ly = self._event_logical_pos(event)
            self._handle_tap(lx, ly)
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN):
            self._handle_tap(None, None, key_confirm=True)

    def _handle_tap(self, lx, ly, key_confirm: bool = False) -> None:
        if self.state == TITLE:
            self.state = PLAY
            self._new_run()
        elif self.state == RESULTS:
            if key_confirm or (lx is not None and self.retry_rect.collidepoint(lx, ly)):
                self.state = PLAY
                self._new_run()
        elif self.state == PAUSED:
            if key_confirm or (lx is not None and self.resume_rect.collidepoint(lx, ly)):
                self.state = PLAY

    def update(self, dt: float) -> None:
        ox, oy, sw, sh = self._letterbox()
        self.input.set_letterbox(ox, oy, sw, sh)
        inp = self.input.compute()

        if inp.pause.just_pressed:
            if self.state == PLAY:
                self.state = PAUSED
            elif self.state == PAUSED:
                self.state = PLAY

        if self.state != PLAY:
            self.title_t += dt
            return

        self.timer -= dt
        self.skater.update(dt, inp)

        if self.skater.state == AIRBORNE:
            self.trail.add(self.skater.x, self.skater.y)
        self.trail.update(dt)

        if self.skater.just_launched:
            self.sfx.play_pop()
            self.trail.clear()

        if self.skater.state == AIRBORNE and self.skater.trick is not None:
            t = self.skater.trick
            name, _base = resolve_trick(t.grab_held, t.grab_time, t.flip_count, t.spin_degrees)
            if name:
                self.trick_text.show(name)
            else:
                self.trick_text.hide()

        if self.skater.just_landed:
            self.sfx.play_thud()
            result = self.skater.last_trick_result
            if result:
                name, base, grab_time, spin_deg = result
                if name:
                    pts = score_trick(base, grab_time, spin_deg, self.combo)
                    self.combo += 1
                    self.score += pts
                    self.popups.add(self.skater.x, self.skater.y - 30, pts)
                    if pts > self.best_trick_score:
                        self.best_trick_score = pts
                        self.best_trick_name = name
                    if self.skater.air_time > 1.0 or pts > 1500:
                        self.camera.shake(10.0, 0.25)
            self.trick_text.hide()

        if self.skater.just_bailed:
            self.sfx.play_buzz()
            self.combo = 0
            self.camera.shake(16.0, 0.35)
            self.trick_text.hide()

        self.popups.update(dt)
        self.trick_text.update(dt)

        target_zoom = 1.0
        if self.skater.y < config.DECK_Y:
            height_above = config.DECK_Y - self.skater.y
            target_zoom = max(0.62, 1.0 - height_above / 900.0)
        self.camera.update(self.skater.x, self.skater.y - 40, target_zoom, dt)

        if self.timer <= 0:
            self.timer = 0.0
            self.state = RESULTS
            if self.score > self.high_score:
                self.high_score = self.score
                save_high_score(self.high_score)

    def draw(self) -> None:
        surf = self.logical
        draw_background(surf, self.camera)
        self.ramp.draw(surf, self.camera)
        self.trail.draw(surf, self.camera, config.YELLOW)
        draw_speed_lines(surf, self.camera, self.skater)
        self.skater.draw(surf, self.camera, self.title_t)
        self.popups.draw(surf, self.camera)

        if self.state == TITLE:
            ui.draw_title_screen(surf, self.title_t)
        else:
            self.hud.draw(surf, self.score, self.combo, self.timer, self.high_score)
            ui.draw_buttons(surf, self.buttons, self.input)
            self.trick_text.draw(surf)
            if self.state == PAUSED:
                ui.draw_pause_overlay(surf, self.resume_rect)
            if self.state == RESULTS:
                ui.draw_results_screen(
                    surf, self.score, self.best_trick_name, self.best_trick_score,
                    self.high_score, self.retry_rect,
                )

        ox, oy, sw, sh = self._letterbox()
        self.window.fill((0, 0, 0))
        scaled = pygame.transform.smoothscale(surf, (sw, sh))
        self.window.blit(scaled, (ox, oy))
        pygame.display.flip()

    async def run(self) -> None:
        running = True
        while running:
            dt = self.clock.tick(config.FPS) / 1000.0
            dt = min(dt, 0.05)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                else:
                    self.handle_event(event)
            self.update(dt)
            self.draw()
            await asyncio.sleep(0)
        pygame.quit()


async def main() -> None:
    game = Game()
    await game.run()


if __name__ == "__main__":
    asyncio.run(main())
