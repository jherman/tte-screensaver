"""TTE's Matrix, reworked for a screensaver: the rain stays sparse and the text resolves out of it.

TTE's Matrix rains for a while, then fills every column and resolves the text from the full screen.
Here the rain never stops. Once RAIN_SECONDS have passed, each text character locks in when a
raindrop reaches it and leaves its rain column, so later drops fall behind it. Anything the rain has
not reached within CATCH_SECONDS resolves by itself, and the finished text holds for HOLD_SECONDS.
"""

import random
import time

from terminaltexteffects.effects.effect_matrix import Matrix, MatrixIterator

RAIN_SECONDS = 20.0
CATCH_SECONDS = 10.0
HOLD_SECONDS = 6.0
# Fraction of the still-unresolved characters forced in per frame once CATCH_SECONDS run out.
LATE_RESOLVE_FRACTION = 0.05


class SparseMatrixIterator(MatrixIterator):
    def __init__(self, effect: "SparseMatrix") -> None:
        super().__init__(effect)
        # TTE treats rain_time 0 as rain without end, so the base iterator never enters its fill phase.
        self.config.rain_time = 0
        self.column_of = {char: column for column in self.pending_columns for char in column.characters}
        self.unresolved = {
            char for char in self.column_of if char.input_symbol != " " or self._has_input_colors(char)
        }
        self.started = time.monotonic()
        self.resolved_at: float | None = None

    def __next__(self) -> str:
        elapsed = time.monotonic() - self.started
        if self.resolved_at is not None and elapsed - self.resolved_at >= HOLD_SECONDS:
            raise StopIteration

        if elapsed >= RAIN_SECONDS and self.unresolved:
            for char in [char for char in self.unresolved if char.is_visible]:
                self._resolve(char)
            if elapsed >= RAIN_SECONDS + CATCH_SECONDS and self.unresolved:
                count = max(1, int(len(self.unresolved) * LATE_RESOLVE_FRACTION))
                for char in random.sample(list(self.unresolved), count):
                    self._resolve(char)
            if not self.unresolved:
                self.resolved_at = elapsed

        return super().__next__()

    def _resolve(self, char) -> None:
        column = self.column_of[char]
        for members in (column.characters, column.pending_characters, column.visible_characters):
            if char in members:
                members.remove(char)
        char.motion.current_coord = char.input_coord
        # Rain that drops onto this cell draws on layer 0, beneath the text.
        char.layer = 1
        self.terminal.set_character_visibility(char, is_visible=True)
        char.animation.activate_scene("resolve")
        self.active_characters.add(char)
        self.unresolved.discard(char)


class SparseMatrix(Matrix):
    @property
    def _iterator_cls(self) -> type[MatrixIterator]:
        return SparseMatrixIterator
