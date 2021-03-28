"""Home Assistant data types."""

import datetime


class State:
    """Represents the current state of an entity."""
    def __init__(self, entity_id: str, state: str,
                 last_updated: datetime.datetime,
                 last_changed: datetime.datetime,
                 domain: str = None,
                 object_id: str = None,
                 name: str = None,
                 attributes: dict = {},
                 **kwargs):
        self.entity_id = entity_id
        self.state = state
        self.last_updated = last_updated
        self.last_changed = last_changed
        self.domain = domain
        self.object_id = object_id,
        self.name = name
        self.attributes = attributes

    def __str__(self) -> str:
        return f'{self.entity_id}: {self.state} ({self.domain}) {self.attributes}'

    @classmethod
    def from_dict(cls, data: dict) -> 'State':
        """Parse an entity state from the parsed JSON representation.
        Returns None if data was invalid."""
        if not {'entity_id', 'state', 'last_updated', 'last_changed'}.issubset(data.keys()):
            print(f'State missing keys {",".join(data.keys())}')
            return None
        try:
            return cls(**data)
        except Exception as e:
            print(f'State exception: {e}')
            return None
