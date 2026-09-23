import itertools

import pytest

from src import sparse_matrix
from src.ansi import parse_frame
from src.effects import EffectManager

TEXT = "HELLO\nWORLD"
TEXT_LETTERS = set("HELOWRD")  # none of these are Matrix rain symbols
WIDTH, HEIGHT = 60, 20
FPS = 60


@pytest.fixture
def clock(monkeypatch):
    now = [0.0]
    monkeypatch.setattr(sparse_matrix.time, "monotonic", lambda: now[0])
    return now


def play(clock):
    """Yield (seconds, cells) for every frame of a Matrix run, advancing the fake clock at FPS."""
    manager = EffectManager(TEXT, ["Matrix"], WIDTH, HEIGHT, start_index=0)
    for n in itertools.count():
        clock[0] = n / FPS
        frame = manager.get_next_frame()
        if frame is None:
            return
        yield clock[0], parse_frame(frame, WIDTH, HEIGHT)


def text_read_from(cells):
    return "".join(char for _, (char, _) in sorted(cells.items()) if char in TEXT_LETTERS)


def test_matrix_rains_sparsely_then_resolves_the_text_and_ends(clock):
    frames = list(play(clock))
    end_seconds, last_cells = frames[-1]

    rain = [cells for seconds, cells in frames if seconds < sparse_matrix.RAIN_SECONDS]
    assert rain and all(text_read_from(cells) == "" for cells in rain)
    assert max(len(cells) for _, cells in frames) < 0.6 * WIDTH * HEIGHT
    assert text_read_from(last_cells) == "HELLOWORLD"
    assert end_seconds <= sparse_matrix.RAIN_SECONDS + sparse_matrix.CATCH_SECONDS + sparse_matrix.HOLD_SECONDS + 5


def test_resolved_text_stays_put_while_rain_keeps_falling(clock):
    resolved_at = None
    for seconds, cells in play(clock):
        if resolved_at is None and text_read_from(cells) == "HELLOWORLD":
            resolved_at = seconds
            rain_then = {pos for pos, (char, _) in cells.items() if char not in TEXT_LETTERS}
        elif resolved_at is not None:
            assert text_read_from(cells) == "HELLOWORLD"
            last_rain = {pos for pos, (char, _) in cells.items() if char not in TEXT_LETTERS}
    assert resolved_at is not None
    assert last_rain and last_rain != rain_then
