from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from .const import MQTT_LOCATOR_ANGLE_TOPIC, MQTT_LOCATOR_ORIENTATION_TOPIC
from .entity import EntityType, TaikaEntity
from .events import Event, EventBaseType, EventGenerator, EventType, Metadata
from .mqtthandler import TaikaMQTTHandler
from .utils import Vector3, unify_mac


@dataclass
class LocatorMetadata(Metadata):
    """Represent locator metadata."""

    mac: str
    position: Vector3
    orientation: Vector3


class LocatorEvent(Event):
    """Base class for all ring events."""

    def __init__(self, event_type: EventType = EventType.RING_EVT, **kwargs) -> None:
        super().__init__(event_type=event_type, **kwargs)


class LocatorMetadataEvent(LocatorEvent):
    """Event class for ring's Metadata-related events."""

    def __init__(self, metadata: Metadata | None = None) -> None:
        super().__init__(event_type=EventType.RING_META_EVT, metadata=metadata)


class Locator(TaikaMQTTHandler, TaikaEntity):
    def __init__(
        self,
        mac: str,
        position: Vector3,
        orientation: Vector3,
        global_event_cb: Callable[[Event], None] | None = None,
    ) -> None:
        super().__init__(entity_type=EntityType.LOCATOR)
        self._metadata: LocatorMetadata = LocatorMetadata(
            mac=mac, position=position, orientation=orientation
        )
        self._meta_evt_gen: EventGenerator = EventGenerator(
            event=LocatorMetadataEvent,
            metadata=self._metadata,
            global_event_cb=global_event_cb,
        )
        self._unified_mac: str = unify_mac(mac)
        self._mqtt_handlers[
            f"{MQTT_LOCATOR_ANGLE_TOPIC}{self._unified_mac}/+"
        ] = self._update_angle_mqtt
        self._mqtt_handlers[
            f"{MQTT_LOCATOR_ORIENTATION_TOPIC}{self._unified_mac}/+"
        ] = self._update_orientation_mqtt

    @property
    def metadata(self) -> LocatorMetadata:
        """Return this Locator's metadata."""
        return self._metadata

    async def _update_angle_mqtt(self, data: dict[str, Any]) -> None:
        pass

    async def _update_orientation_mqtt(self, data: dict[str, Any]) -> None:
        pass

    async def handle_metadata_update(self) -> None:
        await self._meta_evt_gen.trigger()

    async def register_event_cb(
        self,
        event_type: EventType,
        callback: Callable[[EventBaseType], Awaitable[None]],
    ) -> None:
        match event_type:
            case EventType.LOCATOR_EVT:
                self._meta_evt_gen.add_callback(callback)
            case EventType.LOCATOR_META_EVT:
                self._meta_evt_gen.add_callback(callback)
            case _:
                print("Invalid event for locators!")

    async def remove_event_cb(
        self,
        event_type: EventType,
        callback: Callable[[EventBaseType], Awaitable[None]],
    ) -> bool:
        ret = False
        match event_type:
            case EventType.LOCATOR_EVT:
                ret = self._meta_evt_gen.remove_callback(callback)
                if not all([ret]):
                    print("Not all generators were found!")
                    ret = False
            case EventType.LOCATOR_META_EVT:
                ret = self._meta_evt_gen.remove_callback(callback)
            case _:
                print("Invalid event for locators!")
        return ret
