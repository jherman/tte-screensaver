import pygame

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
