from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Type

from .const import (
    MQTT_GESTURE_KEY,
    MQTT_IMU_QUAT_KEYS,
    MQTT_MAGN_VECT_KEYS,
    MQTT_MIMU_QUAT_KEYS,
    MQTT_POS_KEYS,
    MQTT_RING_GESTURE_TOPIC,
    MQTT_RING_ORIENTATION_TOPIC,
    MQTT_RING_POSITION_TOPIC,
)
from .entity import EntityType, TaikaEntity
from .events import Event, EventBaseType, EventGenerator, EventType, Metadata
from .mqtthandler import TaikaMQTTHandler
from .utils import Quaternion, Vector3, unify_mac


class Gesture(Enum):
    NOELE = 0
    GESTURE1 = 1
    GESTURE2 = 2
    GESTURE3 = 3
    GESTURE4 = 4
    GESTURE5 = 5
    GESTURE6 = 6
    GESTURE7 = 7

    @classmethod
    def _missing_(cls: Type, value: object) -> Any:
        return super()._missing_(value)


@dataclass
class RingMetadata(Metadata):
    """Represent ring metadata."""

    mac: str
    name: str


class RingEvent(Event):
    """Base class for all ring events."""

    def __init__(self, event_type: EventType = EventType.RING_EVT, **kwargs) -> None:
        super().__init__(event_type=event_type, **kwargs)


class RingMetadataEvent(RingEvent):
    """Event class for ring's Metadata-related events."""

    def __init__(self, metadata: Metadata | None = None) -> None:
        super().__init__(event_type=EventType.RING_META_EVT, metadata=metadata)


class RingMoveEvent(RingEvent):
    """Event class for ring's movement-related events."""

    def __init__(self, metadata: Metadata | None = None, **kwargs) -> None:
        super().__init__(event_type=EventType.RING_MOVE_EVT, metadata=metadata)
        if not all(key in kwargs.keys() for key in ["position"]):
            raise Exception("position update fail")
        self._position: Vector3 = kwargs["position"]

    @property
    def position(self) -> Vector3:
        """Return the updated position associated with this event."""
        return self._position


class RingOrientationEvent(RingEvent):
    """Event class for ring's orientation-related events."""

    def __init__(self, metadata: Metadata | None = None, **kwargs) -> None:
        super().__init__(event_type=EventType.RING_ORIENTATION_EVT, metadata=metadata)
        if not any(key in kwargs for key in ["imu", "mimu", "magn"]):
            raise Exception("orientation update fail")
        self._imu: Quaternion = kwargs["imu"]
        self._mimu: Quaternion = kwargs["mimu"]
        self._magn: Vector3 = kwargs["magn"]

    @property
    def mimu(self) -> Quaternion:
        """
        Get the MIMU (Magnetometer + IMU) data associated to this event.

        :return: Orientation data calculated with magnetometer and IMU.
        :rtype: Quaternion
        """
        return self._mimu

    @property
    def imu(self) -> Quaternion:
        """
        Get the IMU (Inertial Measurement Unit) data associated to this event.

        :return: Orientation data calculated with IMU.
        :rtype: Quaternion
        """
        return self._imu

    @property
    def magn(self) -> Vector3:
        """
        Get the magnetometer data associated to this event.

        :return: Magnetometer vector
        :rtype: Vector3
        """
        return self._magn


class RingTouchpadEvent(RingEvent):
    """Event class for ring's touchpad-related events."""

    def __init__(self, metadata: Metadata | None = None, **kwargs) -> None:
        super().__init__(event_type=EventType.RING_TOUCHPAD_EVT, metadata=metadata)


class RingGestureEvent(RingEvent):
    """Event class for ring's gesture-related events."""

    def __init__(self, metadata: Metadata | None = None, **kwargs) -> None:
        super().__init__(event_type=EventType.RING_GESTURE_EVT, metadata=metadata)
        if not all(key in kwargs.keys() for key in ["gesture"]):
            raise Exception("gesture event creation fail")
        self._gesture: Gesture = kwargs["gesture"]

    @property
    def gesture(self) -> Gesture:
        """Return the gesture associated with this event."""
        return self._gesture


class Ring(TaikaMQTTHandler, TaikaEntity):
    def __init__(
        self,
        mac: str,
        name: str,
        global_event_cb: Callable[[Event], None] | None = None,
    ) -> None:
        super().__init__(entity_type=EntityType.RING)
        # Ring's data variables available outside via properties
        self._position: Vector3 | None = None
        self._imu: Quaternion | None = None
        self._mimu: Quaternion | None = None
        self._magn: Vector3 | None = None
        self._battery: int = 0
        self._gesture: Gesture = Gesture.NOELE
        self._metadata: RingMetadata = RingMetadata(mac=mac, name=name)
        # Internal methods & private variables
        self._meta_evt_gen: EventGenerator = EventGenerator(
            event=RingMetadataEvent,
            metadata=self._metadata,
            global_event_cb=global_event_cb,
        )
        self._move_evt_gen: EventGenerator = EventGenerator(
            event=RingMoveEvent,
            metadata=self._metadata,
            global_event_cb=global_event_cb,
        )
        self._orientation_evt_gen: EventGenerator = EventGenerator(
            event=RingOrientationEvent,
            metadata=self._metadata,
            global_event_cb=global_event_cb,
        )
        self._touchpad_evt_gen: EventGenerator = EventGenerator(
            event=RingTouchpadEvent,
            metadata=self._metadata,
            global_event_cb=global_event_cb,
        )
        self._gesture_evt_gen: EventGenerator = EventGenerator(
            event=RingGestureEvent,
            metadata=self._metadata,
            global_event_cb=global_event_cb,
        )
        self._unified_mac: str = unify_mac(mac)
        self._mqtt_handlers[
            f"{MQTT_RING_POSITION_TOPIC}{self._unified_mac}"
        ] = self._update_position_mqtt
        self._mqtt_handlers[
            f"{MQTT_RING_ORIENTATION_TOPIC}{self._unified_mac}"
        ] = self._update_orientation_mqtt
        self._mqtt_handlers[
            f"{MQTT_RING_GESTURE_TOPIC}{self._unified_mac}"
        ] = self._update_gesture_mqtt

    @property
    def position(self) -> Vector3 | None:
        """Return the latest position of this Ring."""
        return self._position

    @property
    def imu(self) -> Quaternion | None:
        """Return the latest IMU quaternion of this Ring."""
        return self._imu

    @property
    def mimu(self) -> Quaternion | None:
        """Return the latest MIMU quaternion of this Ring."""
        return self._mimu

    @property
    def magnetometer(self) -> Vector3 | None:
        """Return the latest magnetometer vector of this Ring."""
        return self._magn

    @property
    def battery(self) -> int:
        """Return the latest battery reading of this Ring."""
        return self._battery

    @property
    def gesture(self) -> Gesture:
        """Return the latest gesture recognized for this Ring."""
        return self._gesture

    @property
    def metadata(self) -> RingMetadata:
        """Return this Ring's metadata."""
        return self._metadata

    def _update_position(self, position: Vector3) -> None:
        self._position = position

    def _update_imu(
        self, imu: Quaternion | None = None, mimu: Quaternion | None = None
    ) -> None:
        if isinstance(imu, Quaternion):
            self._imu = imu
        if isinstance(mimu, Quaternion):
            self._mimu = mimu

    def _update_magn(self, magn: Vector3 | None = None) -> None:
        if magn:
            self.magn = magn

    async def _update_orientation_mqtt(self, data: dict[str, Any]) -> None:
        imu = None
        mimu = None
        magn = None
        if all(key in data for key in MQTT_IMU_QUAT_KEYS.values()):
            imu = Quaternion.from_dict(data=data, keys=MQTT_IMU_QUAT_KEYS)
        if all(key in data for key in MQTT_MIMU_QUAT_KEYS.values()):
            mimu = Quaternion.from_dict(data=data, keys=MQTT_MIMU_QUAT_KEYS)
        if all(key in data for key in MQTT_MAGN_VECT_KEYS.values()):
            magn = Vector3.from_dict(data=data, keys=MQTT_MAGN_VECT_KEYS)
        self._update_imu(imu=imu, mimu=mimu)
        self._update_magn(magn=magn)
        if any([imu, mimu, magn]):
            await self._orientation_evt_gen.trigger(imu=imu, mimu=mimu, magn=magn)
        return

    async def _update_position_mqtt(self, data: dict[str, Any]) -> None:
        if all(key in data for key in MQTT_POS_KEYS.values()):
            position = Vector3.from_dict(data=data, keys=MQTT_POS_KEYS)
            self._update_position(position=position)
            await self._move_evt_gen.trigger(position=position)

    async def _update_gesture_mqtt(self, data: dict[str, Any]) -> None:
        if MQTT_GESTURE_KEY in data.keys():
            self._gesture = data["gesture"]
            await self._gesture_evt_gen.trigger(gesture=data["gesture"])

    async def handle_metadata_update(self) -> None:
        await self._meta_evt_gen.trigger()

    async def register_event_cb(
        self,
        event_type: EventType,
        callback: Callable[[EventBaseType], Awaitable[None]],
    ) -> None:
        match event_type:
            case EventType.RING_EVT:
                self._move_evt_gen.add_callback(callback)
                self._orientation_evt_gen.add_callback(callback)
                self._touchpad_evt_gen.add_callback(callback)
            case EventType.RING_MOVE_EVT:
                self._move_evt_gen.add_callback(callback)
            case EventType.RING_ORIENTATION_EVT:
                self._orientation_evt_gen.add_callback(callback)
            case EventType.RING_TOUCHPAD_EVT:
                self._touchpad_evt_gen.add_callback(callback)
            case _:
                print("Invalid event for rings!")

    async def remove_event_cb(
        self,
        event_type: EventType,
        callback: Callable[[EventBaseType], Awaitable[None]],
    ) -> bool:
        ret = False
        match event_type:
            case EventType.RING_EVT:
                ret = self._move_evt_gen.remove_callback(callback)
                ret2 = self._orientation_evt_gen.remove_callback(callback)
                ret3 = self._touchpad_evt_gen.remove_callback(callback)
                if not all([ret, ret2, ret3]):
                    print("Not all generators were found!")
                    ret = False
            case EventType.RING_MOVE_EVT:
                ret = self._move_evt_gen.remove_callback(callback)
            case EventType.RING_ORIENTATION_EVT:
                ret = self._orientation_evt_gen.remove_callback(callback)
            case EventType.RING_TOUCHPAD_EVT:
                ret = self._touchpad_evt_gen.remove_callback(callback)
            case _:
                print("Invalid event for rings!")
        return ret
