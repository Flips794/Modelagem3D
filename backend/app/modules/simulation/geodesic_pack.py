from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from math import floor, pi, sqrt
from typing import Any, Iterable

import numpy as np

from app.modules.simulation.schemas import (
    SimulationBox3D,
    SimulationBoxCenter,
    SimulationFrame3D,
    SimulationTopology3D,
)


@dataclass(slots=True)
class PackedMolecule:
    molecule: dict[str, Any]
    original_index: int
    center: np.ndarray
    radius: float
    translated_positions: np.ndarray
    translation: np.ndarray
    layer_radius: float


ATOMIC_MASS_DA: dict[str, float] = {
    "H": 1.008,
    "C": 12.011,
    "N": 14.007,
    "O": 15.999,
    "F": 18.998,
    "P": 30.974,
    "S": 32.06,
    "Cl": 35.45,
    "Br": 79.904,
    "I": 126.904,
    "Na": 22.990,
    "K": 39.098,
    "Ca": 40.078,
    "Fe": 55.845,
    "Cu": 63.546,
    "Zn": 65.38,
}


def _as_positions(molecule: dict[str, Any]) -> np.ndarray:
    positions = np.asarray(molecule.get("positions"), dtype=float)

    if positions.ndim != 2 or positions.shape[1] != 3:
        raise ValueError(
            "Cada molécula precisa ter molecule['positions'] com shape (N, 3)."
        )

    if positions.shape[0] == 0:
        raise ValueError("Molécula sem átomos não pode ser empacotada.")

    return positions


def _as_masses(molecule: dict[str, Any], atom_count: int) -> np.ndarray:
    masses = molecule.get("masses")

    if masses is None:
        return np.ones(atom_count, dtype=float)

    masses_array = np.asarray(masses, dtype=float)

    if masses_array.ndim != 1 or masses_array.shape[0] != atom_count:
        raise ValueError("molecule['masses'] precisa ter shape (N,).")

    masses_array = np.where(masses_array <= 0, 1.0, masses_array)

    return masses_array


def calculate_center_of_mass(positions: np.ndarray, masses: np.ndarray) -> np.ndarray:
    total_mass = float(np.sum(masses))

    if total_mass <= 0:
        return np.mean(positions, axis=0)

    return np.sum(positions * masses[:, None], axis=0) / total_mass


def calculate_occupation_radius(
    positions: np.ndarray,
    center_of_mass: np.ndarray,
    padding: float,
) -> float:
    distances = np.linalg.norm(positions - center_of_mass[None, :], axis=1)
    farthest = float(np.max(distances))

    return farthest + float(padding)


def fibonacci_sphere_points(count: int, radius: float) -> np.ndarray:
    if count <= 0:
        return np.zeros((0, 3), dtype=float)

    if count == 1:
        return np.array([[0.0, 0.0, radius]], dtype=float)

    points = np.zeros((count, 3), dtype=float)
    golden_angle = pi * (3.0 - sqrt(5.0))

    for i in range(count):
        y = 1.0 - (2.0 * i) / (count - 1)
        radial = sqrt(max(0.0, 1.0 - y * y))
        theta = golden_angle * i

        x = np.cos(theta) * radial
        z = np.sin(theta) * radial

        points[i] = np.array([x * radius, y * radius, z * radius], dtype=float)

    return points


def estimate_layer_capacity(layer_radius: float, occupation_radius: float) -> int:
    safe_radius = max(float(occupation_radius), 1e-6)

    surface_area = 4.0 * pi * layer_radius * layer_radius
    footprint_area = pi * (2.0 * safe_radius) ** 2

    return max(1, int(floor(surface_area / footprint_area)))


def _prepare_molecule_records(
    molecules: Iterable[dict[str, Any]],
    padding: float,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for index, molecule in enumerate(molecules):
        positions = _as_positions(molecule)
        masses = _as_masses(molecule, positions.shape[0])
        center = calculate_center_of_mass(positions, masses)
        radius = calculate_occupation_radius(positions, center, padding)

        records.append(
            {
                "molecule": molecule,
                "original_index": index,
                "positions": positions,
                "masses": masses,
                "center": center,
                "radius": radius,
            }
        )

    records.sort(key=lambda item: item["radius"], reverse=True)

    return records


def pack_molecules_concentrically(
    molecules: list[dict[str, Any]],
    padding: float = 0.35,
    initial_layer_radius: float | None = None,
    oversampling_factor: int = 4,
) -> list[PackedMolecule]:
    if padding < 0:
        raise ValueError("padding precisa ser >= 0.")

    if len(molecules) == 0:
        return []

    records = _prepare_molecule_records(molecules, padding=padding)

    max_radius = max(float(item["radius"]) for item in records)
    layer_radius = (
        float(initial_layer_radius)
        if initial_layer_radius is not None
        else max_radius + padding
    )

    remaining = records[:]
    placed: list[PackedMolecule] = []
    placed_centers: list[np.ndarray] = []
    placed_radii: list[float] = []

    while remaining:
        largest_remaining_radius = float(remaining[0]["radius"])
        layer_radius = max(layer_radius, largest_remaining_radius + padding)

        capacity = estimate_layer_capacity(layer_radius, largest_remaining_radius)
        candidate_count = max(
            capacity * max(1, oversampling_factor),
            len(remaining),
            8,
        )

        candidate_points = fibonacci_sphere_points(candidate_count, layer_radius)
        used_candidate_indices: set[int] = set()
        next_remaining: list[dict[str, Any]] = []

        for record in remaining:
            radius = float(record["radius"])
            selected_point: np.ndarray | None = None
            selected_candidate_index: int | None = None

            for candidate_index, candidate_point in enumerate(candidate_points):
                if candidate_index in used_candidate_indices:
                    continue

                valid = True

                for existing_center, existing_radius in zip(
                    placed_centers,
                    placed_radii,
                    strict=True,
                ):
                    min_distance = existing_radius + radius + padding
                    actual_distance = float(
                        np.linalg.norm(candidate_point - existing_center)
                    )

                    if actual_distance < min_distance:
                        valid = False
                        break

                if valid:
                    selected_point = candidate_point
                    selected_candidate_index = candidate_index
                    break

            if selected_point is None or selected_candidate_index is None:
                next_remaining.append(record)
                continue

            used_candidate_indices.add(selected_candidate_index)

            translation = selected_point - record["center"]
            translated_positions = record["positions"] + translation[None, :]

            packed = PackedMolecule(
                molecule=record["molecule"],
                original_index=int(record["original_index"]),
                center=np.asarray(selected_point, dtype=float),
                radius=radius,
                translated_positions=translated_positions,
                translation=translation,
                layer_radius=layer_radius,
            )

            placed.append(packed)
            placed_centers.append(packed.center)
            placed_radii.append(packed.radius)

        if len(next_remaining) == len(remaining):
            layer_radius += (2.0 * max_radius) + padding
        else:
            layer_radius += (2.0 * max_radius) + padding
            remaining = next_remaining

    placed.sort(key=lambda item: item.original_index)

    return placed


def _mass_for_element(element: str) -> float:
    return ATOMIC_MASS_DA.get(element, 12.011)


def _build_grouped_molecules(
    topology: SimulationTopology3D,
    frame: SimulationFrame3D,
) -> list[dict[str, Any]]:
    coordinates = np.asarray(frame.coordinates, dtype=float)

    if coordinates.ndim != 2 or coordinates.shape[1] != 3:
        raise ValueError("frame.coordinates precisa ter shape (N, 3).")

    if len(topology.atoms) != coordinates.shape[0]:
        raise ValueError(
            "topology.atoms e frame.coordinates precisam ter o mesmo número de átomos."
        )

    groups: "OrderedDict[str, list[int]]" = OrderedDict()

    for atom in topology.atoms:
        groups.setdefault(atom.moleculeId, []).append(atom.index)

    molecules: list[dict[str, Any]] = []

    for molecule_id, atom_indices in groups.items():
        positions = coordinates[atom_indices]
        masses = np.asarray(
            [
                topology.atoms[index].mass
                if topology.atoms[index].mass is not None
                else _mass_for_element(topology.atoms[index].element)
                for index in atom_indices
            ],
            dtype=float,
        )

        molecules.append(
            {
                "id": molecule_id,
                "indices": atom_indices,
                "positions": positions,
                "masses": masses,
            }
        )

    return molecules


def _compute_box_for_coordinates(
    coordinates: np.ndarray,
    padding: float,
    minimum_side: float = 18.0,
) -> SimulationBox3D:
    if coordinates.size == 0:
        side = minimum_side
    else:
        max_abs = float(np.max(np.abs(coordinates)))
        side = max(minimum_side, 2.0 * (max_abs + padding + 2.0))

    return SimulationBox3D(
        x=side,
        y=side,
        z=side,
        center=SimulationBoxCenter(x=0.0, y=0.0, z=0.0),
    )


def repack_topology_frame_concentrically(
    topology: SimulationTopology3D,
    frame: SimulationFrame3D,
    padding: float = 0.45,
) -> tuple[SimulationTopology3D, SimulationFrame3D]:
    """
    Reempacota o frame recebido do frontend usando camadas concêntricas.

    O frontend ainda monta uma topologia inicial, mas o estado físico inicial
    usado pelo OpenMM é este frame reempacotado no backend.
    """
    original_coordinates = np.asarray(frame.coordinates, dtype=float)
    molecules = _build_grouped_molecules(topology, frame)

    packed = pack_molecules_concentrically(
        molecules=molecules,
        padding=padding,
        initial_layer_radius=None,
        oversampling_factor=5,
    )

    new_coordinates = np.array(original_coordinates, copy=True)

    for packed_item in packed:
        atom_indices = packed_item.molecule["indices"]

        for local_index, atom_index in enumerate(atom_indices):
            new_coordinates[atom_index] = packed_item.translated_positions[local_index]

    new_box = _compute_box_for_coordinates(new_coordinates, padding=padding)

    new_topology = topology.model_copy(
        update={
            "box": new_box,
            "title": f"{topology.title} · geodesic",
        }
    )

    new_frame = frame.model_copy(
        update={
            "frameIndex": 0,
            "timePs": 0.0,
            "coordinates": [
                (float(x), float(y), float(z))
                for x, y, z in new_coordinates.tolist()
            ],
            "box": new_box,
            "hiddenBonds": [],
        }
    )

    return new_topology, new_frame


