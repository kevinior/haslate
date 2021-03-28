"""Material design icons."""

import importlib.resources
import json
import typing

import pygame.freetype

import ui.data.fonts

_FONT_MAP = {
    'normal': 'Roboto-Regular.ttf',
    'black': 'Roboto-Black.ttf',
    'italic': 'Roboto-Italic.ttf'
}

def _read_metadata() -> typing.Dict[str, int]:
    # Read the MDI metadata file and store just enough information to
    # look up code points from names.
    result = {}
    with importlib.resources.open_binary(ui.data.fonts, 'MDI_meta.json') as metafile:
        meta = json.load(metafile)
        for icon in meta:
            result[icon['name']] = chr(int(icon['codepoint'], 16))
    return result

def _load_font(filename: str) -> pygame.freetype.Font:
    fontfile = importlib.resources.open_binary(ui.data.fonts, filename)
    return pygame.freetype.Font(fontfile)

def _load_icon_font() -> pygame.freetype.Font:
    return _load_font('MaterialDesignIconsDesktop.ttf')

def _load_text_fonts() -> typing.Dict[str, pygame.freetype.Font]:
    result = {}
    for (style, filename) in _FONT_MAP.items():
        font = _load_font(filename)
        font.kerning = True
        font.origin = True
        result[style] = font
    return result

def get_icon(name: str) -> str:
    """Given an MDI icon name, return a string containing the character."""
    return _ICON_LOOKUP.get(name, _UNKNOWN_ICON)

def get_icon_font() -> pygame.freetype.Font:
    return _ICON_FONT

def get_font(style: typing.Union[str, pygame.freetype.Font]) -> pygame.freetype.Font:
    if isinstance(style, pygame.freetype.Font):
        return style
    return _TEXT_FONTS.get(style, _TEXT_FONTS['normal'])

pygame.init()
pygame.freetype.set_default_resolution(300)
_ICON_LOOKUP = _read_metadata()
_UNKNOWN_ICON = '\ufffd'
_ICON_FONT = _load_icon_font()
_TEXT_FONTS = _load_text_fonts()
_TEXT_FONTS['icon'] = _ICON_FONT
