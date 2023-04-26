# aiotaika

[![Documentation Status](https://readthedocs.org/projects/aiotaika-python/badge/?version=stable)](https://aiotaika-python.readthedocs.io/en/stable/?badge=stable) [![Latest PyPI release](https://img.shields.io/pypi/v/aiotaika)](https://pypi.org/project/aiotaika/) ![Supported Python versions](https://img.shields.io/pypi/pyversions/aiotaika.svg)

## Taika asynchronous client library for Python

This library provides a very intuitive API for developers to easily create Python applications for Taika Tech's Spatial User Interface (SUI). With SUI, you can program actions to your physical environment, which are triggered based on location, orientation, and/or gesture data coming from a Taika Ring or Taika Tag.

You can find aiotaika's documentation from [Read the Docs](https://aiotaika-python.readthedocs.io/).

## Basic Examples

For more examples, see [examples](/examples) folder of the repository.

### Callback Example

In this example, we subscribe to move events and gesture events of ring ID 3.
In the callback function, we track the latest position and when a gesture event
happens, we print out which gesture was made with the latest location data.

With callbacks one can register one or more callbacks to a single callback function.
However, the Event type must be a parent class of all incoming event objects in that
callback function. Here `RingGestureEvent` and `RingMoveEvent` inherit from
`RingEvent`.

```
import asyncio

from aiotaika import TaikaClient
from aiotaika.events import EventType
from aiotaika.ring import RingGestureEvent, RingMoveEvent

Vector3 last_position

async def my_callback(event: RingEvent) -> None:
    if isinstance(event, RingMoveEvent):
        last_position = event.position
    elif isinstance(event, RingGestureEvent):
        print(f"{event.gesture} in position {last_position}")


async def main() -> None:
    async with TaikaClient(
        host="127.0.0.1", username="root", password=""
    ) as taika:
        rings = taika.rings
        for key, ring in rings.items():
            print("{}: {}".format(key, ring.metadata))
        await rings[3].register_event_cb(EventType.RING_MOVE_EVT, my_callback)
        await rings[3].register_event_cb(EventType.RING_GESTURE_EVT, my_callback)
        await asyncio.sleep(5)


try:
    asyncio.run(main())
except KeyboardInterrupt:
    pass
```

### Asynchronous Generator Example (no callbacks!)

This example shows simply how all the incoming events can be handled via the `events`
AsyncGenerator of the `TaikaClient` class. In this example, we simply print out a
ring's name and position when a `RingMoveEvent` happens.

```
import asyncio

from aiotaika import TaikaClient
from aiotaika.ring import RingMoveEvent

async def main() -> None:
    async with TaikaClient(
        host="127.0.0.1", username="root", password=""
    ) as taika:
        async with taika.events() as events:
            async for event in events:
                if isinstance(event, RingMoveEvent):
                    print(f"Ring {event.metadata.name} position:")
                    print(f"x: {event.position.x}, z: {event.position.z}")
                    print(f"height: {event.position.y}")


try:
    asyncio.run(main())
except KeyboardInterrupt:
    pass
```

## Requirements:

### Hardware

- Taika Development Kit

### Software

_Note: these should be automatically satisfied if `aiotaika` is installed via `pip`._

You can find precise version requirements from [pyproject.toml](/pyproject.toml)

- `Python`
- `asyncio-mqtt`
- `aiomysql`
