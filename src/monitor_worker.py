"""Worker process that runs one monitor's effects and streams cell deltas to the display process.

TTE frame generation and ANSI parsing are pure Python and CPU-bound, so each monitor gets its
own process and core. The display process only blits. This module must not import pygame.
"""

import queue
from dataclasses import dataclass
from typing import Iterator, List, Tuple

from .ansi import Cells, DrawOp, Position, diff_cells, parse_frame
from .effects import EffectManager

Delta = Tuple[str, List[Position], List[DrawOp]]  # (effect name, clears, draws)

PUT_POLL_SECONDS = 0.1


@dataclass(frozen=True)
class WorkerSpec:
    text: str
    enabled_effects: List[str]
    canvas_width: int
    canvas_height: int
    start_index: int


def frame_deltas(effects: EffectManager, canvas_width: int, canvas_height: int) -> Iterator[Delta]:
    """Yield one delta per display tick, switching to the next effect when the current one ends."""
    prev_cells: Cells = {}
    while True:
        frame = effects.get_next_frame()
        if frame is None:
            effects.switch_to_next_effect()
            prev_cells = {}
            frame = effects.get_next_frame()

        if not frame:
            yield effects.get_current_effect_name(), [], []
            continue

        cells = parse_frame(frame, canvas_width, canvas_height)
        clears, draws = diff_cells(prev_cells, cells)
        prev_cells = cells
        yield effects.get_current_effect_name(), clears, draws


def run_worker(spec: WorkerSpec, deltas, stop) -> None:
    """Process entry point. Deltas are incremental, so each one is delivered in order or the worker stops."""
    # Let this process exit on stop even if the display process never reads what is still buffered.
    deltas.cancel_join_thread()
    effects = EffectManager(
        text=spec.text,
        enabled_effects=spec.enabled_effects,
        canvas_width=spec.canvas_width,
        canvas_height=spec.canvas_height,
        start_index=spec.start_index,
    )
    for delta in frame_deltas(effects, spec.canvas_width, spec.canvas_height):
        if not _put_until_stopped(deltas, delta, stop):
            return


def _put_until_stopped(deltas, delta: Delta, stop) -> bool:
    while not stop.is_set():
        try:
            deltas.put(delta, timeout=PUT_POLL_SECONDS)
            return True
        except queue.Full:
            pass
    return False
