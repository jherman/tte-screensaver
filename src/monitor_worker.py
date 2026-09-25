"""Worker process that runs one monitor's effects and streams cell deltas to the display process.

TTE frame generation and ANSI parsing are pure Python and CPU-bound, so each monitor gets its
own process and core. The display process only blits. This module must not import pygame.
"""

import queue
import threading
from dataclasses import dataclass
from typing import Callable, Iterator, List, Optional, Tuple

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
    seed: Optional[int] = None


def frame_deltas(
    effects: EffectManager,
    canvas_width: int,
    canvas_height: int,
    before_switch: Callable[[], None] = lambda: None,
) -> Iterator[Delta]:
    """Yield one delta per display tick, switching to the next effect when the current one ends."""
    prev_cells: Cells = {}
    while True:
        frame = effects.get_next_frame()
        if frame is None:
            before_switch()
            # prev_cells stays: the old effect's last frame is still on screen and must be diffed away.
            effects.switch_to_next_effect()
            frame = effects.get_next_frame()

        if frame is None:
            yield effects.get_current_effect_name(), [], []
            continue

        # TTE effects yield ANSI text; native effects (src/native_effects) yield Cells directly.
        cells = frame if isinstance(frame, dict) else parse_frame(frame, canvas_width, canvas_height)
        clears, draws = diff_cells(prev_cells, cells)
        prev_cells = cells
        yield effects.get_current_effect_name(), clears, draws


def run_worker(spec: WorkerSpec, deltas, stop, switch_barrier=None) -> None:
    """Process entry point. Deltas are incremental, so each one is delivered in order or the worker stops.

    Workers sharing a switch_barrier (and a seed) hold their final frame until every monitor's effect
    has ended, then all start the same next effect.
    """
    # Let this process exit on stop even if the display process never reads what is still buffered.
    deltas.cancel_join_thread()
    effects = EffectManager(
        text=spec.text,
        enabled_effects=spec.enabled_effects,
        canvas_width=spec.canvas_width,
        canvas_height=spec.canvas_height,
        start_index=spec.start_index,
        seed=spec.seed,
    )
    before_switch = (lambda: _wait_for_other_monitors(switch_barrier)) if switch_barrier else (lambda: None)
    for delta in frame_deltas(effects, spec.canvas_width, spec.canvas_height, before_switch):
        if not _put_until_stopped(deltas, delta, stop):
            return


def _wait_for_other_monitors(switch_barrier) -> None:
    # The display aborts the barrier when a monitor's worker dies or the screensaver stops;
    # the remaining monitors then carry on unsynced rather than wait forever.
    if switch_barrier.broken:
        return
    try:
        switch_barrier.wait()
    except threading.BrokenBarrierError:
        pass


def _put_until_stopped(deltas, delta: Delta, stop) -> bool:
    while not stop.is_set():
        try:
            deltas.put(delta, timeout=PUT_POLL_SECONDS)
            return True
        except queue.Full:
            pass
    return False
