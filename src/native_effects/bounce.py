"""Bounce: the DVD-logo screensaver, starring the text. And yes, it hits the corner."""

import colorsys
import math
import random
from typing import Iterator

from ..ansi import Cells, Color
from .base import NativeEffect, ease_in_out, layout_text, mix, text_colors

SPEED_COLS, SPEED_ROWS = 11.0, 5.5  # cells per second; equal on screen, since a cell is twice as tall as wide
CORNER_AT, BOUNCE_UNTIL, GLIDE, HOLD = 12.0, 19.0, 2.0, 4.0  # seconds
CELEBRATE = 2.5  # seconds of sparks after the corner hit
SPARKS = 80
LOGO_COLORS = [(255, 70, 70), (70, 200, 255), (255, 215, 60), (120, 255, 120), (255, 110, 230), (170, 130, 255), (255, 150, 60)]
TEXT_STOPS = [(255, 110, 230), (170, 130, 255), (70, 200, 255)]
SPARK_GLYPHS = "*•·"


def reflect(u: float, span: float) -> float:
    """Position after bouncing between 0 and span, given the unbounced distance u."""
    if span <= 0:
        return 0.0
    m = u % (2 * span)
    return m if m <= span else 2 * span - m


def rainbow(hue: float) -> Color:
    r, g, b = colorsys.hsv_to_rgb(hue % 1.0, 0.75, 1.0)
    return (round(r * 255), round(g * 255), round(b * 255))


class Bounce(NativeEffect):
    def frames(self, width: int, height: int) -> Iterator[Cells]:
        rng = random.Random()
        centered = layout_text(self.text, width, height)
        if not centered:
            return
        final_color = text_colors(centered, TEXT_STOPS)
        top = min(row for row, _ in centered)
        left = min(col for _, col in centered)
        logo = {(row - top, col - left): (char, (row, col)) for (row, col), char in centered.items()}
        span_cols = width - 1 - max(col for _, col in logo)
        span_rows = height - 1 - max(row for row, _ in logo)
        # Solve the path backwards from a corner: u is the unbounced distance, which is 0 or span at CORNER_AT.
        end_col = rng.choice((0.0, float(max(0, span_cols))))
        end_row = rng.choice((0.0, float(max(0, span_rows))))

        def unbounced(t: float):
            return end_col + SPEED_COLS * (t - CORNER_AT), end_row + SPEED_ROWS * (t - CORNER_AT)

        def wall_hits(u: float, span: int) -> int:
            return math.floor(u / span) if span > 0 else 0

        corner = (round(reflect(end_row, span_rows)) + (0 if end_row == 0 else max(row for row, _ in logo)),
                  round(reflect(end_col, span_cols)) + (0 if end_col == 0 else max(col for _, col in logo)))
        sparks = [(rng.uniform(0, math.tau), rng.uniform(8, 26), rng.random()) for _ in range(SPARKS)]

        for t in self.seconds():
            if t >= BOUNCE_UNTIL + GLIDE + HOLD:
                return
            u_col, u_row = unbounced(min(t, BOUNCE_UNTIL))
            col, row = reflect(u_col, span_cols), reflect(u_row, span_rows)
            color = LOGO_COLORS[(wall_hits(u_col, span_cols) + wall_hits(u_row, span_rows)) % len(LOGO_COLORS)]
            since_corner = t - CORNER_AT
            if 0 <= since_corner < 1.0:
                color = rainbow(since_corner * 3)
            settle = 0.0
            if t > BOUNCE_UNTIL:
                settle = ease_in_out((t - BOUNCE_UNTIL) / GLIDE)
                row += (top - row) * settle
                col += (left - col) * settle
            origin = (round(row), round(col))

            cells: Cells = {}
            if 0 <= since_corner < CELEBRATE:
                life = since_corner / CELEBRATE
                for angle, speed, hue in sparks:
                    distance = speed * since_corner
                    pos = (int(corner[0] + math.sin(angle) * distance / 2), int(corner[1] + math.cos(angle) * distance))
                    if 0 <= pos[0] < height and 0 <= pos[1] < width:
                        glyph = SPARK_GLYPHS[min(len(SPARK_GLYPHS) - 1, int(life * len(SPARK_GLYPHS)))]
                        cells[pos] = (glyph, mix(rainbow(hue), (0, 0, 0), life))
            for (d_row, d_col), (char, home) in logo.items():
                pos = (origin[0] + d_row, origin[1] + d_col)
                if 0 <= pos[0] < height and 0 <= pos[1] < width:
                    cells[pos] = (char, mix(color, final_color[home], settle))
            yield cells
