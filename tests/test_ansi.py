import pytest

from src.ansi import diff_cells, parse_frame

WHITE = (255, 255, 255)
ESC = "\x1b["


def parse(frame, width=200, height=100):
    return parse_frame(frame, width, height)


def cells(entries):
    return {(row, col): (char, color) for row, col, char, color in entries}


@pytest.mark.parametrize(
    "frame, expected",
    [
        ("", []),
        ("ab", [(0, 0, "a", WHITE), (0, 1, "b", WHITE)]),
        ("a b", [(0, 0, "a", WHITE), (0, 2, "b", WHITE)]),
        ("a\nb", [(0, 0, "a", WHITE), (1, 0, "b", WHITE)]),
        ("ab\n\n c", [(0, 0, "a", WHITE), (0, 1, "b", WHITE), (2, 1, "c", WHITE)]),
        ("abc\rX", [(0, 0, "a", WHITE), (0, 1, "b", WHITE), (0, 2, "c", WHITE), (0, 0, "X", WHITE)]),
        ("a\r\nb", [(0, 0, "a", WHITE), (1, 0, "b", WHITE)]),
        ("\t", [(0, 0, "\t", WHITE)]),
        ("█╗", [(0, 0, "█", WHITE), (0, 1, "╗", WHITE)]),
    ],
)
def test_text_layout(frame, expected):
    assert parse(frame) == cells(expected)


@pytest.mark.parametrize(
    "frame, expected",
    [
        (f"{ESC}3;5Hx", [(2, 4, "x", WHITE)]),
        (f"ab{ESC}1;1Hc", [(0, 0, "a", WHITE), (0, 1, "b", WHITE), (0, 0, "c", WHITE)]),
        (f"{ESC}10;20Hx\ny", [(9, 19, "x", WHITE), (10, 0, "y", WHITE)]),
        (f"{ESC}Hx", [(0, 0, "x", WHITE)]),
        (f"a{ESC}Hx", [(0, 0, "a", WHITE), (0, 1, "x", WHITE)]),
        (f"a{ESC}5Hx", [(0, 0, "a", WHITE), (0, 1, "x", WHITE)]),
        (f"a{ESC}1;2;3Hx", [(0, 0, "a", WHITE), (0, 1, "x", WHITE)]),
        (f"a{ESC}2Jx", [(0, 0, "a", WHITE), (0, 1, "x", WHITE)]),
        (f"a{ESC}Kx", [(0, 0, "a", WHITE), (0, 1, "x", WHITE)]),
    ],
)
def test_cursor_and_control_sequences(frame, expected):
    assert parse(frame) == cells(expected)


@pytest.mark.parametrize(
    "frame, expected",
    [
        ("\x1bx", [(0, 0, "\x1b", WHITE), (0, 1, "x", WHITE)]),
        (f"{ESC}?25lx", [(0, 0, "\x1b", WHITE), (0, 1, "[", WHITE), (0, 2, "?", WHITE),
                         (0, 3, "2", WHITE), (0, 4, "5", WHITE), (0, 5, "l", WHITE), (0, 6, "x", WHITE)]),
        ("x\x1b", [(0, 0, "x", WHITE), (0, 1, "\x1b", WHITE)]),
        (f"x{ESC}", [(0, 0, "x", WHITE), (0, 1, "\x1b", WHITE), (0, 2, "[", WHITE)]),
    ],
)
def test_unrecognized_escapes_are_drawn_as_text(frame, expected):
    assert parse(frame) == cells(expected)


@pytest.mark.parametrize(
    "sgr, color",
    [
        ("38;2;1;2;3", (1, 2, 3)),
        ("38;2;255;128;0", (255, 128, 0)),
        ("38;5;196", (255, 0, 0)),
        ("38;5;16", (0, 0, 0)),
        ("38;5;110", (102, 153, 204)),
        ("38;5;9", (255, 85, 85)),
        ("38;5;2", (0, 170, 0)),
        ("38;5;232", (8, 8, 8)),
        ("38;5;255", (238, 238, 238)),
        ("31", (170, 0, 0)),
        ("37", (170, 170, 170)),
        ("90", (85, 85, 85)),
        ("92", (85, 255, 85)),
        ("1;31", (170, 0, 0)),
        ("31;32", (170, 0, 0)),
        ("0", WHITE),
        ("", WHITE),
        ("0;90;40", WHITE),
        ("39", (1, 2, 3)),
        ("40", (1, 2, 3)),
        ("1", (1, 2, 3)),
        (";", (1, 2, 3)),
        ("38;2;9;9", (1, 2, 3)),
        ("38;5", (1, 2, 3)),
        ("38", (1, 2, 3)),
    ],
)
def test_sgr_color_after_truecolor(sgr, color):
    frame = f"{ESC}38;2;1;2;3ma{ESC}{sgr}mb"
    assert parse(frame) == cells([(0, 0, "a", (1, 2, 3)), (0, 1, "b", color)])


def test_color_persists_across_text_newlines_and_cursor_moves():
    frame = f"{ESC}31ma\nb{ESC}5;5Hc{ESC}0md"
    red = (170, 0, 0)
    assert parse(frame) == cells([
        (0, 0, "a", red), (1, 0, "b", red), (4, 4, "c", red), (4, 5, "d", WHITE),
    ])


def test_color_starts_white_on_every_call():
    parse(f"{ESC}31ma")
    assert parse("a") == cells([(0, 0, "a", WHITE)])


@pytest.mark.parametrize(
    "frame, width, height, expected",
    [
        ("abcd", 2, 5, [(0, 0, "a", WHITE), (0, 1, "b", WHITE)]),
        ("a\nb\nc", 5, 2, [(0, 0, "a", WHITE), (1, 0, "b", WHITE)]),
        ("abcd\rx", 2, 5, [(0, 0, "a", WHITE), (0, 1, "b", WHITE), (0, 0, "x", WHITE)]),
        (f"{ESC}1;0Habc", 5, 5, [(0, 0, "b", WHITE), (0, 1, "c", WHITE)]),
        (f"{ESC}0;1Habc\nd", 5, 5, [(0, 0, "d", WHITE)]),
        (f"{ESC}3;3Hx", 2, 2, []),
        (f"{ESC}1;2Habc", 2, 2, [(0, 1, "a", WHITE)]),
    ],
)
def test_clipping_to_canvas(frame, width, height, expected):
    assert parse(frame, width, height) == cells(expected)


def test_last_write_to_a_cell_wins():
    frame = f"ab{ESC}1;1H{ESC}31mX"
    assert parse(frame, 10, 10) == {
        (0, 0): ("X", (170, 0, 0)),
        (0, 1): ("b", WHITE),
    }


RED = (170, 0, 0)


@pytest.mark.parametrize(
    "prev, curr, clears, draws",
    [
        ({}, {}, [], []),
        ({}, {(0, 0): ("a", WHITE)}, [], [(0, 0, "a", WHITE)]),
        ({(0, 0): ("a", WHITE)}, {(0, 0): ("a", WHITE)}, [], []),
        ({(0, 0): ("a", WHITE)}, {}, [(0, 0)], []),
        ({(0, 0): ("a", WHITE)}, {(0, 0): ("b", WHITE)}, [(0, 0)], [(0, 0, "b", WHITE)]),
        ({(0, 0): ("a", WHITE)}, {(0, 0): ("a", RED)}, [(0, 0)], [(0, 0, "a", RED)]),
        (
            {(0, 0): ("a", WHITE), (1, 1): ("b", WHITE), (2, 2): ("c", WHITE)},
            {(1, 1): ("b", WHITE), (2, 2): ("x", WHITE), (3, 3): ("d", RED)},
            [(0, 0), (2, 2)],
            [(2, 2, "x", WHITE), (3, 3, "d", RED)],
        ),
    ],
)
def test_diff_cells(prev, curr, clears, draws):
    actual_clears, actual_draws = diff_cells(prev, curr)
    assert sorted(actual_clears) == clears
    assert sorted(actual_draws) == draws
