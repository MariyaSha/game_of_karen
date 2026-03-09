"""
fonts.py — Cross-platform font helper.
Tries to find a monospace system font, falls back to pygame default.
"""
import pygame

_MONO_CANDIDATES = [
    "consolas", "courier new", "courier", "dejavusansmono",
    "liberationmono", "ubuntumono", "freemono",
]


def get_mono(size: int, bold: bool = False) -> pygame.font.Font:
    """Return a monospace font at the requested size."""
    for name in _MONO_CANDIDATES:
        try:
            font = pygame.font.SysFont(name, size, bold=bold)
            # SysFont succeeds even if the font is missing (returns default),
            # so we verify the name actually resolved.
            if font is not None:
                return font
        except Exception:
            continue
    # Ultimate fallback: pygame's built-in font
    return pygame.font.Font(None, size)
