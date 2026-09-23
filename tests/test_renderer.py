import pygame
import pytest

from src.renderer import ANSIRenderer

BLACK = (0, 0, 0)
RED = (255, 0, 0)


@pytest.fixture(scope="module")
def renderer():
    return ANSIRenderer(font_size=16)


def lit_pixels(surface, renderer, row, col, offset=(0, 0)):
    x0 = offset[0] + col * renderer.char_width
    y0 = offset[1] + row * renderer.char_height
    return {
        surface.get_at((x, y))[:3]
        for x in range(x0, x0 + renderer.char_width)
        for y in range(y0, y0 + renderer.char_height)
    } - {BLACK}


def test_draw_then_clear_a_cell(renderer):
    surface = pygame.Surface((renderer.char_width * 4, renderer.char_height * 3))
    surface.fill(BLACK)

    renderer.apply_delta(surface, [], [(1, 2, "M", RED)])
    assert RED in lit_pixels(surface, renderer, 1, 2)
    assert lit_pixels(surface, renderer, 0, 0) == set()

    renderer.apply_delta(surface, [(1, 2)], [])
    assert lit_pixels(surface, renderer, 1, 2) == set()


def test_offset_places_cells_in_the_monitor_region(renderer):
    offset = (renderer.char_width * 2, renderer.char_height)
    surface = pygame.Surface((renderer.char_width * 4, renderer.char_height * 3))
    surface.fill(BLACK)

    renderer.apply_delta(surface, [], [(0, 0, "M", RED)], *offset)
    assert RED in lit_pixels(surface, renderer, 0, 0, offset)
    assert lit_pixels(surface, renderer, 0, 0) == set()


def test_clears_are_blitted_before_draws(renderer):
    surface = pygame.Surface((renderer.char_width, renderer.char_height))
    surface.fill(BLACK)
    renderer.apply_delta(surface, [], [(0, 0, "M", (0, 0, 255))])

    renderer.apply_delta(surface, [(0, 0)], [(0, 0, "M", RED)])
    assert (0, 0, 255) not in lit_pixels(surface, renderer, 0, 0)
    assert RED in lit_pixels(surface, renderer, 0, 0)
