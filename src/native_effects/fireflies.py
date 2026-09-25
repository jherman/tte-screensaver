"""Fireflies: a sparse swarm blinks through the dark, then fireflies fly in and settle on the text."""

import math
import random
from typing import Dict, Iterator, List

from ..ansi import Cells, Position
from .base import NativeEffect, layout_text, mix, scale, text_colors

GATHER_AT, LAUNCH_SPAN, FORCE_AFTER, HOLD = 7.0, 8.0, 21.0, 5.0  # seconds
AMBIENT_PER_CELL = 1 / 90
WANDER = 1.8  # how quickly a wandering firefly changes heading, in radians per sqrt(second)
SEEK_SPEED = (16.0, 28.0)  # cells per second
DARK, GLOW, WHITE = (55, 75, 20), (230, 255, 130), (255, 255, 255)
TEXT_STOPS = [(255, 215, 90), (200, 240, 90), (120, 230, 120)]
BREATH_LEVELS = 5  # breathing is quantized so the renderer caches a handful of colors per cell


def glow_glyph(brightness: float) -> str:
    return "●" if brightness > 0.65 else "•" if brightness > 0.3 else "·"


class Fireflies(NativeEffect):
    def frames(self, width: int, height: int) -> Iterator[Cells]:
        rng = random.Random()
        text = layout_text(self.text, width, height)
        text_color = text_colors(text, TEXT_STOPS)
        landed: Dict[Position, float] = {}
        breath_phase = {pos: rng.uniform(0, math.tau) for pos in text}

        def edge_point():
            side = rng.randrange(4)
            if side < 2:
                return rng.uniform(0, width), (-1.0 if side == 0 else float(height))
            return (-1.0 if side == 2 else float(width)), rng.uniform(0, height)

        ambient: List[list] = [
            [rng.uniform(0, width), rng.uniform(0, height), rng.uniform(0, math.tau), rng.uniform(2, 5),
             rng.uniform(0, 4), rng.uniform(1.5, 3.5)]
            for _ in range(max(15, int(width * height * AMBIENT_PER_CELL)))
        ]
        seekers: List[list] = []  # [x, y, target, launch_at, speed, wobble]
        for pos in text:
            x, y = edge_point()
            seekers.append([x, y, pos, GATHER_AT + rng.uniform(0, LAUNCH_SPAN), rng.uniform(*SEEK_SPEED), rng.uniform(0, math.tau)])
        done_at = None if text else 15.0
        previous = None

        for t in self.seconds():
            if done_at is not None and t >= done_at + HOLD:
                return
            dt = 0.0 if previous is None else min(t - previous, 0.1)
            previous = t
            cells: Cells = {}

            for fly in ambient:
                fly[2] += rng.gauss(0, WANDER) * math.sqrt(dt)
                fly[0] = (fly[0] + math.cos(fly[2]) * fly[3] * dt) % width
                fly[1] = (fly[1] + math.sin(fly[2]) * fly[3] * dt / 2) % height
                brightness = max(0.0, math.sin(math.tau * ((t + fly[4]) % fly[5]) / fly[5])) ** 2
                if brightness > 0.08:
                    cells[int(fly[1]), int(fly[0])] = (glow_glyph(brightness), mix(DARK, GLOW, brightness))

            flying = []
            for seeker in seekers:
                x, y, (row, col), launch_at, speed, wobble = seeker
                if t < launch_at:
                    flying.append(seeker)
                    continue
                d_col, d_row = col + 0.5 - x, (row + 0.5 - y) * 2
                distance = math.hypot(d_col, d_row)
                step = speed * dt
                if distance <= max(step, 0.7) or t >= FORCE_AFTER:
                    landed[row, col] = t
                    continue
                heading = math.atan2(d_row, d_col) + math.sin(t * 5 + wobble) * 0.5
                seeker[0] = x + math.cos(heading) * step
                seeker[1] = y + math.sin(heading) * step / 2
                if 0 <= seeker[1] < height and 0 <= seeker[0] < width:
                    cells[int(seeker[1]), int(seeker[0])] = ("•", GLOW)
                flying.append(seeker)
            seekers = flying
            if done_at is None and len(landed) == len(text):
                done_at = t

            for pos, since in landed.items():
                breath = round((0.82 + 0.18 * math.sin(t * 1.7 + breath_phase[pos])) * BREATH_LEVELS) / BREATH_LEVELS
                color = mix(WHITE, scale(text_color[pos], breath), (t - since) / 0.5)
                cells[pos] = (text[pos], color)
            yield cells
