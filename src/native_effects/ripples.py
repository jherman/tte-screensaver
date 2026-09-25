"""Ripples: raindrops on a still pond. The rings wash the text into view, then make it glint as they pass."""

import math
import random
from typing import Dict, Iterator

from ..ansi import Cells, Position
from .base import NativeEffect, layout_text, mix, text_colors

DROP_EVERY = 0.22  # average seconds between drops
RING_SPEED = 13.0  # cells per second, measured in square units (a row counts as two columns)
RING_REACH = (18.0, 40.0)  # a ripple's radius when it fades out, in square units
RING_GAP = 3.0  # distance between a ripple's leading and trailing ring
REVEAL_AFTER, AIM_AFTER, FORCE_AFTER = 4.0, 12.0, 21.0  # seconds
FORCE_FRACTION = 0.04
HOLD_SECONDS = 5.0
DEEP, FOAM, WHITE = (35, 90, 150), (185, 240, 255), (255, 255, 255)
TEXT_STOPS = [(110, 235, 225), (80, 160, 245), (140, 120, 250)]


def ring_glyph(brightness: float) -> str:
    return "○" if brightness > 0.6 else "◦" if brightness > 0.3 else "·"


class Ripples(NativeEffect):
    def frames(self, width: int, height: int) -> Iterator[Cells]:
        rng = random.Random()
        text = layout_text(self.text, width, height)
        text_color = text_colors(text, TEXT_STOPS)
        revealed: Dict[Position, float] = {}
        ripples = []  # (row, col, born, reach)
        next_drop = 0.0
        done_at = None if text else 20.0

        for t in self.seconds():
            if done_at is not None and t >= done_at + HOLD_SECONDS:
                return
            while t >= next_drop:
                bare = [pos for pos in text if pos not in revealed]
                if t >= AIM_AFTER and bare and rng.random() < 0.6:
                    row, col = rng.choice(bare)
                else:
                    row, col = rng.uniform(0, height), rng.uniform(0, width)
                ripples.append((row, col, next_drop, rng.uniform(*RING_REACH)))
                next_drop += rng.expovariate(1 / DROP_EVERY) * (2.0 if done_at is not None else 1.0)
            ripples = [ripple for ripple in ripples if (t - ripple[2]) * RING_SPEED < ripple[3] + RING_GAP]

            water: Dict[Position, float] = {}
            for row, col, born, reach in ripples:
                radius = (t - born) * RING_SPEED
                fade = max(0.0, 1.0 - radius / reach)
                if radius < 1.0:
                    water[int(row), int(col)] = 1.0
                for ring, strength in ((radius, 1.0), (radius - RING_GAP, 0.55)):
                    if ring <= 0.5:
                        continue
                    points = max(12, int(ring * 5))
                    for i in range(points):
                        angle = math.tau * i / points
                        pos = (int(row + math.sin(angle) * ring / 2), int(col + math.cos(angle) * ring))
                        if 0 <= pos[0] < height and 0 <= pos[1] < width:
                            water[pos] = max(water.get(pos, 0.0), fade * strength)

            if t >= REVEAL_AFTER:
                for pos, brightness in water.items():
                    if brightness > 0.25 and pos in text and pos not in revealed:
                        revealed[pos] = t
            if t >= FORCE_AFTER:
                bare = [pos for pos in text if pos not in revealed]
                for pos in rng.sample(bare, min(len(bare), max(1, int(len(bare) * FORCE_FRACTION)))):
                    revealed[pos] = t
            if done_at is None and len(revealed) == len(text):
                done_at = t

            cells: Cells = {}
            for pos, brightness in water.items():
                if brightness > 0.05:
                    cells[pos] = ("●" if brightness >= 1.0 else ring_glyph(brightness), mix(DEEP, FOAM, 0.25 + 0.75 * brightness))
            for pos, since in revealed.items():
                color = mix(WHITE, text_color[pos], (t - since) / 0.8)
                cells[pos] = (text[pos], mix(color, WHITE, water.get(pos, 0.0) * 0.6))
            yield cells
