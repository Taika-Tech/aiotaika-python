# Taika asynchronous client library for Python
#    Copyright (C) 2023 Taika Tech Oy
#    Author Jussi Hietanen
#
# This library is free software; you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free Software
# Foundation. See the GNU Lesser General Public License for more details.

import asyncio
import logging
from asyncio import AbstractEventLoop
from collections.abc import Callable
from contextlib import asynccontextmanager
from types import TracebackType
from typing import AsyncGenerator, Dict, Optional, Type

import aiomysql
import asyncio_mqtt as aiomqtt
from asyncio_mqtt import MqttError

from .const import (
    DB_LOCATOR_ID,
    DB_LOCATOR_LAST_DB_UPDATE,
    DB_LOCATOR_MAC,
    DB_LOCATOR_ORIENTATION_KEYS,
    DB_LOCATOR_POSITION_KEYS,
    DB_RING_ID,
    DB_RING_LAST_DB_UPDATE,
    DB_RING_MAC,
    DB_RING_NAME,
    DB_TABLE_LOCATORS,
    DB_TABLE_PORTALS,
    DB_TABLE_RINGS,
    DEFAULT_DB_PORT,
    DEFAULT_MQTT_PORT,
    MQTT_SUBSCRIBE_ALL,
)
from .events import Event
from .locator import Locator, LocatorMetadata
from .mqtthandler import TaikaMQTTHandler
from .ring import Ring, RingMetadata
from .utils import Vector3

MARIADB_REFRESH_INTERVAL = 3
MQTT_RECONNECT_INTERVAL = 5

_LOGGER = logging.getLogger(__name__)


class TaikaClient(TaikaMQTTHandler):
    """Control and retrieve data from a Taika Centralunit."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        loop: AbstractEventLoop | None = None,
        mqtt_port: int | None = None,
        db_port: int | None = None,
    ) -> None:
        """
        Initialize a Taika AIO client instance.

        *Note: It is required to call* :meth:`TaikaClient.initialize`
        *before working with this instance.*

        :param host: the hostname or IP address of the centralunit
        :type host: str
        :param username: the set username of the centralunit
        :type username: str
        :param password: the set password of the centralunit
        :type password: str
        :param loop: asyncio event loop to use, defaults to
            asyncio.get_running_loop()
        :type loop: AbstractEventLoop, optional
        :param mqtt_port: port to use for MQTT connection, defaults to
            :const:`.const.DEFAULT_MQTT_PORT`
        :type mqtt_port: int, optional
        :param db_port: port to use for database connection, defaults to
            :const:`.const.DEFAULT_DB_PORT`
        :type db_port: int, optional

        """
        super().__init__()
        self._host = host
        self._username = username
        self._password = password
        if loop is None:
            loop = asyncio.get_running_loop()
        self._loop = loop
        if not isinstance(mqtt_port, int):
            mqtt_port = DEFAULT_MQTT_PORT
        self._mqtt_port = mqtt_port
        if not isinstance(db_port, int):
            db_port = DEFAULT_DB_PORT
        self._db_port = db_port
        self._running: bool = False
        self._async_running: asyncio.Future[int | None] = asyncio.Future()
        self._db_pool: aiomysql.Pool | None = None
        self._mqtt_client: aiomqtt.Client | None = None
        self._rings: Dict[int, Ring] = {}
        self._locators: Dict[int, Locator] = {}
        self._portals: Dict[int, object] | None = None
        self._async_generator_callbacks: list[Callable[[Event], None]] = []

    def _on_event(self, event: Event) -> None:
        for callback in self._async_generator_callbacks:
            callback(event)

    async def list_rings(self) -> Dict[int, RingMetadata]:
        """
        Return a mutable Dict with rings' RingMetadata dataclass structures.

        The dicitionary keys are unique IDs for the rings for this Taika
        CentralUnit, and these keys should persist between system restarts or
        updates.
        """
        ret = {}
        for id, ring in self._rings.items():
            ret[id] = ring.metadata
        return ret

    async def list_locators(self) -> Dict[int, LocatorMetadata]:
        """
        Return a mutable Dict with locators' LocatorMetadata dataclass structures.

        The dicitionary keys are unique IDs for the locators for this Taika
        CentralUnit, and these keys should persist between system restarts or
        updates.
        """
        ret = {}
        for id, locator in self._locators.items():
            ret[id] = locator.metadata
        return ret

    @property
    def rings(self) -> Dict[int, Ring]:
        """
        Return an immutable Dict with Ring structures.

        The dicitionary keys are unique IDs for the rings for this Taika
        CentralUnit, and these keys should persist between system restarts or
        updates.
        """
        return self._rings

    @property
    def locators(self) -> Dict[int, Locator]:
        """
        Return an immutable Dict with Locator structures.

        The dicitionary keys are unique IDs for the locators for this Taika
        CentralUnit, and these keys should persist between system restarts or
        updates.
        """
        return self._locators

    def _get_callback_generator(
        self,
        *,
        queue_class: type[asyncio.Queue[Event]] = asyncio.Queue,
        queue_maxsize: int = 0,
    ) -> tuple[Callable[[Event], None], AsyncGenerator[Event, None]]:
        events: asyncio.Queue[Event] = queue_class(maxsize=queue_maxsize)

        def _callback(event: Event) -> None:
            """Put the new message in the queue."""
            try:
                events.put_nowait(event)
            except asyncio.QueueFull:
                # This event will be discarded. TODO: issue a warning here?
                pass

        async def _generator() -> AsyncGenerator[Event, None]:
            """Forward all events from the message queue."""
            while True:
                # Wait until either event is received or TaikaClient is closed
                get: asyncio.Task[Event] = self._loop.create_task(events.get())
                try:
                    done, _ = await asyncio.wait(
                        (get, self._async_running), return_when=asyncio.FIRST_COMPLETED
                    )
                except asyncio.CancelledError:
                    # Cancel io, return forward exception
                    get.cancel()
                    raise
                if get in done:
                    # Forward the event to async generator
                    yield get.result()
                else:
                    # Something bad happened, raise runtime error
                    get.cancel()
                    raise RuntimeError("Error forwarding an event to the generator")

        return _callback, _generator()

    @asynccontextmanager
    async def events(
        self,
        *,
        queue_class: type[asyncio.Queue[Event]] = asyncio.Queue,
        queue_maxsize: int = 100,
    ) -> AsyncGenerator[AsyncGenerator[Event, None], None]:
        """Return async generator of incoming events.

        Use queue_maxsize to modify the maximum size of thequeue size. If queue is
        full, the to-be-added event will be discarded quietly.
        """
        callback, generator = self._get_callback_generator(
            queue_class=queue_class, queue_maxsize=queue_maxsize
        )

        try:
            # Append callbacks to call when an event is received
            self._async_generator_callbacks.append(callback)
            # Back to the caller, async
            yield generator
        finally:
            # Exiting the with statement's scope
            self._async_generator_callbacks.remove(callback)

    async def initialize(self) -> None:
        """
        Initialize the connection to the centralunit, initialize
        all metadata for this Centralunit context.

        *Note: Not required to call when using* `async with ...`
        (see :meth:`TaikaClient.__aenter__`)
        """
        if not isinstance(self._loop, AbstractEventLoop):
            raise RuntimeError("Taika client event loop is not set!")

        self._running = True

        # Connect to MQTT
        def mqtt_return_callback(_fut) -> None:
            if self._running is True:
                raise RuntimeError("Unhandled return of Taika MQTT client!")

        fut_mqtt = self._loop.create_task(self._mqtt_listen())

        fut_mqtt.add_done_callback(mqtt_return_callback)

        # Connect to MariaDB
        await self._mariadb_init_pool()

        # Initialize metadata from mariadb
        await self._mariadb_update_metadata()

        def mariadb_return_callback(_fut) -> None:
            if self._running is True:
                raise RuntimeError("Unhandled return of Taika MariaDB client!")

        fut_mariadb = self._loop.create_task(self._mariadb_update_loop())

        fut_mariadb.add_done_callback(mariadb_return_callback)

    async def close(self) -> None:
        """
        Close the connection and clean up this context manager.

        *Note: Not required to call when using* `async with ...`
        (see :meth:`TaikaClient.__aexit__`)
        """
        self._running = False

        # Wait for MySQL connection to close gracefully
        if isinstance(self._db_pool, aiomysql.Pool):
            self._db_pool.close()
            await self._db_pool.wait_closed()
        # Wait for MQTT connection to close gracefully
        if isinstance(self._mqtt_client, aiomqtt.Client):
            await self._mqtt_client.disconnect()

    async def __aenter__(self) -> "TaikaClient":
        """
        Initialize and return a Taika AIO client context manager.

        Calls :meth:`TaikaClient.initialize` to initialize the context manager.
        """
        await self.initialize()
        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> Optional[bool]:
        """
        Exit context manager and clean up.

        Calls :meth:`TaikaClient.close`.
        """
        await self.close()
        if exc_val:
            raise exc_val
        return True

    async def _update_portals(self, portals) -> None:
        # Pass this function until Portal class is defined
        return

    async def _update_rings(self, rings) -> None:
        for ring in rings:
            if ring[DB_RING_ID] not in self._rings:
                # Add new ring to the Dictionary, update its callbacks if required
                new_ring = Ring(
                    mac=ring[DB_RING_MAC],
                    name=ring[DB_RING_NAME],
                    global_event_cb=self._on_event,
                )
                new_ring.last_updated = ring[DB_RING_LAST_DB_UPDATE]
                # TODO: add callbacks!
                self._rings[ring[DB_RING_ID]] = new_ring
                # TODO: trigger callbacks!
            else:
                # Update existing ring in the Dictionary if required
                if (
                    self._rings[ring[DB_RING_ID]].last_updated
                    != ring[DB_RING_LAST_DB_UPDATE]
                ):
                    self._rings[ring[DB_RING_ID]].last_updated = ring[
                        DB_RING_LAST_DB_UPDATE
                    ]
                    await self._rings[ring[DB_RING_ID]].handle_metadata_update()
        return

    async def _update_locators(self, locators) -> None:
        for locator in locators:
            if locator[DB_LOCATOR_ID] not in self._locators:
                # Add new locator to the Dictionary, update its callbacks if required
                new_locator = Locator(
                    mac=locator[DB_LOCATOR_MAC],
                    position=Vector3.from_dict(
                        data=locator, keys=DB_LOCATOR_POSITION_KEYS
                    ),
                    orientation=Vector3.from_dict(
                        data=locator, keys=DB_LOCATOR_ORIENTATION_KEYS
                    ),
                    global_event_cb=self._on_event,
                )
                new_locator.last_updated = locator[DB_LOCATOR_LAST_DB_UPDATE]
                # TODO: add callbacks!
                self._locators[locator[DB_LOCATOR_ID]] = new_locator
                # TODO: trigger callbacks!
            else:
                # Update existing ring in the Dictionary if required
                if (
                    self._locators[locator[DB_LOCATOR_ID]].last_updated
                    != locator[DB_LOCATOR_LAST_DB_UPDATE]
                ):
                    self._locators[locator[DB_LOCATOR_ID]].last_updated = locator[
                        DB_LOCATOR_LAST_DB_UPDATE
                    ]
                    await self._locators[
                        locator[DB_LOCATOR_ID]
                    ].handle_metadata_update()
        return

    async def _mqtt_listen(self) -> None:
        """Start listening for new MQTT messages."""
        while self._running:
            try:
                async with aiomqtt.Client(
                    hostname=self._host,
                    port=self._mqtt_port,
                    protocol=aiomqtt.ProtocolVersion.V5,
                ) as self._mqtt_client:
                    await self._mqtt_client.subscribe(MQTT_SUBSCRIBE_ALL)
                    async with self._mqtt_client.messages() as messages:
                        async for message in messages:
                            if isinstance(message.payload, (bytes, str)):
                                for ring in self._rings.values():
                                    await ring.handle_mqtt_update(
                                        message.topic, message.payload
                                    )
            except MqttError:
                if self._running is False:
                    return
                _LOGGER.warning("Connection to Taika MQTT broker failed - retrying")
                await asyncio.sleep(MQTT_RECONNECT_INTERVAL)
            except Exception as ex:
                _LOGGER.warning(f"Unexpected exception happened: {ex=}, {type(ex)=}")

    async def _mariadb_init_pool(self) -> None:
        """(re)Initialize connection to the MariaDB server."""
        self._db_pool = await aiomysql.create_pool(
            host=self._host,
            port=self._db_port,
            user=self._username,
            password=self._password,
            db="taika",
            loop=self._loop,
            autocommit=False,
        )

    async def _mariadb_update_metadata(self) -> None:
        if not isinstance(self._db_pool, aiomysql.Pool):
            return
        try:
            async with self._db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    query = "SELECT * FROM "
                    await cur.execute(query + DB_TABLE_PORTALS)
                    res = await cur.fetchall()
                    await self._update_portals(res)
                    await cur.execute(query + DB_TABLE_RINGS)
                    res = await cur.fetchall()
                    await self._update_rings(res)
                    await cur.execute(query + DB_TABLE_LOCATORS)
                    res = await cur.fetchall()
                    await self._update_locators(res)
        except Exception as ex:
            print(ex)

    async def _mariadb_update_loop(self) -> None:
        while self._running:
            await self._mariadb_update_metadata()
            await asyncio.sleep(MARIADB_REFRESH_INTERVAL)
        return
