========
Examples
========

Even though the "examples" folder in the git repository of the library offer
some ready-written examples, this page explains in a walk-through fashion
the development of a simple user application using Taika AIO client library
for python.

To include Taika AIO client library in a project::

    import aiotaika

To connect to a Taika CentralUnit, you should write code like this in async
context::

    async with TaikaClient(host="myhostname",
                           username="myusername",
                           password="mypassword"
                          ) as taika:
        # Now do something with the library...

If you're not a fan of `async with`, you can also write in following fashion::

    taika = TaikaClient(host="myhostname",
                        username="myusername",
                        password="mypassword"
                        )
    await taika.initialize()
    # now do something with the library ...
    await taika.close()

Now, you want to fetch some information from the system. Let's fetch all the
rings in the system and print out metadata of the first ring::

    rings = taika.rings
    print(rings.items()[0].metadata)

You might also want to subscribe to some events that happen in the system.
Let's write a snippet that subscribes to same ring's RingMoveEvents. We need
a couple of imports first::

    from aiotaika.events import EventType
    from aiotaika.ring import RingMoveEvent

First, we implement a callback that will be called whenever a RingMoveEvent
is triggered for our chosen ring. This event must conform to the event
callback type (Callable[[Event], Awaitable[None]])::

    async def move_evt_cb(event: RingMoveEvent) -> None:
        # print out the position if it's y component is over 1.0
        if event.position.y > 1.0:
            print(event.position)

Now, we tell the client context manager to trigger this callback when our
chosen ring moves::

    rings.items()[0].register_event_cb(EventType.RING_MOVE_EVT, move_evt_cb)

And here's the complete code example. As you can see, with just a couple of
lines of code, we can follow the position of our chosen ring in our Python
program!::

    import aiotaika
    from aiotaika.events import EventType
    from aiotaika.ring import RingMoveEvent

    async def cb(event: RingMoveEvent) -> None:
        # print out the position if it's y component is over 1.0
        if event.position.y > 1.0:
            print(event.position)

    async def main() -> None:
        async with TaikaClient(host="myhostname",
                            username="myusername",
                            password="mypassword"
                            ) as taika:
            rings = taika.rings
            rings.items()[0].register_event_cb(EventType.RING_MOVE_EVT, cb)
            asyncio.sleep(5)


    asyncio.run(main())
