"""Per-phase frame timing for tte-screensaver.

Drop into the repo root and run:  python profile_frames.py [EffectName ...]
Runs the real screensaver fullscreen for MAX_FRAMES frames, then prints where the time went.
Effect names on the command line restrict the run to those effects.
"""

import collections
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
from src import screensaver as ss
from src.config import load_config

MAX_FRAMES = 600

phase_durations: dict[str, list[float]] = collections.defaultdict(list)
monitor_ticks: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])  # [delta applied, no delta ready]
applied_deltas = [0]
monitors_seen: dict[int, object] = {}
startup: dict[str, float] = {}  # first flip, and when every monitor's worker had delivered a delta
flip_timestamps: list[float] = []
environment_info: dict[str, object] = {}


def wrap_apply_delta(original):
    def counted_apply_delta(*args, **kwargs):
        applied_deltas[0] += 1
        return original(*args, **kwargs)
    return counted_apply_delta


def wrap_render(original):
    def timed_render(monitor_effect, surface):
        monitors_seen[id(monitor_effect)] = monitor_effect
        if "live" not in startup:
            return original(monitor_effect, surface)
        applied_before = applied_deltas[0]
        started = time.perf_counter()
        try:
            return original(monitor_effect, surface)
        finally:
            elapsed = time.perf_counter() - started
            monitor = f"{monitor_effect.monitor.width}x{monitor_effect.monitor.height} at ({monitor_effect.monitor.x}, {monitor_effect.monitor.y})"
            applied = applied_deltas[0] > applied_before
            monitor_ticks[monitor][0 if applied else 1] += 1
            if applied:
                phase_durations[f"blit: {monitor_effect.effect_name}"].append(elapsed)
    return timed_render


def wrap_flip(original):
    def timed_flip():
        if not environment_info:
            display_surface = pygame.display.get_surface()
            environment_info["video driver"] = pygame.display.get_driver()
            environment_info["window size"] = display_surface.get_size()
        started = time.perf_counter()
        original()
        finished = time.perf_counter()
        startup.setdefault("first flip", finished)
        if "live" not in startup:
            # Workers build their first effect in parallel with the display; measure steady state only.
            if monitors_seen and all(m.effect_name is not None for m in monitors_seen.values()):
                startup["live"] = finished
            return
        phase_durations["flip"].append(finished - started)
        flip_timestamps.append(finished)
        if len(flip_timestamps) >= MAX_FRAMES:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
    return timed_flip


def print_report() -> None:
    config = load_config()
    print(f"\npygame {pygame.version.ver}, SDL {pygame.get_sdl_version()}, Python {sys.version.split()[0]}")
    print(f"font_size={config.font_size} target_fps={config.target_fps}")
    for key, value in environment_info.items():
        print(f"{key}: {value}")

    if "live" in startup:
        print(f"all workers live {startup['live'] - startup['first flip']:.2f} s after the first flip; measuring from there")
    if len(flip_timestamps) < 2:
        print("Not enough frames recorded.")
        return

    frame_intervals = [b - a for a, b in zip(flip_timestamps, flip_timestamps[1:])]
    mean_interval = statistics.mean(frame_intervals)
    print(f"\nframes={len(flip_timestamps)}  avg frame={mean_interval * 1000:.1f} ms  ->  {1 / mean_interval:.1f} fps\n")
    print(f"{'phase':32s} {'calls':>6s} {'mean ms':>8s} {'p95 ms':>8s}")
    for phase, durations in sorted(phase_durations.items(), key=lambda item: -statistics.mean(item[1])):
        ordered = sorted(durations)
        p95 = ordered[round(0.95 * (len(ordered) - 1))]
        print(f"{phase:32s} {len(durations):6d} {statistics.mean(durations) * 1000:8.2f} {p95 * 1000:8.2f}")

    # A worker that cannot keep up leaves ticks with no delta; its effect then animates below display fps.
    elapsed = flip_timestamps[-1] - flip_timestamps[0]
    print()
    print(f"{'monitor':32s} {'deltas':>6s} {'no delta':>8s} {'effect fps':>10s}")
    for monitor, (applied, waited) in monitor_ticks.items():
        print(f"{monitor:32s} {applied:6d} {waited:8d} {applied / elapsed:10.1f}")


if __name__ == "__main__":
    ss.MonitorEffect.update_and_render = wrap_render(ss.MonitorEffect.update_and_render)
    ss.ANSIRenderer.apply_delta = wrap_apply_delta(ss.ANSIRenderer.apply_delta)
    pygame.display.flip = wrap_flip(pygame.display.flip)
    try:
        run_config = load_config()
        if sys.argv[1:]:
            run_config.enabled_effects = sys.argv[1:]
        ss.run_screensaver(fullscreen=True, config=run_config)
    finally:
        print_report()
