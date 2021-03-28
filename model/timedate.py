"""Allow listening for changes to the date/time."""


_listeners = set()


class DateTimeListener:
    """A class that can register as a listener for datetime events."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def datetime_updated(self):
        """Called for registered listeners when the date/time has changed."""
        pass

def add_listener(listener: DateTimeListener):
    if listener not in _listeners:
        _listeners.add(listener)

def remove_listener(listener: DateTimeListener):
    if listener in _listeners:
        _listeners.remove(listener)

def update_listeners():
    for l in _listeners:
        l.datetime_updated()
