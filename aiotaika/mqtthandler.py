# Taika asynchronous client library for Python
#    Copyright (C) 2023 Taika Tech Oy
#    Author Jussi Hietanen
#
# This library is free software; you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free Software
# Foundation. See the GNU Lesser General Public License for more details.

"""Abstract base class for Taika MQTT Handler."""

import json
from collections.abc import Awaitable, Callable
from typing import Any, Dict

from asyncio_mqtt import Topic


class TaikaMQTTHandler:
    """
    TaikMQTTHandler should be inherited if a class should do something with MQTT
    traffic.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._mqtt_handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[None]]] = {}

    async def handle_mqtt_update(self, topic: Topic, message: str | bytes) -> None:
        for wildcard, updater in self._mqtt_handlers.items():
            if topic.matches(wildcard):
                await updater(json.loads(message))
