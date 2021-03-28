"""User interface utilities."""

from __future__ import annotations
import collections
import html.parser
import re
from typing import Callable, Iterable, List, Tuple, Optional, Sequence

import pygame
import pygame.draw
import pygame.freetype

import ui.resources


class Format:
    """The current text format."""
    def __init__(self, style: int, size: int, line_height: int, y_offset: int) -> None:
        self.style = style
        self.size = size
        self.line_height = line_height
        self.y_offset = y_offset

    def __repr__(self) -> str:
        return f'style:{self.style},size:{self.size},y_offset:{self.y_offset}'


def _format_b(fmt: Format) -> Format:
    return Format(fmt.style | pygame.freetype.STYLE_STRONG, fmt.size,
                  fmt.line_height, fmt.y_offset)

def _format_i(fmt: Format) -> Format:
    return Format(fmt.style | pygame.freetype.STYLE_OBLIQUE, fmt.size,
                  fmt.line_height, fmt.y_offset)

def _format_sup(fmt: Format) -> Format:
    return Format(fmt.style, fmt.size // 2, fmt.line_height, -(fmt.line_height * 3 // 8))

def _format_null(fmt: Format) -> Format:
    return fmt


FORMATTERS = {
    'b': _format_b,
    'i': _format_i,
    'sup': _format_sup
}


class FormattedRun:
    """A run of formatted text."""
    def __init__(self, text: str, formatters: Iterable[Callable]):
        self.text = text
        self.formatters = formatters

    def apply(self, fmt: Format) -> Format:
        for f in self.formatters:
            fmt = f(fmt)
        return fmt

    def __repr__(self) -> str:
        return f'"{self.text}"[{[f for f in self.formatters]}]'


class HtmlParser(html.parser.HTMLParser):
    def __init__(self, *, convert_charrefs: bool = True) -> None:
        super().__init__(convert_charrefs=convert_charrefs)
        self.runs = []
        self.current_text = ''
        self.stack = collections.deque()

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        formatter = FORMATTERS.get(tag, _format_null)
        self.runs.append(FormattedRun(self.current_text, self.stack.copy()))
        self.stack.append(formatter)
        self.current_text = ''

    def handle_endtag(self, tag: str) -> None:
        self.runs.append(FormattedRun(self.current_text, self.stack.copy()))
        self.current_text = ''
        self.stack.pop()  # check it's the tag we expected?

    def handle_data(self, data: str) -> None:
        self.current_text += data

    def close(self) -> None:
        super().close()
        self.runs.append(FormattedRun(self.current_text, self.stack.copy()))

    def get_runs(self) -> List[FormattedRun]:
        return self.runs


def draw_text(to_draw: Sequence[Tuple[str, int, str]]) -> Sequence[Tuple[pygame.Surface, pygame.Rect]]:
    """Draw lines of text, returning a list of tuples of Surfaces to be blitted
    on to the destination surface and their Rects."""
    cur_y = 0
    result = []
    for (style, size, line) in to_draw:
        font = ui.resources.get_font(style)
        (line_s, line_r) = font.render(line, fgcolor=pygame.Color('black'), size=size)
        line_r.topleft = (0, cur_y)
        cur_y += line_r.height
        result.append((line_s, line_r))
    return result


def split_formatted_runs(text: str) -> List[FormattedRun]:
    """Split HTML-ish formatted `text` into a list of FormattedRuns.
    For example, 'aaaa<sup>bbbb</sup>' will be split into a normally-formatted
    run 'aaaa' and a superscript run 'bbbb'."""
    p = HtmlParser()
    p.feed(text)
    p.close()
    return p.get_runs()


def format_wrap_text(width: int, height: int, text: str,
                     font: pygame.freetype.Font, base_size: int) -> Tuple[pygame.Surface, pygame.Rect]:
    """Wrap the text to fit into `width` by `height` creating a surface
    and rendering to it. Embedded HTML-ish formatting is allowed.
    Returns the surface and a Rect giving the size of the rendered text
    and the origin of the last line."""
    surface = pygame.Surface((width, height), flags=pygame.SRCALPHA)
    surface.fill(pygame.Color(255, 0, 255, 0))
    font_height = font.get_sized_height(base_size)
    line_height = font_height - 5
    x = 0
    y = line_height
    max_x = max_y = 0
    base_fmt = Format(font.style, base_size, font_height, 0)
    font.origin = True
    for run in split_formatted_runs(text):
        fmt = run.apply(base_fmt)
        for word in re.split(r'(\s+)', run.text):
            is_space = re.match(r'^\s+$', word)
            bounds = font.get_rect(word, style=fmt.style, size=fmt.size)
            if x > 0 and x + bounds.width + bounds.x >= width:
                if is_space:
                    continue
                x = 0
                y += line_height
            if y + bounds.height - bounds.y >= height:
                # Too much text, give up
                break
            font.render_to(surface, (x, y + fmt.y_offset),
                           None, style=fmt.style, size=fmt.size)
            x += bounds.width
            max_x = max(x, max_x)
            max_y = max(y + bounds.height - bounds.y, max_y)
    return (surface, pygame.Rect(0, y, max_x, max_y))