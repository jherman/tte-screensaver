import pytest

from src.effects import AVAILABLE_EFFECTS, EffectManager
from src.native_effects import Bounce, Fireflies, Hyperspace, Life, Pipes, Ripples, Snowfall
from src.native_effects.base import layout_text

WIDTH, HEIGHT = 60, 20
FPS = 60
TEXT = "HELLO\nWORLD"
# Centered on a 60x20 canvas: 2 rows starting at row 9, 5 columns starting at column 27.
TEXT_CELLS = {(9 + row, 27 + col): char for row, line in enumerate(["HELLO", "WORLD"]) for col, char in enumerate(line)}
NATIVE_EFFECTS = [Hyperspace, Snowfall, Life, Pipes, Ripples, Fireflies, Bounce]


def play(effect_class, seconds_limit=60.0):
    """Drive an effect with a fake clock at FPS; return (seconds, cells) for every frame."""
    now = [0.0]
    effect = effect_class(TEXT)
    effect.clock = lambda: now[0]
    effect.terminal_config.canvas_width = WIDTH
    effect.terminal_config.canvas_height = HEIGHT
    frames = []
    for index, cells in enumerate(effect):
        frames.append((now[0], cells))
        now[0] = (index + 1) / FPS
        if now[0] > seconds_limit:
            break
    return frames


def shows_text(cells):
    return all(cells.get(pos, ("", None))[0] == char for pos, char in TEXT_CELLS.items())


@pytest.fixture(scope="module", params=NATIVE_EFFECTS, ids=lambda cls: cls.__name__)
def run(request):
    return request.param, play(request.param)


def test_frames_are_cells_inside_the_canvas(run):
    _, frames = run
    for _, cells in frames:
        for (row, col), (char, color) in cells.items():
            assert 0 <= row < HEIGHT and 0 <= col < WIDTH
            assert isinstance(char, str) and len(char) == 1 and char != " "
            assert len(color) == 3 and all(0 <= channel <= 255 for channel in color)


def test_the_text_is_revealed_not_shown_from_the_start(run):
    _, frames = run
    assert not any(shows_text(cells) for seconds, cells in frames if seconds < 1.0)


def test_the_effect_ends_showing_the_whole_text(run):
    effect_class, frames = run
    end_seconds, last_cells = frames[-1]
    assert end_seconds < 60, f"{effect_class.__name__} did not end"
    assert shows_text(last_cells)


@pytest.mark.parametrize("effect_class", NATIVE_EFFECTS, ids=lambda cls: cls.__name__)
def test_native_effects_are_available_to_the_effect_manager(effect_class):
    name = effect_class.__name__
    assert AVAILABLE_EFFECTS[name] is effect_class
    manager = EffectManager(TEXT, [name], WIDTH, HEIGHT, start_index=0)
    assert isinstance(manager.get_next_frame(), dict)


def test_layout_centers_ascii_art_and_ignores_its_ansi_codes():
    art = "\x1b[0;92;42mAB\x1b[0m\n\x1b[90m C\x1b[0m"
    assert layout_text(art, 10, 4) == {(1, 4): "A", (1, 5): "B", (2, 5): "C"}


def test_layout_clips_text_larger_than_the_canvas():
    assert layout_text("ABCDE", 3, 1) == {(0, 0): "B", (0, 1): "C", (0, 2): "D"}


def test_bounce_hits_a_corner():
    letters = set(TEXT) - {"\n"}

    def in_a_corner(cells):
        logo = [pos for pos, (char, _) in cells.items() if char in letters]
        if len(logo) < len(TEXT_CELLS):
            return False
        rows = [row for row, _ in logo]
        cols = [col for _, col in logo]
        return (min(rows) == 0 or max(rows) == HEIGHT - 1) and (min(cols) == 0 or max(cols) == WIDTH - 1)

    assert any(in_a_corner(cells) for _, cells in play(Bounce))
