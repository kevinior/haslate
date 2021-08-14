"""Application configuration parsing."""

from __future__ import annotations

import enum
import pathlib
import re
import shutil
import typing
from typing import Sequence, Type, TypeVar

import ruamel.yaml

import app.utils
import model
import ui.config
import ui.widgets


# Configuration paths
CONFIG_FILE = pathlib.Path('config/haslate.yaml')
if app.utils.is_on_device():
    # The latest used configuration
    CUR_CONFIG_PATH = pathlib.Path.home() / 'haslate'
    # User-editable configuration
    EXT_CONFIG_PATH = pathlib.Path('/media/data')
else:
    CUR_CONFIG_PATH = pathlib.Path('.')
    EXT_CONFIG_PATH = pathlib.Path('/tmp/haslate')
CUR_CONFIG_FILE = CUR_CONFIG_PATH / CONFIG_FILE
EXT_CONFIG_FILE = EXT_CONFIG_PATH / CONFIG_FILE


T = TypeVar('T')

class ConfigItem:
    """Parent class for all configuration values and containers."""
    def __init__(self, parent: ConfigSection, name: str) -> None:
        self.parent = parent
        self.name = name
        self.path = self.get_path(parent, name)

    @classmethod
    def get_path(cls, parent: ConfigSection, name: str) -> str:
        if parent:
            return f'{parent.path}/{name}'
        else:
            return f'/{name}'

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, ConfigItem):
            return False
        return self.value == o.value

    @classmethod
    def from_data(cls: Type[T], parent: ConfigSection, name: str, data: typing.Dict) -> T:
        raise NotImplementedError


class BoolValue(ConfigItem):
    """A single boolean value in the configuration."""
    def __init__(self, parent: ConfigSection, name: str, value: bool) -> None:
        super().__init__(parent, name)
        self.value = value

    @classmethod
    def from_data(cls: Type[T], parent: ConfigSection, name: str, data: typing.Dict) -> T:
        if data and not isinstance(data, bool):
            raise TypeError(f'Not a bool: {data} @{cls.get_path(parent, name)}')
        return cls(parent, name, data)


class StringValue(ConfigItem):
    """A single string value in the configuration."""
    def __init__(self, parent: ConfigSection, name: str, value: str) -> None:
        super().__init__(parent, name)
        self.value = value

    @classmethod
    def from_data(cls: Type[T], parent: ConfigSection, name: str, data: typing.Dict) -> T:
        if data and not isinstance(data, str):
            raise TypeError(f'Not a string: {data} @{cls.get_path(parent, name)}')
        return cls(parent, name, data)


class IntPairValue(ConfigItem):
    """A pair of integers."""
    def __init__(self, parent: ConfigSection, name: str, first: int, second: int) -> None:
        super().__init__(parent, name)
        self.first = first
        self.second = second

    @classmethod
    def from_data(cls: Type[T], parent: ConfigSection, name: str, data: typing.Dict) -> T:
        if not isinstance(data, list):
            raise TypeError(f'Not a list: {data} @{cls.get_path(parent, name)}')
        if len(data) != 2 or not isinstance(data[0], int) or not isinstance(data[1], int):
            raise TypeError(f'Must contain two ints: {data} @{cls.get_path(parent, name)}')
        return cls(parent, name, data[0], data[1])

    @property
    def value(self) -> typing.Tuple[int, int]:
        return (self.first, self.second)


class DictValue(ConfigItem):
    """A free-form dict."""
    def __init__(self, parent: ConfigSection, name: str, value: dict) -> None:
        super().__init__(parent, name)
        self.value = value

    @classmethod
    def from_data(cls: Type[T], parent: ConfigSection, name: str, data: typing.Dict) -> T:
        if not isinstance(data, dict):
            raise TypeError(f'Not a dict: {data} @{cls.get_path(parent, name)}')
        return cls(parent, name, data)


class ConfigSection(ConfigItem):
    """A container in the configuration."""
    KEYS = {}
    DEFAULTS = {}

    def __init__(self, parent: ConfigSection, name: str) -> None:
        super().__init__(parent, name)
        self.contents = {}

    def __getattr__(self, name: str) -> ConfigItem:
        if name in self.contents:
            return self.contents[name]
        if name in self.DEFAULTS and name in self.KEYS:
            return self.KEYS[name].from_data(self, name, self.DEFAULTS[name])
        raise AttributeError(f'No {name} in {self.path}')

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, ConfigSection):
            return False
        return all([self.contents.get(k, None) == o.contents.get(k, None) for k in self.contents])

    @classmethod
    def from_data(cls: Type[T], parent: ConfigSection, name: str, data: typing.Dict) -> T:
        if not isinstance(data, dict):
            raise TypeError(f'Not a dict: {data} @{cls.get_path(parent, name)}')
        result = cls(parent, name)
        for (k, v) in data.items():
            if k in cls.KEYS:
                result.contents[k] = cls.KEYS[k].from_data(result, k, v)
        return result


class ArraySection(ConfigItem):
    """An array of configuration items."""
    VALUE_TYPE: ConfigItem = None

    def __init__(self, parent: ConfigSection, name: str) -> None:
        super().__init__(parent, name)
        self.contents = []

    def __iter__(self):
        return self.contents.__iter__()

    def __eq__(self, o: object) -> bool:
        return self.contents == o.contents

    @classmethod
    def from_data(cls: Type[T], parent: ConfigSection, name: str, data: typing.Dict) -> T:
        if not isinstance(data, list):
            raise TypeError(f'Not a list: {data} @{cls.get_path(parent, name)}')
        result = cls(parent, name)
        for (i, v) in enumerate(data):
            vi = cls.VALUE_TYPE.from_data(result, str(i), v)
            result.contents.append(vi)
        return result


class WifiConfigSection(ConfigSection):
    KEYS = {
        'ssid': StringValue,
        'password': StringValue,
        'force_wpa2': BoolValue
    }
    DEFAULTS = {
        'force_wpa2': False
    }


class SystemConfigSection(ConfigSection):
    KEYS = {
        'hostname': StringValue,
        'wifi': WifiConfigSection,
        'timezone': StringValue
    }
    DEFAULTS = {
        'timezone': 'UTC'
    }


class ItemSection(ConfigSection):
    KEYS = {
        'at': IntPairValue,
        'size': IntPairValue,
        'type': StringValue,
        'format': StringValue,
        'data': DictValue,
        'widget': DictValue
    }
    DEFAULTS = {
        'size': [1, 1],
        'format': None,
        'data': {},
        'widget': {}
    }

class PageItemsSection(ArraySection):
    VALUE_TYPE = ItemSection


class PageSection(ConfigSection):
    KEYS = {
        'name': StringValue,
        'items': PageItemsSection
    }

class PagesSection(ArraySection):
    VALUE_TYPE = PageSection


class ApplicationConfigSection(ConfigSection):
    KEYS = {
        'homeassistant_uri': StringValue,
        'homeassistant_token': StringValue,
        'grid': IntPairValue,
        'pages': PagesSection
    }

    def __init__(self, parent: ConfigSection, name: str) -> None:
        super().__init__(parent, name)
        self.layout = None
        self.layout_size = None

    def get_layout(self, screen_size: typing.Tuple[int, int]):
        if self.layout and self.layout_size == screen_size:
            return self.layout
        self.layout_size = screen_size
        self.layout = Parser.parse_config(self, screen_size)
        return self.layout


class Config(ConfigSection):
    """Top-level configuration."""
    KEYS = {
        'system': SystemConfigSection,
        'application': ApplicationConfigSection
    }


class Parser:
    _MODELS = {}

    _TYPE_TO_MODEL = {
        'datetime': model.DatetimeModel,
        'battery': model.BatteryModel,
        'wifi': model.WifiModel,
        'usb': model.UsbModel,
        'hass_switch': model.HassSwitchModel,
        'hass_light': model.HassSwitchModel,
        'hass_sensor': model.HassSensorModel,
        'hass_boolean': model.HassSwitchModel
    }

    _TYPE_TO_WIDGET = {
        'datetime': ui.widgets.DateTimeButton,
        'battery': ui.widgets.BatteryButton,
        'wifi': ui.widgets.WifiButton,
        'usb': ui.widgets.UsbButton,
        'hass_switch': ui.widgets.SwitchButton,
        'hass_light': ui.widgets.LightButton,
        'hass_sensor': ui.widgets.ValueButton,
        'hass_boolean': ui.widgets.SwitchButton,
        'action': ui.widgets.ActionButton,
        'empty': ui.widgets.Button
    }

    @staticmethod
    def _get_int_pair(object: typing.Dict, key: str) -> typing.Tuple[int]:
        """Get the value of key in object as an integer pair.
        The YAML value must be a sequence with two integer values.
        Returns None if the key does not exist or the value is
        invalid."""
        result = None
        try:
            result = tuple(object[key])
        except:
            return None
        if len(result) != 2:
            return None
        return result

    @staticmethod
    def _get_model(itemtype: str, data: dict) -> model.Model:
        """Look up the appropriate model type for `itemtype` and
        return the instance of the model."""
        if itemtype not in Parser._TYPE_TO_MODEL:
            return None
        key = Parser._TYPE_TO_MODEL[itemtype].get_key(itemtype, **data)
        if key not in Parser._MODELS:
            Parser._MODELS[key] = Parser._TYPE_TO_MODEL[itemtype](**data)
        return Parser._MODELS[key]

    @staticmethod
    def _get_widget(itemtype: str, format: typing.Optional[str]) -> ui.widgets.Widget:
        """Look up the appropriate widget type for `itemtype` and
        `format` and return an instance."""
        if itemtype not in Parser._TYPE_TO_WIDGET:
            return None
        return Parser._TYPE_TO_WIDGET[itemtype]

    @staticmethod
    def parse_config(config: ApplicationConfigSection, screen_size: typing.Tuple[int, int]) -> ui.config.Layout:
        """Parse the contents of the application config into a layout object."""
        layout = ui.config.Layout(screen_size, config.grid.first, config.grid.second)
        for p in config.pages:
            page = ui.config.Page(p.name)
            for i in p.items:
                at = i.at.value
                size = i.size.value
                model = Parser._get_model(i.type.value, i.data.value)
                rect = layout.get_rect(at[0], at[1], size[0], size[1])
                widget = Parser._get_widget(i.type.value, i.format.value)
                if widget is None:
                    print(f'Unknown type: {i.type.value}')
                    continue
                print(f'Creating {i.type.value}({widget}): {i.widget.value}')
                item = widget(format=i.format.value, rect=rect, model=model, **i.widget.value)
                page.add(item)
                item.model_updated()
                item.draw()
            layout.add_page(page)
        return layout


def parse_config_file(file: pathlib.Path) -> Config:
    y = ruamel.yaml.YAML(typ='safe')
    with file.open('r') as f:
        data = y.load(f)
    conf = Config.from_data(None, file.name, data)
    return conf


async def write_config_template(file: pathlib.Path) -> None:
    (wifi_aps, inuse) = await app.utils.get_wifi_aps()
    hostname = app.utils.get_hostname()
    vars = {
        'ACCESS_POINTS': [f'"{ap.ssid}"' for ap in wifi_aps],
        'HOSTNAME': hostname
    }
    if inuse:
        vars['WIFI_SSID'] = inuse
    template = (CUR_CONFIG_PATH / pathlib.Path('config/template.yaml')).read_text()
    file.parent.mkdir(parents=True, exist_ok=True)
    with file.open('w') as f:
        for line in template.splitlines():
            m = re.search(r'\$\$(.*)\$\$', line)
            if m:
                pattern = r'\$\$' + m.group(1) + r'\$\$'
                value = vars.get(m.group(1), m.group(1))
                if isinstance(value, str) or not isinstance(value, Sequence):
                    f.write(re.sub(pattern, value, line))
                    f.write('\n')
                else:
                    for v in value:
                        f.write(re.sub(pattern, v, line))
                        f.write('\n')
            else:
                f.write(line)
                f.write('\n')


async def apply_config(current: Config, ext: Config) -> bool:
    system_config_changed = False
    assert(ext)
    if not current:
        await app.utils.update_hostname(ext.system.hostname.value)
        await app.utils.update_wifi(ext.system.wifi)
        await app.utils.update_timezone(ext.system.timezone.value)
        system_config_changed = True
    else:
        if current.system.hostname != ext.system.hostname:
            await app.utils.update_hostname(ext.system.hostname.value)
            system_config_changed = True
        if current.system.wifi != ext.system.wifi:
            await app.utils.update_wifi(ext.system.wifi)
            system_config_changed = True
        if current.system.timezone != ext.system.timezone:
            await app.utils.update_timezone(ext.system.timezone.value)
    shutil.copy(EXT_CONFIG_FILE, CUR_CONFIG_FILE)
    return system_config_changed


def copy_cur_config_to_ext() -> None:
    EXT_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(CUR_CONFIG_FILE, EXT_CONFIG_FILE)


class ReadResult(enum.Enum):
    READ_OK = enum.auto()
    READ_ERROR = enum.auto()
    READ_NO_CONFIG = enum.auto()
    READ_NEED_REBOOT = enum.auto()


async def read() -> typing.Tuple[ReadResult, Config]:
    """Read the current and external config."""
    ext_config = None
    cur_config = None
    # Mount /media/data
    success = await app.utils.mount_data_partition()
    if not success:
        return ReadResult.READ_ERROR
    result = ReadResult.READ_OK
    if EXT_CONFIG_FILE.is_file():
        ext_config = parse_config_file(EXT_CONFIG_FILE)
    if CUR_CONFIG_FILE.is_file():
        cur_config = parse_config_file(CUR_CONFIG_FILE)
    # TODO annotate the ext file with errors?
    if not ext_config and not cur_config:
        await write_config_template(EXT_CONFIG_FILE)
        result = ReadResult.READ_NO_CONFIG
    elif not ext_config and cur_config:
        copy_cur_config_to_ext()
    elif ext_config != cur_config:
        if await apply_config(cur_config, ext_config):
            result = ReadResult.READ_NEED_REBOOT
        cur_config = parse_config_file(CUR_CONFIG_FILE)
    success = await app.utils.unmount_data_partition()
    if not success and result == ReadResult.READ_OK:
        return ReadResult.READ_ERROR
    return (result, cur_config)
