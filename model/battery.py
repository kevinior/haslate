"""Make local battery data available."""

import asyncio
from enum import Enum
import pathlib


UPDATE_PERIOD = 1  # Once per second

POWER_SUPPLY_PATH = pathlib.Path('/sys/class/power_supply')

_listeners = set()
_battery_update_task = None


class BatteryStatus(Enum):
    UNKNOWN = 'unknown'
    CHARGING = 'charging'
    DISCHARGING = 'discharging'
    NOT_CHARGING = 'not charging'
    FULL = 'full'


class BatteryState:
    """The current state of the battery."""
    def __init__(self, status: BatteryStatus, level: int) -> None:
        self._status = status
        self.level = level

    def __bool__(self):
        return self._status and self.status != BatteryStatus.UNKNOWN

    def __str__(self) -> str:
        return f'Battery: {self.level}% {self._status}'

    @property
    def is_charging(self):
        return self._status == BatteryStatus.CHARGING

    @property
    def status(self):
        if self._status == None:
            return BatteryStatus.UNKNOWN
        return self._status


class BatteryStateListener:
    """A class that can register as a listener for battery state."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def battery_state_updated(self, battery_state: BatteryState):
        """Called for registered listeners when the battery state
        has updated. Values will be None if the battery state is
        unknown."""
        pass


def add_listener(listener: BatteryStateListener):
    print(f'battery.add_listener:{listener}')
    if listener not in _listeners:
        _listeners.add(listener)
        ensure_task()

def remove_listener(listener: BatteryStateListener):
    if listener in _listeners:
        _listeners.remove(listener)

def update_listeners(battery_state: BatteryState):
    print(f'battery.update_listeners({battery_state})')
    for l in _listeners:
        l.battery_state_updated(battery_state)

def read_value(path: pathlib.Path) -> str:
    try:
        return path.read_text().strip().lower()
    except:
        return None

def find_battery_path() -> pathlib.Path:
    for ps in POWER_SUPPLY_PATH.iterdir():
        print(f'find_battery_path: trying {ps}')
        try:
            if not ps.is_dir():
                continue
            if read_value(ps / 'type') == 'battery':
                return ps
        except:
            pass
    return None

def get_battery_state(battery_path: pathlib.Path) -> BatteryState:
    if not battery_path:
        return BatteryState(BatteryStatus.UNKNOWN, None)
    print(f'get_battery_state: {battery_path}')
    status_text = read_value(battery_path / 'status')
    try:
        status = BatteryStatus(status_text)
    except ValueError:
        status = BatteryStatus.UNKNOWN
    level = read_value(battery_path / 'capacity')
    if level:
        level = int(level)
    return BatteryState(status, level)

async def battery_updater():
    battery_path = find_battery_path()
    while len(_listeners) > 0:
        update_listeners(get_battery_state(battery_path))
        await asyncio.sleep(UPDATE_PERIOD)

def ensure_task():
    """Make sure the battery update task is running."""
    if not _battery_update_task:
        asyncio.create_task(battery_updater())