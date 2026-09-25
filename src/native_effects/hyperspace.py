"""Hyperspace: a starfield jumps to warp, drops back out, and the text is waiting at the center."""

import math
import random
from typing import Iterator

from ..ansi import Cells
from .base import NativeEffect, ease_in_out, layout_text, mix, text_colors

# Phase lengths in seconds.
CRUISE, ACCELERATE, WARP, DECELERATE, REVEAL, HOLD = 2.5, 3.0, 3.5, 2.5, 1.5, 5.0
# Star speed toward the viewer, in depth units per second (depth runs from 1 far away to 0).
CRUISE_SPEED, WARP_SPEED, DRIFT_SPEED = 0.12, 2.4, 0.04
# How far behind each star its streak reaches, in seconds of travel.
STREAK_SECONDS = 0.07

FAR_STAR, NEAR_STAR, WARP_TINT = (60, 80, 130), (225, 235, 255), (150, 200, 255)
TEXT_STOPS = [(120, 225, 255), (180, 150, 255), (255, 165, 220)]
WHITE = (255, 255, 255)
STAR_GLYPHS = ".·•●"


def speed_at(t: float) -> float:
    if t < CRUISE:
        return CRUISE_SPEED
    t -= CRUISE
    if t < ACCELERATE:
        return CRUISE_SPEED + (WARP_SPEED - CRUISE_SPEED) * ease_in_out(t / ACCELERATE) ** 2
    t -= ACCELERATE
    if t < WARP:
        return WARP_SPEED
    t -= WARP
    if t < DECELERATE:
        return DRIFT_SPEED + (WARP_SPEED - DRIFT_SPEED) * (1 - ease_in_out(t / DECELERATE))
    return DRIFT_SPEED


def streak_glyph(d_col: float, d_row: float) -> str:
    d_row *= 2  # a cell is about twice as tall as it is wide
    if abs(d_col) > 2 * abs(d_row):
        return "─"
    if abs(d_row) > 2 * abs(d_col):
        return "│"
    return "╲" if d_col * d_row > 0 else "╱"


class Hyperspace(NativeEffect):
    def frames(self, width: int, height: int) -> Iterator[Cells]:
        rng = random.Random()
        text = layout_text(self.text, width, height)
        colors = text_colors(text, TEXT_STOPS)
        center_col, center_row = (width - 1) / 2, (height - 1) / 2
        # Project with square pixels: a cell is about twice as tall as wide.
        focal = max(width, height * 2) / 2
        reveal_at = CRUISE + ACCELERATE + WARP + DECELERATE
        max_reach = max(1.0, max((math.hypot(col - center_col, (row - center_row) * 2) for row, col in text), default=1.0))

        def new_star(depth: float) -> list:
            return [rng.uniform(-1, 1), rng.uniform(-1, 1), depth]

        def project(x: float, y: float, depth: float):
            return center_col + x / depth * focal, center_row + y / depth * focal / 2

        stars = [new_star(rng.uniform(0.05, 1.0)) for _ in range(max(40, width * height // 14))]
        previous = None
        for t in self.seconds():
            if t >= reveal_at + REVEAL + HOLD:
                return
            dt = 0.0 if previous is None else min(t - previous, 0.1)
            previous = t
            speed = speed_at(t)
            warp = min(1.0, max(0.0, (speed - CRUISE_SPEED) / (WARP_SPEED - CRUISE_SPEED)))
            cells: Cells = {}

            for star in stars:
                x, y, depth = star
                depth -= speed * dt
                col, row = project(x, y, depth) if depth > 0.02 else (-1, -1)
                if not (0 <= row < height and 0 <= col < width):
                    star[:] = new_star(1.0)
                    continue
                star[2] = depth
                nearness = 1.0 - depth
                head = mix(mix(FAR_STAR, NEAR_STAR, nearness), WARP_TINT, warp * 0.5)
                tail_depth = min(1.0, depth + speed * STREAK_SECONDS)
                tail_col, tail_row = project(x, y, tail_depth)
                length = max(abs(col - tail_col), abs(row - tail_row))
                if length < 1.5:
                    glyph = STAR_GLYPHS[min(len(STAR_GLYPHS) - 1, int(nearness * len(STAR_GLYPHS)))]
                    cells[int(row), int(col)] = (glyph, head)
                    continue
                glyph = streak_glyph(col - tail_col, row - tail_row)
                steps = int(min(length, max(width, height)))
                for step in range(steps + 1):
                    f = step / steps
                    cell = (int(tail_row + (row - tail_row) * f), int(tail_col + (col - tail_col) * f))
                    if 0 <= cell[0] < height and 0 <= cell[1] < width:
                        cells[cell] = (glyph, mix(FAR_STAR, head, 0.25 + 0.75 * f))

            reveal = (t - reveal_at) / REVEAL
            if reveal > 0:
                for (row, col), char in text.items():
                    # The text lights up from the center outward, flashing white before settling.
                    local = reveal * 1.6 - math.hypot(col - center_col, (row - center_row) * 2) / max_reach * 0.6
                    if local > 0:
                        cells[row, col] = (char, mix(WHITE, colors[row, col], local))
            yield cells
