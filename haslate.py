#!/usr/bin/env python3

"""HAslate - E-ink Home Assistant Dashboard."""

import argparse
import asyncio
from dataclasses import dataclass

import model
import pathlib
import typing

import pygame
import pygame.event
import pygame.freetype
import pygame.key
import pygame.time

import app.config
import app.utils
import hass.client
import hass.types
import model.entitystore
import model.timedate
import model.usb
import ui.config
import ui.resources
import ui.utils


# The Kobo Clara HD screen is 1448x1072
SCREEN_SIZE = (1448, 1072)
# Make it easier to find resources
APP_DIR = pathlib.Path(__file__).absolute().parent
RESOURCE_DIR = APP_DIR / 'data'
FONT_DIR = RESOURCE_DIR / 'fonts'
THEME_DIR = RESOURCE_DIR / 'themes'
# Frames per second for pygame, no point setting it too high
# since the screen update time is ~1s.
FRAME_RATE = 2

# Custom events
SCENE_CHANGE = pygame.event.custom_type()
USB_CONNECTED = pygame.event.custom_type()
SECONDS_TICK = pygame.event.custom_type()

# pygame doesn't seem to recognise the power key, so we have to use
# the scancode
SCANCODE_POWER = 102


class Clock:
    """An asyncio-compatible version of pygame.time.Clock."""
    def __init__(self):
        self.last_tick_ms = pygame.time.get_ticks() or 0

    async def tick(self, fps=0):
        if fps <= 0:
            return

        frame_time_ms = (1.0 / fps) * 1000
        now = pygame.time.get_ticks()
        ms_since_last = now - self.last_tick_ms
        delay_s = (frame_time_ms - ms_since_last) / 1000.0
        if delay_s < 0:
            delay_s = 0
        await asyncio.sleep(delay_s)


@dataclass
class State:
    """Shared state for the application."""
    config: app.config.Config = None
    layout: ui.config.Layout = None
    exit_task: asyncio.Task = None


class Scene:
    def __init__(self, state: State) -> None:
        self.state = state

    """The main application state and display."""
    def enter(self):
        """Called when the scene is about to be displayed."""
        pass

    def exit(self):
        """Called when the scene is about to be replaced by another.
        This should clean up any resources that the scene is using."""
        pass

    def update(self, event_list: typing.Iterable) -> None:
        """Called with a list of pygame events."""
        pass

    def draw(self, surface: pygame.Surface) -> typing.List[pygame.Rect]:
        """Called to draw the UI onto the provided surface.
        Returns a list of changed rectangles suitable for passing
        to pygame.display.update."""
        return []

class CheckConfig(Scene):
    def __init__(self, state: State) -> None:
        super().__init__(state)
        self.drawn = False
        self.config_loader = None

    def enter(self):
        self.config_loader = asyncio.create_task(app.config.read())

    def update(self, event_list: typing.Iterable) -> None:
        if self.config_loader.done():
            (result, conf) = self.config_loader.result()
            self.state.config = conf
            new_scene = ConfigError
            if result == app.config.ReadResult.READ_OK:
                self.state.layout = conf.application.get_layout(SCREEN_SIZE)
                new_scene = MainUi
            elif result == app.config.ReadResult.READ_NEED_REBOOT:
                new_scene = Reboot
            elif result == app.config.ReadResult.READ_NO_CONFIG:
                new_scene = NoConfig
            pygame.event.post(pygame.event.Event(SCENE_CHANGE, new_scene=new_scene))

    def draw(self, surface: pygame.Surface) -> typing.List[pygame.Rect]:
        if self.drawn:
            return []
        else:
            self.drawn = True
            return [surface.blit(text_s, text_r.topleft) for (text_s, text_r) in ui.utils.draw_text([
                ('black', 48, 'Initialising')
            ])]


class ConfigError(Scene):
    def __init__(self, state: State) -> None:
        super().__init__(state)
        self.drawn = False

    def enter(self):
        asyncio.create_task(app.utils.enable_mass_storage(usb_connected))

    def draw(self, surface: pygame.Surface) -> typing.List[pygame.Rect]:
        if self.drawn:
            return []
        else:
            self.drawn = True
            return [surface.blit(text_s, text_r.topleft) for (text_s, text_r) in ui.utils.draw_text([
                ('black', 48, 'Configuration error')
            ])]


class Reboot(Scene):
    def __init__(self, state: State) -> None:
        super().__init__(state)
        self.drawn = False

    def draw(self, surface: pygame.Surface) -> typing.List[pygame.Rect]:
        if self.drawn:
            return []
        else:
            self.drawn = True
            return [surface.blit(text_s, text_r.topleft) for (text_s, text_r) in ui.utils.draw_text([
                ('black', 24, 'System configuration updated'),
                ('normal', 16, 'Tap to reboot')
            ])]

    def update(self, event_list: typing.Iterable) -> None:
        for event in event_list:
            if event.type == pygame.MOUSEBUTTONDOWN:
                app.utils.reboot()


class NoConfig(Scene):
    def __init__(self, state: State) -> None:
        super().__init__(state)
        self.drawn = False

    def enter(self):
        asyncio.create_task(app.utils.enable_mass_storage(usb_connected))

    def draw(self, surface: pygame.Surface) -> typing.List[pygame.Rect]:
        if self.drawn:
            return []
        else:
            self.drawn = True
            self.drawn = True
            return [surface.blit(text_s, text_r.topleft) for (text_s, text_r) in ui.utils.draw_text([
                ('black', 24, 'No configuration found'),
                ('normal', 16, f'Connect USB and edit {app.config.CONFIG_FILE}')
            ])]


class MainUi(Scene):
    def __init__(self, state: State) -> None:
        super().__init__(state)
        self.conn = hass.client.Connection(
            self.state.config.application.homeassistant_uri.value,
            self.state.config.application.homeassistant_token.value)
        self.connecting = None

    async def connect_and_setup(self):
        await self.conn.connect()
        states = await self.conn.get_states()
        if states:
            for s in states:
                model.entitystore.update_state(s)
        status = await self.conn.subscribe_state_changed(state_changed)
        if not status:
            raise ConnectionError('subscribe_state_changed failed')

    async def close_connection(self):
        if self.conn:
            await self.conn.close()
        self.conn = None

    def enter(self):
        asyncio.create_task(app.utils.enable_mass_storage(usb_connected))

    def exit(self):
        self.state.exit_task = asyncio.create_task(self.close_connection())

    def update(self, event_list: typing.Iterable) -> None:
        if self.connecting:
            if self.connecting.done():
                if self.connecting.exception():
                    # Connection setup failed
                    asyncio.create_task(self.conn.close())
                    self.connecting = None
                elif not self.conn.is_running():
                    # Disconnect? Try to reopen the connection
                    conn = hass.client.Connection(
                        self.state.config.application.homeassistant_uri.value,
                        self.state.config.application.homeassistant_token.value)
                    self.connecting = asyncio.create_task(self.connect_and_setup())
        else:
            self.connecting = asyncio.create_task(self.connect_and_setup())
        for event in event_list:
            if event.type == model.CALL_SERVICE:
                asyncio.create_task(
                    self.conn.call_service(event.domain, event.service,
                                      event.service_data)
                )
            elif event.type == SECONDS_TICK:
                model.timedate.update_listeners()
        self.state.layout.update(event_list)

    def draw(self, surface: pygame.Surface) -> typing.List[pygame.Rect]:
        return self.state.layout.draw(surface)


def state_changed(new_state: hass.types.State):
    model.entitystore.update_state(new_state)

def usb_connected(is_connected: bool) -> None:
    model.usb.update_listeners(is_connected)
    pygame.event.post(pygame.event.Event(USB_CONNECTED, is_connected=is_connected))


async def main(args):
    state = State()
    scene = None

    pygame.init()
    pygame.display.set_caption('Kobo testing')
    flags = 0
    if not args.window:
        print('Trying to run fullscreen')
        flags |= pygame.FULLSCREEN | pygame.NOFRAME
    top_surface = pygame.display.set_mode(SCREEN_SIZE, flags=flags)

    def switch_scene(new_scene_class: typing.Type[Scene]) -> Scene:
        new_scene = new_scene_class(state)
        if scene:
            scene.exit()
        top_surface.fill(pygame.Color('white'))
        pygame.display.update()
        new_scene.enter()
        return new_scene

    scene = switch_scene(CheckConfig)

    clock = Clock()
    is_running = True

    # Post an event every second
    pygame.time.set_timer(SECONDS_TICK, 1000)

    while is_running:
        await clock.tick(FRAME_RATE)
        event_list = pygame.event.get()
        for event in event_list:
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and
                                             event.scancode == SCANCODE_POWER):
                scene.exit()
                is_running = False
            elif event.type == SCENE_CHANGE:
                scene = switch_scene(event.new_scene)
            if event.type == USB_CONNECTED and not event.is_connected:
                scene = switch_scene(CheckConfig)
        scene.update(event_list)
        pygame.display.update(scene.draw(top_surface))

        # TODO: update the datetime models

    if state.exit_task:
        await state.exit_task

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--window', help='Run in a window, default is fullscreen',
                        action='store_true')
    args = parser.parse_args()

    asyncio.run(main(args), debug=True)
