"""Restrições e campo médio mesoscópico para o motor CG existente.

As superfícies são mínimos de energia locais de clusters detectados, não uma
trajetória ou distribuição pré-calculada de moléculas. Raios em unidades CG;
este campo qualitativo não constitui uma previsão de equilíbrio atomístico.
"""
from __future__ import annotations

import math

import numpy as np


def principal_axes(points):
    xyz = np.asarray(points, dtype=float)
    centered = xyz - xyz.mean(axis=0)
    values, vectors = np.linalg.eigh(centered.T @ centered / max(len(xyz), 1))
    return values, vectors


def constrain_bond_lengths(positions, indexed_bonds, iterations=8):
    """Projeção de comprimentos, sem trocar a topologia ou mover ao centro.

    Bonds adjacentes se sobrepõem por construção no modelo CG. Colisões
    intermoleculares são tratadas separadamente pelo solver de volume excluído.
    """
    for _ in range(iterations):
        for a, b, rest, _stiffness in indexed_bonds:
            delta = [positions[b][k] - positions[a][k] for k in range(3)]
            dist = math.sqrt(sum(v * v for v in delta))
            if dist < 1e-10:
                positions[a][0] -= rest * 0.5
                positions[b][0] += rest * 0.5
                continue
            correction = 0.5 * (dist - rest) / dist
            for k in range(3):
                shift = delta[k] * correction
                positions[a][k] += shift
                positions[b][k] -= shift


def apply_local_encounter_forces(*, positions, velocities, groups, particles, plan):
    """Aproximação local, simétrica, sem força em direção à origem da cena."""
    if plan.micellized_fraction <= 0.05:
        return
    reverse = "inversa" in plan.morphology.lower()
    anchor_kind = "head" if reverse else "tail"
    active = []
    for indices in groups.values():
        anchors = [i for i in indices if particles[i].kind == anchor_kind]
        if not anchors or not any(particles[i].kind == "head" for i in indices):
            continue
        active.append((indices, np.mean([positions[i] for i in anchors], axis=0)))
    if len(active) < 2:
        return
    centers = np.array([center for _indices, center in active])
    delta = centers[None, :, :] - centers[:, None, :]
    distance = np.linalg.norm(delta, axis=2)
    # Somente a região de captura; o contato próximo fica com forças de beads.
    mask = (distance > 1.8) & (distance < 5.5)
    weight = np.where(mask, np.minimum(distance - 1.8, 5.5 - distance), 0.0)
    strength = 0.0035 * plan.final_alpha
    forces = strength * np.sum(delta / np.maximum(distance[:, :, None], 1e-9) * weight[:, :, None], axis=1)
    # Um limite comum preserva a soma nula das forças de encontro.
    peak = float(np.max(np.linalg.norm(forces, axis=1)))
    if peak > 0.025:
        forces *= 0.025 / peak
    for (indices, _center), force in zip(active, forces):
        for i in indices:
            for k in range(3):
                velocities[i][k] += float(force[k]) / len(indices)


def apply_chain_bending_forces(*, positions, velocities, groups, particles):
    """Rigidez angular suave: comprimentos corretos não impedem uma cauda de
    dobrar sobre si mesma e virar um novelo de beads dentro do agregado."""
    for indices in groups.values():
        chain = sorted((i for i in indices if particles[i].kind in {"tail", "head"}), key=lambda i: particles[i].bead_index)
        for a, b, c in zip(chain, chain[1:], chain[2:]):
            for k in range(3):
                curvature = positions[a][k] - 2.0 * positions[b][k] + positions[c][k]
                force = 0.12 * curvature
                velocities[a][k] -= force / max(particles[a].mass, 0.1)
                velocities[b][k] += 2.0 * force / max(particles[b].mass, 0.1)
                velocities[c][k] -= force / max(particles[c].mass, 0.1)


def apply_finite_cluster_forces(*, positions, velocities, particles, clusters, plan):
    """Segregação e orientação com raio finito e eixos de inércia estáveis.

    Cada molécula conserva seus bonds. O campo depende do cluster atual, do
    volume de seus beads e do contorno das caudas; não há slots angulares,
    núcleo fixo na origem ou imposição de uma esfera a toda composição.
    """
    if plan.micellized_fraction <= 0.05 or not getattr(plan, "geometry_template", True):
        return   # sem CPP válido não há forma prevista para impor ao agregado
    morphology = plan.morphology.lower()
    reverse = "inversa" in morphology
    vesicle = "vesícula" in morphology
    planar = not vesicle and ("lamelar" in morphology or "bicamada" in morphology)
    cylinder = "cilíndrica" in morphology or "wormlike" in morphology

    for cluster in clusters.values():
        if cluster["size"] < 3:
            continue
        by_molecule = {}
        for i in cluster["particle_indices"]:
            by_molecule.setdefault(particles[i].molecule_id, []).append(i)
        molecules = []
        for indices in by_molecule.values():
            tails = sorted((i for i in indices if particles[i].kind == "tail"), key=lambda i: particles[i].bead_index)
            heads = [i for i in indices if particles[i].kind == "head"]
            if tails and heads:
                molecules.append((tails, heads))
        if len(molecules) < 3:
            continue

        xyz = np.asarray(positions, dtype=float)
        anchors = [np.mean(xyz[heads if reverse else tails], axis=0) for tails, heads in molecules]
        if planar and not reverse:
            # A normal da membrana vem da interface entre as pontas das caudas.
            # Incluir cabeças nas duas folhas fazia o eixo girar em 90 graus.
            anchors = [xyz[tails[0]] for tails, _heads in molecules]
        center = np.mean(anchors, axis=0)
        _eigenvalues, axes = principal_axes(anchors)
        axis = axes[:, -1] if cylinder else axes[:, 0]
        saved_axis = cluster.get("organization_axis")
        if saved_axis is not None:
            axis = np.asarray(saved_axis, dtype=float)
        # O sinal de um autovetor não deve alternar entre passos.
        if axis[int(np.argmax(np.abs(axis)))] < 0:
            axis = -axis
        cluster["organization_axis"] = axis.tolist()

        tail_indices = [i for tails, _heads in molecules for i in tails]
        head_indices = [i for _tails, heads in molecules for i in heads]
        tail_volume = sum(4.0 * math.pi * particles[i].radius ** 3 / 3.0 for i in tail_indices) / 0.64
        head_volume = sum(4.0 * math.pi * particles[i].radius ** 3 / 3.0 for i in head_indices) / 0.64
        contour = float(np.mean([max(1, len(tails) - 1) * 0.46 for tails, _heads in molecules]))
        core_radius = max(0.65, (3.0 * (head_volume if reverse else tail_volume) / (4.0 * math.pi)) ** (1.0 / 3.0))
        cylinder_radius = max(0.65, contour * 0.85)
        half_length = max(0.25, (tail_volume - 4.0 * math.pi * cylinder_radius ** 3 / 3.0) / (2.0 * math.pi * cylinder_radius ** 2))
        axial_sigma = float(np.std((np.asarray(anchors) - center) @ axis))
        axial_dilation = float(np.clip((half_length / math.sqrt(3.0)) / max(axial_sigma, 0.1), 0.8, 1.3))
        membrane_radius = max(contour + 0.9, math.sqrt(tail_volume / (4.0 * math.pi * max(2.0 * contour, 0.9)) ))
        disk_radius = max(1.0, math.sqrt(tail_volume / (2.0 * math.pi * max(contour, 0.7))))
        strength = (0.095 if planar else 0.065) * plan.final_alpha * min(1.0, len(molecules) / 8.0)
        contributions = []

        for tails, heads in molecules:
            indices = tails + heads
            molecular_center = np.mean(xyz[indices], axis=0)
            offset = molecular_center - center
            distance = float(np.linalg.norm(offset))
            normal = offset / distance if distance > 1e-9 else np.array([1.0, 0.0, 0.0])
            base = center
            chain_axis = np.mean(xyz[heads], axis=0) - xyz[tails[0]]
            leaflet = 1.0
            axial_force = np.zeros(3)

            if planar:
                leaflet = 1.0 if float(np.dot(chain_axis, axis)) >= 0 else -1.0
                if reverse:
                    leaflet = -leaflet
                lateral = offset - axis * float(np.dot(offset, axis))
                lateral_length = float(np.linalg.norm(lateral))
                if lateral_length > disk_radius:
                    lateral *= disk_radius / lateral_length
                base = center + lateral
                normal = axis * leaflet
                radii = [0.20 + j * 0.46 for j in range(len(tails))] + [0.20 + (len(tails) - 1) * 0.46 + 0.48] * len(heads)
                if reverse:
                    radii = [0.70 + (len(tails) - 1 - j) * 0.46 for j in range(len(tails))] + [0.22] * len(heads)
            elif vesicle:
                leaflet = 1.0 if float(np.dot(chain_axis, normal)) >= 0 else -1.0
                radii = [max(0.25, membrane_radius + leaflet * j * 0.46) for j in range(len(tails))]
                radii += [max(0.25, membrane_radius + leaflet * ((len(tails) - 1) * 0.46 + 0.48))] * len(heads)
            else:
                radius = core_radius
                if cylinder:
                    projection = float(np.clip(np.dot(offset, axis), -half_length, half_length))
                    axis_point = center + axis * projection
                    base = center + axis * float(np.clip(projection * axial_dilation, -half_length, half_length))
                    # Pressão axial de densidade: sem ela a atração isotrópica
                    # encurta o cilindro até voltar a um glóbulo.
                    axial_force = axis * (float(np.dot(base - molecular_center, axis))) * (0.14 * plan.final_alpha)
                    radial = molecular_center - axis_point
                    length = float(np.linalg.norm(radial))
                    normal = radial / length if length > 1e-9 else axes[:, 0]
                    radius = cylinder_radius
                if reverse:
                    radii = [radius + 0.48 + (len(tails) - 1 - j) * 0.46 for j in range(len(tails))] + [radius] * len(heads)
                else:
                    # O núcleo não pode ultrapassar o contorno da molécula.
                    radius = min(radius, contour + 0.75)
                    radii = [max(0.16, radius - (len(tails) - 1 - j) * 0.46) for j in range(len(tails))] + [radius + 0.48] * len(heads)

            for i, radius in zip(indices, radii):
                displacement = base + normal * radius - xyz[i]
                force = strength * displacement + axial_force
                contributions.append((i, force))

        if not contributions:
            continue
        # Campo interno: remove translação líquida antes de aplicá-lo.
        average_force = np.mean([force for _i, force in contributions], axis=0)
        corrected = [force - average_force for _i, force in contributions]
        peak = max(float(np.linalg.norm(force)) for force in corrected)
        factor = min(1.0, 0.075 / max(peak, 1e-9))
        for (i, _force), force in zip(contributions, corrected):
            for k in range(3):
                velocities[i][k] += float(force[k]) * factor / max(particles[i].mass, 0.1)
