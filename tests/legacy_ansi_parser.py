"""Verbatim copy of the per-character parser that parse_ansi_frame_sparse replaced.

Used only as the equivalence oracle in test_ansi_parser.py.
"""

import re

ANSI_ESCAPE = re.compile(r"\x1b\[([0-9;]*)m")
ANSI_CURSOR_POS = re.compile(r"\x1b\[(\d+);(\d+)H")
ANSI_ANY = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def legacy_parse_ansi_frame_sparse(renderer, frame, canvas_width=200, canvas_height=100):
    cells = []
    current_color = renderer.default_fg_color
    cursor_row = 0
    cursor_col = 0

    i = 0
    frame_len = len(frame)
    while i < frame_len:
        char = frame[i]

        if char == "\x1b" and i + 1 < frame_len and frame[i + 1] == "[":
            pos_match = ANSI_CURSOR_POS.match(frame, i)
            if pos_match:
                cursor_row = int(pos_match.group(1)) - 1
                cursor_col = int(pos_match.group(2)) - 1
                i = pos_match.end()
                continue

            color_match = ANSI_ESCAPE.match(frame, i)
            if color_match:
                codes = color_match.group(1).split(";")
                current_color = renderer._parse_color_codes(codes, current_color)
                i = color_match.end()
                continue

            other_match = ANSI_ANY.match(frame, i)
            if other_match:
                i = other_match.end()
                continue

        if char == "\n":
            cursor_row += 1
            cursor_col = 0
            i += 1
            continue

        if char == "\r":
            cursor_col = 0
            i += 1
            continue

        if char != " " and 0 <= cursor_row < canvas_height and 0 <= cursor_col < canvas_width:
            cells.append((cursor_row, cursor_col, char, current_color))

        cursor_col += 1
        i += 1

    return cells
