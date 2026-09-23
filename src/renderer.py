"""Pygame renderer that draws parsed ANSI cells as cached glyphs."""

import sys
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import pygame

from .ansi import DrawOp, Position

# Fonts that cover glyphs the bundled font lacks, such as the half-width katakana in TTE's Matrix rain.
FALLBACK_FONT_NAMES = ["ms gothic", "yu gothic", "noto sans mono cjk jp", "noto sans cjk jp"]
# A Unicode noncharacter: every font draws its missing-glyph box for it.
MISSING_GLYPH_PROBE = "\uffff"


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
        self._missing_glyph = self._glyph_signature(self.font, MISSING_GLYPH_PROBE)
        self._missing_chars: Dict[str, bool] = {}
        self._fallback_font = self._get_fallback_font(font_size)

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

    @staticmethod
    def _get_fallback_font(size: int) -> Optional[pygame.font.Font]:
        for font_name in FALLBACK_FONT_NAMES:
            path = pygame.font.match_font(font_name)
            if path:
                try:
                    return pygame.font.Font(path, size)
                except Exception:
                    continue
        return None

    @staticmethod
    def _glyph_signature(font: pygame.font.Font, char: str) -> Tuple[Tuple[int, int], bytes]:
        glyph = font.render(char, True, (255, 255, 255))
        # The glyph's shape is only in the alpha channel; RGB is the flat text color.
        return glyph.get_size(), pygame.image.tobytes(glyph, "RGBA")

    def get_char_surface(
        self, char: str, color: Tuple[int, int, int]
    ) -> pygame.Surface:
        """Get a cached surface for a character with given color."""
        cache_key = (char, color)
        surface = self._char_cache.get(cache_key)
        if surface is None:
            surface = self._char_cache[cache_key] = self._render_char(char, color)
        return surface

    def _render_char(self, char: str, color: Tuple[int, int, int]) -> pygame.Surface:
        if self._fallback_font is None or not self._is_missing_glyph(char):
            return self.font.render(char, True, color)
        glyph = self._fallback_font.render(char, True, color)
        cell = pygame.Surface((self.char_width, self.char_height), pygame.SRCALPHA)
        cell.blit(glyph, ((self.char_width - glyph.get_width()) // 2, (self.char_height - glyph.get_height()) // 2))
        return cell

    def _is_missing_glyph(self, char: str) -> bool:
        missing = self._missing_chars.get(char)
        if missing is None:
            missing = self._missing_chars[char] = self._glyph_signature(self.font, char) == self._missing_glyph
        return missing

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
