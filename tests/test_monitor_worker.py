import multiprocessing
import time

import pygame
import pytest

from src.config import Config
from src.monitor_worker import WorkerSpec, frame_deltas, run_worker
from src.renderer import ANSIRenderer
from src.screensaver import MonitorEffect, MonitorInfo

WHITE = (255, 255, 255)
RED = (255, 0, 0)
SPAWN = multiprocessing.get_context("spawn")


class ScriptedEffects:
    """Stands in for EffectManager: plays each (name, frames) effect in order."""

    def __init__(self, *effects):
        self.effects = list(effects)
        self.frames = iter(self.effects[0][1])

    def get_current_effect_name(self):
        return self.effects[0][0]

    def get_next_frame(self):
        return next(self.frames, None)

    def switch_to_next_effect(self):
        self.effects.pop(0)
        self.frames = iter(self.effects[0][1])


def take(iterator, n):
    return [next(iterator) for _ in range(n)]


def test_each_frame_becomes_a_delta_against_the_previous_frame():
    effects = ScriptedEffects(("Beams", ["a", "ab", " b"]), ("Matrix", []))
    assert take(frame_deltas(effects, 10, 5), 3) == [
        ("Beams", [], [(0, 0, "a", WHITE)]),
        ("Beams", [], [(0, 1, "b", WHITE)]),
        ("Beams", [(0, 0)], []),
    ]


def test_effect_switch_redraws_the_new_effect_from_scratch():
    effects = ScriptedEffects(("Beams", ["ab"]), ("Matrix", ["a"]))
    assert take(frame_deltas(effects, 10, 5), 2) == [
        ("Beams", [], [(0, 0, "a", WHITE), (0, 1, "b", WHITE)]),
        ("Matrix", [], [(0, 0, "a", WHITE)]),
    ]


def test_effect_with_no_frames_still_yields_one_empty_delta_per_tick():
    effects = ScriptedEffects(("Beams", ["a"]), ("Matrix", []), ("Rain", ["x"]))
    assert take(frame_deltas(effects, 10, 5), 3) == [
        ("Beams", [], [(0, 0, "a", WHITE)]),
        ("Matrix", [], []),
        ("Rain", [], [(0, 0, "x", WHITE)]),
    ]


def wait_for(predicate, timeout=60.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def test_worker_process_streams_deltas_and_stops_when_its_queue_is_full():
    deltas = SPAWN.Queue(maxsize=2)
    stop = SPAWN.Event()
    spec = WorkerSpec(text="hello", enabled_effects=["Print"], canvas_width=20, canvas_height=5, start_index=0)
    process = SPAWN.Process(target=run_worker, args=(spec, deltas, stop), daemon=True)
    process.start()
    try:
        names = {deltas.get(timeout=60)[0] for _ in range(3)}
        assert names == {"Print"}
        assert wait_for(deltas.full, timeout=10), "worker should fill the bounded queue and block"

        stop.set()
        process.join(timeout=5)
        assert process.exitcode == 0
    finally:
        if process.is_alive():
            process.terminate()


@pytest.fixture
def renderer():
    return ANSIRenderer(font_size=16)


def monitor_pixels(surface, monitor, offset):
    return {
        surface.get_at((x, y))[:3]
        for x in range(offset[0], offset[0] + monitor.width)
        for y in range(offset[1], offset[1] + monitor.height)
    }


def test_monitor_draws_worker_deltas_and_blanks_when_the_worker_dies(renderer):
    monitor = MonitorInfo(x=40, y=0, width=renderer.char_width * 12, height=renderer.char_height * 3)
    surface = pygame.Surface((40 + monitor.width, monitor.height))
    surface.fill(RED)
    config = Config(ascii_art="hi", enabled_effects=["Print"])
    stop = SPAWN.Event()
    monitor_effect = MonitorEffect(monitor, config, renderer, (0, 0), 0, SPAWN, stop)
    try:
        assert wait_for(lambda: monitor_effect.update_and_render(surface) or monitor_effect.effect_name)
        assert monitor_effect.effect_name == "Print"
        assert surface.get_at((0, 0))[:3] == RED

        monitor_effect.process.terminate()
        monitor_effect.process.join(timeout=5)
        for _ in range(4):
            monitor_effect.update_and_render(surface)

        assert monitor_pixels(surface, monitor, (40, 0)) == {(0, 0, 0)}
        assert surface.get_at((0, 0))[:3] == RED
    finally:
        stop.set()
        monitor_effect.close()
    assert not monitor_effect.process.is_alive()


def test_the_switch_hook_runs_after_an_effect_ends_and_before_the_next_starts():
    events = []
    effects = ScriptedEffects(("Beams", ["a"]), ("Matrix", ["b"]))
    deltas = frame_deltas(effects, 10, 5, before_switch=lambda: events.append("switch"))
    for _ in range(2):
        events.append(next(deltas)[0])
    assert events == ["Beams", "switch", "Matrix"]


def effect_runs(names):
    """Collapse consecutive repeats: ["A", "A", "B"] -> ["A", "B"]."""
    return [name for index, name in enumerate(names) if index == 0 or names[index - 1] != name]


def test_synced_workers_play_the_same_effects_in_the_same_order():
    stop = SPAWN.Event()
    barrier = SPAWN.Barrier(2)
    queues, processes = [], []
    for width, height in ((12, 3), (40, 12)):
        spec = WorkerSpec(
            text="hi", enabled_effects=["Print", "Slide", "Wipe", "Expand"],
            canvas_width=width, canvas_height=height, start_index=0, seed=11,
        )
        deltas = SPAWN.Queue(maxsize=2)
        process = SPAWN.Process(target=run_worker, args=(spec, deltas, stop, barrier), daemon=True)
        process.start()
        queues.append(deltas)
        processes.append(process)
    try:
        seen = [[], []]
        deadline = time.monotonic() + 120
        while min(len(effect_runs(names)) for names in seen) < 5 and time.monotonic() < deadline:
            for names, deltas in zip(seen, queues):
                try:
                    names.append(deltas.get(timeout=0.01)[0])
                except Exception:
                    pass
        runs = [effect_runs(names)[:5] for names in seen]
        assert len(runs[0]) == 5
        assert runs[0] == runs[1]
    finally:
        stop.set()
        barrier.abort()
        for process in processes:
            process.join(timeout=5)
            if process.is_alive():
                process.terminate()


def test_an_aborted_switch_barrier_lets_a_worker_carry_on_alone():
    stop = SPAWN.Event()
    barrier = SPAWN.Barrier(2)
    spec = WorkerSpec(text="hi", enabled_effects=["Print", "Slide"], canvas_width=12, canvas_height=3, start_index=0)
    deltas = SPAWN.Queue(maxsize=2)
    process = SPAWN.Process(target=run_worker, args=(spec, deltas, stop, barrier), daemon=True)
    process.start()
    names = []

    def read_available():
        for _ in range(50):
            try:
                names.append(deltas.get(timeout=0.01)[0])
            except Exception:
                return

    try:
        assert wait_for(lambda: read_available() or barrier.n_waiting == 1, timeout=60), (
            "worker should hold at the end of its first effect, waiting for the missing monitor"
        )
        assert effect_runs(names) == ["Print"]

        barrier.abort()
        assert wait_for(lambda: read_available() or len(effect_runs(names)) >= 3, timeout=60)
        assert effect_runs(names)[:3] == ["Print", "Slide", "Print"]
    finally:
        stop.set()
        process.join(timeout=5)
        if process.is_alive():
            process.terminate()
