"""Forças visuais dos exemplos documentados (só atuam com plan.documented_example_id).

São guias de visualização, não física calibrada: aproximam as moléculas dos núcleos que o motor já
define para a forma (nucleation_count), moldam a membrana nos exemplos DPPC (disco de duas folhas ou
casca de vesícula), levam a água do exemplo AOT para dentro da camada de cabeças e
põem o salicilato na interface do cilindro (anel para dentro, carboxilato para fora). A forma de cada
agregado continua sendo dada pelas forças de organização existentes (organization.apply_finite_cluster_forces).
Nada aqui é evidência de dinâmica molecular real.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

# Intensidades da guia visual (unidades de velocidade do motor por quadro).
GUIDE_K = 0.020            # aproximação ao agregado principal (só para quem está fora dele)
GUIDE_FREE_RADIUS = 1.2    # raio de captura de um núcleo ainda sem agregado
PLACEMENT_K = 0.120        # água do núcleo e salicilato interfacial
MAX_DELTA_V = 0.030        # teto por conta e por aplicação
CORE_FRACTION = 0.70       # água até 70 % do raio mediano das cabeças
INTERFACE_OFFSET = 0.46    # anel/carboxilato a ± um comprimento de ligação da camada de cabeças
TEMPLATE_K = 0.050         # molde de membrana (bicamada/vesícula) por conta, proporcional ao deslocamento
BOND = 0.46                # comprimento de ligação do modelo CG


@dataclass
class ExampleGroups:
    surfactants: list[tuple[list[int], list[int]]] = field(default_factory=list)   # (cabeças, caudas)
    chain_position: dict[int, int] = field(default_factory=dict)                   # conta de cauda → posição (0 = ponta)
    chain_length: dict[int, int] = field(default_factory=dict)                     # conta de cauda → contas na cadeia
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
            chains: dict[int, list[int]] = {}
            for i in tails:
                chains.setdefault(particles[i].chain_index, []).append(i)
            for chain in chains.values():
                chain.sort(key=lambda i: particles[i].bead_index)
                for position, i in enumerate(chain):
                    groups.chain_position[i] = position
                    groups.chain_length[i] = len(chain)
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

    # 1) Guia de agregação: só as moléculas FORA dos agregados principais (os nucleation_count maiores)
    #    vão até a superfície do agregado principal mais próximo. A forma do agregado principal fica com
    #    as forças de organização existentes (puxar membros comprimia vesícula e bicamada numa bola).
    count = max(1, int(plan.nucleation_count))
    hubs = sorted((c for c in clusters.values() if c.get("size", 0) >= 3), key=lambda c: c["size"], reverse=True)[:count]
    hub_members = set()
    targets = []
    for cluster in hubs:
        members = xyz[cluster["particle_indices"]]
        center = members.mean(axis=0)
        radius = float(np.max(np.linalg.norm(members - center, axis=1)))
        targets.append((center, radius))
        hub_members.update(cluster["particle_indices"])
    for point in nucleus_points(count, box_size)[len(targets):]:
        targets.append((point, GUIDE_FREE_RADIUS))
    for heads, tails in groups.surfactants:
        if heads[0] in hub_members:
            continue
        anchor = xyz[heads if reverse else tails].mean(axis=0)
        center, radius = min(targets, key=lambda t: float(np.linalg.norm(anchor - t[0])))
        offset = center - anchor
        distance = float(np.linalg.norm(offset))
        if distance <= radius + 0.5:
            continue
        pull = offset / distance * (GUIDE_K * alpha * min(distance - radius - 0.5, 3.0))
        for index in heads + tails:
            _push(velocities, particles, index, pull)

    # 2) Molde de membrana (DPPC: bicamada e vesícula), só nos agregados principais.
    apply_membrane_template(xyz=xyz, velocities=velocities, particles=particles, groups=groups, hubs=hubs, plan=plan)

    big = [c for c in clusters.values() if c.get("size", 0) >= 3 and c.get("head_indices")]
    if not big:
        return

    # 3) Água do núcleo (AOT): para dentro da camada de cabeças da micela inversa mais próxima.
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

    # 4) Salicilato (CTAB): na interface do cilindro, 1:1 com as cabeças do agregado, anel para dentro.
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


def apply_membrane_template(*, xyz, velocities, particles, groups: ExampleGroups, hubs, plan) -> None:
    """Molde de membrana dos exemplos DPPC (demonstração representativa, força visual).

    Bicamada: disco de duas folhas perpendicular ao eixo que o motor guarda para o agregado.
    Vesícula: casca com folha interna e externa. Cada molécula fica na folha indicada pela orientação
    atual da sua cadeia; as caudas das duas cadeias vão para o meio da membrana, a cabeça para fora dela.
    """
    morphology = plan.morphology.lower()
    vesicle = "vesícula" in morphology
    planar = not vesicle and ("bicamada" in morphology or "lamelar" in morphology)
    if not (vesicle or planar):
        return
    alpha = float(plan.final_alpha)
    for cluster in hubs:
        members = set(cluster["particle_indices"])
        molecules = [(h, t) for h, t in groups.surfactants if h[0] in members]
        if len(molecules) < 6:
            continue
        center = xyz[cluster["particle_indices"]].mean(axis=0)
        normal = np.asarray(cluster.get("organization_axis") or np.linalg.eigh(
            np.cov((xyz[cluster["particle_indices"]] - center).T))[1][:, 0], dtype=float)
        normal /= max(float(np.linalg.norm(normal)), 1e-9)
        count = len(molecules)
        # Disco com metade das moléculas por folha, ~0,8 de espaçamento entre cabeças (sem sobreposição).
        disk_radius = 0.8 * math.sqrt(count / 2.0 / math.pi) * math.sqrt(math.pi)
        # Vesícula mínima (escala reduzida): folha interna com cabeças a 0,9 do centro; mantém as caudas das
        # duas folhas dentro do alcance de contato do detector de agregados (casca maior se partia).
        longest = max((groups.chain_length.get(t[0], len(t)) for _h, t in molecules), default=1)
        shell_radius = (longest - 1) * BOND + 0.68 + 0.9
        # Espalhamento lateral (bicamada): cada molécula vai para o raio do disco que corresponde à sua
        # posição na ordem atual de distância ao eixo (preenche o disco sem trocar vizinhanças).
        lateral_rank: dict[int, float] = {}
        if planar:
            def lateral_distance(molecule):
                offset = (xyz[molecule[0]].mean(axis=0) + xyz[molecule[1]].mean(axis=0)) / 2.0 - center
                return float(np.linalg.norm(offset - normal * float(offset @ normal)))
            ordered = sorted(molecules, key=lateral_distance)
            for rank, (heads_r, _tails_r) in enumerate(ordered):
                lateral_rank[heads_r[0]] = disk_radius * math.sqrt((rank + 0.5) / len(ordered))
        for heads, tails in molecules:
            head = xyz[heads].mean(axis=0)
            tail = xyz[tails].mean(axis=0)
            molecular = (head + tail) / 2.0
            length = max(groups.chain_length.get(tails[0], len(tails)), 1)
            head_height = (length - 1) * BOND + 0.68
            if planar:
                leaflet = 1.0 if float((head - tail) @ normal) >= 0 else -1.0
                offset = molecular - center
                lateral = offset - normal * float(offset @ normal)
                lateral_length = float(np.linalg.norm(lateral))
                if lateral_length > 1e-9:
                    lateral *= lateral_rank.get(heads[0], disk_radius) / lateral_length
                base, direction = center + lateral, normal * leaflet
                head_target = base + direction * head_height
                tail_target = {i: base + direction * (0.20 + groups.chain_position.get(i, 0) * BOND) for i in tails}
            else:
                radial = molecular - center
                radial_length = float(np.linalg.norm(radial))
                outward = radial / radial_length if radial_length > 1e-9 else normal
                leaflet = 1.0 if float((head - tail) @ outward) >= 0 else -1.0
                head_target = center + outward * max(0.3, shell_radius + leaflet * head_height)
                tail_target = {i: center + outward * max(0.3, shell_radius + leaflet * (0.20 + groups.chain_position.get(i, 0) * BOND))
                               for i in tails}
            for index in heads:
                _push(velocities, particles, index, (head_target - xyz[index]) * (TEMPLATE_K * alpha))
            for index in tails:
                _push(velocities, particles, index, (tail_target[index] - xyz[index]) * (TEMPLATE_K * alpha))
