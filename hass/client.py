#!/usr/bin/env python3

"""Client for the Home Assistant websocket API."""

import asyncio
import json
import typing

import websockets

from hass.types import State


COMMAND_TIMEOUT = 5


class ClientError(Exception):
    """All Home Assistant websocket client errors are subclasses of this."""


class AuthError(ClientError):
    """Authentication phase error."""


class CommandError(ClientError):
    """Error resulting from a sent command."""


class Message:
    def __init__(self, type: str = None, **kwargs):
        self.type = type
        self._data = kwargs

    def __getattr__(self, name: str) -> typing.Any:
        if name in self._data:
            return self._data[name]
        raise AttributeError(f'No {name} in message {self}')

    def __str__(self) -> str:
        d = dict(self._data)
        d['type'] = self.type
        return json.dumps(d)


class Command:
    def __init__(self, msg_type: str, id: int, msg_data: str):
        self.msg_type = msg_type
        self.id = id
        self.msg_data = msg_data
        self.event = asyncio.Event()
        self.status = None
        self.result = None

    def got_result(self, result: Message) -> typing.Any:
        """Sets the status and result attributes of the command."""
        if result.success != True:
            self.status = False
            self.result = f'{result.error["code"]}:{result.error["message"]}'
        else:
            self.status = True
            self.result = result.result
        self.event.set()


class Connection:
    def __init__(self, uri: str, access_token: str):
        self.uri = uri
        self.access_token = access_token
        self.msg_id = 1
        self.pending_commands = {}
        self.ws = None
        self.keep_running = True
        self.run_task = None
        self.state_changed_listener = None

    def _msg(self, msg_type: str, **kwargs) -> str:
        """Make a JSON message of type `msg_type` with data specified
        by the keyword arguments."""
        kwargs['type'] = msg_type
        if msg_type != 'auth':
            kwargs['id'] = self.msg_id
            self.msg_id += 1
        return json.dumps(kwargs)

    def _parse(self, data: typing.Optional[str]) -> typing.Optional[Message]:
        """Convert a received message into a Message object. If the
        data is None then None will be returned."""
        if data is None:
            return None
        return Message(**json.loads(data))

    async def _command(self, msg_type: str, **kwargs):
        """Send a command with data specified by the keyword arguments."""
        command = Command(msg_type, self.msg_id, self._msg(msg_type, **kwargs))
        await self.ws.send(command.msg_data)
        self.pending_commands[command.id] = command
        try:
            await asyncio.wait_for(command.event.wait(), timeout=COMMAND_TIMEOUT)
            result = (command.status, command.result)
        except asyncio.TimeoutError:
            result = None
        return result

    def _handle_event(self, event: dict):
        if event['event_type'] == 'state_changed':
            if self.state_changed_listener:
                s = State.from_dict(event['data']['new_state'])
                if s:
                    self.state_changed_listener(s)

    async def connect(self):
        """Connect to the server and handle authentication."""
        self.ws = await websockets.connect(self.uri)
        # Should be in the authentication phase
        message = self._parse(await self.ws.recv())
        if message.type != 'auth_required':
            raise AuthError(f'Got {message.type} in authentication phase')

        await self.ws.send(self._msg('auth', access_token=self.access_token))

        message = self._parse(await self.ws.recv())
        if message.type == 'auth_invalid':
            raise AuthError(f'Invalid auth: {message.message}')
        elif message.type != 'auth_ok':
            raise AuthError(f'Unexpected message in auth: {message}')
        # Now we're in the command phase
        self.run_task = asyncio.create_task(self.run())

    async def run(self):
        """Check for incoming websocket messages and process them."""
        while self.keep_running:
            try:
                data = await self.ws.recv()
                message = self._parse(data)
            except asyncio.TimeoutError:
                # We'll try again next time around
                pass
            except websockets.ConnectionClosed:
                self.keep_running = False
                break
            print(f'Got: {message.type}')
            if message.type == 'result':
                if message.id not in self.pending_commands:
                    print(f'Unexpected result for ID {message.id}')
                else:
                    command = self.pending_commands[message.id]
                    command.got_result(message)
            elif message.type == 'event':
                self._handle_event(message.event)
            else:
                print(f'Unknown message type: {message}')

    async def close(self):
        self.keep_running = False
        if self.ws:
            await self.ws.close()

    def is_running(self):
        return not self.run_task.done()

    async def get_states(self) -> typing.Optional[typing.List[State]]:
        """Fetch all the current states from Home Assistant.
        Returns None if the command failed."""
        (status, result) = await self._command('get_states')
        print(f'get_states -> ({status}, {len(result)})')
        return [State.from_dict(r) for r in result]

    async def subscribe_state_changed(self, listener: typing.Callable[[State], None]) -> bool:
        """Subscribes to state_changed events and returns True if the
        subscription succeeded."""
        print('subscribe_state_changed')
        (status, _) = await self._command('subscribe_events',
                                          event_type='state_changed')
        if status:
            self.state_changed_listener = listener
        return status

    async def call_service(self, domain: str, service: str, service_data: dict) -> bool:
        """Calls a Home Assistant service and returns True if the call
        succeeded."""
        print(f'call_service({domain}, {service}, {service_data}')
        (status, _) = await self._command('call_service',
                                          domain=domain,
                                          service=service,
                                          service_data=service_data)
        print(f'call_service({domain}, {service}, {service_data} -> {status}')
