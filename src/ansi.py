"""Pure ANSI frame parsing and cell diffing, with no pygame dependency so worker processes can use it."""

import re
from typing import Dict, List, Tuple

Color = Tuple[int, int, int]
Position = Tuple[int, int]  # (row, col)
Cells = Dict[Position, Tuple[str, Color]]
DrawOp = Tuple[int, int, str, Color]  # (row, col, char, color)

DEFAULT_FG_COLOR: Color = (255, 255, 255)

# Splits a frame into text runs and the tokens that move the cursor or change color.
# A malformed escape such as "\x1b[?25l" is not a token, so it stays in the text and is drawn.
ANSI_TOKEN = re.compile(r"(\x1b\[[0-9;]*[A-Za-z]|\n|\r)")
CURSOR_POS_PARAMS = re.compile(r"(\d+);(\d+)")

# SGR tokens that set no foreground color (e.g. "\x1b[1m") leave the current color unchanged.
KEEP_COLOR = object()
SGR_CACHE_LIMIT = 65536
_sgr_colors: dict = {}

BASIC_COLORS = [
    (0, 0, 0),        # Black
    (170, 0, 0),      # Red
    (0, 170, 0),      # Green
    (170, 85, 0),     # Yellow/Brown
    (0, 0, 170),      # Blue
    (170, 0, 170),    # Magenta
    (0, 170, 170),    # Cyan
    (170, 170, 170),  # White
]
BRIGHT_COLORS = [
    (85, 85, 85),     # Bright Black (Gray)
    (255, 85, 85),    # Bright Red
    (85, 255, 85),    # Bright Green
    (255, 255, 85),   # Bright Yellow
    (85, 85, 255),    # Bright Blue
    (255, 85, 255),   # Bright Magenta
    (85, 255, 255),   # Bright Cyan
    (255, 255, 255),  # Bright White
]


def parse_frame(frame: str, canvas_width: int, canvas_height: int) -> Cells:
    """Parse an ANSI frame into its visible non-space cells, clipped to the canvas."""
    cells: Cells = {}
    color = DEFAULT_FG_COLOR
    row = col = 0

    parts = ANSI_TOKEN.split(frame)
    # parts alternates text, token, text, ...; pair each text run with the token before it.
    for token, text in zip(["", *parts[1::2]], parts[::2]):
        if token == "\n":
            row += 1
            col = 0
        elif token == "\r":
            col = 0
        elif token:
            final = token[-1]
            if final == "m":
                new_color = _sgr_colors.get(token)
                if new_color is None:
                    if len(_sgr_colors) >= SGR_CACHE_LIMIT:
                        _sgr_colors.clear()
                    new_color = _sgr_colors[token] = parse_color_codes(token[2:-1].split(";"), KEEP_COLOR)
                if new_color is not KEEP_COLOR:
                    color = new_color
            elif final == "H":
                position = CURSOR_POS_PARAMS.fullmatch(token, 2, len(token) - 1)
                if position:
                    row = int(position[1]) - 1
                    col = int(position[2]) - 1

        if text:
            if 0 <= row < canvas_height and col < canvas_width and text.strip(" "):
                skip = -col if col < 0 else 0
                for c, char in enumerate(text[skip:canvas_width - col], col + skip):
                    if char != " ":
                        cells[row, c] = (char, color)
            col += len(text)

    return cells


def diff_cells(prev: Cells, curr: Cells) -> Tuple[List[Position], List[DrawOp]]:
    """Return the cells to clear and the cells to draw to turn prev into curr on screen.

    A changed cell is both cleared and drawn, because glyphs are blitted with transparent backgrounds.
    """
    clears = [pos for pos in prev.keys() - curr.keys()]
    draws = []
    for pos, cell in curr.items():
        prev_cell = prev.get(pos)
        if prev_cell != cell:
            if prev_cell is not None:
                clears.append(pos)
            draws.append((pos[0], pos[1], cell[0], cell[1]))
    return clears, draws


def parse_color_codes(codes: List[str], current_color):
    """Parse ANSI SGR codes and return the resulting foreground color, or current_color if none is set."""
    if not codes or codes == [""]:
        return DEFAULT_FG_COLOR

    i = 0
    while i < len(codes):
        try:
            code = int(codes[i])
        except ValueError:
            i += 1
            continue

        if code == 0:
            # Reset
            return DEFAULT_FG_COLOR
        elif code == 38:
            # Foreground color
            if i + 1 < len(codes):
                try:
                    color_type = int(codes[i + 1])
                except ValueError:
                    i += 1
                    continue

                if color_type == 2 and i + 4 < len(codes):
                    # RGB color: 38;2;R;G;B
                    try:
                        r = int(codes[i + 2])
                        g = int(codes[i + 3])
                        b = int(codes[i + 4])
                        return (r, g, b)
                    except (ValueError, IndexError):
                        pass
                    i += 5
                    continue
                elif color_type == 5 and i + 2 < len(codes):
                    # 256 color: 38;5;N
                    try:
                        color_num = int(codes[i + 2])
                        return xterm_to_rgb(color_num)
                    except (ValueError, IndexError):
                        pass
                    i += 3
                    continue
        elif 30 <= code <= 37:
            # Standard foreground colors
            return BASIC_COLORS[code - 30]
        elif 90 <= code <= 97:
            # Bright foreground colors
            return BRIGHT_COLORS[code - 90]

        i += 1

    return current_color


def xterm_to_rgb(color_num: int) -> Color:
    """Convert xterm 256 color number to RGB."""
    if color_num < 16:
        # Standard colors
        return (BRIGHT_COLORS if color_num >= 8 else BASIC_COLORS)[color_num % 8]
    elif color_num < 232:
        # 216 color cube (6x6x6)
        color_num -= 16
        r = (color_num // 36) % 6
        g = (color_num // 6) % 6
        b = color_num % 6
        return (r * 51, g * 51, b * 51)
    else:
        # Grayscale
        gray = (color_num - 232) * 10 + 8
        return (gray, gray, gray)
