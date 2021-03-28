"""User interface configuration classes."""

import typing

import pygame

import ui.widgets


class Page:
    def __init__(self, name: str):
        """A page that can be filled with widgets."""
        self.name = name
        self.widgets = []
        self.group = pygame.sprite.RenderUpdates()

    def add(self, widget: ui.widgets.Widget):
        self.widgets.append(widget)
        self.group.add(widget)

    def update(self, *args, **kwargs):
        self.group.update(*args, **kwargs)

    def draw(self, surface: pygame.Surface):
        return self.group.draw(surface)


class Layout:
    """A layout that can contain pages with widgets arranged on a
    grid `across` cells across by `down` cells down, drawn
    on a screen of size `size` pixels (width, height)."""

    def __init__(self, size: typing.Tuple, across: int, down: int):
        self.across = across
        self.down = down
        self.pages = []
        self.col_px = size[0] // self.across
        self.row_px = size[1] // self.down
        self.x_pad = (size[0] - (self.col_px * self.across)) // 2
        self.y_pad = (size[1] - (self.row_px * self.down)) // 2
        self.current_page = None

    def add_page(self, page: Page):
        self.pages.append(page)
        if not self.current_page:
            self.current_page = page

    def get_rect(self, col: int, row: int, width: int, height: int) -> pygame.Rect:
        """Get the rectangle describing the position and size of the
        widget."""
        return pygame.Rect((col - 1) * self.col_px + self.x_pad,
                           (row - 1) * self.row_px + self.y_pad,
                           width * self.col_px,
                           height * self.row_px)

    def update(self, *args, **kwargs):
        if self.current_page:
            self.current_page.update(*args, **kwargs)

    def draw(self, surface: pygame.Surface):
        if self.current_page:
            return self.current_page.draw(surface)
        return []
