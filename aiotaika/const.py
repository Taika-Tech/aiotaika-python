"""Constants."""
from typing import Final

DEFAULT_DB_PORT: Final = 3306
DEFAULT_MQTT_PORT: Final = 1883


RING_DATA_HISTORY_LEN: Final = 100

MQTT_SUBSCRIBE_ALL: Final = "#"

MQTT_IMU_QUAT_KEYS: Final = {"w": "imu_0", "x": "imu_1", "y": "imu_2", "z": "imu_3"}
MQTT_MIMU_QUAT_KEYS: Final = {
    "w": "mimu_0",
    "x": "mimu_1",
    "y": "mimu_2",
    "z": "mimu_3",
}

MQTT_MAGN_VECT_KEYS: Final = {"x": "mag_x", "y": "mag_y", "z": "mag_z"}

MQTT_POS_KEYS: Final = {"x": "x", "y": "y", "z": "z"}
MQTT_ROT_KEYS: Final = {"x": "x", "y": "y", "z": "z"}
MQTT_GESTURE_KEY: Final = "gesture"

MQTT_RING_ORIENTATION_TOPIC: Final = "taika/imu/+/"
MQTT_RING_POSITION_TOPIC: Final = "taika/positioning/position/"
MQTT_RING_GESTURE_TOPIC: Final = "taika/gesture/"

MQTT_LOCATOR_ORIENTATION_TOPIC: Final = "taika/imu/"
MQTT_LOCATOR_ANGLE_TOPIC: Final = "taika/positioning/angle/"


DB_RING_ID: Final = "id"
DB_RING_LAST_DB_UPDATE: Final = "lastDbUpdate"
DB_RING_MAC: Final = "mac"
DB_RING_NAME: Final = "name"

DB_LOCATOR_ID: Final = "id"
DB_LOCATOR_LAST_DB_UPDATE: Final = "lastDbUpdate"
DB_LOCATOR_MAC: Final = "mac"
DB_LOCATOR_POSITION_KEYS: Final = {"x": "positionX", "y": "positionY", "z": "positionZ"}
DB_LOCATOR_ORIENTATION_KEYS: Final = {
    "x": "orientationX",
    "y": "orientationY",
    "z": "orientationZ",
}

DB_TABLE_PORTALS: Final = "portals"
DB_TABLE_RINGS: Final = "rings"
DB_TABLE_LOCATORS: Final = "locators"
