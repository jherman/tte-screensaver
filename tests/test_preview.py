import ctypes
import subprocess
import sys
import time
from pathlib import Path

import pygame
import pytest

from src import main as main_module
from src import preview
from src.config import Config

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="the Screen Saver Settings preview is Windows-only")

REPO = Path(__file__).parent.parent


def test_preview_frames_are_a_miniature_of_the_screensaver():
    frames = preview.preview_frames(Config(ascii_art="HELLO\nWORLD", enabled_effects=["Bounce"]), 152, 112)
    for frame in (next(frames) for _ in range(300)):
        assert frame.get_size() == (152, 112)
        if pygame.mask.from_threshold(frame, (0, 0, 0), (1, 1, 1, 255)).count() < 152 * 112:
            return
    pytest.fail("the preview never drew anything")


@pytest.mark.parametrize("args", [["/p", "4242"], ["/P", "4242"], ["/p:4242"]])
def test_preview_mode_draws_into_the_window_windows_passes(monkeypatch, args):
    calls = []
    monkeypatch.setattr(preview, "run_preview", lambda hwnd: calls.append(hwnd))
    monkeypatch.setattr(sys, "argv", ["tte-screensaver.scr", *args])
    main_module.main()
    assert calls == [4242]


def test_preview_paints_into_a_window_and_exits_when_the_window_closes():
    import tkinter

    root = tkinter.Tk()
    box = tkinter.Frame(root, width=160, height=120, background="#ff00ff")
    box.pack()
    root.update()
    hwnd = box.winfo_id()
    user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
    user32.GetDC.restype = ctypes.c_void_p
    gdi32.GetPixel.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
    user32.ReleaseDC.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

    def pixel(x, y):
        dc = user32.GetDC(ctypes.c_void_p(hwnd))
        try:
            return gdi32.GetPixel(dc, x, y)
        finally:
            user32.ReleaseDC(ctypes.c_void_p(hwnd), dc)

    magenta = pixel(80, 60)
    process = subprocess.Popen([sys.executable, "run.py", "/p", str(hwnd)], cwd=REPO)
    try:
        deadline = time.monotonic() + 30
        painted = False
        while time.monotonic() < deadline and not painted:
            root.update()
            painted = pixel(80, 60) != magenta and pixel(5, 5) != magenta
            time.sleep(0.05)
        assert painted, "the preview never painted into the window"

        root.destroy()
        assert process.wait(timeout=15) == 0
    finally:
        if process.poll() is None:
            process.kill()
