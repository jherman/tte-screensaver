"""Snowfall: snow drifts down in three depths, piles up along the bottom, and freezes into the text."""

import math
import random
from typing import Iterator

from ..ansi import Cells
from .base import NativeEffect, layout_text, mix, text_colors

# Per depth (far, mid, near): glyph, color, fall speed in rows per second, sway in columns.
DEPTHS = [
    (".", (80, 95, 125), 2.5, 0.4),
    ("•", (165, 180, 210), 4.5, 0.9),
    ("*", (240, 246, 255), 7.0, 1.6),
]
FLAKES_PER_CELL = 1 / 18
AIM_AFTER, FORCE_AFTER = 12.0, 22.0  # seconds: flakes start aiming at bare letters, then letters freeze anyway
FORCE_FRACTION = 0.04  # of the remaining bare letters frozen per frame once forced
COOL_SECONDS, SPARKLE_SECONDS, HOLD_SECONDS = 1.5, 2.5, 3.5
BANK_ROWS = 3
BANK_GLYPHS = "▁▂▃▄▅▆▇█"
BANK_COLOR = (190, 205, 235)
ICE_STOPS = [(215, 245, 255), (130, 195, 255), (175, 155, 255)]
WHITE = (255, 255, 255)


class Snowfall(NativeEffect):
    def frames(self, width: int, height: int) -> Iterator[Cells]:
        rng = random.Random()
        text = layout_text(self.text, width, height)
        ice = text_colors(text, ICE_STOPS)
        frozen_at: dict = {}
        bank = [0] * width  # eighths of a cell of settled snow per column
        bank_cap = BANK_ROWS * 8

        def new_flake(top: bool, aim=None) -> list:
            depth = 2 if aim else rng.choices((0, 1, 2), weights=(5, 3, 2))[0]
            col = aim[1] + 0.5 if aim else rng.uniform(0, width)
            row = (aim[0] - rng.uniform(3, 8)) if aim else (rng.uniform(-3, 0) if top else rng.uniform(0, height))
            sway = 0.0 if aim else DEPTHS[depth][3]
            return [col, row, depth, sway, rng.uniform(0, math.tau), rng.uniform(0.6, 1.4)]

        flakes = [new_flake(top=False) for _ in range(max(20, int(width * height * FLAKES_PER_CELL)))]
        done_at = None if text else 20.0
        previous = None
        for t in self.seconds():
            if done_at is not None and t >= done_at + SPARKLE_SECONDS + HOLD_SECONDS:
                return
            dt = 0.0 if previous is None else min(t - previous, 0.1)
            previous = t
            bare = [pos for pos in text if pos not in frozen_at]
            cells: Cells = {}

            for flake in flakes:
                col0, row, depth, sway, phase, pace = flake
                glyph, color, fall, _ = DEPTHS[depth]
                row += fall * pace * dt
                flake[1] = row
                col = col0 + math.sin(t * 1.3 * pace + phase) * sway
                cell = (int(row), int(col) % width)
                if depth > 0 and cell in text and cell not in frozen_at:
                    frozen_at[cell] = t
                    flake[:] = self._respawn(new_flake, bare, t, rng)
                    continue
                if row >= height - bank[cell[1]] / 8:
                    bank[cell[1]] = min(bank_cap, bank[cell[1]] + depth + 1)
                    flake[:] = self._respawn(new_flake, bare, t, rng)
                    continue
                if row >= 0:
                    cells[cell] = (glyph, color)

            if t >= FORCE_AFTER and bare:
                for pos in rng.sample(bare, max(1, int(len(bare) * FORCE_FRACTION))):
                    frozen_at[pos] = t
            if done_at is None and len(frozen_at) == len(text):
                done_at = t

            for col, level in enumerate(bank):
                full, partial = divmod(level, 8)
                for depth_row in range(full):
                    cells[height - 1 - depth_row, col] = ("█", BANK_COLOR)
                if partial and full < height:
                    cells[height - 1 - full, col] = (BANK_GLYPHS[partial - 1], BANK_COLOR)

            sparkling = done_at is not None and t - done_at < SPARKLE_SECONDS
            for pos, since in frozen_at.items():
                color = mix(WHITE, ice[pos], (t - since) / COOL_SECONDS)
                if sparkling and rng.random() < 0.03:
                    color = WHITE
                cells[pos] = (text[pos], color)
            yield cells

    @staticmethod
    def _respawn(new_flake, bare, t, rng) -> list:
        if t >= AIM_AFTER and bare and rng.random() < 0.5:
            return new_flake(top=True, aim=rng.choice(bare))
        return new_flake(top=True)
