"""Split per-frame cost into TTE generation, ANSI parsing, and delta drawing, per effect and canvas.

Run from the repo root:  python bench_parse.py [frames]
No window is opened; drawing goes to an offscreen surface of the monitor's size.
draw ms covers diffing against the previous frame, glyph rendering, and blits.
"""

import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import load_config
from src.effects import EffectManager
from src.ansi import diff_cells, parse_frame
from src.renderer import ANSIRenderer

import pygame

EFFECTS = ["Beams", "Spotlights", "Matrix", "SynthGrid"]
MONITORS = {"center 2560x1440": (2560, 1440), "side 1707x2560": (1707, 2560)}


def bench(renderer: ANSIRenderer, text: str, effect: str, width: int, height: int, frames: int):
    manager = EffectManager(text, [effect], width, height, start_index=0)
    surface = pygame.Surface((width * renderer.char_width, height * renderer.char_height))
    renderer.clear_cache()
    prev_cells = {}
    generate, parse, draw = [], [], []
    for _ in range(frames):
        started = time.perf_counter()
        frame = manager.get_next_frame()
        generated = time.perf_counter()
        if frame is None:
            break
        cells = parse_frame(frame, width, height)
        parsed = time.perf_counter()
        renderer.apply_delta(surface, *diff_cells(prev_cells, cells))
        prev_cells = cells
        draw.append(time.perf_counter() - parsed)
        parse.append(parsed - generated)
        generate.append(generated - started)
    return generate, parse, draw, len(renderer._char_cache)


def main() -> None:
    frames = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    config = load_config()
    renderer = ANSIRenderer(font_size=config.font_size)
    print(f"font_size={config.font_size} cell={renderer.char_width}x{renderer.char_height} frames<={frames}\n")
    print(f"{'effect':12s} {'monitor':18s} {'canvas':>9s} {'n':>4s} {'gen ms':>8s} {'parse ms':>9s} {'draw ms':>8s} {'parse %':>8s} {'glyphs':>7s}")
    for effect in EFFECTS:
        for label, (px_w, px_h) in MONITORS.items():
            width, height = px_w // renderer.char_width, px_h // renderer.char_height
            generate, parse, draw, glyphs = bench(renderer, config.ascii_art, effect, width, height, frames)
            gen_ms, parse_ms, draw_ms = (statistics.mean(xs) * 1000 for xs in (generate, parse, draw))
            print(f"{effect:12s} {label:18s} {f'{width}x{height}':>9s} {len(parse):4d} "
                  f"{gen_ms:8.2f} {parse_ms:9.2f} {draw_ms:8.2f} {100 * parse_ms / (gen_ms + parse_ms + draw_ms):7.0f}% {glyphs:7d}")


if __name__ == "__main__":
    main()
