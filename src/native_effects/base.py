"""Shared pieces for effects written for this screensaver rather than taken from TTE.

A native effect yields Cells ({(row, col): (char, color)}) straight to the worker, so there is no
ANSI text to build or parse. Motion is timed with a wall clock, so effects look the same at any
display frame rate.
"""

import math
import time
from types import SimpleNamespace
from typing import Callable, Dict, Iterator, Sequence

from ..ansi import Cells, Color, Position, parse_frame


class NativeEffect:
    def __init__(self, text: str):
        self.text = text
        self.clock: Callable[[], float] = time.monotonic
        # EffectManager configures every effect through TTE's terminal_config; accept the same fields.
        self.terminal_config = SimpleNamespace(
            canvas_width=80, canvas_height=24, anchor_text="c", frame_rate=0, ignore_terminal_dimensions=True,
        )

    def __iter__(self) -> Iterator[Cells]:
        return self.frames(self.terminal_config.canvas_width, self.terminal_config.canvas_height)

    def frames(self, width: int, height: int) -> Iterator[Cells]:
        raise NotImplementedError

    def seconds(self) -> Iterator[float]:
        """Yield the seconds since the first frame, once per frame."""
        start = self.clock()
        while True:
            yield self.clock() - start


def layout_text(text: str, width: int, height: int) -> Dict[Position, str]:
    """Center the text's visible characters on the canvas, ignoring any ANSI color codes in it."""
    glyphs = parse_frame(text, 1 << 16, 1 << 16)
    if not glyphs:
        return {}
    rows = [row for row, _ in glyphs]
    cols = [col for _, col in glyphs]
    top = (height - (max(rows) - min(rows) + 1)) // 2 - min(rows)
    left = (width - (max(cols) - min(cols) + 1)) // 2 - min(cols)
    return {
        (row + top, col + left): char
        for (row, col), (char, _) in glyphs.items()
        if 0 <= row + top < height and 0 <= col + left < width
    }


def mix(a: Color, b: Color, t: float) -> Color:
    t = min(max(t, 0.0), 1.0)
    return (round(a[0] + (b[0] - a[0]) * t), round(a[1] + (b[1] - a[1]) * t), round(a[2] + (b[2] - a[2]) * t))


def gradient(stops: Sequence[Color], t: float) -> Color:
    """Color at position t in [0, 1] along evenly spaced color stops."""
    t = min(max(t, 0.0), 1.0) * (len(stops) - 1)
    index = min(int(t), len(stops) - 2)
    return mix(stops[index], stops[index + 1], t - index)


def scale(color: Color, brightness: float) -> Color:
    return mix((0, 0, 0), color, brightness)


def text_colors(text_cells: Dict[Position, str], stops: Sequence[Color]) -> Dict[Position, Color]:
    """A diagonal gradient across the text's bounding box."""
    if not text_cells:
        return {}
    rows = [row for row, _ in text_cells]
    cols = [col for _, col in text_cells]
    top, left = min(rows), min(cols)
    span = max(1, (max(rows) - top) * 2 + (max(cols) - left))
    return {(row, col): gradient(stops, ((row - top) * 2 + (col - left)) / span) for row, col in text_cells}


def ease_in_out(t: float) -> float:
    t = min(max(t, 0.0), 1.0)
    return 0.5 - 0.5 * math.cos(math.pi * t)
