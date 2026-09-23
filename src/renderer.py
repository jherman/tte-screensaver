"""Pygame renderer that draws parsed ANSI cells as cached glyphs."""

import sys
from typing import List, Optional, Tuple
from pathlib import Path
import pygame

from .ansi import DrawOp, Position


def get_bundled_font_path() -> Optional[Path]:
    """Get path to the bundled font file."""
    # When running from source
    src_dir = Path(__file__).parent.parent
    font_path = src_dir / "assets" / "font.ttf"
    if font_path.exists():
        return font_path

    # When running as frozen executable (PyInstaller)
    if getattr(sys, "frozen", False):
        base_path = Path(sys._MEIPASS)
        font_path = base_path / "assets" / "font.ttf"
        if font_path.exists():
            return font_path

    return None


class ANSIRenderer:
    """Renders ANSI-formatted text to a pygame surface."""

    def __init__(
        self,
        font_size: int = 20,
        background_color: Tuple[int, int, int] = (0, 0, 0),
    ):
        self.font_size = font_size
        self.background_color = background_color

        # Initialize font
        pygame.font.init()
        self.font = self._get_monospace_font(font_size)
        self.char_width, self.char_height = self.font.size("M")

        # Character surface cache for performance
        self._char_cache: dict = {}

        # Pre-create background tile for clearing cells
        self._bg_tile = pygame.Surface((self.char_width, self.char_height))
        self._bg_tile.fill(background_color)

    def _get_monospace_font(self, size: int) -> pygame.font.Font:
        """Get a monospace font, trying bundled font first."""
        # Try bundled font first (has full Unicode support)
        bundled_font = get_bundled_font_path()
        if bundled_font:
            try:
                return pygame.font.Font(str(bundled_font), size)
            except Exception:
                pass

        # Fallback to system fonts with good Unicode support
        monospace_fonts = [
            "cascadia code",
            "cascadia mono",
            "jetbrains mono",
            "consolas",
            "courier new",
            "courier",
            "liberation mono",
            "dejavu sans mono",
            "monospace",
        ]

        for font_name in monospace_fonts:
            try:
                font = pygame.font.SysFont(font_name, size)
                if font:
                    return font
            except Exception:
                continue

        # Fallback to default font
        return pygame.font.Font(None, size)

    def get_char_surface(
        self, char: str, color: Tuple[int, int, int]
    ) -> pygame.Surface:
        """Get a cached surface for a character with given color."""
        cache_key = (char, color)
        if cache_key not in self._char_cache:
            self._char_cache[cache_key] = self.font.render(char, True, color)
        return self._char_cache[cache_key]

    def apply_delta(
        self,
        surface: pygame.Surface,
        clears: List[Position],
        draws: List[DrawOp],
        offset_x: int = 0,
        offset_y: int = 0,
    ) -> None:
        """Blit a cell delta from ansi.diff_cells: background tiles for clears, then glyphs for draws."""
        char_w = self.char_width
        char_h = self.char_height
        if clears:
            bg_tile = self._bg_tile
            surface.blits(
                [(bg_tile, (offset_x + col * char_w, offset_y + row * char_h)) for row, col in clears],
                doreturn=False,
            )
        if draws:
            get_char_surface = self.get_char_surface
            surface.blits(
                [
                    (get_char_surface(char, color), (offset_x + col * char_w, offset_y + row * char_h))
                    for row, col, char, color in draws
                ],
                doreturn=False,
            )

    def clear_cache(self) -> None:
        """Clear the character surface cache."""
        self._char_cache.clear()
