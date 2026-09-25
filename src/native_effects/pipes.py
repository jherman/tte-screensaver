"""Pipes: a nod to the Windows 3D Pipes screensaver. Pipes snake across the screen, then liquid floods the text."""

import random
from collections import deque
from typing import Dict, Iterator, List, Tuple

from ..ansi import Cells, Color, Position
from .base import NativeEffect, layout_text, mix, scale, text_colors

GROW, FLOW, HOLD = 13.0, 3.5, 4.5  # phase lengths in seconds
CELLS_PER_SECOND = 24
TURN_CHANCE = 0.2
ACTIVE_PIPES = 5
MAX_COVERAGE = 0.45  # stop starting new pipes once this share of the screen is piped
PIPE_COLORS = [(235, 70, 70), (70, 205, 95), (70, 130, 240), (240, 200, 60), (60, 210, 220), (215, 90, 220), (245, 140, 50)]
LIQUID, WHITE = (150, 230, 255), (255, 255, 255)
TEXT_STOPS = [(90, 220, 255), (70, 150, 255), (150, 110, 255)]
DIM_TO = 0.3  # pipe brightness once the liquid starts to flow

UP, RIGHT, DOWN, LEFT = (-1, 0), (0, 1), (1, 0), (0, -1)
OPPOSITE = {UP: DOWN, DOWN: UP, LEFT: RIGHT, RIGHT: LEFT}
# The glyph for a cell whose pipe joins these two sides.
JOINT = {
    frozenset((UP, DOWN)): "┃", frozenset((LEFT, RIGHT)): "━",
    frozenset((DOWN, RIGHT)): "┏", frozenset((DOWN, LEFT)): "┓",
    frozenset((UP, RIGHT)): "┗", frozenset((UP, LEFT)): "┛",
}


def flood_order(cells: Dict[Position, str], rng: random.Random) -> List[Position]:
    """Text cells in the order liquid would reach them, spreading through touching cells."""
    order, seen = [], set()
    starts = list(cells)
    rng.shuffle(starts)
    for start in starts:
        if start in seen:
            continue
        seen.add(start)
        queue = deque([start])
        while queue:
            row, col = queue.popleft()
            order.append((row, col))
            for d_row, d_col in (UP, RIGHT, DOWN, LEFT):
                neighbor = (row + d_row, col + d_col)
                if neighbor in cells and neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
    return order


class Pipes(NativeEffect):
    def frames(self, width: int, height: int) -> Iterator[Cells]:
        rng = random.Random()
        text = layout_text(self.text, width, height)
        text_color = text_colors(text, TEXT_STOPS)
        flow = flood_order(text, rng)
        piped: Dict[Position, Tuple[str, Color]] = {}
        pipes: List[dict] = []
        steps_done = 0

        def start_pipe() -> None:
            free = [(rng.randrange(height), rng.randrange(width)) for _ in range(20)]
            free = [pos for pos in free if pos not in piped]
            if free:
                pos = free[0]
                pipes.append({"pos": pos, "dir": rng.choice((UP, RIGHT, DOWN, LEFT)), "from": None,
                              "color": rng.choice(PIPE_COLORS)})
                piped[pos] = ("●", pipes[-1]["color"])

        def advance(pipe: dict) -> bool:
            row, col = pipe["pos"]
            turn = rng.random() < TURN_CHANCE
            sideways = [d for d in (UP, RIGHT, DOWN, LEFT) if d not in (pipe["dir"], OPPOSITE[pipe["dir"]])]
            rng.shuffle(sideways)
            for direction in (sideways + [pipe["dir"]]) if turn else ([pipe["dir"]] + sideways):
                nxt = (row + direction[0], col + direction[1])
                if 0 <= nxt[0] < height and 0 <= nxt[1] < width and nxt not in piped:
                    sides = frozenset((pipe["from"] or OPPOSITE[direction], direction))
                    color = pipe["color"] if direction in (LEFT, RIGHT) else scale(pipe["color"], 0.78)
                    piped[pipe["pos"]] = (JOINT.get(sides, "●"), color)
                    piped[nxt] = ("●", mix(pipe["color"], WHITE, 0.35))
                    pipe.update(pos=nxt, dir=direction, **{"from": OPPOSITE[direction]})
                    return True
            piped[pipe["pos"]] = ("●", pipe["color"])  # boxed in: end with a ball joint
            return False

        for t in self.seconds():
            if t >= GROW + FLOW + HOLD:
                return
            if t < GROW:
                while steps_done < int(t * CELLS_PER_SECOND):
                    steps_done += 1
                    pipes[:] = [pipe for pipe in pipes if advance(pipe)]
                    while len(pipes) < ACTIVE_PIPES and len(piped) < MAX_COVERAGE * width * height:
                        before = len(pipes)
                        start_pipe()
                        if len(pipes) == before:
                            break

            dim = 1.0 if t < GROW else max(DIM_TO, 1.0 - (t - GROW) / 1.5 * (1.0 - DIM_TO))
            cells: Cells = {pos: (glyph, scale(color, dim)) for pos, (glyph, color) in piped.items()}
            if t >= GROW:
                reached = int(len(flow) * min(1.0, (t - GROW) / FLOW))
                for index in range(reached):
                    pos = flow[index]
                    wet_for = (t - GROW) - index / max(1, len(flow)) * FLOW
                    cells[pos] = (text[pos], mix(LIQUID, text_color[pos], wet_for / 0.6))
            yield cells
