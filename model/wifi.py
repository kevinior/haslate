"""Make local wifi signal strength available."""

import asyncio
import re
import typing


UPDATE_PERIOD = 1  # Once per second

_listeners = set()
_wifi_update_task = None


class WifiSignalListener:
    """A class that can register as a listener for wifi signal strength."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def wifi_signal_updated(self, link_quality_pct: float, signal_level: float):
        """Called for registered listeners when the wifi signal information
        has updated. Values will be None if the signal information is
        unknown."""
        pass


def add_listener(listener: WifiSignalListener):
    if listener not in _listeners:
        _listeners.add(listener)
        ensure_task()

def remove_listener(listener: WifiSignalListener):
    if listener in _listeners:
        _listeners.remove(listener)

def update_listeners(link_quality_pct: float, signal_level: float):
    for l in _listeners:
        l.wifi_signal_updated(link_quality_pct, signal_level)

def parse_iwconfig(data: str) -> typing.Tuple[float, float]:
    link_qual = None
    sig_lev = None
    for l in data.splitlines():
        m = re.match(r'.*Link Quality=(\d+)/(\d+)\s+Signal level=([0-9.-]+)',
                     l.decode('ascii'))
        if m:
            link_qual = int(m.group(1)) * 100 / int(m.group(2))
            sig_lev = float(m.group(3))
            break
    return (link_qual, sig_lev)

async def wifi_updater():
    while len(_listeners) > 0:
        proc = await asyncio.create_subprocess_exec(
            '/sbin/iwconfig', 'wlan0',
            stdout=asyncio.subprocess.PIPE)
        (stdout, _) = await proc.communicate()
        if proc.returncode != 0:
            # TODO try again later?
            update_listeners(None, None)
        else:
            # parse the output
            (link_qual, sig_lev) = parse_iwconfig(stdout)
            update_listeners(link_qual, sig_lev)
        await asyncio.sleep(UPDATE_PERIOD)

def ensure_task():
    """Make sure the wifi update task is running."""
    if not _wifi_update_task:
        asyncio.create_task(wifi_updater())