# Taika asynchronous client library for Python
#    Copyright (C) 2023 Taika Tech Oy
#    Author Jussi Hietanen
#
# This library is free software; you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free Software
# Foundation. See the GNU Lesser General Public License for more details.

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Flag, auto
from typing import Generic, TypeVar


class EventType(Flag):
    BASE_EVT = auto()
    RING_EVT = auto()
    RING_META_EVT = auto()
    RING_MOVE_EVT = auto()
    RING_ORIENTATION_EVT = auto()
    RING_TOUCHPAD_EVT = auto()
    RING_GESTURE_EVT = auto()
    LOCATOR_EVT = auto()
    LOCATOR_META_EVT = auto()


@dataclass
class Metadata:
    """
    Base Metadata class type.

    Each Event should implement its own Metadata type (if required) that
    derives from this class.
    """

    pass


@dataclass
class Event:
    """
    Event base class.

    Instances inherited from this class are given as parameters to the
    user-defined callbacks.
    """

    def __init__(
        self,
        event_type: EventType = EventType.BASE_EVT,
        metadata: Metadata | None = None,
    ) -> None:
        self._event_type = event_type
        self._metadata = metadata

    @property
    def event_type(self) -> EventType:
        """
        Get the EventType of this event instance.

        :return: The event type of this Event.
        :rtype: EventType
        """
        return self._event_type

    @property
    def metadata(self) -> Metadata | None:
        """
        Get the Metadata of this event instance.

        :return: The metadata of this Event.
        :rtype: Metadata
        """
        return self._metadata


EventBaseType = TypeVar("EventBaseType", bound=Event)


class EventGenerator(Generic[EventBaseType]):
    """
    EventGenerator is associated to a single EventType and generates events to
    all callbacks that have been registered to it. A class (Entity) that would
    like to raise events should implement its own EventType and Event class,
    and add an EventGenerator for it.
    """

    def __init__(
        self,
        event: type[EventBaseType],
        metadata: Metadata | None = None,
        global_event_cb: Callable[[Event], None] | None = None,
    ) -> None:
        """
        Initialize an EventGenerator instance.

        :param event: the event class of which instances this generator should
            raise.
        :type event: Event
        :param metadata: metadata attached to all raised events from this
            generator. Defaults to `None`.
        :type metadata: Metadata | None

        """
        self._callbacks: list[Callable[[EventBaseType], Awaitable[None]]] = []
        self._event: type[EventBaseType] = event
        self._metadata = metadata
        self._global_evt_cb = global_event_cb

    @property
    def get_event_type(self) -> EventType:
        """
        Get the event type of this generator's associated event.

        :return: EventType of this generator's Event class.
        :rtype: EventType
        """
        return self._event().event_type

    def add_callback(
        self, callback: Callable[[EventBaseType], Awaitable[None]]
    ) -> None:
        """
        Add a callback function to this generator. When this event is
        triggered, all callbacks added to it will be called with this
        generator's event.

        :param callback: callback function to add. This function is called when
            this generator is triggered. The callback function *must* be async.
        :type callback: Callable[[EventBaseType], Awaitable[None]]
        """
        self._callbacks.append(callback)

    def remove_callback(
        self, callback: Callable[[EventBaseType], Awaitable[None]]
    ) -> bool:
        """
        Remove a previously added callback function from this generator. After
        removal, the callback will not be called anymore if this generator is
        triggered.

        :param callback: callback function to remove. The callback function
            *must* be async function which was previously added to this
            generator.
        :type callback: Callable[[EventBaseType], Awaitable[None]]
        :return: returns True if the callback was found and removed, False
            otherwise.
        :rtype: bool
        """
        try:
            self._callbacks.remove(callback)
            return True
        except ValueError:
            return False

    async def trigger(self, **kwargs) -> None:
        """
        Trigger this generator and call all callbacks added via
        :meth:`EventGenerator.add_callback`.

        :param ``**kwargs``: keyword arguments to construct the associated Event.
            **These *must* conform to the required **kwargs of the said Event**
        """
        for callback in self._callbacks:
            await callback(self._event(metadata=self._metadata, **kwargs))

        if self._global_evt_cb:
            self._global_evt_cb(self._event(metadata=self._metadata, **kwargs))
