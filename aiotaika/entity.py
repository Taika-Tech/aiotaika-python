# Taika asynchronous client library for Python
#    Copyright (C) 2023 Taika Tech Oy
#    Author Jussi Hietanen
#
# This library is free software; you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free Software
# Foundation. See the GNU Lesser General Public License for more details.

from abc import ABC
from enum import Enum


class EntityType(Enum):
    """Enumerations for Taika Entity types."""

    NONE = "none"
    RING = "ring"
    LOCATOR = "locator"


class TaikaEntity(ABC):
    """Abstract class which is used for Taika Entity classes' base."""

    def __init__(self, entity_type: EntityType = EntityType.NONE) -> None:
        self._entity_type = entity_type
        self._last_updated = None

    @property
    def entity_type(self) -> EntityType:
        """
        Get the EntityType of this instance.

        :return: The entity type of this TaikaEntity.
        :rtype: EntityType
        """
        return self._entity_type

    @property
    def last_updated(self) -> int | None:
        """
        Returns when this entity was last updated.

        :return: Time when this instance was last updated or None if it was
            not seen during the lifetime of this TaikaClient.
        :rtype: int or None
        """
        return self._last_updated

    @last_updated.setter
    def last_updated(self, value):
        """Set the last_updated value of this TaikaEntity."""
        self._last_updated = value
