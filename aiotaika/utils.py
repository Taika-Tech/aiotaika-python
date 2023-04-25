"""Utility functionality for Taika use."""
import math
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class SphericalAngle:
    azimuth: float
    elevation: float


class Vector3:
    """Represent a 3D vector."""

    def __init__(self, xyz: List[float]):
        self._xyz: List[float] = xyz

    @classmethod
    def from_dict(cls, data: Dict[str, float], keys: Dict[str, str]):
        """
        Create a vector from two dictionaries (data and keys).

        :param data: The dictionary containing the vector values
        :type data: Dict[str, float]
        :param keys: The dictionary containing keys for the data dictionary.
        :type keys: Dict[str, str]
        """
        return cls(xyz=[data[keys["x"]], data[keys["y"]], data[keys["z"]]])

    @property
    def x(self) -> float:
        """Return the x component of the 3-dimensional vector."""
        return self._xyz[0]

    @property
    def y(self) -> float:
        """Return the y component of the 3-dimensional vector."""
        return self._xyz[1]

    @property
    def z(self) -> float:
        """Return the z component of the 3-dimensional vector."""
        return self._xyz[2]

    def __getitem__(self, index):
        return self._xyz[int(index)]

    def __len__(self):
        return len(self._xyz)

    def __str__(self):
        return "x: {:6.2f}   y: {:6.2f}   z: {:6.2f}".format(
            self._xyz[0], self._xyz[1], self._xyz[2]
        )


class Quaternion:
    """Represent a quaternion."""

    def __init__(self, wxyz: List[float]):
        self._wxyz: List[float] = wxyz

    @classmethod
    def from_dict(cls, data: Dict[str, Any], keys: Dict[str, str]):
        """
        Create a quaternion from two dictionaries (data and keys).

        :param data: The dictionary containing the quaternion values
        :type data: Dict[str, float]
        :param keys: The dictionary containing keys for the data dictionary.
        :type keys: Dict[str, str]
        """
        return cls(
            wxyz=[data[keys["w"]], data[keys["x"]], data[keys["y"]], data[keys["z"]]]
        )

    @property
    def w(self) -> float:
        """Return the w component of the quaternion."""
        return self._wxyz[0]

    @property
    def x(self) -> float:
        """Return the x component of the quaternion."""
        return self._wxyz[1]

    @property
    def y(self) -> float:
        """Return the y component of the quaternion."""
        return self._wxyz[2]

    @property
    def z(self) -> float:
        """Return the z component of the quaternion."""
        return self._wxyz[3]

    @property
    def spherical(self) -> SphericalAngle:
        """Transform quaternion to spherical angles."""
        w, x, y, z = self._wxyz
        return SphericalAngle(
            azimuth=math.atan2(2 * (w * x + y * z), 1 - 2 * (x**2 + y**2)),
            elevation=math.asin(2 * (w * y - x * z)),
        )

    def __getitem__(self, index):
        return self._wxyz[int(index)]

    def __len__(self):
        return len(self._wxyz)

    def __str__(self):
        return "w: {:6.2f}   x: {:6.2f}   y: {:6.2f}   z: {:6.2f}".format(
            self._wxyz[0], self._wxyz[1], self._wxyz[2], self._wxyz[3]
        )


def unify_mac(mac: str) -> str:
    """
    Unify a MAC address string to only contain uppercase letters nad numbers.

    :param mac: MAC address to unify
    :type mac: str

    :return: Unified MAC string.
    :rtype: str
    """
    ret = mac.upper()
    ret = ret.replace(":", "")
    return ret
