import time

import pygame

from src import screensaver as screensaver_module
from src.config import Config
from src.screensaver import Screensaver


def test_the_screensaver_lets_windows_turn_the_displays_off():
    # SDL keeps displays awake by default; a screensaver must let the OS power them down.
    screensaver = Screensaver(config=Config())
    try:
        screensaver._init_pygame(fullscreen=False)
        assert pygame.display.get_allow_screensaver() is True
    finally:
        pygame.quit()


def test_windowed_mode_draws_inside_its_window(monkeypatch):
    # A desktop whose origin is left of and above the primary monitor, like a side monitor setup.
    monkeypatch.setattr(screensaver_module, "get_virtual_desktop_size", lambda: (-1707, -1116, 5974, 2569))
    screensaver = Screensaver(config=Config(ascii_art="hello", enabled_effects=["Print"]))
    started = time.monotonic()
    seen = {}
    real_flip = pygame.display.flip

    def flip():
        real_flip()
        surface = pygame.display.get_surface()
        seen["lit"] = pygame.mask.from_threshold(surface, (0, 0, 0), (1, 1, 1, 255)).count() < surface.get_width() * surface.get_height()
        if seen["lit"] or time.monotonic() - started > 30:
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    monkeypatch.setattr(pygame.display, "flip", flip)
    screensaver.run(fullscreen=False)

    assert [(m.offset_x, m.offset_y) for m in screensaver.monitor_effects] == [(0, 0)]
    assert seen["lit"], "nothing was drawn inside the window"
