"""Screen Saver Settings preview: a miniature of the screensaver painted into the dialog's preview window.

Windows runs the screensaver with /p <hwnd> to animate the small monitor in Screen Saver Settings.
The effects render off-screen at a size where the whole ASCII art fits, then each frame is scaled
down and painted into that window with GDI. No pygame window is created, so the dialog's own window
is never taken over. The preview exits once Windows destroys the window.
"""

import ctypes
import time
from ctypes import wintypes
from typing import Iterator

import pygame

from .ansi import parse_frame
from .config import Config, load_config
from .effects import EffectManager
from .monitor_worker import frame_deltas
from .renderer import ANSIRenderer

PREVIEW_FONT_SIZE = 10
PREVIEW_FPS = 30
MARGIN_CELLS = 4
SRCCOPY = 0x00CC0020
DIB_RGB_COLORS = 0


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG), ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD),
    ]


def preview_frames(config: Config, width: int, height: int) -> Iterator[pygame.Surface]:
    """Yield width x height miniatures of the screensaver, one per effect frame."""
    renderer = ANSIRenderer(PREVIEW_FONT_SIZE, config.background_color)
    cell_w, cell_h = renderer.char_width, renderer.char_height
    art = parse_frame(config.ascii_art, 1 << 16, 1 << 16)
    art_cols = max(col for _, col in art) - min(col for _, col in art) + 1 if art else 40
    art_rows = max(row for row, _ in art) - min(row for row, _ in art) + 1 if art else 10
    # A canvas with the preview's aspect ratio that fits the whole art plus a margin.
    cols = art_cols + 2 * MARGIN_CELLS
    rows = max(art_rows + 2 * MARGIN_CELLS, round(cols * cell_w * height / (width * cell_h)))
    cols = max(cols, round(rows * cell_h * width / (height * cell_w)))

    canvas = pygame.Surface((cols * cell_w, rows * cell_h))
    canvas.fill(config.background_color)
    effects = EffectManager(config.ascii_art, config.enabled_effects, cols, rows)
    for _name, clears, draws in frame_deltas(effects, cols, rows):
        renderer.apply_delta(canvas, clears, draws)
        yield pygame.transform.smoothscale(canvas, (width, height))


def run_preview(hwnd: int) -> None:
    user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
    user32.GetDC.restype = ctypes.c_void_p
    user32.GetDC.argtypes = [wintypes.HWND]
    user32.ReleaseDC.argtypes = [wintypes.HWND, ctypes.c_void_p]
    user32.IsWindow.argtypes = [wintypes.HWND]
    gdi32.StretchDIBits.argtypes = [
        ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT, wintypes.DWORD,
    ]
    window = wintypes.HWND(hwnd)
    rect = wintypes.RECT()
    if not user32.IsWindow(window) or not user32.GetClientRect(window, ctypes.byref(rect)):
        return
    width, height = rect.right - rect.left, rect.bottom - rect.top
    if width <= 0 or height <= 0:
        return

    # A negative height makes the bitmap top-down, matching pygame's row order.
    header = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), width, -height, 1, 32, 0, 0, 0, 0, 0, 0)
    next_frame = time.monotonic()
    for frame in preview_frames(load_config(), width, height):
        if not user32.IsWindow(window):
            return
        pixels = pygame.image.tobytes(frame, "BGRA")
        dc = user32.GetDC(window)
        try:
            gdi32.StretchDIBits(dc, 0, 0, width, height, 0, 0, width, height, pixels, ctypes.byref(header),
                                DIB_RGB_COLORS, SRCCOPY)
        finally:
            user32.ReleaseDC(window, dc)
        next_frame += 1 / PREVIEW_FPS
        time.sleep(max(0.0, next_frame - time.monotonic()))
