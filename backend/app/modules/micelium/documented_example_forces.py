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
TEMPLATE_K = 0.500         # molde de membrana (bicamada/vesícula) por conta, proporcional ao deslocamento
MAX_TEMPLATE_DELTA_V = 0.120
VESICLE_LUMEN = 1.6        # raio das cabeças internas da vesícula: deixa uma cavidade visível no centro
ROD_STEP = 0.33            # comprimento do cilindro por molécula (CTAB): 27 moléculas → ~9 unidades
ROD_TIP_RADIUS = 0.35      # pontas das caudas perto do eixo, sem empilhar contas no mesmo ponto
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


def _push(velocities, particles, index: int, force: np.ndarray, cap: float = MAX_DELTA_V) -> None:
    norm = float(np.linalg.norm(force))
    if norm > cap:
        force = force * (cap / norm)
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

    # Exemplos DPPC: o molde de membrana substitui a guia e as forças gerais de organização (ver engine).
    if is_membrane_demo(plan):
        apply_membrane_template(xyz=xyz, velocities=velocities, particles=particles, groups=groups, plan=plan)
        return
    # Exemplo CTAB: o molde de cilindro substitui a guia e as forças gerais; o salicilato segue abaixo.
    rod = is_rod_demo(plan)
    if rod:
        apply_rod_template(xyz=xyz, velocities=velocities, particles=particles, groups=groups, plan=plan)

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
    for heads, tails in ([] if rod else groups.surfactants):
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


def is_rod_demo(plan) -> bool:
    morphology = plan.morphology.lower()
    return bool(plan.documented_example_id) and ("cilíndrica" in morphology or "wormlike" in morphology)


def is_template_demo(plan) -> bool:
    """Exemplos cuja forma vem de um molde visual (membranas DPPC, cilindro CTAB)."""
    return is_membrane_demo(plan) or is_rod_demo(plan)


def apply_rod_template(*, xyz, velocities, particles, groups: ExampleGroups, plan) -> None:
    """Molde visual de cilindro do exemplo CTAB (demonstração representativa, força visual).

    Um trecho de micela vermiforme ao longo de x, em volta do centro das moléculas: as cabeças ocupam uma
    hélice de ângulo áureo na superfície e as caudas apontam para o eixo. Cada molécula fica com o ponto livre
    mais próximo da sua cabeça atual. Comprimento ROD_STEP por molécula: com poucas moléculas, um cilindro
    compacto de mesmo volume seria quase esférico; a cena mostra a geometria, não a densidade real.
    """
    molecules = groups.surfactants
    if len(molecules) < 6:
        return
    gain = TEMPLATE_K * float(plan.final_alpha)
    every = [i for heads, tails in molecules for i in heads + tails]
    center = xyz[every].mean(axis=0)
    axis, side_u, side_v = np.eye(3)
    longest = max((groups.chain_length.get(t[0], len(t)) for _h, t in molecules), default=1)
    head_radius = ROD_TIP_RADIUS + (longest - 1) * BOND + 0.48
    count = len(molecules)
    length = ROD_STEP * count
    golden = math.pi * (3.0 - math.sqrt(5.0))
    sites = []
    for k in range(count):
        radial = math.cos(golden * k) * side_u + math.sin(golden * k) * side_v
        sites.append((axis * (-length / 2.0 + (k + 0.5) * length / count), radial))
    free = list(range(count))
    for heads, tails in molecules:
        head = xyz[heads].mean(axis=0) - center
        best = min(free, key=lambda k: float(np.linalg.norm(sites[k][0] + sites[k][1] * head_radius - head)))
        free.remove(best)
        base, radial = sites[best]
        head_target = center + base + radial * head_radius
        for index in heads:
            _push(velocities, particles, index, (head_target - xyz[index]) * gain, cap=MAX_TEMPLATE_DELTA_V)
        for index in tails:
            target = center + base + radial * (ROD_TIP_RADIUS + groups.chain_position.get(index, 0) * BOND)
            _push(velocities, particles, index, (target - xyz[index]) * gain, cap=MAX_TEMPLATE_DELTA_V)


def is_membrane_demo(plan) -> bool:
    morphology = plan.morphology.lower()
    return bool(plan.documented_example_id) and ("vesícula" in morphology or "bicamada" in morphology or "lamelar" in morphology)


def apply_membrane_template(*, xyz, velocities, particles, groups: ExampleGroups, plan) -> None:
    """Molde de membrana dos exemplos DPPC (demonstração representativa, força visual).

    Atua sobre TODAS as moléculas do exemplo, em volta do centro delas (um agregado só):
    - bicamada: disco de duas folhas perpendicular a z; a folha de cada molécula segue a orientação atual
      da sua cadeia; as moléculas se espalham pelo disco na ordem da distância ao eixo;
    - vesícula: casca mínima com folha interna e externa e cavidade central (cabeças internas a
      VESICLE_LUMEN do centro).
    As caudas das duas cadeias vão para o meio da membrana e a cabeça para a face.
    """
    morphology = plan.morphology.lower()
    vesicle = "vesícula" in morphology
    molecules = groups.surfactants
    if len(molecules) < 6:
        return
    alpha = float(plan.final_alpha)
    gain = TEMPLATE_K * alpha
    every = [i for heads, tails in molecules for i in heads + tails]
    center = xyz[every].mean(axis=0)
    normal = np.array([0.0, 0.0, 1.0])
    longest = max((groups.chain_length.get(t[0], len(t)) for _h, t in molecules), default=1)
    head_height = (longest - 1) * BOND + 0.68
    count = len(molecules)
    # Disco com metade das moléculas por folha e ~0,8 de espaçamento entre cabeças.
    disk_radius = 0.8 * math.sqrt(count / 2.0)
    shell_radius = head_height + VESICLE_LUMEN
    shell_direction: dict[int, np.ndarray] = {}
    if vesicle:
        # Direções-alvo uniformes na casca (espiral de Fibonacci); cada molécula fica com o ponto livre mais
        # próximo da sua direção atual (preenche a casca toda, sem lado vazio).
        golden = math.pi * (3.0 - math.sqrt(5.0))
        points = []
        for k in range(count):
            z = 1.0 - 2.0 * (k + 0.5) / count
            r = math.sqrt(max(0.0, 1.0 - z * z))
            points.append(np.array([r * math.cos(golden * k), r * math.sin(golden * k), z]))
        free = list(range(count))
        for heads_m, tails_m in molecules:
            current = (xyz[heads_m].mean(axis=0) + xyz[tails_m].mean(axis=0)) / 2.0 - center
            norm = float(np.linalg.norm(current))
            current = current / norm if norm > 1e-9 else normal
            best = max(free, key=lambda k: float(points[k] @ current))
            free.remove(best)
            shell_direction[heads_m[0]] = points[best]
    # Folhas por cota (não pela orientação do momento): bicamada 1/2 + 1/2; vesícula 1/3 interna + 2/3 externa
    # (folha interna densa com cabeças a 0,9 do centro). As moléculas que já apontam para o lado certo ficam nele.
    leaflet_of: dict[int, float] = {}
    def orientation(molecule):
        heads_m, tails_m = molecule
        chain = xyz[heads_m].mean(axis=0) - xyz[tails_m].mean(axis=0)
        if vesicle:
            return float(chain @ shell_direction[heads_m[0]])
        return float(chain @ normal)
    ranked = sorted(molecules, key=orientation)
    lower_quota = round(count / 3) if vesicle else count // 2
    for rank, (heads_m, _tails_m) in enumerate(ranked):
        leaflet_of[heads_m[0]] = -1.0 if rank < lower_quota else 1.0
    lateral_target: dict[int, np.ndarray] = {}
    if not vesicle:
        # Cada face preenche o disco em padrão de girassol; cada molécula fica com o ponto livre mais próximo
        # da sua posição lateral atual (sem lobos vazios).
        axis_u = np.array([1.0, 0.0, 0.0])
        axis_v = np.array([0.0, 1.0, 0.0])
        golden = math.pi * (3.0 - math.sqrt(5.0))
        for side in (-1.0, 1.0):
            members = [m for m in molecules if leaflet_of[m[0][0]] == side]
            total = max(len(members), 1)
            points = [disk_radius * math.sqrt((k + 0.5) / total) * (math.cos(golden * k) * axis_u + math.sin(golden * k) * axis_v)
                      for k in range(len(members))]
            free = list(range(len(members)))
            for heads_m, tails_m in members:
                current = (xyz[heads_m].mean(axis=0) + xyz[tails_m].mean(axis=0)) / 2.0 - center
                current = current - normal * float(current @ normal)
                best = min(free, key=lambda k: float(np.linalg.norm(points[k] - current)))
                free.remove(best)
                lateral_target[heads_m[0]] = points[best]
    for heads, tails in molecules:
        head = xyz[heads].mean(axis=0)
        tail = xyz[tails].mean(axis=0)
        molecular = (head + tail) / 2.0
        if not vesicle:
            leaflet = leaflet_of[heads[0]]
            base, direction = center + lateral_target[heads[0]], normal * leaflet
            head_target = base + direction * head_height
            tail_target = {i: base + direction * (0.20 + groups.chain_position.get(i, 0) * BOND) for i in tails}
        else:
            outward = shell_direction[heads[0]]
            leaflet = leaflet_of[heads[0]]
            head_target = center + outward * (shell_radius + leaflet * head_height)
            tail_target = {i: center + outward * (shell_radius + leaflet * (0.20 + groups.chain_position.get(i, 0) * BOND))
                           for i in tails}
        for index in heads:
            _push(velocities, particles, index, (head_target - xyz[index]) * gain, cap=MAX_TEMPLATE_DELTA_V)
        for index in tails:
            _push(velocities, particles, index, (tail_target[index] - xyz[index]) * gain, cap=MAX_TEMPLATE_DELTA_V)
