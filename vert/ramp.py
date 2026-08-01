"""Ramp geometry: a single vert halfpipe built from flat and circular-arc segments.

Collision is done by looking up the ramp surface height (and slope) at a given
world x-coordinate, so the skater never needs polygon collision math.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List

import pygame

import config


@dataclass
class Segment:
    kind: str  # "flat" or "arc"
    x0: float
    x1: float
    y: float = 0.0    # used when kind == "flat"
    cx: float = 0.0   # used when kind == "arc" (circle center)
    cy: float = 0.0
    r: float = 0.0


class Ramp:
    """Deck -> transition -> flat bottom -> transition -> deck."""

    def __init__(self) -> None:
        r = config.TRANSITION_RADIUS
        dw = config.DECK_WIDTH
        fw = config.FLAT_WIDTH
        deck_y = config.DECK_Y

        left_deck_end = dw
        left_trans_end = dw + r
        flat_end = dw + r + fw
        right_trans_end = dw + 2 * r + fw
        right_deck_end = right_trans_end + dw

        # Both arcs share the formula y = cy + sqrt(r^2 - (x-cx)^2): the
        # circle's lower-right quadrant, which starts flat (horizontal
        # tangent, matching the flat bottom) and ends vertical (matching the
        # coping lip).
        self.segments: List[Segment] = [
            Segment("flat", 0.0, left_deck_end, y=deck_y),
            Segment("arc", left_deck_end, left_trans_end, cx=left_deck_end + r, cy=deck_y, r=r),
            Segment("flat", left_trans_end, flat_end, y=config.FLAT_Y),
            Segment("arc", flat_end, right_trans_end, cx=flat_end, cy=deck_y, r=r),
            Segment("flat", right_trans_end, right_deck_end, y=deck_y),
        ]
        self.total_width = right_deck_end
        self.left_coping_x = left_deck_end
        self.right_coping_x = right_trans_end
        self.flat_bottom_left = left_trans_end
        self.flat_bottom_right = flat_end

    def _segment_at(self, x: float) -> Segment:
        x = max(0.0, min(self.total_width, x))
        for seg in self.segments:
            if seg.x0 <= x <= seg.x1:
                return seg
        return self.segments[-1]

    def segment_kind_at(self, x: float) -> str:
        return self._segment_at(x).kind

    def in_transition(self, x: float) -> bool:
        return self._segment_at(x).kind == "arc"

    def height_at(self, x: float) -> float:
        seg = self._segment_at(x)
        if seg.kind == "flat":
            return seg.y
        dx = max(-seg.r, min(seg.r, x - seg.cx))
        return seg.cy + math.sqrt(max(0.0, seg.r * seg.r - dx * dx))

    def slope_at(self, x: float) -> float:
        seg = self._segment_at(x)
        if seg.kind == "flat":
            return 0.0
        dx = x - seg.cx
        dx = max(-seg.r + 0.001, min(seg.r - 0.001, dx))
        denom = math.sqrt(max(1e-6, seg.r * seg.r - dx * dx))
        return -dx / denom

    # --- drawing ---
    def draw(self, surface: pygame.Surface, camera) -> None:
        step = 6
        xs = list(range(0, int(self.total_width) + step, step))
        pts = [camera.to_screen(x, self.height_at(x)) for x in xs]
        bottom_y = config.LOGICAL_HEIGHT + 120
        poly = pts + [(pts[-1][0], bottom_y), (pts[0][0], bottom_y)]
        pygame.draw.polygon(surface, config.RAMP_FILL, poly)
        pygame.draw.lines(surface, config.BLACK, False, pts, 10)
        pygame.draw.lines(surface, config.RAMP_FILL_2, False, pts, 4)

        for cx in (self.left_coping_x, self.right_coping_x):
            p = camera.to_screen(cx, self.height_at(cx))
            pygame.draw.circle(surface, config.YELLOW, (int(p[0]), int(p[1])), 7)
            pygame.draw.circle(surface, config.BLACK, (int(p[0]), int(p[1])), 7, 2)

        self._draw_fence(surface, camera)
        self._draw_graffiti(surface, camera)

    def _draw_fence(self, surface: pygame.Surface, camera) -> None:
        top_y = config.DECK_Y - 150
        spacing = 26
        for seg in (self.segments[0], self.segments[-1]):
            x = seg.x0
            while x < seg.x1:
                p0 = camera.to_screen(x, seg.y)
                p1 = camera.to_screen(x, top_y)
                pygame.draw.line(surface, config.FENCE_COLOR, p0, p1, 1)
                x += spacing
            y = top_y
            while y < seg.y:
                p0 = camera.to_screen(seg.x0, y)
                p1 = camera.to_screen(seg.x1, y)
                pygame.draw.line(surface, config.FENCE_COLOR, p0, p1, 1)
                y += spacing

    def _draw_graffiti(self, surface: pygame.Surface, camera) -> None:
        spots = [
            (self.segments[1].x0 + 55, config.MAGENTA),
            (self.segments[1].x0 + 150, config.LIME),
            (self.segments[3].x0 + 60, config.ORANGE),
            (self.segments[3].x0 + 155, config.CYAN),
        ]
        for gx, col in spots:
            gy = self.height_at(gx) - 35
            p = camera.to_screen(gx, gy)
            radius = max(4, int(20 * camera.zoom))
            pygame.draw.circle(surface, col, (int(p[0]), int(p[1])), radius)
            pygame.draw.circle(surface, config.BLACK, (int(p[0]), int(p[1])), radius, 3)
