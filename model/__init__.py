"""Data model for the application."""

from collections import namedtuple
from datetime import date
import datetime
import re
import typing

import pygame

from hass.types import State
import model.battery
from model.battery import BatteryStateListener, BatteryState
import model.timedate
from model.timedate import DateTimeListener
import model.entitystore
from model.entitystore import EntityListenerMixin
import model.usb
from model.usb import UsbConnectionListener
import model.wifi
from model.wifi import WifiSignalListener


# Custom event types
MODEL_UPDATED = pygame.event.custom_type()
CALL_SERVICE = pygame.event.custom_type()


class Model:
    """Parent class of all model types."""
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        print('Model()')

    def updated(self):
        pygame.event.post(pygame.event.Event(MODEL_UPDATED, model=self))

    @classmethod
    def get_key(cls, prefix: str, **kwargs) -> str:
        """Return a key that is unique for all models representing
        the same data value. Defaults to returning prefix."""
        return prefix


class DatetimeModel(DateTimeListener, Model):
    def __init__(self):
        super().__init__()
        model.timedate.add_listener(self)

    def get_value(self) -> datetime.datetime:
        return datetime.datetime.now()

    def datetime_updated(self):
        self.updated()


class BatteryModel(BatteryStateListener, Model):
    def __init__(self):
        super().__init__()
        self.value = None
        model.battery.add_listener(self)

    def get_value(self) -> BatteryState:
        return self.value

    def battery_state_updated(self, battery_state: BatteryState):
        self.value = battery_state
        self.updated()


class WifiModel(WifiSignalListener, Model):
    def __init__(self):
        super().__init__()
        self.value = None
        model.wifi.add_listener(self)

    def wifi_signal_updated(self, link_quality_pct: float, signal_level: float):
        self.value = link_quality_pct
        self.updated()

    def get_value(self) -> float:
        return self.value


class UsbModel(UsbConnectionListener, Model):
    def __init__(self):
        super().__init__()
        self.value = False
        model.usb.add_listener(self)

    def usb_connection_updated(self, is_connected: bool):
        self.value = is_connected
        self.updated()

    def get_value(self) -> bool:
        return self.value


class HassModel(EntityListenerMixin, Model):
    """Represents a Home Assistant entity state."""
    def __init__(self, entity: str):
        super().__init__(entity=entity)
        self.entity = entity
        print(f'HassModel({entity})')
        model.entitystore.add_listener(self)

    @classmethod
    def get_key(cls, prefix: str, **kwargs) -> str:
        return f'{prefix}:{kwargs["entity"]}'

    def call_service(self, domain: str, service: str, service_data: dict):
        pygame.event.post(pygame.event.Event(CALL_SERVICE,
                                             domain=domain,
                                             service=service,
                                             service_data=service_data))


class HassSwitchModel(HassModel):
    """Represents a switch entity in Home Assistant."""
    def __init__(self, entity: str):
        super().__init__(entity=entity)
        print(f'HassSwitch({entity})')
        self.value = None
        m = re.match(r'(\w+)\.', self.entity)
        self.domain = m.group(1)

    def get_value(self) -> bool:
        return self.value

    def state_changed(self, new_state: State):
        super().state_changed(new_state)
        print(f'HassSwitch: new state: {new_state}')
        if new_state.state == 'on':
            self.value = True
        elif new_state.state == 'off':
            self.value = False
        else:
            self.value = None
        self.updated()

    def toggle(self):
        self.call_service(domain='homeassistant', service='toggle',
                          service_data={'entity_id': self.entity})


class HassSensorModel(HassModel):
    """Represents a sensor entity in Home Assistant."""
    def __init__(self, entity: str):
        super().__init__(entity=entity)
        print(f'HassSensor({entity}')
        self.value = None
        self.units = None

    def get_value(self) -> typing.Tuple[typing.Any, str]:
        """The return value is a tuple of the value and the units.
        If units is None then the value is a string, otherwise it's
        a float."""
        return (self.value, self.units)

    def state_changed(self, new_state: State):
        super().state_changed(new_state)
        print(f'HassSensor: new state: {new_state}')
        units = new_state.attributes.get('unit_of_measurement', None)
        if units:
            self.units = units
            self.value = float(new_state.state)
        else:
            self.value = new_state.state
        self.updated()
