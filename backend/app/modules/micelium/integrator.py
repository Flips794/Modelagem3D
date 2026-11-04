from __future__ import annotations

import math
import random
from collections import defaultdict

from app.modules.micelium.forcefield import (
    build_spatial_hash,
    compute_forces,
    direct_delta,
    neighbor_cells,
)
from app.modules.micelium.schemas import MiceliumBond, MiceliumEnvironment, MiceliumParticle
from app.modules.micelium.vector_utils import sanitize_positions


Vector = list[float]


def cap_velocity(
    vx: float,
    vy: float,
    vz: float,
    max_speed: float,
) -> tuple[float, float, float]:
    speed = math.sqrt(vx * vx + vy * vy + vz * vz)

    if speed <= max_speed or speed <= 1e-12:
        return vx, vy, vz

    scale = max_speed / speed
    return vx * scale, vy * scale, vz * scale


def build_particle_index(particles: list[MiceliumParticle]) -> dict[str, int]:
    return {particle.id: index for index, particle in enumerate(particles)}


def build_molecule_groups(particles: list[MiceliumParticle]) -> dict[str, list[int]]:
    groups: dict[str, list[int]] = defaultdict(list)

    for index, particle in enumerate(particles):
        groups[particle.molecule_id].append(index)

    return groups


def build_bond_adjacency(
    particles: list[MiceliumParticle],
    bonds: list[MiceliumBond] | None,
) -> dict[int, list[int]]:
    id_to_index = build_particle_index(particles)
    adjacency: dict[int, list[int]] = defaultdict(list)

    for bond in bonds or []:
        atom_a = id_to_index.get(bond.particle_a)
        atom_b = id_to_index.get(bond.particle_b)

        if atom_a is None or atom_b is None:
            continue

        adjacency[atom_a].append(atom_b)
        adjacency[atom_b].append(atom_a)

    return adjacency


def keep_molecules_contiguous(
    *,
    particles: list[MiceliumParticle],
    positions: list[Vector],
    bonds: list[MiceliumBond] | None,
    box_size: float,
) -> list[Vector]:
    """
    Mantém cada molécula contínua em coordenadas diretas.

    Não aplica wrap periódico por bead. Isso evita o erro visual em que cabeça
    e cauda aparecem em lados opostos da caixa e a ligação fica gigante.
    """
    del box_size

    if not positions:
        return positions

    corrected = sanitize_positions(positions)
    groups = build_molecule_groups(particles)
    adjacency = build_bond_adjacency(particles, bonds)

    for group in groups.values():
        if len(group) <= 1:
            continue

        group_set = set(group)
        visited: set[int] = set()

        for root in group:
            if root in visited:
                continue

            visited.add(root)
            stack = [root]

            while stack:
                current = stack.pop()

                for neighbor in adjacency.get(current, []):
                    if neighbor not in group_set or neighbor in visited:
                        continue

                    dx, dy, dz = direct_delta(corrected[current], corrected[neighbor])
                    corrected[neighbor] = [
                        corrected[current][0] + dx,
                        corrected[current][1] + dy,
                        corrected[current][2] + dz,
                    ]

                    visited.add(neighbor)
                    stack.append(neighbor)

    return corrected


def enforce_bond_constraints(
    *,
    particles: list[MiceliumParticle],
    positions: list[Vector],
    bonds: list[MiceliumBond] | None,
    box_size: float,
    iterations: int = 18,
) -> list[Vector]:
    if not bonds:
        return keep_molecules_contiguous(
            particles=particles,
            positions=positions,
            bonds=bonds,
            box_size=box_size,
        )

    id_to_index = build_particle_index(particles)
    corrected = keep_molecules_contiguous(
        particles=particles,
        positions=positions,
        bonds=bonds,
        box_size=box_size,
    )

    for _ in range(iterations):
        for bond in bonds:
            atom_a = id_to_index.get(bond.particle_a)
            atom_b = id_to_index.get(bond.particle_b)

            if atom_a is None or atom_b is None:
                continue

            dx, dy, dz = direct_delta(corrected[atom_a], corrected[atom_b])
            distance = math.sqrt(dx * dx + dy * dy + dz * dz)

            if distance <= 1e-9:
                continue

            rest_length = max(0.18, float(bond.length or 0.48))
            error = distance - rest_length
            correction = 0.5 * 0.96 * error / distance

            corrected[atom_a][0] += dx * correction
            corrected[atom_a][1] += dy * correction
            corrected[atom_a][2] += dz * correction

            corrected[atom_b][0] -= dx * correction
            corrected[atom_b][1] -= dy * correction
            corrected[atom_b][2] -= dz * correction

    return corrected


def damp_bond_relative_velocities(
    *,
    particles: list[MiceliumParticle],
    velocities: list[Vector],
    bonds: list[MiceliumBond] | None,
) -> list[Vector]:
    """
    Reduz velocidade relativa interna para a ligação cabeça-cauda não alongar.
    """
    if not bonds:
        return velocities

    id_to_index = build_particle_index(particles)
    corrected = sanitize_positions(velocities)

    for bond in bonds:
        atom_a = id_to_index.get(bond.particle_a)
        atom_b = id_to_index.get(bond.particle_b)

        if atom_a is None or atom_b is None:
            continue

        relative_velocity = [
            corrected[atom_b][axis] - corrected[atom_a][axis]
            for axis in range(3)
        ]

        for axis in range(3):
            delta = relative_velocity[axis] * 0.32
            corrected[atom_a][axis] += delta
            corrected[atom_b][axis] -= delta

    return corrected


def resolve_nonbonded_overlaps(
    *,
    particles: list[MiceliumParticle],
    positions: list[Vector],
    bonds: list[MiceliumBond] | None,
    box_size: float,
    iterations: int = 3,
) -> list[Vector]:
    corrected = keep_molecules_contiguous(
        particles=particles,
        positions=positions,
        bonds=bonds,
        box_size=box_size,
    )

    if len(corrected) <= 1:
        return corrected

    for _ in range(iterations):
        cell_size = 1.45
        grid = build_spatial_hash(corrected, cell_size)
        visited: set[tuple[int, int]] = set()

        for cell, indices in grid.items():
            for other_cell in neighbor_cells(cell):
                other_indices = grid.get(other_cell)

                if not other_indices:
                    continue

                for atom_a in indices:
                    for atom_b in other_indices:
                        if atom_b <= atom_a:
                            continue

                        pair = (atom_a, atom_b)

                        if pair in visited:
                            continue

                        visited.add(pair)

                        if particles[atom_a].molecule_id == particles[atom_b].molecule_id:
                            continue

                        dx, dy, dz = direct_delta(corrected[atom_a], corrected[atom_b])
                        distance_squared = dx * dx + dy * dy + dz * dz

                        if distance_squared <= 1e-12:
                            dx, dy, dz = 1.0, 0.0, 0.0
                            distance = 1e-6
                        else:
                            distance = math.sqrt(distance_squared)

                        min_distance = (
                            particles[atom_a].radius
                            + particles[atom_b].radius
                            + 0.24
                        )

                        if distance >= min_distance:
                            continue

                        push = 0.5 * (min_distance - distance) / max(distance, 1e-6)

                        corrected[atom_a][0] -= dx * push
                        corrected[atom_a][1] -= dy * push
                        corrected[atom_a][2] -= dz * push

                        corrected[atom_b][0] += dx * push
                        corrected[atom_b][1] += dy * push
                        corrected[atom_b][2] += dz * push

        corrected = enforce_bond_constraints(
            particles=particles,
            positions=corrected,
            bonds=bonds,
            box_size=box_size,
            iterations=8,
        )

    return corrected


def step_brownian_langevin(
    *,
    particles: list[MiceliumParticle],
    positions: list[Vector],
    velocities: list[Vector],
    environment: MiceliumEnvironment,
    box_size: float,
    dt: float,
    rng: random.Random,
    bonds: list[MiceliumBond] | None = None,
) -> tuple[list[Vector], list[Vector]]:
    """
    Integrador browniano/Langevin simplificado.

    Correção definitiva do erro:
    "not enough values to unpack (expected 4, got 3)"

    Este arquivo não usa mais unpack de 4 variáveis a partir de zip com 3 listas.
    O loop principal usa índice explícito, então não há como esse erro ocorrer aqui.
    """
    substeps = 5 if len(particles) < 1200 else 4 if len(particles) < 2600 else 3
    local_dt = min(dt, 0.009) / substeps

    current_positions = enforce_bond_constraints(
        particles=particles,
        positions=positions,
        bonds=bonds,
        box_size=box_size,
        iterations=16,
    )
    current_velocities = sanitize_positions(velocities)

    thermal = math.sqrt(max(environment.temperature_k, 1.0) / 298.15)
    agitation = min(3.0, environment.agitation_rpm / 1000.0)
    noise_scale = 0.0075 * thermal + 0.003 * agitation
    damping = max(0.90, 0.982 - agitation * 0.008)

    for _ in range(substeps):
        forces = compute_forces(
            particles,
            current_positions,
            environment,
            box_size,
            bonds=bonds,
        )

        next_positions: list[Vector] = []
        next_velocities: list[Vector] = []

        for index, particle in enumerate(particles):
            position = current_positions[index]
            velocity = current_velocities[index]
            force = forces[index] if index < len(forces) else [0.0, 0.0, 0.0]

            inv_mass = 1.0 / max(particle.mass, 0.05)

            vx = (
                velocity[0] * damping
                + force[0] * inv_mass * local_dt
                + rng.gauss(0.0, noise_scale)
            )
            vy = (
                velocity[1] * damping
                + force[1] * inv_mass * local_dt
                + rng.gauss(0.0, noise_scale)
            )
            vz = (
                velocity[2] * damping
                + force[2] * inv_mass * local_dt
                + rng.gauss(0.0, noise_scale)
            )

            vx, vy, vz = cap_velocity(
                vx,
                vy,
                vz,
                max_speed=0.72 + agitation * 0.10,
            )

            next_positions.append(
                [
                    position[0] + vx * local_dt,
                    position[1] + vy * local_dt,
                    position[2] + vz * local_dt,
                ]
            )
            next_velocities.append([vx, vy, vz])

        next_positions = enforce_bond_constraints(
            particles=particles,
            positions=next_positions,
            bonds=bonds,
            box_size=box_size,
            iterations=20,
        )
        next_positions = resolve_nonbonded_overlaps(
            particles=particles,
            positions=next_positions,
            bonds=bonds,
            box_size=box_size,
            iterations=2,
        )
        next_velocities = damp_bond_relative_velocities(
            particles=particles,
            velocities=next_velocities,
            bonds=bonds,
        )

        current_positions = next_positions
        current_velocities = next_velocities

    return sanitize_positions(current_positions), sanitize_positions(current_velocities)


