"""Stores Home Assistant entity information and sends out updates
to registered listeners."""

from hass.types import State

_listeners = {}


class EntityListenerMixin:
    """A class that can register as a listener for entity events."""
    def __init__(self, entity: str, **kwargs):
        super().__init__(**kwargs)
        print(f'EntityListenerMixin({entity})')
        self.entity = entity

    def state_changed(self, new_state: State):
        """Called for registered listeners when the entity state
        has changed."""
        pass


def add_listener(listener: EntityListenerMixin):
    entity = listener.entity
    print(f'Adding listener for {entity}: {listener}')
    if entity not in _listeners:
        _listeners[entity] = set()
    _listeners[entity].add(listener)

def remove_listener(listener: EntityListenerMixin):
    entity = listener.entity
    if entity in _listeners:
        if listener in _listeners[entity]:
            _listeners.remove(entity)

def update_state(new_state: State):
    """Provide a list of updated state data. If new_state is None
    it will be ignored."""
    if not new_state:
        return
    print(f'update_state: {new_state.entity_id}')
    entity = new_state.entity_id
    if entity in _listeners:
        for l in _listeners[entity]:
            print(f'update_state: calling {l}')
            l.state_changed(new_state)
