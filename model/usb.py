"""Make USB connection state available."""

_listeners = set()


class UsbConnectionListener:
    """A class that can register as a listener for USB
    (dis)connection events."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def usb_connection_updated(self, is_connected: bool):
        """Called for registered listeners when the USB connection state
        has changed."""
        pass

def add_listener(listener: UsbConnectionListener):
    if listener not in _listeners:
        _listeners.add(listener)

def remove_listener(listener: UsbConnectionListener):
    if listener in _listeners:
        _listeners.remove(listener)

def update_listeners(is_connected: bool):
    for l in _listeners:
        l.usb_connection_updated(is_connected)
