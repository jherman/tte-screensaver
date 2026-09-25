"""Life: Conway's Game of Life swarms, the text comes alive in the middle of it, and winter clears the rest."""

import random
from collections import Counter
from typing import Iterator

from ..ansi import Cells
from .base import NativeEffect, gradient, layout_text, mix, text_colors

GENERATIONS_PER_SECOND = 14
SEED_DENSITY = 0.3
FREE, SWARM, FADE, HOLD = 8.0, 8.0, 5.0, 4.0  # phase lengths in seconds
GLIDER_EVERY = 1.2  # seconds between gliders dropped in while the colony runs free
AGE_STOPS = [(225, 255, 240), (90, 235, 185), (45, 160, 210), (75, 70, 170)]
OLD_AGE = 12
TEXT_STOPS = [(255, 205, 95), (255, 125, 150), (175, 115, 255)]
WHITE = (255, 255, 255)
NEIGHBORS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
GLIDERS = [
    [(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)],
    [(0, 1), (1, 0), (2, 0), (2, 1), (2, 2)],
    [(0, 0), (0, 1), (0, 2), (1, 0), (2, 1)],
    [(0, 0), (0, 1), (0, 2), (1, 2), (2, 1)],
]


class Life(NativeEffect):
    def frames(self, width: int, height: int) -> Iterator[Cells]:
        rng = random.Random()
        text = layout_text(self.text, width, height)
        text_color = text_colors(text, TEXT_STOPS)
        immortal = set(text)
        age = {
            (row, col): 0 for row in range(height) for col in range(width)
            if rng.random() < SEED_DENSITY and (row, col) not in immortal
        }
        generation = 0
        next_glider = GLIDER_EVERY
        cells: Cells = {}

        for t in self.seconds():
            if t >= FREE + SWARM + FADE + HOLD:
                return
            target = int(t * GENERATIONS_PER_SECOND)
            if generation >= target and cells:
                yield cells
                continue
            while generation < target:
                generation += 1
                if t < FREE and t >= next_glider:
                    next_glider += GLIDER_EVERY
                    top, left = rng.randrange(height), rng.randrange(width)
                    for row, col in rng.choice(GLIDERS):
                        age[(top + row) % height, (left + col) % width] = 0
                winter = min(1.0, max(0.0, (t - FREE - SWARM) / FADE))
                age = self._step(age, immortal if t >= FREE else set(), width, height, winter, rng)

            cells = {pos: ("●" if years < 3 else "•", gradient(AGE_STOPS, years / OLD_AGE)) for pos, years in age.items()}
            if t >= FREE:
                glow = (t - FREE) / 1.5
                for pos, char in text.items():
                    cells[pos] = (char, mix(WHITE, text_color[pos], glow))
            yield cells

    @staticmethod
    def _step(age: dict, immortal: set, width: int, height: int, winter: float, rng: random.Random) -> dict:
        counts: Counter = Counter()
        for row, col in (*age, *immortal):
            for d_row, d_col in NEIGHBORS:
                counts[(row + d_row) % height, (col + d_col) % width] += 1
        survivors = {}
        for pos, n in counts.items():
            if pos in immortal:
                continue
            if pos in age:
                if n in (2, 3) and rng.random() >= winter:
                    survivors[pos] = age[pos] + 1
            elif n == 3 and rng.random() >= winter:
                survivors[pos] = 0
        return survivors
