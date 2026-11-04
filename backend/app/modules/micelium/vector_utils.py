from __future__ import annotations

import math
from typing import Iterable


Vector3 = list[float]


def as_xyz(position: Iterable[float]) -> tuple[float, float, float]:
    values = list(position)

    if len(values) < 3:
        raise ValueError(
            "Coordenada inválida no Micelium Engine: "
            f"esperado pelo menos 3 valores, recebido {len(values)}."
        )

    return float(values[0]), float(values[1]), float(values[2])


def to_xyz_list(position: Iterable[float]) -> Vector3:
    x, y, z = as_xyz(position)
    return [x, y, z]


def add(a: Iterable[float], b: Iterable[float]) -> Vector3:
    ax, ay, az = as_xyz(a)
    bx, by, bz = as_xyz(b)

    return [ax + bx, ay + by, az + bz]


def subtract(a: Iterable[float], b: Iterable[float]) -> Vector3:
    ax, ay, az = as_xyz(a)
    bx, by, bz = as_xyz(b)

    return [ax - bx, ay - by, az - bz]


def scale(vector: Iterable[float], factor: float) -> Vector3:
    x, y, z = as_xyz(vector)

    return [x * factor, y * factor, z * factor]


def length(vector: Iterable[float]) -> float:
    x, y, z = as_xyz(vector)

    return math.sqrt(x * x + y * y + z * z)


def normalize(vector: Iterable[float]) -> Vector3:
    x, y, z = as_xyz(vector)
    norm = math.sqrt(x * x + y * y + z * z)

    if norm <= 1e-12:
        return [1.0, 0.0, 0.0]

    return [x / norm, y / norm, z / norm]


def distance_3d(a: Iterable[float], b: Iterable[float]) -> float:
    ax, ay, az = as_xyz(a)
    bx, by, bz = as_xyz(b)

    dx = ax - bx
    dy = ay - by
    dz = az - bz

    return math.sqrt(dx * dx + dy * dy + dz * dz)


def center_of(points: list[Iterable[float]]) -> Vector3:
    if not points:
        return [0.0, 0.0, 0.0]

    sx = 0.0
    sy = 0.0
    sz = 0.0

    for point in points:
        x, y, z = as_xyz(point)
        sx += x
        sy += y
        sz += z

    total = float(len(points))

    return [sx / total, sy / total, sz / total]


def clamp_to_box(position: Iterable[float], box_size: float) -> Vector3:
    x, y, z = as_xyz(position)
    half = max(float(box_size), 1.0) / 2.0

    return [
        max(-half, min(half, x)),
        max(-half, min(half, y)),
        max(-half, min(half, z)),
    ]


def sanitize_positions(positions: list[Iterable[float]]) -> list[Vector3]:
    return [to_xyz_list(position) for position in positions]


