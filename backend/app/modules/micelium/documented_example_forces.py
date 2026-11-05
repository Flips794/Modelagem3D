"""Forças visuais dos exemplos documentados (só atuam com plan.documented_example_id).

São guias de visualização, não física calibrada: aproximam as moléculas dos núcleos que o motor já
define para a forma (nucleation_count), levam a água do exemplo AOT para dentro da camada de cabeças e
põem o salicilato na interface do cilindro (anel para dentro, carboxilato para fora). A forma de cada
agregado continua sendo dada pelas forças de organização existentes (organization.apply_finite_cluster_forces).
Nada aqui é evidência de dinâmica molecular real.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

# Intensidades da guia visual (unidades de velocidade do motor por quadro).
GUIDE_K = 0.010            # aproximação ao núcleo do agregado
GUIDE_FREE_RADIUS = 1.2    # dentro deste raio do núcleo a guia não atua (a forma é das forças de organização)
PLACEMENT_K = 0.120        # água do núcleo e salicilato interfacial
MAX_DELTA_V = 0.030        # teto por conta e por aplicação
CORE_FRACTION = 0.70       # água até 70 % do raio mediano das cabeças
INTERFACE_OFFSET = 0.46    # anel/carboxilato a ± um comprimento de ligação da camada de cabeças


@dataclass
class ExampleGroups:
    surfactants: list[tuple[list[int], list[int]]] = field(default_factory=list)   # (cabeças, caudas)
    core_water: list[list[int]] = field(default_factory=list)
    salicylates: list[tuple[int, int]] = field(default_factory=list)              # (anel, carboxilato)


def build_example_groups(particles) -> ExampleGroups:
    by_molecule: dict[str, list[int]] = {}
    for index, particle in enumerate(particles):
        by_molecule.setdefault(particle.molecule_id, []).append(index)
    groups = ExampleGroups()
    for indices in by_molecule.values():
        heads = [i for i in indices if particles[i].kind == "head"]
        tails = [i for i in indices if particles[i].kind == "tail"]
        role = particles[indices[0]].example_role
        if heads and tails:
            groups.surfactants.append((heads, tails))
        elif role == "core_water":
            groups.core_water.append(indices)
        elif role == "interfacial_aromatic_anion" and len(indices) == 2:
            ring, carboxylate = sorted(indices, key=lambda i: particles[i].bead_index)
            groups.salicylates.append((ring, carboxylate))
    return groups


def nucleus_points(count: int, box_size: float) -> np.ndarray:
    """Núcleos determinísticos (o mesmo arranjo em todos os trechos da mesma mistura)."""
    if count <= 1:
        return np.zeros((1, 3))
    radius = 0.28 * box_size
    return np.array([[radius * math.cos(2 * math.pi * k / count), 0.0, radius * math.sin(2 * math.pi * k / count)]
                     for k in range(count)])


def _push(velocities, particles, index: int, force: np.ndarray) -> None:
    norm = float(np.linalg.norm(force))
    if norm > MAX_DELTA_V:
        force = force * (MAX_DELTA_V / norm)
    mass = max(float(particles[index].mass), 0.1)
    for k in range(3):
        velocities[index][k] += float(force[k]) / mass


def apply_documented_example_forces(*, positions, velocities, particles, groups: ExampleGroups, clusters, plan,
                                    box_size: float) -> None:
    if not plan.documented_example_id:
        return
    xyz = np.asarray(positions, dtype=float)
    morphology = plan.morphology.lower()
    reverse = "inversa" in morphology
    alpha = float(plan.final_alpha)

    # 1) Guia de agregação: cada surfactante até o núcleo mais próximo (só translação; sem orientar).
    nuclei = nucleus_points(int(plan.nucleation_count), box_size)
    for heads, tails in groups.surfactants:
        anchor = xyz[heads if reverse else tails].mean(axis=0)
        offsets = nuclei - anchor
        distances = np.linalg.norm(offsets, axis=1)
        k = int(np.argmin(distances))
        distance = float(distances[k])
        if distance <= GUIDE_FREE_RADIUS:
            continue
        pull = offsets[k] / distance * (GUIDE_K * alpha * min(distance - GUIDE_FREE_RADIUS, 3.0))
        for index in heads + tails:
            _push(velocities, particles, index, pull)

    big = [c for c in clusters.values() if c.get("size", 0) >= 3 and c.get("head_indices")]
    if not big:
        return

    # 2) Água do núcleo (AOT): para dentro da camada de cabeças da micela inversa mais próxima.
    if reverse and groups.core_water:
        shells = []
        for cluster in big:
            center = xyz[cluster["head_indices"]].mean(axis=0)
            radius = float(np.median(np.linalg.norm(xyz[cluster["head_indices"]] - center, axis=1)))
            shells.append((center, radius))
        for indices in groups.core_water:
            point = xyz[indices].mean(axis=0)
            center, radius = min(shells, key=lambda shell: float(np.linalg.norm(point - shell[0])))
            offset = point - center
            distance = float(np.linalg.norm(offset))
            target = CORE_FRACTION * radius
            if distance <= target:
                continue
            pull = -offset / max(distance, 1e-9) * (PLACEMENT_K * alpha * min(distance - target, 3.0))
            for index in indices:
                _push(velocities, particles, index, pull)

    # 3) Salicilato (CTAB): na interface do cilindro, 1:1 com as cabeças do agregado, anel para dentro.
    if ("cilíndrica" in morphology or "wormlike" in morphology) and groups.salicylates:
        assigned: set[int] = set()
        for cluster in big:
            members = xyz[cluster["particle_indices"]]
            center = members.mean(axis=0)
            axis = cluster.get("organization_axis")
            if axis is None:
                centered = members - center
                axis = np.linalg.eigh(centered.T @ centered)[1][:, -1]
            axis = np.asarray(axis, dtype=float)
            axis = axis / max(float(np.linalg.norm(axis)), 1e-9)

            def radial(point):
                rel = point - center
                return rel - axis * float(rel @ axis)

            head_radius = float(np.median([np.linalg.norm(radial(xyz[i])) for i in cluster["head_indices"]]))
            head_axial = [(xyz[i] - center) @ axis for i in cluster["head_indices"]]
            # Fora das pontas: o salicilato vai para a superfície lateral, não para as tampas do cilindro.
            axial_low, axial_high = min(head_axial) + 0.5, max(head_axial) - 0.5
            candidates = sorted(
                (s for s in range(len(groups.salicylates)) if s not in assigned),
                key=lambda s: float(np.linalg.norm(radial(xyz[groups.salicylates[s][0]]))),
            )[: len(cluster["head_indices"])]
            for s in candidates:
                assigned.add(s)
                ring, carboxylate = groups.salicylates[s]
                r_vec = radial(xyz[ring])
                r_len = float(np.linalg.norm(r_vec))
                outward = r_vec / r_len if r_len > 1e-9 else np.array([1.0, 0.0, 0.0])
                axial_position = float((xyz[ring] - center) @ axis)
                if axial_low < axial_high:
                    axial_position = min(max(axial_position, axial_low), axial_high)
                axial = center + axis * axial_position
                for index, offset in ((ring, -INTERFACE_OFFSET), (carboxylate, INTERFACE_OFFSET)):
                    target = axial + outward * max(head_radius + offset, 0.2)
                    displacement = target - xyz[index]
                    _push(velocities, particles, index, displacement * (PLACEMENT_K * alpha))
