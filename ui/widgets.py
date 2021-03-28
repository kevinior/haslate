"""User interface widgets."""

from model.battery import BatteryState
from typing import Optional

import pygame

import model
import ui.resources
import ui.utils

# How many pixels to pad the inside of widgets.
PADDING = 5

# If set to True then debug lines will be drawn in widgets
WIDGET_DEBUG = False

class Widget(pygame.sprite.Sprite):
    """Parent class of the user interface widgets."""
    def __init__(self, rect: pygame.Rect,
                 model: model.Model,
                 background: pygame.Color):
        super().__init__()
        self.rect = rect
        self.model = model
        self.draw_rect = self.rect.copy()
        self.draw_rect.topleft = (0, 0)
        self.content_rect = self.draw_rect.inflate(-PADDING * 2, -PADDING * 2)
        self.background = background
        self.image = pygame.Surface(self.rect.size)
        self.is_updated = False

    def draw(self) -> pygame.Rect:
        """Returns the remaining rect for subclasses to draw on."""
        self.image.fill(self.background)
        if WIDGET_DEBUG:
            pygame.draw.rect(self.image, pygame.Color('gray50'),
                            self.content_rect, 1)
            pygame.draw.line(self.image, pygame.Color('gray50'),
                             self.content_rect.midtop,
                             self.content_rect.midbottom)
            pygame.draw.line(self.image, pygame.Color('gray50'),
                             self.content_rect.midleft,
                             self.content_rect.midright)
        return self.content_rect

    def update(self, event_list):
        for event in event_list:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.rect.collidepoint(event.pos):
                    self.clicked()
            elif event.type == model.MODEL_UPDATED:
                if event.model == self.model:
                    self.model_updated()
                    self.draw()

    def clicked(self):
        pass

    def model_updated(self):
        pass



class Button(Widget):
    """A button with optional label and value."""
    def __init__(self, format: str, rect: pygame.Rect, model: model.Model,
                 label: Optional[str] = None, value: Optional[str] = None,
                 icon: Optional[str] = None,
                 background: Optional[pygame.Color] = pygame.Color('white'),
                 label_font: Optional[str] = 'normal', label_size: Optional[int] = 12,
                 label_color: Optional[pygame.Color] = pygame.Color('black'),
                 value_font: Optional[str] = 'normal', value_size: Optional[int] = 24,
                 value_color: Optional[pygame.Color] = pygame.Color('black'),
                 icon_size: Optional[int] = 24,
                 icon_color: Optional[pygame.Color] = pygame.Color('black'),
                 border_color: Optional[pygame.Color] = pygame.Color('black'),
                 border_width: Optional[int] = 2,
                 shift_value: bool = False):
        super().__init__(rect, model, background)
        self.format = format
        self.label = label
        self.value = value
        self.icon = icon
        self.border_color = border_color
        self.border_width = border_width
        self.label_font = ui.resources.get_font(label_font)
        self.label_size = label_size
        self.label_color = label_color
        self.value_font = ui.resources.get_font(value_font)
        self.value_size = value_size
        self.value_color = value_color
        self.shift_value = shift_value
        self.icon_size = icon_size
        self.icon_color = icon_color

    def draw(self):
        dest_rect = super().draw()
        if self.border_width > 0:
            pygame.draw.rect(self.image, self.border_color,
                            self.draw_rect, self.border_width)
        label_height = self.label_font.get_sized_height(self.label_size)
        if self.label:
            ls, lr = ui.utils.format_wrap_text(
                dest_rect.width, dest_rect.height, self.label,
                self.label_font, self.label_size
            )
            if WIDGET_DEBUG:
                pygame.draw.circle(ls, pygame.Color('red'), lr.topleft, 2)
            label_height = lr.height
            lr.centerx = self.content_rect.centerx
            lr.top = self.content_rect.top
            self.image.blit(ls, lr)
            if self.shift_value:
                dest_rect = dest_rect.move(0, label_height).clip(self.content_rect)
            if WIDGET_DEBUG:
                pygame.draw.rect(self.image, pygame.Color('blue'), lr, 1)
                pygame.draw.rect(self.image, pygame.Color('green'), dest_rect, 1)
                pygame.draw.line(self.image, pygame.Color('magenta'),
                                dest_rect.midtop,
                                dest_rect.midbottom)
                pygame.draw.line(self.image, pygame.Color('magenta'),
                                dest_rect.midleft,
                                dest_rect.midright)
        if self.value:
            ics, icr = ui.utils.format_wrap_text(
                dest_rect.width, dest_rect.height, self.value,
                self.value_font, self.value_size
            )
            baseline_offset = icr.top
            ascent = self.value_font.get_sized_ascender(self.value_size)
            if WIDGET_DEBUG:
                pygame.draw.circle(ics, pygame.Color('red'), icr.topleft, 2)
            icr.centerx = dest_rect.centerx
            icr.top = dest_rect.centery - baseline_offset + (ascent // 2)
            self.image.blit(ics, icr)
            if WIDGET_DEBUG:
                pygame.draw.rect(self.image, pygame.Color('blue'), icr, 1)
        elif self.icon:
            ics, icr = ui.resources.get_icon_font().render(
                ui.resources.get_icon(self.icon),
                fgcolor=self.icon_color, size=self.icon_size)
            baseline_offset = icr.top
            ascent = ui.resources.get_icon_font().get_sized_ascender(self.icon_size)
            if WIDGET_DEBUG:
                pygame.draw.circle(ics, pygame.Color('red'), icr.topleft, 2)
            icr.centerx = dest_rect.centerx
            icr.top = dest_rect.centery - baseline_offset + (ascent // 2)
            self.image.blit(ics, icr)
            if WIDGET_DEBUG:
                pygame.draw.rect(self.image, pygame.Color('blue'), icr, 1)


class DateTimeButton(Button):
    """A button that can display a datetime.datetime in a given
    format."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.label_format = None
        if '\n' in self.format:
            self.label_format, self.format = self.format.split('\n')

    def model_updated(self):
        super().model_updated()
        dt = self.model.get_value()
        self.value = dt.strftime(self.format)
        if self.label_format:
            self.label = dt.strftime(self.label_format)


class ActionButton(Button):
    """A button that can perform a local action."""
    def __init__(self, action: str, **kwargs):
        super().__init__(**kwargs)
        self.action = action

    def clicked(self):
        super().clicked()
        if self.action == 'quit':
            pygame.event.post(pygame.event.Event(pygame.QUIT))


class BatteryButton(Button):
    """A button that can show the battery state as an icon or
    percentage."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.format != 'icon' and self.format != 'percent':
            raise ValueError('Invalid format {}'.format(self.format))

    def model_updated(self):
        super().model_updated()
        if self.format == 'icon':
            self.icon = self._format_icon(self.model.get_value())
        elif self.format == 'percent':
            self.value = self._format_percent(self.model.get_value())

    def _format_icon(self, value: BatteryState) -> str:
        if not value:
            return 'battery-unknown'
        level = (value.level // 10) * 10
        if level < 10:
            if value.is_charging:
                return 'battery-charging-outline'
            else:
                return 'battery-alert'
        charging = ''
        if value.is_charging:
            charging = '-charging'
        if level >= 100:
            icon = f'battery{charging:s}'
        else:
            icon = f'battery{charging:s}-{level:d}'
        return icon

    def _format_percent(self, value: BatteryState) -> str:
        if not value:
            return '???%'
        charging = ''
        if value.is_charging:
            charging = '+'
        return f'{charging}{value.level:d}%'


class WifiButton(Button):
    """A button that can show the current wifi signal strength as an
    icon."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def model_updated(self):
        super().model_updated()
        self.icon = self._format_icon(self.model.get_value())

    def _format_icon(self, value: float) -> str:
        if value is None:
            return 'wifi-strength-off-outline'
        level = int(value // 20)
        if level < 1:
            return 'wifi-strength-outline'
        if level > 4:
            level = 4
        return 'wifi-strength-{:d}'.format(level)


class UsbButton(Button):
    """A button that shows the current USB connection state as an icon."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def model_updated(self):
        super().model_updated()
        self.icon = self._format_icon(self.model.get_value())

    def _format_icon(self, value: bool) -> str:
        if value:
            return 'usb-port'
        else:
            return 'cable-data'

class SwitchButton(Button):
    """A button that can show the current state of a switch as an icon."""
    def __init__(self, on_icon: str = 'electric-switch-closed',
                 off_icon: str = 'electric_switch', **kwargs):
        super().__init__(**kwargs)
        self.on_icon = on_icon
        self.off_icon = off_icon
        self.off_label = self.on_label = self.label
        if self.label and '\n' in self.label:
            self.off_label, self.on_label = self.label.split('\n')

    def model_updated(self):
        super().model_updated()
        self.label = self._format_label(self.model.get_value())
        self.icon = self._format_icon(self.model.get_value())

    def _format_label(self, value) -> str:
        if value is None:
            return f'{self.off_label}?{self.on_label}?'
        elif value:
            return self.on_label
        else:
            return self.off_label

    def _format_icon(self, value) -> str:
        if value is None:
            return 'timelapse'
        elif value:
            return self.on_icon
        else:
            return self.off_icon

    def clicked(self):
        """Change to the opposite state."""
        super().clicked()
        if self.model.get_value() is not None:
            self.model.toggle()


class LightButton(Button):
    """A button for controlling a light. Very similar to SwitchButton
    but the icon changes colour depending on the value."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.icon is None:
            self.icon = 'lightbulb'
        self.conf_icon = self.icon

    def model_updated(self):
        super().model_updated()
        self.icon = self._format_icon(self.model.get_value())
        if self.model.get_value():
            self.icon_color = pygame.Color('black')
        else:
            self.icon_color = pygame.Color('gray50')

    def _format_icon(self, value) -> str:
        if value is None:
            return 'timelapse'
        else:
            return self.conf_icon

    def clicked(self):
        """Change to the opposite state."""
        super().clicked()
        if self.model.get_value() is not None:
            self.model.toggle()


class ValueButton(Button):
    """A button that shows a value with an optional label.
    The formatting will use Python's string.format method with
    the keyword arguments v for the value and u for the units."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.format is None:
            self.format = '{v}'

    def model_updated(self):
        super().model_updated()
        (value, units) = self.model.get_value()
        if units:
            try:
                self.value = self.format.format(v=value,
                                                u=units)
            except ValueError:
                self.value = '!fmt'
        else:
            self.value = value
