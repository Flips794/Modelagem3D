from __future__ import annotations

import math
from collections import defaultdict

from app.modules.micelium.schemas import MiceliumBond, MiceliumEnvironment, MiceliumParticle
from app.modules.micelium.vector_utils import as_xyz


Vector = list[float]
Cell = tuple[int, int, int]


def zeros(n: int) -> list[Vector]:
    return [[0.0, 0.0, 0.0] for _ in range(n)]


def direct_delta(a: Vector, b: Vector) -> tuple[float, float, float]:
    """
    Delta direto, sem imagem mínima.

    Correção crítica:
    Aceita coordenadas [x, y, z] e também ignora qualquer valor extra.
    Nunca espera 4 valores.
    """
    ax, ay, az = as_xyz(a)
    bx, by, bz = as_xyz(b)
    return bx - ax, by - ay, bz - az


# Mantido apenas por compatibilidade com imports antigos.
def minimum_image_delta(a: Vector, b: Vector, box_size: float) -> tuple[float, float, float]:
    void_box_size = box_size
    del void_box_size
    return direct_delta(a, b)


def add_scaled(force: Vector, dx: float, dy: float, dz: float, scale: float) -> None:
    force[0] += dx * scale
    force[1] += dy * scale
    force[2] += dz * scale


def cap_force(force: Vector, max_force: float = 34.0) -> None:
    norm = math.sqrt(force[0] * force[0] + force[1] * force[1] + force[2] * force[2])
    if norm > max_force:
        scale = max_force / norm
        force[0] *= scale
        force[1] *= scale
        force[2] *= scale


def spatial_cell(position: Vector, cell_size: float) -> Cell:
    x, y, z = as_xyz(position)
    return (
        math.floor(x / cell_size),
        math.floor(y / cell_size),
        math.floor(z / cell_size),
    )


def build_spatial_hash(positions: list[Vector], cell_size: float) -> dict[Cell, list[int]]:
    grid: dict[Cell, list[int]] = defaultdict(list)
    for index, position in enumerate(positions):
        grid[spatial_cell(position, cell_size)].append(index)
    return grid


def neighbor_cells(cell: Cell):
    cx, cy, cz = cell
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                yield (cx + dx, cy + dy, cz + dz)


def deterministic_unit_pair(i: int, j: int) -> tuple[float, float, float]:
    seed = (i + 1) * 928371 + (j + 3) * 364479
    x = math.sin(seed * 0.017) + 0.13
    y = math.sin(seed * 0.031) + 0.29
    z = math.sin(seed * 0.047) + 0.41
    norm = math.sqrt(x * x + y * y + z * z) or 1.0
    return x / norm, y / norm, z / norm


def build_bond_lookup(
    particles: list[MiceliumParticle],
    bonds: list[MiceliumBond] | None,
) -> tuple[dict[str, int], set[tuple[int, int]]]:
    id_to_index = {particle.id: index for index, particle in enumerate(particles)}
    bonded_pairs: set[tuple[int, int]] = set()
    for bond in bonds or []:
        a = id_to_index.get(bond.particle_a)
        b = id_to_index.get(bond.particle_b)
        if a is None or b is None:
            continue
        bonded_pairs.add((min(a, b), max(a, b)))
    return id_to_index, bonded_pairs


def apply_bond_forces(
    *,
    particles: list[MiceliumParticle],
    positions: list[Vector],
    bonds: list[MiceliumBond] | None,
    forces: list[Vector],
) -> None:
    """
    Ligações internas = molas topológicas fixas.

    Usa delta direto, nunca imagem mínima. A molécula não pode ser dividida por
    PBC durante renderização.
    """
    if not bonds:
        return
    id_to_index = {particle.id: index for index, particle in enumerate(particles)}
    for bond in bonds:
        i = id_to_index.get(bond.particle_a)
        j = id_to_index.get(bond.particle_b)
        if i is None or j is None:
            continue
        dx, dy, dz = direct_delta(positions[i], positions[j])
        r2 = dx * dx + dy * dy + dz * dz
        if r2 < 1e-10:
            dx, dy, dz = deterministic_unit_pair(i, j)
            r = 1e-5
        else:
            r = math.sqrt(r2)
        rest = max(0.18, float(bond.length or 0.48))
        stiffness = max(1.0, float(bond.stiffness or 2.0)) * 42.0
        stretch = max(-0.35, min(0.35, r - rest))
        scale = stiffness * stretch / max(r, 1e-5)
        add_scaled(forces[i], dx, dy, dz, scale)
        add_scaled(forces[j], -dx, -dy, -dz, scale)


def apply_soft_box_forces(
    *,
    particles: list[MiceliumParticle],
    positions: list[Vector],
    box_size: float,
    forces: list[Vector],
) -> None:
    """
    Parede macia por molécula, não por bead.

    A versão anterior empurrava cada bead separadamente. Em surfactantes isso
    podia puxar a cabeça para um lado e a cauda para outro, alongando ligações.
    Aqui calculamos o centro de cada molécula e aplicamos a mesma correção a
    todos os seus beads, preservando a topologia interna.
    """
    half = box_size / 2.0
    limit = half * 0.88
    stiffness = 4.2

    groups: dict[str, list[int]] = defaultdict(list)
    for index, particle in enumerate(particles):
        groups[particle.molecule_id].append(index)

    for indices in groups.values():
        if not indices:
            continue

        center = [
            sum(positions[index][axis] for index in indices) / len(indices)
            for axis in range(3)
        ]

        group_force = [0.0, 0.0, 0.0]

        for axis in range(3):
            value = center[axis]
            excess = abs(value) - limit
            if excess <= 0:
                continue

            direction = 1.0 if value > 0 else -1.0
            group_force[axis] -= direction * stiffness * excess

        if group_force == [0.0, 0.0, 0.0]:
            continue

        for index in indices:
            forces[index][0] += group_force[0]
            forces[index][1] += group_force[1]
            forces[index][2] += group_force[2]


def compute_forces(
    particles: list[MiceliumParticle],
    positions: list[Vector],
    environment: MiceliumEnvironment,
    box_size: float,
    bonds: list[MiceliumBond] | None = None,
) -> list[Vector]:
    """
    Campo de força coarse-grained estável.

    Topologia química interna é fixa. Só forças intermoleculares são dinâmicas.
    O motor usa coordenadas contínuas para renderização; não aplica wrap por
    partícula, evitando ligações gigantes e resets visuais.
    """
    n = len(particles)
    forces = zeros(n)
    if n == 0:
        return forces

    _, bonded_pairs = build_bond_lookup(particles, bonds)
    apply_bond_forces(particles=particles, positions=positions, bonds=bonds, forces=forces)
    apply_soft_box_forces(particles=particles, positions=positions, box_size=box_size, forces=forces)

    dielectric = max(environment.dielectric_constant, 1.0)
    polarity = max(0.0, min(1.0, environment.solvent_polarity_index))
    ionic_strength = max(environment.ionic_strength_mol_l, 0.0)
    cutoff = 4.2
    grid = build_spatial_hash(positions, cutoff)
    debye_nm = 8.0 if ionic_strength <= 1e-9 else min(8.0, 0.304 / math.sqrt(ionic_strength))
    screening = 1.0 / max(debye_nm, 0.2)
    visited_pairs: set[tuple[int, int]] = set()

    for cell, indices in grid.items():
        for other_cell in neighbor_cells(cell):
            other_indices = grid.get(other_cell)
            if not other_indices:
                continue
            for i in indices:
                pi = particles[i]
                for j in other_indices:
                    if j <= i:
                        continue
                    pair = (i, j)
                    if pair in visited_pairs or pair in bonded_pairs:
                        continue
                    visited_pairs.add(pair)
                    pj = particles[j]
                    if pi.molecule_id == pj.molecule_id:
                        continue
                    dx, dy, dz = direct_delta(positions[i], positions[j])
                    r2 = dx * dx + dy * dy + dz * dz
                    if r2 < 1e-10:
                        dx, dy, dz = deterministic_unit_pair(i, j)
                        r = 1e-5
                        r2 = r * r
                    else:
                        if r2 > cutoff * cutoff:
                            continue
                        r = math.sqrt(r2)

                    inv_r = 1.0 / max(r, 1e-5)
                    contact = max(pi.radius + pj.radius + 0.16, 0.22)

                    # Repulsão curta mais conservadora: impede sobreposição.
                    if r < contact:
                        repulsion = 44.0 * (contact - r) / contact
                        scale = repulsion * inv_r
                        add_scaled(forces[i], -dx, -dy, -dz, scale)
                        add_scaled(forces[j], dx, dy, dz, scale)

                    # Atração hidrofóbica moderada; não deve esmagar moléculas.
                    hydrophobic_pair = pi.hydrophobicity * pj.hydrophobicity
                    if hydrophobic_pair > 0.05:
                        preferred = contact * 1.75
                        attraction = polarity * hydrophobic_pair * math.exp(-((r - preferred) ** 2) / 3.8)
                        scale = 0.095 * attraction * inv_r
                        add_scaled(forces[i], dx, dy, dz, scale)
                        add_scaled(forces[j], -dx, -dy, -dz, scale)

                    # Cabeças polares muito próximas se repelem.
                    polar_pair = pi.polarity * pj.polarity
                    if polar_pair > 0.2 and r < 2.1:
                        head_repulsion = 0.74 * polar_pair * polarity * (2.1 - r)
                        scale = head_repulsion * inv_r
                        add_scaled(forces[i], -dx, -dy, -dz, scale)
                        add_scaled(forces[j], dx, dy, dz, scale)

                    # Coulomb blindado e limitado.
                    q_product = pi.charge * pj.charge
                    if abs(q_product) > 1e-6:
                        electrostatic = 0.9 * q_product * math.exp(-screening * r) / (dielectric * max(r2, 0.18))
                        electrostatic = max(-0.65, min(0.65, electrostatic))
                        scale = electrostatic * inv_r
                        add_scaled(forces[i], -dx, -dy, -dz, scale)
                        add_scaled(forces[j], dx, dy, dz, scale)

    for force in forces:
        cap_force(force)
    return forces


