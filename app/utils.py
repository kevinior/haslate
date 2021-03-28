"""Application utilities."""

import asyncio
from dataclasses import dataclass
import os
import pathlib
import platform
import typing

# Partition containing the FAT filesystem that can be mounted over USB.
EXT_PARTITION = '/dev/mmcblk0p3'
# Local mountpoint for that partition.
EXT_MOUNTPOINT = '/media/data'
# File containing USB MSC gadget state
MSC_STATE_FILE = pathlib.Path('/sys/class/udc/ci_hdrc.0/state')


def is_on_device() -> bool:
    """Returns True if running on a device, False if running on desktop."""
    return platform.machine() != 'x86_64'

def data_partition_is_mounted() -> bool:
    mounts = pathlib.Path('/proc/mounts').read_text()
    return mounts.find(EXT_MOUNTPOINT) >= 0

async def mount_data_partition() -> bool:
    if not is_on_device():
        return True
    if data_partition_is_mounted():
        print(f'{EXT_MOUNTPOINT} already mounted')
        return True
    proc = await asyncio.create_subprocess_shell(f'mount {EXT_MOUNTPOINT}')
    await proc.communicate()
    if proc.returncode != 0:
        print(f'mount {EXT_MOUNTPOINT} failed with {proc.returncode}')
        return False
    print(f'Mounted {EXT_MOUNTPOINT}')
    return True

async def unmount_data_partition() -> bool:
    if not is_on_device():
        return True
    if not data_partition_is_mounted():
        print(f'{EXT_MOUNTPOINT} is not mounted')
        return True
    proc = await asyncio.create_subprocess_shell(f'umount {EXT_MOUNTPOINT}')
    await proc.communicate()
    if proc.returncode != 0:
        print(f'umount {EXT_MOUNTPOINT} failed with {proc.returncode}')
        return False
    print(f'Unmounted {EXT_MOUNTPOINT}')
    return True


@dataclass
class WifiAp:
    inuse: typing.Union[bool, str]
    ssid: str
    mode: str
    chan: str
    rate: str
    signal: str
    bars: str
    security: str


async def get_wifi_aps() -> typing.List[WifiAp]:
    proc = await asyncio.create_subprocess_exec(
        '/usr/bin/nmcli', '--terse', 'device', 'wifi', 'list',
        stdout = asyncio.subprocess.PIPE
    )
    (stdout, _) = await proc.communicate()
    if proc.returncode != 0:
        print(f'nmcli (wifi list) failed with {proc.returncode}')
        return ([], None)
    result = []
    inuse_ap = None
    for line in stdout.decode().splitlines():
        ap = WifiAp(*line.split(':'))
        if ap.inuse == '*':
            ap.inuse = True
            inuse_ap = ap.ssid
        else:
            ap.inuse = False
        result.append(ap)
    return (result, inuse_ap)

def get_hostname() -> str:
    return pathlib.Path('/etc/hostname').read_text().strip()

async def update_hostname(new_hostname: str) -> None:
    if not is_on_device():
        return
    proc = await asyncio.create_subprocess_exec(
        '/usr/bin/nmcli', '--terse', 'general', 'hostname', new_hostname
    )
    await proc.communicate()
    if proc.returncode != 0:
        print(f'nmcli (set hostname) failed with {proc.returncode}')

async def update_wifi(wifi_config):
    if not is_on_device():
        return
    proc = await asyncio.create_subprocess_exec(
        '/usr/bin/nmcli', '--terse', 'device', 'wifi', 'connect',
        wifi_config.ssid.value, 'password', wifi_config.password.value
    )
    await proc.communicate()
    if proc.returncode != 0:
        print(f'nmcli (update wifi) failed with {proc.returncode}')

async def update_timezone(new_timezone: str) -> None:
    if not is_on_device:
        return
    proc = await asyncio.create_subprocess_shell(
        f'sudo /usr/bin/timedatectl set-timezone {new_timezone}'
    )
    await proc.communicate()
    if proc.returncode != 0:
        print(f'timedatectl failed with {proc.returncode}')

def reboot() -> None:
    if is_on_device():
        os.system('sudo /bin/systemctl reboot')
    else:
        pid = os.getpid()
        print(f'My PID is {pid}, sending SIGTERM...')
        os.system(f'kill -s TERM {pid}')

async def enable_mass_storage(usb_callback: typing.Callable[[bool], None]) -> bool:
    if is_on_device():
        proc = await asyncio.create_subprocess_shell(
            f'sudo /sbin/modprobe g_mass_storage file={EXT_PARTITION}'
        )
        await proc.communicate()
        if proc.returncode != 0:
            print(f'modprobe (MSC) failed with {proc.returncode}')
            return False
        asyncio.create_task(watch_mass_storage(usb_callback))
    else:
        print('enable_mass_storage')
    return True

async def disable_mass_storage() -> bool:
    if is_on_device():
        proc = await asyncio.create_subprocess_shell(
            f'sudo /sbin/rmmod g_mass_storage'
        )
        await proc.communicate()
        if proc.returncode != 0:
            print(f'rmmod (MSC) failed with {proc.returncode}')
            return False
    else:
        print('disable_mass_storage')
    return True

async def watch_mass_storage(usb_callback: typing.Callable[[bool], None]) -> None:
    print('Waiting for USB connect...')
    connected = False
    while not connected:
        if MSC_STATE_FILE.read_text().strip() == 'configured':
            connected = True
        await asyncio.sleep(1)
    usb_callback(True)
    print('USB connected, waiting for disconnect...')
    while connected:
        if MSC_STATE_FILE.read_text().strip() != 'configured':
            connected = False
        await asyncio.sleep(1)
    await disable_mass_storage()
    usb_callback(False)
