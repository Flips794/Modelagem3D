from __future__ import annotations

from collections import defaultdict, deque
import math
import numpy as np

from app.modules.micelium.organization import principal_axes

from app.modules.micelium.schemas import (
    MicelleCluster,
    MiceliumAnalysis,
    MiceliumEnvironment,
    MiceliumParticle,
)
from app.modules.micelium.vector_utils import (
    as_xyz,
    center_of,
    distance_3d,
    sanitize_positions,
)


Vector = list[float]


def distance(a: Vector, b: Vector) -> float:
    return distance_3d(a, b)


def particle_center(indices: list[int], positions: list[Vector]) -> Vector:
    return center_of([positions[index] for index in indices])


def group_by_molecule(particles: list[MiceliumParticle]) -> dict[str, list[int]]:
    groups: dict[str, list[int]] = defaultdict(list)

    for index, particle in enumerate(particles):
        groups[particle.molecule_id].append(index)

    return dict(groups)


def molecule_kind(indices: list[int], particles: list[MiceliumParticle]) -> str:
    kinds = {str(particles[index].kind) for index in indices}

    if all(particles[index].role == "solvent" or particles[index].kind == "solvent" for index in indices):
        return "solvent"

    if "head" in kinds and "tail" in kinds:
        return "surfactant"

    return "solute"


def molecule_centers(
    particles: list[MiceliumParticle],
    positions: list[Vector],
) -> dict[str, Vector]:
    groups = group_by_molecule(particles)

    return {
        molecule_id: particle_center(indices, positions)
        for molecule_id, indices in groups.items()
    }


def surfactant_tail_centers(
    particles: list[MiceliumParticle],
    positions: list[Vector],
) -> dict[str, Vector]:
    groups = group_by_molecule(particles)
    result: dict[str, Vector] = {}

    for molecule_id, indices in groups.items():
        if molecule_kind(indices, particles) != "surfactant":
            continue

        tail_indices = [
            index
            for index in indices
            if particles[index].kind == "tail"
        ]

        if tail_indices:
            result[molecule_id] = particle_center(tail_indices, positions)

    return result


def surfactant_head_centers(
    particles: list[MiceliumParticle],
    positions: list[Vector],
) -> dict[str, Vector]:
    groups = group_by_molecule(particles)
    result: dict[str, Vector] = {}

    for molecule_id, indices in groups.items():
        if molecule_kind(indices, particles) != "surfactant":
            continue

        head_indices = [
            index
            for index in indices
            if particles[index].kind == "head"
        ]

        if head_indices:
            result[molecule_id] = particle_center(head_indices, positions)

    return result


def cluster_surfactant_molecules(
    particles: list[MiceliumParticle],
    positions: list[Vector],
    cutoff: float = 2.15,
    anchor_kind: str = "tail",
) -> list[list[str]]:
    tail_centers = (surfactant_head_centers if anchor_kind == "head" else surfactant_tail_centers)(particles, positions)

    if not tail_centers:
        return []

    molecule_ids = list(tail_centers.keys())
    cell_size = max(cutoff, 0.5)

    def cell_key(position: Vector) -> tuple[int, int, int]:
        return (
            math.floor(position[0] / cell_size),
            math.floor(position[1] / cell_size),
            math.floor(position[2] / cell_size),
        )

    grid: dict[tuple[int, int, int], list[str]] = {}

    for molecule_id, center in tail_centers.items():
        grid.setdefault(cell_key(center), []).append(molecule_id)

    graph: dict[str, list[str]] = {molecule_id: [] for molecule_id in molecule_ids}

    for molecule_id in molecule_ids:
        center = tail_centers[molecule_id]
        cx, cy, cz = cell_key(center)

        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    bucket = grid.get((cx + dx, cy + dy, cz + dz), [])

                    for other_id in bucket:
                        if other_id <= molecule_id:
                            continue

                        if distance_3d(center, tail_centers[other_id]) <= cutoff:
                            graph[molecule_id].append(other_id)
                            graph[other_id].append(molecule_id)

    visited: set[str] = set()
    clusters: list[list[str]] = []

    for start in molecule_ids:
        if start in visited:
            continue

        queue: deque[str] = deque([start])
        visited.add(start)
        component: list[str] = []

        while queue:
            current = queue.popleft()
            component.append(current)

            for neighbor in graph[current]:
                if neighbor in visited:
                    continue

                visited.add(neighbor)
                queue.append(neighbor)

        if len(component) >= 3:
            clusters.append(component)

    return clusters


def molecule_particle_ids(
    molecule_ids: list[str],
    groups: dict[str, list[int]],
    particles: list[MiceliumParticle],
) -> list[str]:
    ids: list[str] = []

    for molecule_id in molecule_ids:
        for index in groups.get(molecule_id, []):
            ids.append(particles[index].id)

    return ids


def cluster_shape_metrics(member_centers: list[Vector]) -> tuple[float, float]:
    if len(member_centers) < 3:
        return 0.0, 0.0

    center = center_of(member_centers)
    distances = [distance_3d(point, center) for point in member_centers]

    mean_radius = sum(distances) / max(len(distances), 1)
    radius_variance = sum((value - mean_radius) ** 2 for value in distances) / max(len(distances), 1)
    irregularity = min(1.0, math.sqrt(radius_variance) / max(mean_radius, 1e-9))

    xs = [point[0] for point in member_centers]
    ys = [point[1] for point in member_centers]
    zs = [point[2] for point in member_centers]

    extents = sorted(
        [
            max(xs) - min(xs),
            max(ys) - min(ys),
            max(zs) - min(zs),
        ],
        reverse=True,
    )

    anisotropy = 0.0 if extents[0] <= 1e-9 else 1.0 - (extents[2] / extents[0])

    return irregularity, min(1.0, max(0.0, anisotropy))


def orientation_score_for_cluster(
    molecule_ids: list[str],
    tail_centers: dict[str, Vector],
    head_centers: dict[str, Vector],
) -> float:
    valid = [
        molecule_id
        for molecule_id in molecule_ids
        if molecule_id in tail_centers and molecule_id in head_centers
    ]

    if not valid:
        return 0.0

    cluster_tail_center = center_of([tail_centers[molecule_id] for molecule_id in valid])
    total = 0.0

    for molecule_id in valid:
        tail = tail_centers[molecule_id]
        head = head_centers[molecule_id]

        outward = [
            head[0] - tail[0],
            head[1] - tail[1],
            head[2] - tail[2],
        ]

        radial = [
            tail[0] - cluster_tail_center[0],
            tail[1] - cluster_tail_center[1],
            tail[2] - cluster_tail_center[2],
        ]

        outward_norm = math.sqrt(sum(value * value for value in outward))
        radial_norm = math.sqrt(sum(value * value for value in radial))

        if outward_norm <= 1e-9 or radial_norm <= 1e-9:
            continue

        dot = sum(outward[index] * radial[index] for index in range(3))
        cosine = dot / max(outward_norm * radial_norm, 1e-9)

        total += max(0.0, min(1.0, (cosine + 1.0) / 2.0))

    return total / max(len(valid), 1)


def hydrophobic_core_score_for_cluster(
    molecule_ids: list[str],
    tail_centers: dict[str, Vector],
) -> float:
    if len(molecule_ids) < 3:
        return 0.0

    centers = [
        tail_centers[molecule_id]
        for molecule_id in molecule_ids
        if molecule_id in tail_centers
    ]

    if len(centers) < 3:
        return 0.0

    center = center_of(centers)
    distances = [distance_3d(point, center) for point in centers]
    mean_distance = sum(distances) / max(len(distances), 1)

    return max(0.0, min(1.0, 1.0 / (1.0 + max(0.0, mean_distance - 1.6) * 0.42)))


def classify_morphology(
    aggregation_number: int,
    orientation_score: float,
    core_score: float,
    anisotropy: float,
    irregularity: float,
) -> str:
    if aggregation_number < 6:
        return "pré-cluster hidrofóbico"

    if orientation_score < 0.42 or core_score < 0.42:
        return "agregado irregular instável"

    if anisotropy > 0.68:
        return "agregado alongado/cilíndrico provável"

    if irregularity > 0.42:
        return "micela irregular em estabilização"

    if aggregation_number >= 18:
        return "micela esférica irregular provável"

    return "pré-micela orientada"


def geometry_evidence_for_cluster(molecule_ids, tail_centers, head_centers, morphology, tail_tips=None):
    """Mede as coordenadas; a tendência prevista não comprova uma geometria."""
    reverse = "inversa" in morphology.lower()
    planar = "lamelar" in morphology or "bicamada" in morphology
    vesicle = "vesícula" in morphology
    cylinder = "cilíndrica" in morphology or "wormlike" in morphology
    tails = np.array([tail_centers[mid] for mid in molecule_ids])
    heads = np.array([head_centers[mid] for mid in molecule_ids])
    anchors = heads if reverse else tails
    center = anchors.mean(axis=0)
    eigenvalues, axes = principal_axes(anchors)
    chain = heads - tails
    chain /= np.maximum(np.linalg.norm(chain, axis=1)[:, None], 1e-9)
    if planar and not vesicle:
        # As duas folhas afastam as cabeças do plano central. A normal é o
        # diretor nemático das cadeias; as pontas das caudas medem a interface.
        director_values, director_axes = np.linalg.eigh(chain.T @ chain / len(chain))
        normal = director_axes[:, -1]
        interface = np.array([tail_tips[mid] for mid in molecule_ids]) if tail_tips and not reverse else anchors
        centered_interface = interface - interface.mean(axis=0)
        normal_variance = float(np.mean((centered_interface @ normal) ** 2))
        lateral_variance = float(np.mean(np.sum(centered_interface ** 2, axis=1))) - normal_variance
        signed_tail = (tails - center) @ normal
        signed_head = (heads - center) @ normal
        outward = np.where(signed_head[:, None] >= 0, normal, -normal)
        separation = (np.abs(signed_tail) - np.abs(signed_head)) if reverse else (np.abs(signed_head) - np.abs(signed_tail))
        shape_ok = lateral_variance > 2.0 * max(normal_variance, 1e-9) and director_values[-1] > 0.60
    else:
        radial = (tails + heads) * 0.5 - center
        tail_radial, head_radial = tails - center, heads - center
        if cylinder:
            axis = axes[:, -1]
            radial -= np.outer(radial @ axis, axis)
            tail_radial -= np.outer(tail_radial @ axis, axis)
            head_radial -= np.outer(head_radial @ axis, axis)
        outward = radial / np.maximum(np.linalg.norm(radial, axis=1)[:, None], 1e-9)
        difference = np.linalg.norm(head_radial, axis=1) - np.linalg.norm(tail_radial, axis=1)
        separation = np.abs(difference) if vesicle else -difference if reverse else difference
        if cylinder:
            shape_ok = eigenvalues[-1] > eigenvalues[1] * 1.6
        elif vesicle:
            shape_ok = bool(np.any(difference < -0.15) and np.any(difference > 0.15))
        else:
            shape_ok = eigenvalues[-1] < max(eigenvalues[0], 1e-9) * 3.0
    cosine = np.sum(chain * outward, axis=1)
    if vesicle:
        cosine = np.abs(cosine)
    elif reverse:
        cosine = -cosine
    orientation = float(np.mean(np.clip(cosine, 0.0, 1.0)))
    segregation = float(np.mean(separation > 0.18))
    return orientation, segregation, bool(shape_ok)


def mean_head_distance(
    particles: list[MiceliumParticle],
    positions: list[Vector],
    max_pairs: int = 7000,
) -> float | None:
    head_positions = [
        positions[index]
        for index, particle in enumerate(particles)
        if particle.kind == "head"
    ]

    if len(head_positions) < 2:
        return None

    total = 0.0
    pairs = 0

    for i in range(len(head_positions)):
        if pairs >= max_pairs:
            break

        for j in range(i + 1, len(head_positions)):
            if pairs >= max_pairs:
                break

            total += distance_3d(head_positions[i], head_positions[j])
            pairs += 1

    if pairs == 0:
        return None

    return total / pairs


def analyze_micelium_state(
    *,
    particles: list[MiceliumParticle],
    positions: list[Vector],
    environment: MiceliumEnvironment,
    molecule_count: int,
    c_over_cmc_proxy: float | None,
    real_concentration_mmol_l: float | None = None,
    real_amount_mmol: float | None = None,
    critical_amount_mmol: float | None = None,
    missing_amount_mmol: float | None = None,
    excess_amount_mmol: float | None = None,
    visual_scale_factor: float | None = None,
    morphology_hint: str | None = None,
) -> tuple[list[MicelleCluster], MiceliumAnalysis]:
    safe_positions = sanitize_positions(positions)
    groups = group_by_molecule(particles)
    centers = molecule_centers(particles, safe_positions)
    tail_centers = surfactant_tail_centers(particles, safe_positions)
    head_centers = surfactant_head_centers(particles, safe_positions)
    tail_tips = {mid: safe_positions[min((i for i in indices if particles[i].kind == "tail"), key=lambda i: particles[i].bead_index)] for mid, indices in groups.items() if mid in tail_centers}

    surfactant_molecule_ids: set[str] = set()
    solvent_molecule_ids: set[str] = set()
    solute_molecule_ids: set[str] = set()

    for molecule_id, indices in groups.items():
        kind = molecule_kind(indices, particles)

        if kind == "solvent":
            solvent_molecule_ids.add(molecule_id)
        elif kind == "surfactant":
            surfactant_molecule_ids.add(molecule_id)
        else:
            solute_molecule_ids.add(molecule_id)

    cluster_members = cluster_surfactant_molecules(
        particles=particles,
        positions=safe_positions,
        anchor_kind="head" if "inversa" in (morphology_hint or "") else "tail",
    )

    clusters: list[MicelleCluster] = []
    orientation_evidence = []
    core_evidence = []
    organized_molecules = 0

    for cluster_index, molecule_ids in enumerate(cluster_members):
        member_centers = [
            centers[molecule_id]
            for molecule_id in molecule_ids
            if molecule_id in centers
        ]

        if not member_centers:
            continue

        center = center_of(member_centers)
        radius = max(distance_3d(point, center) for point in member_centers)
        aggregation_number = len(molecule_ids)

        orientation_score = orientation_score_for_cluster(
            molecule_ids=molecule_ids,
            tail_centers=tail_centers,
            head_centers=head_centers,
        )

        core_score = hydrophobic_core_score_for_cluster(
            molecule_ids=molecule_ids,
            tail_centers=tail_centers,
        )

        irregularity, anisotropy = cluster_shape_metrics(member_centers)
        shape_ok = False
        if morphology_hint:
            orientation_score, core_score, shape_ok = geometry_evidence_for_cluster(
                molecule_ids, tail_centers, head_centers, morphology_hint, tail_tips,
            )
        orientation_evidence.append((orientation_score, aggregation_number))
        core_evidence.append((core_score, aggregation_number))

        ccmc_score = (
            0.35
            if c_over_cmc_proxy is None
            else max(0.0, min(1.0, (c_over_cmc_proxy - 0.75) / 1.8))
        )

        aggregation_score = max(0.0, min(1.0, aggregation_number / 48.0))
        electrostatic_penalty = max(0.0, 0.16 - environment.ionic_strength_mol_l * 0.75)
        thermal_penalty = max(0.0, (environment.temperature_k - 318.15) / 120.0)

        stability = (
            0.24 * ccmc_score
            + 0.24 * aggregation_score
            + 0.24 * core_score
            + 0.20 * orientation_score
            + 0.08 * max(0.0, 1.0 - irregularity)
            - electrostatic_penalty
            - thermal_penalty
        )

        stability = max(0.0, min(1.0, stability))

        morphology = classify_morphology(
            aggregation_number=aggregation_number,
            orientation_score=orientation_score,
            core_score=core_score,
            anisotropy=anisotropy,
            irregularity=irregularity,
        )

        organized = (
            aggregation_number >= 6 and orientation_score >= 0.62
            and core_score >= 0.70 and shape_ok
            and c_over_cmc_proxy is not None and c_over_cmc_proxy >= 1.0
        )
        if morphology_hint:
            morphology = morphology_hint if organized else "agregado em reorganização"
        if organized:
            organized_molecules += aggregation_number

        clusters.append(
            MicelleCluster(
                id=f"micelle_cluster_{cluster_index + 1}",
                particle_ids=molecule_particle_ids(molecule_ids, groups, particles),
                surfactant_count=aggregation_number,
                center=list(as_xyz(center)),
                radius=radius,
                core_radius=max(0.2, sum(distance_3d((head_centers if "inversa" in (morphology_hint or "") else tail_centers)[mid], center) for mid in molecule_ids) / len(molecule_ids)),
                stability_score=stability,
                aggregation_number=aggregation_number,
                morphology=morphology,
                phase="organização mesoscópica" if organized else "pré-agregação",
            )
        )

    clusters.sort(key=lambda cluster: cluster.stability_score * cluster.surfactant_count, reverse=True)

    largest_cluster_size = max(
        (cluster.surfactant_count for cluster in clusters),
        default=0,
    )

    average_cluster_size = (
        sum(cluster.surfactant_count for cluster in clusters) / len(clusters)
        if clusters
        else 0.0
    )

    stability_score = max(
        (cluster.stability_score for cluster in clusters),
        default=0.0,
    )

    ccmc_term = (
        0.0
        if c_over_cmc_proxy is None
        else max(0.0, min(1.0, (c_over_cmc_proxy - 0.65) / 2.0))
    )

    cluster_term = min(1.0, largest_cluster_size / 42.0)
    stability_term = stability_score
    surfactant_term = min(1.0, len(surfactant_molecule_ids) / 48.0)

    micelle_probability = max(
        0.0,
        min(
            1.0,
            0.25 * ccmc_term
            + 0.25 * cluster_term
            + 0.32 * stability_term
            + 0.18 * surfactant_term,
        ),
    )

    warnings: list[str] = []

    if not particles:
        warnings.append("Nenhuma partícula foi gerada pelo Micelium Engine.")

    if len(surfactant_molecule_ids) == 0:
        warnings.append("Nenhum surfactante detectado; micelização improvável.")

    if len(surfactant_molecule_ids) > 0 and len(surfactant_molecule_ids) < 8:
        warnings.append("Poucos surfactantes para micela estável; resultado deve ser lido como tendência visual.")

    if c_over_cmc_proxy is not None and c_over_cmc_proxy < 1.0:
        warnings.append("C/CMC abaixo de 1; micela estável não deve ser forçada.")

    if clusters and stability_score < 0.42:
        warnings.append("Agregados detectados, mas ainda sem orientação/compactação suficiente para micela estável.")

    if environment.visual_speed_multiplier != 1.0 or environment.simulation_speed:
        warnings.append("Velocidade 3D é parâmetro visual/computacional; não altera química real.")

    analysis = MiceliumAnalysis(
        total_particles=len(particles),
        molecule_count=molecule_count,
        surfactant_count=len(surfactant_molecule_ids),
        solvent_count=len(solvent_molecule_ids),
        solute_count=len(solute_molecule_ids),
        c_over_cmc_proxy=c_over_cmc_proxy,
        real_concentration_mmol_l=real_concentration_mmol_l,
        real_amount_mmol=real_amount_mmol,
        critical_amount_mmol=critical_amount_mmol,
        missing_amount_mmol=missing_amount_mmol,
        excess_amount_mmol=excess_amount_mmol,
        visual_scale_factor=visual_scale_factor,
        micelle_probability=micelle_probability,
        average_cluster_size=average_cluster_size,
        cluster_count=len(clusters),
        largest_cluster_size=largest_cluster_size,
        mean_head_distance=mean_head_distance(particles, safe_positions),
        stability_score=stability_score,
        dominant_morphology=clusters[0].morphology if clusters else "monômeros dispersos",
        morphology_distribution={name: sum(c.morphology == name for c in clusters) for name in {c.morphology for c in clusters}},
        formation_phase=("organização mesoscópica" if organized_molecules else "autoagregação em curso" if clusters else "dispersão"),
        micellized_fraction=organized_molecules / max(len(surfactant_molecule_ids), 1),
        free_monomer_fraction=max(0.0, 1.0 - sum(c.surfactant_count for c in clusters) / max(len(surfactant_molecule_ids), 1)),
        orientation_score=sum(score * weight for score, weight in orientation_evidence) / max(sum(weight for _score, weight in orientation_evidence), 1),
        hydrophobic_core_score=sum(score * weight for score, weight in core_evidence) / max(sum(weight for _score, weight in core_evidence), 1),
        hydrophobic_exposure=1.0 - sum(score * weight for score, weight in core_evidence) / max(sum(weight for _score, weight in core_evidence), 1),
        warnings=warnings,
    )

    return clusters, analysis


