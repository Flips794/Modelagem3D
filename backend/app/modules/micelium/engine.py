from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass, field

from app.modules.micelium.analyzer import analyze_micelium_state
from app.modules.micelium.ai_bridge import enrich_molecules_with_ai
from app.modules.micelium.mapping import build_particle_template, infer_surfactant_like, stable_id
from app.modules.micelium.organization import (
    apply_local_encounter_forces,
    apply_chain_bending_forces,
    apply_finite_cluster_forces,
    constrain_bond_lengths,
)
from app.modules.micelium.schemas import (
    MiceliumBond,
    MiceliumFrame,
    MiceliumMoleculeInput,
    MiceliumParticle,
    MiceliumSimulationRequest,
    MiceliumSimulationResponse,
)
from app.modules.micelium.vector_utils import sanitize_positions


Vector = list[float]


# Estado leve em memória para continuidade por chunks REST.
# Chaveado pela mistura/ambiente; ignora seed para evitar reset entre chunks.
_MICELIUM_SESSION_STATE: dict[str, dict[str, object]] = {}


@dataclass(slots=True)
class MicellizationMetrics:
    c_over_cmc: float | None
    real_concentration_mmol_l: float | None
    real_amount_mmol: float | None
    critical_amount_mmol: float | None
    missing_amount_mmol: float | None
    excess_amount_mmol: float | None
    visual_scale_factor: float | None
    ignored_components: list[str] = field(default_factory=list)
    # c/CMC só dos componentes com CMC conhecida; o total (c_over_cmc) fica None se algo foi ignorado.
    partial_c_over_cmc: float | None = None


@dataclass(slots=True)
class FormationPlan:
    morphology: str
    formation_phase: str
    micellized_fraction: float
    free_monomer_fraction: float
    nucleation_count: int
    final_alpha: float
    orientation_score: float
    hydrophobic_core_score: float
    hydrophobic_exposure: float
    # Web Lite v1: sem CPP válido não há molde geométrico; base declarada da previsão.
    geometry_template: bool = True
    morphology_basis: str = ""


@dataclass(slots=True)
class SolventEnvironmentProfile:
    name: str
    polarity: float
    hydrophobicity: float
    dielectric: float
    protic_score: float
    aggregation_modifier: float
    inverse_modifier: float
    cmc_modifier: float
    notes: list[str]


def infer_solvent_profile(request: MiceliumSimulationRequest) -> SolventEnvironmentProfile:
    solvent_molecules = [molecule for molecule in request.molecules if molecule.role == "solvent"]
    env = request.environment
    label = (env.solvent_name or "").lower()
    notes: list[str] = []

    solvent_polarity = clamp(float(env.solvent_polarity_index), 0.0, 1.0)
    solvent_hydrophobicity = clamp(1.0 - solvent_polarity, 0.0, 1.0)
    protic_score = 0.55 if solvent_polarity >= 0.55 else 0.18

    dielectric_hint = None
    if solvent_molecules:
        first = solvent_molecules[0]
        label = f"{first.name or ''} {first.formula or ''} {first.smiles or ''}".lower()
        notes.append(f"Solvente selecionado em excesso: {first.name or first.formula or first.smiles}.")

        if first.smiles.strip() == "O" or "água" in label or "agua" in label or "water" in label or "h2o" in label:
            solvent_polarity = max(solvent_polarity, 0.98)
            solvent_hydrophobicity = min(solvent_hydrophobicity, 0.02)
            protic_score = 1.0
            solvent_name = "água"
        elif first.smiles.strip() in {"CCO", "OCC"} or re.search(r"\b(?:etanol|ethanol)\b", label):
            solvent_polarity = 0.62
            dielectric_hint = 24.5
            solvent_hydrophobicity = 0.28
            protic_score = 0.82
            solvent_name = "etanol"
        elif first.smiles.strip() in {"CO", "OC"} or "metanol" in label or "methanol" in label:
            solvent_polarity = 0.78
            dielectric_hint = 32.6
            solvent_hydrophobicity = 0.12
            protic_score = 0.90
            solvent_name = "metanol"
        elif "óleo" in label or "oleo" in label or "oil" in label or "hexan" in label or re.fullmatch(r"C{5,}", first.smiles.strip()):
            solvent_polarity = 0.08
            dielectric_hint = 1.9
            solvent_hydrophobicity = 0.88
            protic_score = 0.05
            solvent_name = "meio apolar"
        else:
            solvent_name = first.name or first.formula or "solvente personalizado"
    else:
        solvent_name = env.solvent_name or "meio contínuo"
        # Mesmo perfil para solvente contínuo e traçadores explícitos. Valores
        # personalizados do painel continuam prevalecendo sobre padrões.
        if solvent_polarity == 1.0:
            if re.search(r"\b(?:etanol|ethanol)\b", label):
                solvent_polarity, protic_score, dielectric_hint = 0.62, 0.82, 24.5
            elif "metanol" in label or "methanol" in label:
                solvent_polarity, protic_score, dielectric_hint = 0.78, 0.90, 32.6
            elif any(token in label for token in ("hexan", "heptan", "óleo", "oleo", "oil", "apolar")):
                solvent_polarity, protic_score, dielectric_hint = 0.08, 0.05, 1.9
        solvent_hydrophobicity = 1.0 - solvent_polarity

    dielectric = max(1.0, float(env.dielectric_constant))
    if dielectric_hint is not None and abs(dielectric - 78.5) < 1e-6:
        dielectric = dielectric_hint
    ionic = max(0.0, float(env.ionic_strength_mol_l))

    water_like = solvent_polarity >= 0.82 and dielectric >= 45
    ethanol_like = 0.42 <= solvent_polarity < 0.82 or 15 <= dielectric < 45
    apolar_like = solvent_polarity < 0.35 or dielectric < 15

    if water_like:
        aggregation_modifier = 1.00 + min(0.18, ionic * 1.8)
        inverse_modifier = 0.12
        cmc_modifier = max(0.55, 1.0 - min(0.35, ionic * 2.3))
        notes.append("Meio aquoso/polar: favorece núcleo hidrofóbico clássico e cabeças expostas.")
    elif apolar_like:
        aggregation_modifier = 0.38
        inverse_modifier = 1.00
        cmc_modifier = 2.60
        notes.append("Meio apolar: favorece orientação inversa ou agregados reversos.")
    elif ethanol_like:
        aggregation_modifier = 0.62 + min(0.16, ionic * 0.8)
        inverse_modifier = 0.25
        cmc_modifier = 1.65
        notes.append("Meio alcoólico/cossolvente: reduz contraste hidrofóbico; agregação fica mais frouxa e lenta.")
    else:
        aggregation_modifier = 0.78
        inverse_modifier = 0.45
        cmc_modifier = 1.35
        notes.append("Meio misto: micelização intermediária e mais sensível à composição.")

    return SolventEnvironmentProfile(
        name=solvent_name,
        polarity=solvent_polarity,
        hydrophobicity=solvent_hydrophobicity,
        dielectric=dielectric,
        protic_score=protic_score,
        aggregation_modifier=clamp(aggregation_modifier, 0.05, 1.35),
        inverse_modifier=clamp(inverse_modifier, 0.0, 1.2),
        cmc_modifier=clamp(cmc_modifier, 0.30, 4.0),
        notes=notes,
    )


def random_unit_vector(rng: random.Random) -> Vector:
    z = rng.uniform(-1.0, 1.0)
    theta = rng.uniform(0.0, math.tau)
    radius = math.sqrt(max(0.0, 1.0 - z * z))
    return [radius * math.cos(theta), radius * math.sin(theta), z]


def normalize(vector: Vector) -> Vector:
    length = math.sqrt(sum(v * v for v in vector))
    if length <= 1e-9:
        return [1.0, 0.0, 0.0]
    return [v / length for v in vector]



def dot(a: Vector, b: Vector) -> float:
    """
    Produto escalar entre dois vetores 3D.

    v30.2:
    Implementação direta para este engine.py.
    Aceita listas/tuplas com pelo menos 3 valores.
    """
    try:
        ax = float(a[0])
        ay = float(a[1])
        az = float(a[2])
        bx = float(b[0])
        by = float(b[1])
        bz = float(b[2])
    except Exception:
        return 0.0

    return ax * bx + ay * by + az * bz


def add(a: Vector, b: Vector) -> Vector:
    return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]


def sub(a: Vector, b: Vector) -> Vector:
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]


def scale(vector: Vector, factor: float) -> Vector:
    return [vector[0] * factor, vector[1] * factor, vector[2] * factor]


def lerp(a: Vector, b: Vector, t: float) -> Vector:
    return [
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
    ]


def clamp(value: float, low: float, high: float) -> float:
    if not math.isfinite(value):
        return low
    return max(low, min(high, value))


def smoothstep(value: float) -> float:
    t = clamp(value, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def add_jitter(center: Vector, rng: random.Random, amount: float) -> Vector:
    if amount <= 0:
        return center
    return [
        center[0] + rng.uniform(-amount, amount),
        center[1] + rng.uniform(-amount, amount),
        center[2] + rng.uniform(-amount, amount),
    ]


def local_to_oriented(local: Vector, base: Vector, direction: Vector | None) -> Vector:
    if direction is None:
        return [base[0] + local[0], base[1] + local[1], base[2] + local[2]]

    x_axis = normalize(direction)
    helper = [0.0, 1.0, 0.0] if abs(x_axis[1]) < 0.85 else [0.0, 0.0, 1.0]

    z_axis = normalize(
        [
            x_axis[1] * helper[2] - x_axis[2] * helper[1],
            x_axis[2] * helper[0] - x_axis[0] * helper[2],
            x_axis[0] * helper[1] - x_axis[1] * helper[0],
        ]
    )
    y_axis = normalize(
        [
            z_axis[1] * x_axis[2] - z_axis[2] * x_axis[1],
            z_axis[2] * x_axis[0] - z_axis[0] * x_axis[2],
            z_axis[0] * x_axis[1] - z_axis[1] * x_axis[0],
        ]
    )

    return [
        base[0] + x_axis[0] * local[0] + y_axis[0] * local[1] + z_axis[0] * local[2],
        base[1] + x_axis[1] * local[0] + y_axis[1] * local[1] + z_axis[1] * local[2],
        base[2] + x_axis[2] * local[0] + y_axis[2] * local[1] + z_axis[2] * local[2],
    ]


def golden_sphere_direction(index: int, total: int, rng: random.Random) -> Vector:
    if total <= 1:
        return random_unit_vector(rng)
    offset = 2.0 / total
    increment = math.pi * (3.0 - math.sqrt(5.0))
    y = ((index * offset) - 1.0) + offset / 2.0
    radius = math.sqrt(max(0.0, 1.0 - y * y))
    phi = (index % total) * increment + rng.uniform(-0.18, 0.18)
    return normalize([math.cos(phi) * radius, y, math.sin(phi) * radius])


def molecule_amount_mmol(molecule: MiceliumMoleculeInput, volume_l: float) -> float | None:
    if molecule.real_amount_mmol is not None:
        return max(0.0, float(molecule.real_amount_mmol))
    if molecule.real_concentration_mmol_l is not None:
        return max(0.0, float(molecule.real_concentration_mmol_l) * volume_l)
    return None


def molecule_concentration_mmol_l(molecule: MiceliumMoleculeInput, volume_l: float) -> float | None:
    if molecule.real_concentration_mmol_l is not None:
        return max(0.0, float(molecule.real_concentration_mmol_l))
    if molecule.real_amount_mmol is not None:
        return max(0.0, float(molecule.real_amount_mmol) / max(volume_l, 1e-12))
    return None


def calculate_micellization_metrics(
    molecules: list[MiceliumMoleculeInput],
    volume_ml: float,
    solvent_profile: SolventEnvironmentProfile | None = None,
) -> MicellizationMetrics:
    volume_l = max(volume_ml / 1000.0, 1e-12)
    candidates: list[tuple[float, float, float, float]] = []
    ignored: list[str] = []

    for molecule in molecules:
        if molecule.role == "solvent":
            continue
        if not infer_surfactant_like(molecule):
            continue
        label = molecule.name or molecule.id or molecule.smiles
        if not molecule.cmc_mmol_l or molecule.cmc_mmol_l <= 0:
            if molecule.real_amount_mmol == 0 or molecule.real_concentration_mmol_l == 0:
                continue
            ignored.append(f"{label} (sem CMC no domínio de aplicação)")
            continue

        concentration = molecule_concentration_mmol_l(molecule, volume_l)
        amount = molecule_amount_mmol(molecule, volume_l)
        if concentration is None or amount is None:
            ignored.append(f"{label} (sem quantidade real informada)")
            continue

        cmc = float(molecule.cmc_mmol_l)
        # CMC is already evaluated for this environment (or supplied by user).
        # Applying a second solvent/salt factor would double-correct C/CMC.

        ratio = concentration / max(cmc, 1e-12)
        critical_amount = cmc * volume_l
        candidates.append((ratio, concentration, amount, critical_amount))

    visual_scales = [
        molecule.visual_scale_factor
        for molecule in molecules
        if molecule.visual_scale_factor is not None
    ]
    visual_scale_factor = min(visual_scales) if visual_scales else None

    if not candidates:
        return MicellizationMetrics(
            c_over_cmc=None,
            real_concentration_mmol_l=None,
            real_amount_mmol=None,
            critical_amount_mmol=None,
            missing_amount_mmol=None,
            excess_amount_mmol=None,
            visual_scale_factor=visual_scale_factor,
            ignored_components=ignored,
        )

    # Mistura ideal (Clint): soma das contribuições ci/CMCi. Não usa
    # contagem visual e não transforma solutos comuns em surfactantes.
    ratio = sum(item[0] for item in candidates)
    concentration = sum(item[1] for item in candidates)
    amount = sum(item[2] for item in candidates)
    critical_amount = amount / ratio if ratio > 0 else candidates[0][3] if len(candidates) == 1 else None

    if ignored:
        # Total da mistura desconhecido: não se apresenta o subconjunto como total.
        return MicellizationMetrics(
            c_over_cmc=None,
            real_concentration_mmol_l=None,
            real_amount_mmol=None,
            critical_amount_mmol=None,
            missing_amount_mmol=None,
            excess_amount_mmol=None,
            visual_scale_factor=visual_scale_factor,
            ignored_components=ignored,
            partial_c_over_cmc=ratio,
        )

    return MicellizationMetrics(
        c_over_cmc=ratio,
        real_concentration_mmol_l=concentration,
        real_amount_mmol=amount,
        critical_amount_mmol=critical_amount,
        missing_amount_mmol=max(0.0, critical_amount - amount) if critical_amount is not None else None,
        excess_amount_mmol=max(0.0, amount - critical_amount) if critical_amount is not None else None,
        visual_scale_factor=visual_scale_factor,
        ignored_components=ignored,
    )


def c_over_cmc_proxy(
    molecules: list[MiceliumMoleculeInput],
    volume_ml: float,
    solvent_profile: SolventEnvironmentProfile | None = None,
) -> float | None:
    return calculate_micellization_metrics(molecules, volume_ml, solvent_profile).c_over_cmc


def estimate_cpp_from_molecule(molecule: MiceliumMoleculeInput) -> float | None:
    if molecule.packing_parameter is not None and molecule.packing_parameter > 0:
        return float(molecule.packing_parameter)

    if molecule.tail_volume_a3 and molecule.head_area_a2 and molecule.tail_carbon_count:
        length = 1.5 + 1.265 * max(molecule.tail_carbon_count, 1)
        return float(molecule.tail_volume_a3) / max(float(molecule.head_area_a2) * length, 1e-9)

    from app.modules.chemistry.parameters import validated_calculations as validated
    from rdkit import Chem
    mol = Chem.MolFromSmiles(molecule.smiles)
    if mol is None:
        return None
    return validated.packing_estimate(validated.profile(mol))["cpp"]


def average_cpp(molecules: list[MiceliumMoleculeInput]) -> float | None:
    values = [
        estimate_cpp_from_molecule(molecule)
        for molecule in molecules
        if molecule.role != "solvent" and infer_surfactant_like(molecule)
    ]
    values = [value for value in values if value is not None]
    if not values:
        return None
    return sum(values) / len(values)


def micelle_strength_from_request(
    request: MiceliumSimulationRequest,
    solvent_profile: SolventEnvironmentProfile | None = None,
) -> float:
    surfactant_count = sum(
        molecule.count
        for molecule in request.molecules
        if molecule.role != "solvent" and infer_surfactant_like(molecule)
    )
    if surfactant_count < 4:
        return 0.0

    count_term = min(1.0, surfactant_count / 64.0)
    if solvent_profile is None:
        solvent_profile = infer_solvent_profile(request)

    metrics = calculate_micellization_metrics(
        request.molecules,
        request.environment.volume_ml,
        solvent_profile,
    )
    ccmc_term = (
        min(0.55, count_term * 0.55)
        if metrics.c_over_cmc is None
        else min(1.0, max(0.0, (metrics.c_over_cmc - 0.70) / 2.4))
    )

    polarity = solvent_profile.polarity
    ionic = min(1.0, request.environment.ionic_strength_mol_l * 4.0)
    agitation = min(1.0, request.environment.agitation_rpm / 1800.0)

    base_strength = max(count_term * 0.62, ccmc_term)
    environment_factor = (0.54 + 0.26 * polarity + 0.12 * ionic + 0.04 * agitation)
    environment_factor *= solvent_profile.aggregation_modifier

    return min(1.0, base_strength * environment_factor)


def estimate_nucleation_count(surfactant_count: int, ccmc: float | None, strength: float) -> int:
    if surfactant_count < 6 or strength <= 0.08:
        return 0
    ratio = ccmc if ccmc is not None else 0.9 + strength
    if ratio < 0.85:
        return 0
    if ratio < 1.2:
        return 0
    if ratio < 2.2:
        return max(1, min(4, surfactant_count // 34 + 1))
    return max(2, min(7, surfactant_count // 55 + 1))



def choose_formation_plan(
    request: MiceliumSimulationRequest,
    surfactant_count: int,
    metrics: MicellizationMetrics,
    solvent_profile: SolventEnvironmentProfile,
) -> FormationPlan:
    """
    Seleção físico-química da morfologia.

    Base:
    - CPP (packing parameter) médio dos surfactantes;
    - C/CMC;
    - polaridade / dielétrica do meio;
    - força iônica (blindagem de cabeça iônica);
    - concentração visual/real e número de surfactantes.

    Morfologias alvo:
    - CPP < 1/3: micela esférica
    - 1/3 <= CPP < 1/2: micela cilíndrica / wormlike
    - 1/2 <= CPP < 1: bicamada / lamelar / vesicular
    - CPP >= 1 ou meio muito apolar: inversa
    """
    env = request.environment
    polarity = clamp(float(solvent_profile.polarity), 0.0, 1.0)
    dielectric = max(1.0, float(solvent_profile.dielectric))
    ionic_strength = max(0.0, float(env.ionic_strength_mol_l))
    # Visualização: usa o c/CMC parcial quando há componente sem CMC (rotulado como aproximação).
    ccmc = metrics.c_over_cmc if metrics.c_over_cmc is not None else metrics.partial_c_over_cmc
    real_conc = max(0.0, float(metrics.real_concentration_mmol_l or 0.0))

    surfactants = [m for m in request.molecules if m.role != "solvent" and infer_surfactant_like(m)]
    # Só componentes que entram em c/CMC (com CMC válida) definem a geometria prevista.
    with_cmc = [m for m in surfactants if m.cmc_mmol_l and m.cmc_mmol_l > 0]
    cpp_values = [(estimate_cpp_from_molecule(m), molecule_concentration_mmol_l(m, env.volume_ml / 1000.0)) for m in with_cmc]
    weighted = [(value, weight if weight is not None else 1.0) for value, weight in cpp_values if value is not None]
    total_weight = sum(weight for _value, weight in weighted)
    cpp_known = total_weight > 0
    # Sem CPP não se assume valor padrão (antes: 0,34, que impunha uma morfologia).
    base_cpp = sum(value * weight for value, weight in weighted) / total_weight if cpp_known else 0.34

    # Ajuste do CPP efetivo pelo meio:
    # - sal reduz repulsão cabeça-cabeça => maior CPP efetivo
    # - meio menos polar favorece compactação e inversão
    # - dielétrica baixa favorece agregação mais compacta / inversa
    ionic_fraction = sum("anionic" in (m.surfactant_class or "").lower() or "cationic" in (m.surfactant_class or "").lower() for m in surfactants) / max(len(surfactants), 1)
    ionic_bonus = 0.10 * clamp(ionic_strength / 0.20, 0.0, 1.0) * ionic_fraction
    polarity_bonus = 0.12 * clamp((0.55 - polarity) / 0.55, 0.0, 1.0)
    dielectric_bonus = 0.08 * clamp((25.0 - min(dielectric, 25.0)) / 24.0, 0.0, 1.0)

    effective_cpp = clamp(base_cpp + ionic_bonus + polarity_bonus + dielectric_bonus, 0.08, 1.60)

    # Fase de formação baseada em C/CMC
    if ccmc is None or ccmc <= 0.0:
        final_alpha = 0.0
        micellized_fraction = 0.0
        formation_phase = "monômeros dispersos"
    elif ccmc < 1.0:
        final_alpha = 0.08
        micellized_fraction = 0.03
        formation_phase = "abaixo da CMC: contatos transitórios"
    elif ccmc < 1.20:
        final_alpha = 0.18
        micellized_fraction = 0.10
        formation_phase = "próximo da CMC: pré-agregados instáveis"
    elif ccmc < 1.60:
        final_alpha = 0.34
        micellized_fraction = 0.22
        formation_phase = "nucleação inicial"
    elif ccmc < 2.50:
        final_alpha = 0.56
        micellized_fraction = 0.42
        formation_phase = "autoagregação crescente"
    elif ccmc < 4.00:
        final_alpha = 0.72
        micellized_fraction = 0.62
        formation_phase = "micelização estabelecida"
    else:
        final_alpha = 0.84
        micellized_fraction = 0.78
        formation_phase = "domínio agregado estável"

    high_concentration = (ccmc or 0.0) >= 2.0 or real_conc >= 10.0
    very_high_concentration = (ccmc or 0.0) >= 4.0 or real_conc >= 25.0

    inverse_favored = (
        polarity < 0.42
        or dielectric < 18.0
        or solvent_profile.inverse_modifier > 1.12
    )

    if ccmc is None or ccmc < 1.0:
        morphology = "monômeros/pré-agregados"
    elif not cpp_known:
        morphology = "agregados sem geometria prevista (CPP indisponível)"
    else:
        if inverse_favored and effective_cpp >= 0.72:
            if effective_cpp >= 1.02 or very_high_concentration:
                morphology = "lamelar compacta/inversa"
            else:
                morphology = "micela inversa"
        elif effective_cpp < 0.33:
            morphology = "micela esférica"
        elif effective_cpp < 0.50:
            morphology = "micela cilíndrica/wormlike"
        elif effective_cpp < 0.85:
            if very_high_concentration and surfactant_count >= 70 and polarity >= 0.55:
                morphology = "vesícula/bicamada fechada"
            elif high_concentration and surfactant_count >= 40:
                morphology = "bicamada plana/lamelar"
            else:
                morphology = "micela cilíndrica curta/transicional"
        elif effective_cpp < 1.00:
            if polarity >= 0.55:
                morphology = "bicamada plana/lamelar"
            else:
                morphology = "lamelar compacta/inversa"
        else:
            morphology = "micela inversa" if polarity < 0.60 else "bicamada plana/lamelar"

    # Ajustes de estabilidade por morfologia.
    if "esférica" in morphology:
        orientation_score = clamp(0.30 + 0.72 * final_alpha, 0.0, 1.0)
        hydrophobic_core_score = clamp(0.26 + 0.76 * final_alpha, 0.0, 1.0)
        nucleation_count = max(1, min(10, math.ceil(max(surfactant_count, 1) / 18)))
    elif "cilíndrica" in morphology or "wormlike" in morphology:
        final_alpha = clamp(final_alpha + 0.03, 0.0, 0.90)
        orientation_score = clamp(0.34 + 0.70 * final_alpha, 0.0, 1.0)
        hydrophobic_core_score = clamp(0.24 + 0.70 * final_alpha, 0.0, 1.0)
        nucleation_count = max(1, min(8, math.ceil(max(surfactant_count, 1) / 24)))
    elif "vesícula" in morphology:
        final_alpha = clamp(final_alpha + 0.05, 0.0, 0.92)
        orientation_score = clamp(0.40 + 0.66 * final_alpha, 0.0, 1.0)
        hydrophobic_core_score = clamp(0.18 + 0.56 * final_alpha, 0.0, 1.0)
        nucleation_count = max(1, min(5, math.ceil(max(surfactant_count, 1) / 42)))
    elif "lamelar" in morphology or "bicamada" in morphology:
        final_alpha = clamp(final_alpha + 0.02, 0.0, 0.90)
        orientation_score = clamp(0.38 + 0.64 * final_alpha, 0.0, 1.0)
        hydrophobic_core_score = clamp(0.16 + 0.52 * final_alpha, 0.0, 1.0)
        nucleation_count = max(1, min(6, math.ceil(max(surfactant_count, 1) / 36)))
    elif "inversa" in morphology:
        final_alpha = clamp(final_alpha + 0.04, 0.0, 0.92)
        orientation_score = clamp(0.34 + 0.74 * final_alpha, 0.0, 1.0)
        hydrophobic_core_score = clamp(0.20 + 0.70 * final_alpha, 0.0, 1.0)
        nucleation_count = max(1, min(7, math.ceil(max(surfactant_count, 1) / 28)))
    else:
        orientation_score = clamp(0.24 + 0.58 * final_alpha, 0.0, 1.0)
        hydrophobic_core_score = clamp(0.16 + 0.54 * final_alpha, 0.0, 1.0)
        nucleation_count = max(1, min(10, math.ceil(max(surfactant_count, 1) / 20)))

    if ccmc is not None and ccmc < 1.0:
        final_alpha = min(final_alpha, 0.10)
        micellized_fraction = min(micellized_fraction, 0.05)

    hydrophobic_exposure = clamp(1.0 - hydrophobic_core_score, 0.0, 1.0)

    if ccmc is None:
        basis = "sem c/CMC (nenhum componente com CMC e quantidade real): sem previsão de agregação"
    elif not cpp_known:
        basis = f"c/CMC = {ccmc:.3g} (agregação esperada acima de 1); CPP indisponível: forma não prevista, sem molde geométrico"
    else:
        basis = (f"CPP médio = {base_cpp:.3f} (Tanford + área de cabeça CG não calibrada), CPP efetivo no meio = "
                 f"{effective_cpp:.3f}; c/CMC = {ccmc:.3g}; limiares de Israelachvili–Mitchell–Ninham")

    return FormationPlan(
        morphology=morphology,
        formation_phase=formation_phase,
        micellized_fraction=micellized_fraction,
        free_monomer_fraction=clamp(1.0 - micellized_fraction, 0.0, 1.0),
        nucleation_count=nucleation_count,
        final_alpha=final_alpha,
        orientation_score=orientation_score,
        hydrophobic_core_score=hydrophobic_core_score,
        hydrophobic_exposure=hydrophobic_exposure,
        geometry_template=bool(cpp_known and ccmc is not None and ccmc >= 1.0),
        morphology_basis=basis,
    )

def target_for_group(
    *,
    particles: list[MiceliumParticle],
    indices: list[int],
    base: Vector,
    direction: Vector | None,
) -> dict[int, Vector]:
    result: dict[int, Vector] = {}
    for index in indices:
        local = list(particles[index].position[:3])
        result[index] = local_to_oriented(local, base, direction)
    return result



def group_particle_indices_by_molecule(particles: list[MiceliumParticle]) -> dict[str, list[int]]:
    groups: dict[str, list[int]] = {}

    for index, particle in enumerate(particles):
        groups.setdefault(particle.molecule_id, []).append(index)

    return groups


def is_solvent_group(indices: list[int], particles: list[MiceliumParticle]) -> bool:
    return bool(indices) and all(particles[index].kind == "solvent" for index in indices)


def is_surfactant_group(indices: list[int], particles: list[MiceliumParticle]) -> bool:
    if not indices:
        return False

    kinds = {particles[index].kind for index in indices}

    return "head" in kinds and "tail" in kinds


def dispersed_center(index: int, total: int, box_size: float, rng: random.Random) -> Vector:
    """
    Centro inicial disperso no volume.

    Não pré-organiza no centro. A distribuição usa uma casca irregular dentro
    da caixa para que frame 0 pareça solução, não micela pronta.
    """
    safe_total = max(total, 1)
    direction = golden_sphere_direction(index, safe_total, rng)
    filling = ((index + 0.5) / safe_total) ** (1.0 / 3.0)
    radius = (box_size * 0.44) * filling
    jitter = box_size * 0.10

    return [
        direction[0] * radius + rng.uniform(-jitter, jitter),
        direction[1] * radius + rng.uniform(-jitter, jitter),
        direction[2] * radius + rng.uniform(-jitter, jitter),
    ]


def create_irregular_nuclei(count: int, box_size: float, rng: random.Random) -> list[Vector]:
    if count <= 0:
        return []

    if count == 1:
        return add_jitter([0.0, 0.0, 0.0], rng, box_size * 0.05)

    nuclei: list[Vector] = []
    radius = max(1.2, min(box_size * 0.22, 2.4 + count * 0.35))

    for index in range(count):
        direction = golden_sphere_direction(index, count, rng)
        nuclei.append(
            add(
                scale(direction, radius * rng.uniform(0.55, 1.20)),
                scale(random_unit_vector(rng), rng.uniform(0.15, 0.85)),
            )
        )

    return nuclei


def target_for_group(
    *,
    particles: list[MiceliumParticle],
    indices: list[int],
    base: Vector,
    direction: Vector | None,
) -> dict[int, Vector]:
    """
    Posiciona uma cópia molecular respeitando orientação cabeça-cauda.

    Para surfactantes, o template vem como cauda -> cabeça ao longo de x.
    Aqui a cabeça fica em `base` e a cauda aponta no sentido oposto de
    `direction`. Assim:
    - micela normal: direction para fora, cabeça fora, cauda dentro;
    - micela inversa: direction para dentro, cabeça dentro, cauda fora;
    - bicamada: direction normal à folha.
    """
    if not indices:
        return {}

    if direction is None:
        direction = [1.0, 0.0, 0.0]

    direction = normalize(direction)
    local_x_values = [float(particles[index].position[0]) for index in indices]
    head_indices = [index for index in indices if particles[index].kind == "head"]

    if head_indices:
        head_anchor_x = max(float(particles[index].position[0]) for index in head_indices)
    else:
        head_anchor_x = max(local_x_values) if local_x_values else 0.0

    out: dict[int, Vector] = {}

    for index in indices:
        particle = particles[index]
        local = [
            float(particle.position[0]) - head_anchor_x,
            float(particle.position[1]),
            float(particle.position[2]),
        ]
        out[index] = local_to_oriented(local, base, direction)

    return out


def _safe_visual_count(molecule: MiceliumMoleculeInput) -> int:
    """
    Quantidade visual segura.

    v28:
    Mantém qualidade química, mas reduz custo computacional. O motor continua
    usando propriedades reais/concentração para CMC; este count é só render.
    """
    count = molecule.visual_count if molecule.visual_count is not None else molecule.count

    try:
        count_int = int(round(float(count)))
    except Exception:
        count_int = int(molecule.count or 1)

    count_int = max(1, count_int)

    if molecule.role == "solvent":
        return min(count_int, 28)

    is_surfactant = (
        bool(molecule.is_surfactant)
        or (molecule.tail_carbon_count or 0) >= 8
        or molecule.packing_parameter is not None
    )

    if is_surfactant:
        return min(count_int, 120)

    return min(count_int, 72)


def _estimate_box_size(request: MiceliumSimulationRequest, estimated_particles: int) -> float:
    volume_term = max(0.0, float(request.environment.volume_ml)) ** (1.0 / 3.0)
    particle_term = max(1, estimated_particles) ** (1.0 / 3.0)
    agitation_term = min(2.5, max(0.0, request.environment.agitation_rpm) / 900.0)

    return max(10.0, min(70.0, 8.0 + volume_term * 0.55 + particle_term * 1.15 + agitation_term))



def request_session_key(request: MiceliumSimulationRequest) -> str:
    """
    Assinatura físico-química da mistura.

    v31:
    Usada para continuar chunks REST sem reiniciar a cena.
    Ignora seed e dados transitórios; considera composição e ambiente.
    """
    env = request.environment

    env_parts = [
        "env",
        getattr(env, "solvent_name", None),
        getattr(env, "volume_ml", None),
        getattr(env, "temperature_k", None),
        getattr(env, "pressure_atm", None),
        getattr(env, "ph", None),
        getattr(env, "ionic_strength_mol_l", None),
        getattr(env, "solvent_polarity_index", None),
        getattr(env, "dielectric_constant", None),
        getattr(env, "agitation_rpm", None),
    ]

    molecule_parts: list[tuple] = []

    for molecule in request.molecules:
        molecule_parts.append(
            (
                getattr(molecule, "id", None),
                getattr(molecule, "name", None),
                getattr(molecule, "smiles", None),
                getattr(molecule, "formula", None),
                getattr(molecule, "role", None),
                getattr(molecule, "count", None),
                getattr(molecule, "visual_count", None),
                getattr(molecule, "real_amount_mmol", None),
                getattr(molecule, "real_concentration_mmol_l", None),
                getattr(molecule, "cmc_mmol_l", None),
                getattr(molecule, "packing_parameter", None),
                getattr(molecule, "tail_carbon_count", None),
                getattr(molecule, "head_area_a2", None),
                getattr(molecule, "tail_volume_a3", None),
                getattr(molecule, "hlb", None),
                getattr(molecule, "effective_hlb", None),
                getattr(molecule, "surfactant_class", None),
                bool(getattr(molecule, "is_surfactant", False)),
            )
        )

    # A assinatura preserva a ordem usada nos arrays de partículas. Ordená-la
    # permitia reutilizar coordenadas em moléculas diferentes após reordenar.
    return repr((tuple(env_parts), tuple(molecule_parts), int(request.max_particles)))



def build_initial_state(
    request: MiceliumSimulationRequest,
) -> tuple[
    list[MiceliumParticle],
    list[MiceliumBond],
    list[Vector],
    list[Vector],
    float,
    str,
]:
    """
    Monta partículas CG antes da dinâmica.

    Correção crítica da v08:
    - cada cópia visual recebe molecule_id próprio;
    - count/visual_count controlam apenas renderização;
    - a posição inicial é dispersa, não micela pronta;
    - respeita request.max_particles;
    - preserva bonds internos para molas flexíveis.
    """
    rng = random.Random(request.seed)
    templates = [(molecule, build_particle_template(molecule)) for molecule in request.molecules]

    estimated_particles = 0
    for molecule, template in templates:
        estimated_particles += _safe_visual_count(molecule) * max(1, len(template.particles))

    box_size = _estimate_box_size(request, min(estimated_particles, request.max_particles))

    particles: list[MiceliumParticle] = []
    bonds: list[MiceliumBond] = []
    positions: list[Vector] = []
    velocities: list[Vector] = []
    representation_counts: dict[str, int] = {}

    molecule_copy_counter = 0

    for molecule_index, (molecule, template) in enumerate(templates):
        template_size = max(1, len(template.particles))
        desired_copies = _safe_visual_count(molecule)
        remaining_particle_slots = max(0, request.max_particles - len(particles))
        max_copies = remaining_particle_slots // template_size
        copies = max(0, min(desired_copies, max_copies))

        if copies <= 0:
            continue

        representation_counts[template.representation] = representation_counts.get(template.representation, 0) + copies

        for copy_index in range(copies):
            copy_molecule_id = f"{molecule.id or stable_id(molecule.name, molecule.smiles)}:component:{molecule_index}:copy:{copy_index}"
            center = dispersed_center(
                molecule_copy_counter,
                max(estimated_particles // template_size, 1),
                box_size,
                rng,
            )
            direction = random_unit_vector(rng)
            id_map: dict[str, str] = {}

            for particle in template.particles:
                local_position = [
                    float(particle.position[0]),
                    float(particle.position[1]) + rng.uniform(-0.035, 0.035),
                    float(particle.position[2]) + rng.uniform(-0.035, 0.035),
                ]
                position = local_to_oriented(local_position, center, direction)
                velocity = scale(random_unit_vector(rng), rng.uniform(0.001, 0.035))
                new_particle_id = f"{copy_molecule_id}:{particle.kind}:{particle.bead_index}"
                id_map[particle.id] = new_particle_id

                new_particle = particle.model_copy(
                    update={
                        "id": new_particle_id,
                        "molecule_id": copy_molecule_id,
                        "position": position,
                        "velocity": velocity,
                    }
                )

                particles.append(new_particle)
                positions.append(position)
                velocities.append(velocity)

            for bond in template.bonds:
                particle_a = id_map.get(bond.particle_a)
                particle_b = id_map.get(bond.particle_b)

                if not particle_a or not particle_b:
                    continue

                bonds.append(
                    bond.model_copy(
                        update={
                            "id": f"{copy_molecule_id}:bond:{len(bonds)}",
                            "particle_a": particle_a,
                            "particle_b": particle_b,
                        }
                    )
                )

            molecule_copy_counter += 1

    if not particles:
        raise ValueError("Nenhuma partícula foi gerada para o ambiente 3D. Verifique quantidade visual, SMILES e papéis da mistura.")

    if len(representation_counts) == 1:
        representation = next(iter(representation_counts))
    else:
        representation = "+".join(sorted(representation_counts.keys()))

    return (
        particles,
        bonds,
        sanitize_positions(positions),
        sanitize_positions(velocities),
        box_size,
        representation,
    )


def build_formation_targets(
    *,
    request: MiceliumSimulationRequest,
    particles: list[MiceliumParticle],
    initial_positions: list[Vector],
    box_size: float,
    plan: FormationPlan,
    rng: random.Random,
) -> tuple[list[Vector], list[Vector]]:
    groups = group_particle_indices_by_molecule(particles)
    target_positions = [list(position) for position in initial_positions]
    precluster_positions = [list(position) for position in initial_positions]

    surfactant_groups = [
        (molecule_id, indices)
        for molecule_id, indices in groups.items()
        if is_surfactant_group(indices, particles)
    ]
    solute_groups = [
        (molecule_id, indices)
        for molecule_id, indices in groups.items()
        if not is_surfactant_group(indices, particles) and not is_solvent_group(indices, particles)
    ]

    micellized_count = int(round(len(surfactant_groups) * plan.micellized_fraction))
    micellized_count = min(len(surfactant_groups), max(0, micellized_count))
    active_surfactants = surfactant_groups[:micellized_count]
    free_surfactants = surfactant_groups[micellized_count:]

    nuclei = create_irregular_nuclei(plan.nucleation_count, box_size, rng)
    if active_surfactants and not nuclei:
        nuclei = [[0.0, 0.0, 0.0]]

    cluster_count = max(1, len(nuclei))
    cluster_buckets: list[list[tuple[str, list[int]]]] = [[] for _ in range(cluster_count)]
    for index, group in enumerate(active_surfactants):
        cluster_buckets[index % cluster_count].append(group)

    morphology = plan.morphology.lower()

    for cluster_index, bucket in enumerate(cluster_buckets):
        if not bucket:
            continue

        nucleus = nuclei[cluster_index % len(nuclei)]
        bucket_size = len(bucket)

        sphere_radius = 0.55 + math.sqrt(max(bucket_size, 1)) * 0.18
        cylinder_ring = max(6, min(20, int(math.sqrt(bucket_size) * 2.2)))
        bilayer_grid = max(2, math.ceil(math.sqrt(max(bucket_size, 1) / 2.0)))
        vesicle_radius = 1.60 + math.sqrt(max(bucket_size, 1)) * 0.22
        bilayer_thickness = 1.10

        for local_index, (_molecule_id, indices) in enumerate(bucket):
            pre_direction = golden_sphere_direction(local_index, bucket_size, rng)
            pre_radius = 2.9 + math.sqrt(max(bucket_size, 1)) * 0.22 + rng.uniform(-0.65, 1.05)
            pre_base = add(
                nucleus,
                add(
                    scale(pre_direction, pre_radius),
                    scale(random_unit_vector(rng), rng.uniform(0.4, 1.4)),
                ),
            )

            # 1) micela cilíndrica / wormlike
            if "cilíndrica" in morphology or "wormlike" in morphology:
                angle = math.tau * ((local_index % cylinder_ring) / cylinder_ring) + rng.uniform(-0.12, 0.12)
                ring_index = local_index // cylinder_ring
                axial = (ring_index - (math.ceil(bucket_size / cylinder_ring) - 1) / 2.0) * 0.72
                centerline_bend = math.sin(ring_index * 0.65) * 0.55
                radial = [math.cos(angle), 0.0, math.sin(angle)]
                base = add(nucleus, [radial[0] * 1.05 + centerline_bend, axial, radial[2] * 1.05])
                direction = radial

            # 2) vesícula / bicamada fechada
            elif "vesícula" in morphology:
                outer_leaflet = (local_index % 2) == 0
                outward = golden_sphere_direction(local_index, bucket_size, rng)
                radius = vesicle_radius + (0.55 if outer_leaflet else -0.55)
                base = add(nucleus, scale(outward, radius + rng.uniform(-0.12, 0.12)))
                direction = outward if outer_leaflet else scale(outward, -1.0)

            # 3) bicamada plana / lamelar
            elif "bicamada plana" in morphology or "lamelar" in morphology:
                plane_row = local_index // bilayer_grid
                plane_col = local_index % bilayer_grid
                x = (plane_col - (bilayer_grid - 1) / 2.0) * 1.12 + rng.uniform(-0.18, 0.18)
                y = (plane_row - (math.ceil(bucket_size / bilayer_grid) - 1) / 2.0) * 1.12 + rng.uniform(-0.18, 0.18)
                upper_leaflet = (local_index % 2) == 0
                z = bilayer_thickness / 2.0 if upper_leaflet else -bilayer_thickness / 2.0
                base = add(nucleus, [x, y, z])
                direction = [0.0, 0.0, 1.0] if upper_leaflet else [0.0, 0.0, -1.0]

            # 4) micela inversa
            elif "inversa" in morphology:
                outward = golden_sphere_direction(local_index, bucket_size, rng)
                base = add(nucleus, scale(outward, sphere_radius + rng.uniform(-0.20, 0.30)))
                direction = scale(outward, -1.0)

            # 5) micela esférica/circular
            else:
                outward = golden_sphere_direction(local_index, bucket_size, rng)
                base = add(nucleus, scale(outward, sphere_radius + rng.uniform(-0.20, 0.35)))
                direction = outward

            for particle_index, position in target_for_group(
                particles=particles,
                indices=indices,
                base=base,
                direction=direction,
            ).items():
                target_positions[particle_index] = position

            for particle_index, position in target_for_group(
                particles=particles,
                indices=indices,
                base=pre_base,
                direction=pre_direction,
            ).items():
                precluster_positions[particle_index] = position

    # Monômeros livres permanecem dispersos no volume.
    for monomer_index, (_molecule_id, indices) in enumerate(free_surfactants):
        direction = random_unit_vector(rng)
        center = add_jitter(
            dispersed_center(monomer_index, max(len(free_surfactants), 1), box_size, rng),
            rng,
            1.9,
        )
        for particle_index, position in target_for_group(
            particles=particles,
            indices=indices,
            base=center,
            direction=direction,
        ).items():
            target_positions[particle_index] = position
            precluster_positions[particle_index] = lerp(initial_positions[particle_index], position, 0.22)

    # Solutos hidrofóbicos tendem ao interior do agregado; polares ficam na interface/solução.
    for solute_index, (_molecule_id, indices) in enumerate(solute_groups):
        molecule_particles = [particles[index] for index in indices]
        hydrophobicity = max((particle.hydrophobicity for particle in molecule_particles), default=0.0)
        polarity = max((particle.polarity for particle in molecule_particles), default=0.0)

        if nuclei and hydrophobicity > polarity and plan.micellized_fraction > 0.20:
            nucleus = nuclei[solute_index % len(nuclei)]
            center = add(nucleus, scale(random_unit_vector(rng), rng.uniform(0.3, 1.2)))
        else:
            center = add_jitter(initial_positions[indices[0]], rng, 1.5)

        for particle_index, position in target_for_group(
            particles=particles,
            indices=indices,
            base=center,
            direction=None,
        ).items():
            target_positions[particle_index] = position
            precluster_positions[particle_index] = lerp(initial_positions[particle_index], position, 0.30)

    return sanitize_positions(precluster_positions), sanitize_positions(target_positions)

def vector_distance(a: Vector, b: Vector) -> float:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    dz = a[2] - b[2]
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def clamp_vector_to_box(position: Vector, box_size: float) -> Vector:
    half = max(float(box_size), 1.0) / 2.0
    return [
        max(-half, min(half, position[0])),
        max(-half, min(half, position[1])),
        max(-half, min(half, position[2])),
    ]


def frame_phase(progress: float) -> str:
    if progress < 0.18:
        return "dispersão browniana"
    if progress < 0.42:
        return "colisões e pré-agregados"
    if progress < 0.72:
        return "nucleação e crescimento"
    if progress < 0.90:
        return "reorganização morfológica"
    return "estabilização dinâmica"


def moving_target(
    *,
    initial: Vector,
    precluster: Vector,
    final: Vector,
    progress: float,
    plan: FormationPlan,
) -> Vector:
    if plan.final_alpha <= 0.0:
        return initial

    if progress < 0.18:
        return initial

    if progress < 0.48:
        local = smoothstep((progress - 0.18) / 0.30)
        return lerp(initial, precluster, local * min(0.75, plan.final_alpha + 0.12))

    local = smoothstep((progress - 0.48) / 0.52)
    return lerp(precluster, final, local * plan.final_alpha)


def particle_drag(particle: MiceliumParticle, temperature_k: float, agitation_rpm: float) -> float:
    base = 0.90
    if particle.kind == "solvent":
        base = 0.78
    elif particle.kind == "head":
        base = 0.86
    elif particle.kind == "tail":
        base = 0.88

    temp_boost = clamp((temperature_k - 298.15) / 120.0, -0.10, 0.12)
    agitation_boost = clamp(agitation_rpm / 12000.0, 0.0, 0.10)
    return clamp(base - temp_boost - agitation_boost, 0.68, 0.94)


def brownian_amplitude(
    *,
    particle: MiceliumParticle,
    temperature_k: float,
    agitation_rpm: float,
    progress: float,
) -> float:
    thermal = math.sqrt(max(temperature_k, 1.0) / 298.15)
    agitation = 1.0 + clamp(agitation_rpm / 1800.0, 0.0, 1.7)

    if particle.kind == "solvent":
        base = 0.030
    elif particle.kind == "head":
        base = 0.022
    elif particle.kind == "tail":
        base = 0.018
    else:
        base = 0.024

    # No início há difusão maior; perto do agregado ainda há respiração,
    # mas sem congelar a molécula.
    relaxation = 1.0 - 0.35 * smoothstep(progress)
    return base * thermal * agitation * relaxation


def target_attraction_strength(particle: MiceliumParticle, progress: float, plan: FormationPlan) -> float:
    if plan.final_alpha <= 0.0:
        return 0.0

    base = 0.004 + 0.032 * smoothstep(progress)

    if particle.kind == "head":
        return base * 0.74

    if particle.kind == "tail":
        return base * 1.05

    if particle.kind == "solute":
        return base * 0.35

    return 0.0


def build_bond_index(
    particles: list[MiceliumParticle],
    bonds: list[MiceliumBond],
) -> list[tuple[int, int, float, float]]:
    particle_index = {particle.id: index for index, particle in enumerate(particles)}
    indexed: list[tuple[int, int, float, float]] = []

    for bond in bonds:
        a = particle_index.get(bond.particle_a)
        b = particle_index.get(bond.particle_b)

        if a is None or b is None:
            continue

        indexed.append((a, b, max(0.08, bond.length), max(0.05, bond.stiffness)))

    return indexed


def build_neighbor_cells(
    positions: list[Vector],
    particles: list[MiceliumParticle],
    cell_size: float,
) -> dict[tuple[int, int, int], list[int]]:
    cells: dict[tuple[int, int, int], list[int]] = {}

    for index, particle in enumerate(particles):
        position = positions[index]
        key = (
            math.floor(position[0] / cell_size),
            math.floor(position[1] / cell_size),
            math.floor(position[2] / cell_size),
        )
        cells.setdefault(key, []).append(index)

    return cells


def neighbor_keys(key: tuple[int, int, int]):
    kx, ky, kz = key

    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                yield (kx + dx, ky + dy, kz + dz)


def apply_pairwise_dynamic_forces(
    *,
    positions: list[Vector],
    velocities: list[Vector],
    particles: list[MiceliumParticle],
    progress: float,
    plan: FormationPlan,
) -> None:
    cell_size = 1.35
    cells = build_neighbor_cells(positions, particles, cell_size)
    visited: set[tuple[int, int]] = set()

    hydrophobic_gain = 0.0035 + 0.010 * smoothstep(progress) * plan.final_alpha
    electrostatic_gain = 0.0030

    for key, members in cells.items():
        candidate_indices: list[int] = []

        for nkey in neighbor_keys(key):
            candidate_indices.extend(cells.get(nkey, []))

        for i in members:
            pi = particles[i]
            for j in candidate_indices:
                if j <= i:
                    continue

                pair_key = (i, j)

                if pair_key in visited:
                    continue

                visited.add(pair_key)

                pj = particles[j]
                delta = sub(positions[j], positions[i])
                dist = max(vector_distance(positions[i], positions[j]), 1e-5)
                direction = scale(delta, 1.0 / dist)
                min_distance = (pi.radius + pj.radius) * 0.88

                # Exclusão estérica suave para tirar sobreposição sem virar cristal.
                if dist < min_distance:
                    force = (min_distance - dist) * 0.035
                    velocities[i] = add(velocities[i], scale(direction, -force / max(pi.mass, 0.1)))
                    velocities[j] = add(velocities[j], scale(direction, force / max(pj.mass, 0.1)))

                same_molecule = pi.molecule_id == pj.molecule_id

                if same_molecule:
                    continue

                # Interações explícitas com solvente/cossolvente:
                # água estabiliza cabeças e expulsa caudas; etanol fica intermediário;
                # solvente apolar estabiliza caudas e pode favorecer micelas inversas.
                if pi.kind == "solvent" or pj.kind == "solvent":
                    solvent_index = i if pi.kind == "solvent" else j
                    other_index = j if pi.kind == "solvent" else i
                    solvent = particles[solvent_index]
                    other = particles[other_index]
                    polarity = clamp(solvent.polarity, 0.0, 1.0)
                    hydrophobicity = clamp(solvent.hydrophobicity, 0.0, 1.0)

                    if dist < 2.4:
                        if other.kind == "head":
                            force = (0.006 * polarity - 0.003 * hydrophobicity) * (2.4 - dist)
                        elif other.kind == "tail":
                            force = (0.006 * hydrophobicity - 0.0045 * polarity) * (2.4 - dist)
                        else:
                            force = 0.002 * (polarity - hydrophobicity) * (2.4 - dist)

                        if solvent_index == i:
                            velocities[other_index] = add(velocities[other_index], scale(direction, -force / max(other.mass, 0.1)))
                            velocities[solvent_index] = add(velocities[solvent_index], scale(direction, force / max(solvent.mass, 0.1)))
                        else:
                            velocities[other_index] = add(velocities[other_index], scale(direction, force / max(other.mass, 0.1)))
                            velocities[solvent_index] = add(velocities[solvent_index], scale(direction, -force / max(solvent.mass, 0.1)))

                    continue

                # Cauda-cauda: atração hidrofóbica de curto alcance.
                if pi.kind == "tail" and pj.kind == "tail" and dist < 2.25:
                    force = hydrophobic_gain * (2.25 - dist)
                    velocities[i] = add(velocities[i], scale(direction, force / max(pi.mass, 0.1)))
                    velocities[j] = add(velocities[j], scale(direction, -force / max(pj.mass, 0.1)))

                # Cabeças carregadas/hidrofílicas não devem colapsar no núcleo.
                if pi.kind == "head" and pj.kind == "head" and dist < 2.0:
                    same_sign = pi.charge * pj.charge > 0
                    charge_factor = 1.35 if same_sign else 0.70
                    force = electrostatic_gain * charge_factor * (2.0 - dist)
                    velocities[i] = add(velocities[i], scale(direction, -force / max(pi.mass, 0.1)))
                    velocities[j] = add(velocities[j], scale(direction, force / max(pj.mass, 0.1)))

                # Cabeça-cauda: evita embolar tudo como novelo.
                if {pi.kind, pj.kind} == {"head", "tail"} and dist < 1.15:
                    force = 0.0045 * (1.15 - dist)
                    velocities[i] = add(velocities[i], scale(direction, -force / max(pi.mass, 0.1)))
                    velocities[j] = add(velocities[j], scale(direction, force / max(pj.mass, 0.1)))


def apply_bond_springs(
    *,
    positions: list[Vector],
    velocities: list[Vector],
    particles: list[MiceliumParticle],
    indexed_bonds: list[tuple[int, int, float, float]],
) -> None:
    for a, b, rest_length, stiffness in indexed_bonds:
        delta = sub(positions[b], positions[a])
        dist = max(vector_distance(positions[a], positions[b]), 1e-5)
        direction = scale(delta, 1.0 / dist)
        stretch = dist - rest_length

        # Molas suaves, não barras rígidas.
        force = clamp(stretch * stiffness * 0.040, -0.050, 0.050)

        velocities[a] = add(velocities[a], scale(direction, force / max(particles[a].mass, 0.1)))
        velocities[b] = add(velocities[b], scale(direction, -force / max(particles[b].mass, 0.1)))


def apply_molecule_flexibility(
    *,
    positions: list[Vector],
    velocities: list[Vector],
    particles: list[MiceliumParticle],
    molecule_groups: dict[str, list[int]],
    rng: random.Random,
    progress: float,
) -> None:
    # Pequeno modo de dobra por molécula para a cauda não parecer uma régua.
    for molecule_id, indices in molecule_groups.items():
        tails = [index for index in indices if particles[index].kind == "tail"]
        heads = [index for index in indices if particles[index].kind == "head"]

        if len(tails) < 2:
            continue

        bend_axis = random_unit_vector(rng)
        bend_strength = (0.0015 + 0.0035 * (1.0 - 0.45 * smoothstep(progress)))

        if heads:
            head_center = positions[heads[0]]
        else:
            head_center = positions[tails[-1]]

        for order, index in enumerate(tails):
            lever = (order + 1) / max(len(tails), 1)
            radial = normalize(sub(positions[index], head_center))
            twist = normalize([
                radial[1] * bend_axis[2] - radial[2] * bend_axis[1],
                radial[2] * bend_axis[0] - radial[0] * bend_axis[2],
                radial[0] * bend_axis[1] - radial[1] * bend_axis[0],
            ])
            velocities[index] = add(
                velocities[index],
                scale(twist, bend_strength * lever),
            )


def apply_morphology_breathing(
    *,
    positions: list[Vector],
    velocities: list[Vector],
    particles: list[MiceliumParticle],
    progress: float,
    plan: FormationPlan,
    frame_index: int,
) -> None:
    if plan.final_alpha <= 0.0:
        return

    morphology = plan.morphology.lower()
    omega = math.sin(progress * math.tau * 3.0 + frame_index * 0.11)
    strength = 0.0018 + 0.0032 * plan.final_alpha

    for index, particle in enumerate(particles):
        position = positions[index]
        radial = normalize(position)

        if "cilíndrica" in morphology or "wormlike" in morphology:
            radial = normalize([position[0], 0.0, position[2]])
            axial_wave = math.sin(position[1] * 1.7 + progress * math.tau * 2.0) * strength
            velocities[index] = add(velocities[index], [radial[0] * strength * omega, axial_wave, radial[2] * strength * omega])

        elif "lamelar" in morphology or "vesícula" in morphology or "bicamada" in morphology:
            wave = math.sin(position[0] * 1.2 + position[1] * 0.7 + progress * math.tau * 2.0)
            velocities[index] = add(velocities[index], [0.0, 0.0, wave * strength * 1.4])

        else:
            velocities[index] = add(velocities[index], scale(radial, strength * omega))



def _pvalue(particle: MiceliumParticle, name: str, default: float) -> float:
    try:
        raw = getattr(particle, name, default)
        value = float(default if raw is None else raw)
        return value if math.isfinite(value) else default
    except Exception:
        return default


def _center_of(indices: list[int], positions: list[Vector]) -> Vector:
    if not indices:
        return [0.0, 0.0, 0.0]

    center = [0.0, 0.0, 0.0]
    for index in indices:
        center = add(center, positions[index])

    return scale(center, 1.0 / max(len(indices), 1))


def _kind_indices(indices: list[int], particles: list[MiceliumParticle], kind: str) -> list[int]:
    return [index for index in indices if particles[index].kind == kind]


def _tail_center(indices: list[int], particles: list[MiceliumParticle], positions: list[Vector]) -> Vector:
    tails = _kind_indices(indices, particles, "tail")
    return _center_of(tails or indices, positions)


def _head_center(indices: list[int], particles: list[MiceliumParticle], positions: list[Vector]) -> Vector:
    heads = _kind_indices(indices, particles, "head")
    return _center_of(heads or indices, positions)


def _molecule_radius(indices: list[int], positions: list[Vector]) -> float:
    center = _center_of(indices, positions)
    if not indices:
        return 0.5
    return max(0.35, sum(vector_distance(positions[index], center) for index in indices) / len(indices))


class _UnionFind:
    def __init__(self, items: list[str]) -> None:
        self.parent = {item: item for item in items}

    def find(self, item: str) -> str:
        parent = self.parent[item]
        if parent != item:
            self.parent[item] = self.find(parent)
        return self.parent[item]

    def union(self, a: str, b: str) -> None:
        ra = self.find(a)
        rb = self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def _estimate_pair_cmc_factor(plan: FormationPlan) -> float:
    # Usa o plano químico como proxy contínuo para estabilidade sem criar alvo.
    return clamp(plan.final_alpha, 0.0, 1.0)



def resolve_hard_overlaps(
    *,
    positions: list[Vector],
    velocities: list[Vector],
    particles: list[MiceliumParticle],
    box_size: float,
) -> None:
    """
    Resolve sobreposição por correção posicional.

    v29:
    Força de repulsão por velocidade nem sempre impede atravessamento quando o
    frame é grande ou o sistema fica denso. Esta etapa aplica volume excluído
    diretamente nas posições, como uma restrição física leve.

    Não é animação: é solver de colisão/volume excluído.
    """
    if not positions:
        return

    cell_size = 1.65
    cells = build_neighbor_cells(positions, particles, cell_size)
    # Cada par (i<j) aparece uma única vez: célula única por partícula e 27 vizinhas distintas.
    pair_budget = max(10_000, min(55_000, len(particles) * 55))
    pair_counter = 0
    # Propriedades por partícula calculadas uma vez (mesmas expressões de antes).
    radius_eff = [max(0.16, _pvalue(p, "radius", 0.35)) for p in particles]
    inv_mass = [1.0 / max(_pvalue(p, "mass", 1.0), 0.2) for p in particles]
    kinds = [p.kind for p in particles]
    molecule_ids = [p.molecule_id for p in particles]

    for key, members in cells.items():
        if pair_counter >= pair_budget:
            break

        candidate_indices: list[int] = []
        for nkey in neighbor_keys(key):
            candidate_indices.extend(cells.get(nkey, []))

        if len(candidate_indices) > 128:
            stride = max(1, len(candidate_indices) // 128)
            candidate_indices = candidate_indices[::stride][:128]

        for i in members:
            if pair_counter >= pair_budget:
                break


            for j in candidate_indices:
                if j <= i:
                    continue

                pair_counter += 1


                # Ligações e beads da mesma molécula já são controladas por molas.
                if molecule_ids[i] == molecule_ids[j]:
                    continue

                # Solvente-solvente pode sobrepor visualmente um pouco sem afetar a micela.
                if kinds[i] == "solvent" and kinds[j] == "solvent":
                    continue

                dist = max(vector_distance(positions[i], positions[j]), 1e-6)
                min_distance = max(0.42, (radius_eff[i] + radius_eff[j]) * 1.12)
                if dist >= min_distance:
                    continue
                direction = scale(sub(positions[j], positions[i]), 1.0 / dist)

                overlap = min_distance - dist
                inv_mass_i = inv_mass[i]
                inv_mass_j = inv_mass[j]
                inv_total = max(inv_mass_i + inv_mass_j, 1e-9)

                # Corrige a maior parte da penetração, mantendo suavidade.
                correction = scale(direction, overlap * 0.62)

                positions[i] = clamp_vector_to_box(
                    sub(positions[i], scale(correction, inv_mass_i / inv_total)),
                    box_size,
                )
                positions[j] = clamp_vector_to_box(
                    add(positions[j], scale(correction, inv_mass_j / inv_total)),
                    box_size,
                )

                # Remove componente de velocidade que empurrava as partículas uma para a outra.
                rel_velocity = sub(velocities[j], velocities[i])
                closing = (
                    rel_velocity[0] * direction[0]
                    + rel_velocity[1] * direction[1]
                    + rel_velocity[2] * direction[2]
                )
                if closing < 0:
                    impulse = scale(direction, closing * 0.45)
                    velocities[i] = add(velocities[i], scale(impulse, inv_mass_i / inv_total))
                    velocities[j] = sub(velocities[j], scale(impulse, inv_mass_j / inv_total))


def detect_supramolecular_clusters(
    *,
    particles: list[MiceliumParticle],
    positions: list[Vector],
    plan: FormationPlan,
) -> dict[str, dict]:
    """
    Detecta clusters supramoleculares por contato cauda-cauda.

    Uma micela não é ligação covalente. O grafo covalente da molécula fica fixo;
    este detector cria um grafo supramolecular dinâmico que pode mudar a cada passo.
    """
    molecule_groups = group_particle_indices_by_molecule(particles)

    surfactant_groups = {
        molecule_id: indices
        for molecule_id, indices in molecule_groups.items()
        if is_surfactant_group(indices, particles)
    }

    if len(surfactant_groups) < 2:
        return {}

    ids = list(surfactant_groups.keys())
    uf = _UnionFind(ids)

    reverse = "inversa" in plan.morphology.lower()
    tail_centers = {
        molecule_id: (_head_center if reverse else _tail_center)(indices, particles, positions)
        for molecule_id, indices in surfactant_groups.items()
    }

    # Contato hidrofóbico: acima da CMC o alcance efetivo aumenta um pouco.
    cmc_factor = _estimate_pair_cmc_factor(plan)
    cutoff = 1.65 + 0.55 * cmc_factor

    # Busca O(n²) por moléculas, não por partículas; leve o suficiente para visual.
    for i, molecule_a in enumerate(ids):
        ca = tail_centers[molecule_a]
        for molecule_b in ids[i + 1:]:
            cb = tail_centers[molecule_b]
            if vector_distance(ca, cb) <= cutoff:
                uf.union(molecule_a, molecule_b)

    buckets: dict[str, list[str]] = {}
    for molecule_id in ids:
        root = uf.find(molecule_id)
        buckets.setdefault(root, []).append(molecule_id)

    clusters: dict[str, dict] = {}
    for cluster_index, members in enumerate(buckets.values()):
        if len(members) < 2:
            continue

        member_tail_indices: list[int] = []
        member_head_indices: list[int] = []
        member_particle_indices: list[int] = []

        for molecule_id in members:
            indices = surfactant_groups[molecule_id]
            member_particle_indices.extend(indices)
            member_tail_indices.extend(_kind_indices(indices, particles, "tail"))
            member_head_indices.extend(_kind_indices(indices, particles, "head"))

        tail_center = _center_of(member_tail_indices or member_particle_indices, positions)
        head_center = _center_of(member_head_indices or member_particle_indices, positions)
        full_center = _center_of(member_particle_indices, positions)

        clusters[f"cluster:{cluster_index}"] = {
            "members": members,
            "particle_indices": member_particle_indices,
            "tail_indices": member_tail_indices,
            "head_indices": member_head_indices,
            "tail_center": tail_center,
            "head_center": head_center,
            "center": full_center,
            "size": len(members),
        }

    return clusters


def apply_autonomous_pairwise_forces(
    *,
    positions: list[Vector],
    velocities: list[Vector],
    particles: list[MiceliumParticle],
    request: MiceliumSimulationRequest,
    plan: FormationPlan,
) -> None:
    """
    Forças locais reais aproximadas: nenhuma partícula recebe alvo programado.

    Cada partícula interage conforme sua propriedade:
    - radius/mass: exclusão estérica;
    - charge: eletrostática;
    - hydrophobicity: efeito hidrofóbico;
    - polarity: compatibilidade com cabeça/cauda/solvente;
    - kind: cabeça, cauda, contraíon, solvente, soluto.
    """
    cell_size = 2.45
    cells = build_neighbor_cells(positions, particles, cell_size)
    # Cada par (i<j) aparece uma única vez: célula única por partícula e 27 vizinhas distintas.

    env = request.environment
    dielectric = max(1.0, float(env.dielectric_constant))
    ionic = max(0.0, float(env.ionic_strength_mol_l))
    polarity_medium = clamp(float(env.solvent_polarity_index), 0.0, 1.0)
    cmc_factor = _estimate_pair_cmc_factor(plan)

    # Coeficientes físico-químicos.
    electrostatic_k = 0.055 * (78.5 / dielectric)
    active = plan.micellized_fraction > 0.05
    hydrophobic_k = 0.010 * cmc_factor * polarity_medium ** 2 if active else 0.0
    head_tail_penalty_k = 0.030 * (0.45 + polarity_medium)
    steric_k = 0.145

    # v28: orçamento adaptativo de pares por passo.
    # Evita timeout em sistemas grandes sem remover a física principal.
    pair_budget = max(8_000, min(42_000, len(particles) * 42))
    pair_counter = 0

    # Propriedades por partícula calculadas uma vez por passo (mesmas expressões de
    # antes, que eram reavaliadas a cada par: ~5,6 milhões de chamadas por trecho).
    radius_eff = [max(0.12, _pvalue(p, "radius", 0.35)) for p in particles]
    mass_eff = [max(_pvalue(p, "mass", 1.0), 0.1) for p in particles]
    raw_mass = [max(p.mass, 0.1) for p in particles]
    charge = [_pvalue(p, "charge", 0.0) for p in particles]
    hydro = [clamp(_pvalue(p, "hydrophobicity", 0.0), 0.0, 1.0) for p in particles]
    polar = [clamp(_pvalue(p, "polarity", 0.0), 0.0, 1.0) for p in particles]
    kinds = [p.kind for p in particles]
    molecule_ids = [p.molecule_id for p in particles]
    inverse_morphology = "inversa" in plan.morphology

    for key, members in cells.items():
        if pair_counter >= pair_budget:
            break

        candidate_indices: list[int] = []
        for nkey in neighbor_keys(key):
            candidate_indices.extend(cells.get(nkey, []))

        if len(candidate_indices) > 96:
            # Amostragem espacial determinística: mantém vizinhos representativos
            # sem explodir custo em regiões densas.
            stride = max(1, len(candidate_indices) // 96)
            candidate_indices = candidate_indices[::stride][:96]

        for i in members:
            if pair_counter >= pair_budget:
                break
            kind_i = kinds[i]
            for j in candidate_indices:
                if j <= i:
                    continue

                pair_counter += 1

                kind_j = kinds[j]

                # Solvente-solvente não altera a micelização visual; economiza custo.
                if kind_i == "solvent" and kind_j == "solvent":
                    continue

                delta = sub(positions[j], positions[i])
                dist = max(vector_distance(positions[i], positions[j]), 1e-6)
                direction = scale(delta, 1.0 / dist)

                same_molecule = molecule_ids[i] == molecule_ids[j]

                # Beads covalentes adjacentes compartilham volume no modelo CG.
                # Repulsão entre eles alongava a cadeia e competia com os bonds.
                if same_molecule:
                    continue

                # 1) Exclusão estérica intermolecular.
                ri = radius_eff[i]
                rj = radius_eff[j]
                min_distance = max(0.34, (ri + rj) * 1.10)
                if dist < min_distance:
                    repulsion = (min_distance - dist) * steric_k * 1.55
                    velocities[i] = add(velocities[i], scale(direction, -repulsion / mass_eff[i]))
                    velocities[j] = add(velocities[j], scale(direction, repulsion / mass_eff[j]))

                qi = charge[i]
                qj = charge[j]
                hi = hydro[i]
                hj = hydro[j]
                poli = polar[i]
                polj = polar[j]

                # 2) Eletrostática com blindagem de Debye-Hückel visual.
                if abs(qi * qj) > 1e-9 and dist < 5.2:
                    screening = math.exp(-ionic * dist * 2.2)
                    # qi*qj positivo repele; negativo atrai.
                    electro = -(qi * qj) * electrostatic_k * screening / (dist * dist + 0.35)
                    velocities[i] = add(velocities[i], scale(direction, electro / mass_eff[i]))
                    velocities[j] = add(velocities[j], scale(direction, -electro / mass_eff[j]))

                # 3) Cauda-cauda: autoagregação hidrofóbica.
                if kind_i == "tail" and kind_j == "tail" and min_distance < dist < 2.4:
                    strength = (2.4 - dist) * hydrophobic_k * max(hi * hj, 0.15)
                    velocities[i] = add(velocities[i], scale(direction, strength / mass_eff[i]))
                    velocities[j] = add(velocities[j], scale(direction, -strength / mass_eff[j]))

                if kind_i == "head" and kind_j == "head" and min_distance < dist < 2.4:
                    # Desolvatação das cabeças em meio apolar; em água há
                    # repulsão de hidratação, inclusive para cabeças neutras.
                    if inverse_morphology:
                        strength = 0.035 * cmc_factor * (1.0 - polarity_medium) * (2.4 - dist)
                    else:
                        strength = -0.012 * polarity_medium * max(0.0, 1.4 - dist)
                    velocities[i] = add(velocities[i], scale(direction, strength / raw_mass[i]))
                    velocities[j] = add(velocities[j], scale(direction, -strength / raw_mass[j]))

                # 4) Cabeça-cauda: incompatibilidade polar/apolar em meio polar.
                if ((kind_i == "head" and kind_j == "tail") or (kind_i == "tail" and kind_j == "head")) and dist < 1.75:
                    penalty = (1.75 - dist) * head_tail_penalty_k
                    velocities[i] = add(velocities[i], scale(direction, -penalty / mass_eff[i]))
                    velocities[j] = add(velocities[j], scale(direction, penalty / mass_eff[j]))

                # 5) Solvente implícito/traçador: polar estabiliza cabeça, expulsa cauda;
                # meio apolar estabiliza cauda e favorece inversão.
                if kind_i == "solvent" or kind_j == "solvent":
                    solvent_index = i if kind_i == "solvent" else j
                    other_index = j if solvent_index == i else i
                    other_kind = kinds[other_index]
                    sign = -1.0 if solvent_index == i else 1.0

                    if dist < 2.25:
                        if other_kind == "head":
                            force = 0.006 * (2.0 * polarity_medium - 1.0) * (2.25 - dist)
                        elif other_kind == "tail":
                            force = -0.006 * (2.0 * polarity_medium - 1.0) * (2.25 - dist)
                        else:
                            force = 0.002 * (poli + polj - hi - hj) * (2.25 - dist)

                        velocities[other_index] = add(
                            velocities[other_index],
                            scale(direction, sign * force / mass_eff[other_index]),
                        )
                        velocities[solvent_index] = add(
                            velocities[solvent_index],
                            scale(direction, -sign * force / raw_mass[solvent_index]),
                        )



def apply_cluster_self_organization_forces(
    *,
    positions: list[Vector],
    velocities: list[Vector],
    particles: list[MiceliumParticle],
    clusters: dict[str, dict],
    plan: FormationPlan,
    request: MiceliumSimulationRequest,
) -> None:
    """Campo médio local com tamanho finito e orientação molecular."""
    apply_finite_cluster_forces(
        positions=positions, velocities=velocities, particles=particles,
        clusters=clusters, plan=plan,
    )


def apply_autonomous_confinement(
    *,
    positions: list[Vector],
    velocities: list[Vector],
    box_size: float,
) -> None:
    # Parede suave: não teletransporta, só empurra para dentro.
    limit = box_size * 0.49
    for index, position in enumerate(positions):
        radius = vector_distance(position, [0.0, 0.0, 0.0])
        if radius > limit:
            inward = normalize(scale(position, -1.0))
            velocities[index] = add(velocities[index], scale(inward, (radius - limit) * 0.012))




def apply_initial_center_pulse(
    *,
    positions: list[Vector],
    velocities: list[Vector],
    particles: list[MiceliumParticle],
    frame_index: int,
    total_frames: int,
) -> None:
    """
    Pulso inicial único de aproximação ao centro.

    v31:
    Atua só no primeiro chunk de uma mistura nova.
    Não é animação contínua: é uma condição inicial de mistura para aumentar
    colisões/contato. Depois o motor fica entregue às forças físico-químicas.
    """
    warmup_frames = max(8, min(22, total_frames // 8))

    if frame_index >= warmup_frames:
        return

    # Começa fraco, atinge pico pequeno e some.
    local = frame_index / max(warmup_frames - 1, 1)
    envelope = math.sin(local * math.pi)
    strength = 0.010 * envelope

    for index, particle in enumerate(particles):
        position = positions[index]
        radius = vector_distance(position, [0.0, 0.0, 0.0])

        if radius <= 0.15:
            continue

        inward = normalize(scale(position, -1.0))

        # Solvente também pode acompanhar um pouco, mas menos.
        if particle.kind == "solvent":
            factor = 0.20
        elif particle.kind == "counterion":
            factor = 0.45
        else:
            factor = 1.00

        velocities[index] = add(
            velocities[index],
            scale(inward, strength * factor / max(_pvalue(particle, "mass", 1.0), 0.1)),
        )



def build_dynamic_formation_frames(
    *,
    particles: list[MiceliumParticle],
    bonds: list[MiceliumBond],
    initial_positions: list[Vector],
    initial_velocities: list[Vector] | None,
    precluster_positions: list[Vector],
    target_positions: list[Vector],
    box_size: float,
    request: MiceliumSimulationRequest,
    plan: FormationPlan,
    initial_center_pulse: bool = False,
) -> tuple[list[MiceliumFrame], list[Vector], list[Vector]]:
    """
    Motor autônomo contínuo por chunks.

    v27:
    - ignora precluster_positions e target_positions como caminhos;
    - não usa moving_target;
    - cada molécula/partícula evolui por forças próprias;
    - clusters são detectados dinamicamente por contato cauda-cauda;
    - estabilização só aparece depois que o cluster existe;
    - o grafo covalente fica fixo; o grafo supramolecular muda.
    """
    requested_steps = max(96, int(request.steps or 96))

    # v28: chunk menor e mais leve.
    # A qualidade fica nas forças locais, não em número exagerado de frames.
    if len(particles) <= 450:
        frame_count = min(260, max(120, requested_steps))
        substeps = 2
    elif len(particles) <= 1200:
        frame_count = min(190, max(96, requested_steps))
        substeps = 1
    else:
        frame_count = min(130, max(72, requested_steps))
        substeps = 1

    rng = random.Random(request.seed * 1009 + len(particles) * 17 + 271_027)

    positions = [list(position) for position in initial_positions]

    if initial_velocities is not None and len(initial_velocities) == len(positions):
        velocities = [list(velocity) for velocity in initial_velocities]
    else:
        velocities = [
            scale(random_unit_vector(rng), rng.uniform(0.0005, 0.010))
            for _ in positions
        ]

    indexed_bonds = build_bond_index(particles, bonds)
    molecule_groups = group_particle_indices_by_molecule(particles)
    constrain_bond_lengths(positions, indexed_bonds)

    frames: list[MiceliumFrame] = []

    cached_clusters: dict[str, dict] = {}
    cluster_update_interval = 6 if len(particles) > 900 else 4
    organization_interval = 2 if len(particles) > 900 else 1

    temperature = max(1.0, float(request.environment.temperature_k))
    agitation = max(0.0, float(request.environment.agitation_rpm))
    thermal_scale = clamp(math.sqrt(temperature / 298.15) * (1.0 + agitation / 6000.0), 0.45, 1.75)

    for frame_index in range(frame_count):
        for substep in range(substeps):
            local_rng = rng

            apply_bond_springs(
                positions=positions,
                velocities=velocities,
                particles=particles,
                indexed_bonds=indexed_bonds,
            )

            apply_autonomous_pairwise_forces(
                positions=positions,
                velocities=velocities,
                particles=particles,
                request=request,
                plan=plan,
            )
            apply_chain_bending_forces(
                positions=positions, velocities=velocities, particles=particles,
                groups=molecule_groups,
            )

            apply_local_encounter_forces(
                positions=positions, velocities=velocities, particles=particles,
                groups=molecule_groups, plan=plan,
            )

            if initial_center_pulse:
                apply_initial_center_pulse(
                    positions=positions,
                    velocities=velocities,
                    particles=particles,
                    frame_index=frame_index,
                    total_frames=frame_count,
                )

            if frame_index % cluster_update_interval == 0 and substep == 0:
                detected_clusters = detect_supramolecular_clusters(
                    particles=particles,
                    positions=positions,
                    plan=plan,
                )
                # Mantém o eixo do mesmo agregado entre detecções. Recalcular
                # PCA de caudas em reorganização girava a normal da bicamada.
                for cluster in detected_clusters.values():
                    members = set(cluster["members"])
                    previous = max(cached_clusters.values(), key=lambda old: len(members.intersection(old["members"])), default=None)
                    if previous and "organization_axis" in previous:
                        overlap = len(members.intersection(previous["members"]))
                        if overlap >= max(2, len(members) * 0.4):
                            cluster["organization_axis"] = previous["organization_axis"]
                cached_clusters = detected_clusters

            if frame_index % organization_interval == 0:
                apply_cluster_self_organization_forces(
                    positions=positions,
                    velocities=velocities,
                    particles=particles,
                    clusters=cached_clusters,
                    plan=plan,
                    request=request,
                )

            apply_autonomous_confinement(
                positions=positions,
                velocities=velocities,
                box_size=box_size,
            )

            for index, particle in enumerate(particles):
                # Flutuação térmica pequena e física, não "animação de cena".
                if particle.kind == "solvent":
                    noise = 0.0035 * thermal_scale
                    damping = 0.80
                    max_speed = 0.105
                elif particle.kind == "counterion":
                    noise = 0.0030 * thermal_scale
                    damping = 0.84
                    max_speed = 0.12
                else:
                    noise = 0.0022 * thermal_scale
                    damping = 0.88
                    max_speed = 0.13

                velocities[index] = add(
                    velocities[index],
                    scale(random_unit_vector(local_rng), noise / max(_pvalue(particle, "mass", 1.0), 0.1)),
                )

                velocities[index] = scale(velocities[index], damping)

                speed = vector_distance(velocities[index], [0.0, 0.0, 0.0])
                if speed > max_speed:
                    velocities[index] = scale(velocities[index], max_speed / speed)

                positions[index] = clamp_vector_to_box(
                    add(positions[index], scale(velocities[index], 1.0 / max(substeps, 1))),
                    box_size,
                )

            resolve_hard_overlaps(
                positions=positions,
                velocities=velocities,
                particles=particles,
                box_size=box_size,
            )
            # O solver de colisão não pode deixar bonds alongados. Alternar
            # restrições conserva o grafo e acomoda os contatos intermoleculares.
            constrain_bond_lengths(positions, indexed_bonds)

        frames.append(
            MiceliumFrame(
                frame_index=frame_index,
                time_ps=round(frame_index * request.dt, 6),
                coordinates=sanitize_positions(positions),
            )
        )

    return frames, sanitize_positions(positions), sanitize_positions(velocities)


def build_formation_frames(
    *,
    particles: list[MiceliumParticle],
    bonds: list[MiceliumBond],
    initial_positions: list[Vector],
    initial_velocities: list[Vector] | None,
    precluster_positions: list[Vector],
    target_positions: list[Vector],
    box_size: float,
    request: MiceliumSimulationRequest,
    plan: FormationPlan,
    initial_center_pulse: bool = False,
) -> tuple[list[MiceliumFrame], list[Vector], list[Vector]]:
    return build_dynamic_formation_frames(
        particles=particles,
        bonds=bonds,
        initial_positions=initial_positions,
        initial_velocities=initial_velocities,
        precluster_positions=precluster_positions,
        target_positions=target_positions,
        box_size=box_size,
        request=request,
        plan=plan,
        initial_center_pulse=initial_center_pulse,
    )

REPRESENTATION_LABEL = "Visualização representativa — não é simulação física"
VALIDATION_STATUS = ("não validado experimentalmente: a morfologia prevista vem de CPP/c/CMC e a observada é "
                     "medida nas coordenadas de uma visualização coarse-grained heurística")


class MiceliumEngine:
    def run(self, request: MiceliumSimulationRequest) -> MiceliumSimulationResponse:
        solvent_profile = infer_solvent_profile(request)
        effective_environment = request.environment.model_copy(update={
            "solvent_name": solvent_profile.name,
            "solvent_polarity_index": solvent_profile.polarity,
            "dielectric_constant": solvent_profile.dielectric,
        })
        request = request.model_copy(update={"environment": effective_environment})
        ai_notes: list[str] = []
        enriched_molecules, ai_notes = enrich_molecules_with_ai(request.molecules, request.environment)

        if enriched_molecules != request.molecules:
            request = request.model_copy(update={"molecules": enriched_molecules})

        session_key = request_session_key(request)

        particles, bonds, positions, velocities, box_size, representation = build_initial_state(request)

        session_state = _MICELIUM_SESSION_STATE.get(session_key)

        if session_state:
            saved_positions = session_state.get("positions")
            saved_velocities = session_state.get("velocities")
            saved_particle_count = session_state.get("particle_count")

            if (
                isinstance(saved_positions, list)
                and isinstance(saved_velocities, list)
                and saved_particle_count == len(particles)
                and len(saved_positions) == len(particles)
                and len(saved_velocities) == len(particles)
            ):
                positions = sanitize_positions(saved_positions)  # continua do último frame
                velocities = sanitize_positions(saved_velocities)

        metrics = calculate_micellization_metrics(
            request.molecules,
            request.environment.volume_ml,
            solvent_profile,
        )

        surfactant_count = len({p.molecule_id for p in particles if p.kind == "head"})
        plan = choose_formation_plan(request, surfactant_count, metrics, solvent_profile)

        # v28: o motor autônomo não usa trajetória por alvo.
        # Evita pré-cálculo morfológico pesado sem perder a física local.
        precluster_positions = positions
        target_positions = positions

        frames, final_positions, final_velocities = build_formation_frames(
            particles=particles,
            bonds=bonds,
            initial_positions=positions,
            initial_velocities=velocities,
            precluster_positions=precluster_positions,
            target_positions=target_positions,
            box_size=box_size,
            request=request,
            plan=plan,
            initial_center_pulse=False,
        )

        # Guarda estado final para o próximo chunk REST da mesma mistura.
        _MICELIUM_SESSION_STATE[session_key] = {
            "positions": final_positions,
            "velocities": final_velocities,
            "particle_count": len(particles),
            "box_size": box_size,
        }

        # Evita crescimento indefinido se o usuário testar muitas misturas.
        if len(_MICELIUM_SESSION_STATE) > 12:
            first_key = next(iter(_MICELIUM_SESSION_STATE))
            if first_key != session_key:
                _MICELIUM_SESSION_STATE.pop(first_key, None)

        clusters, analysis = analyze_micelium_state(
            particles=particles,
            positions=final_positions,
            environment=request.environment,
            molecule_count=sum(molecule.count for molecule in request.molecules),
            # Organização observada usa o c/CMC da visualização (parcial se houver componente ignorado).
            c_over_cmc_proxy=metrics.c_over_cmc if metrics.c_over_cmc is not None else metrics.partial_c_over_cmc,
            real_concentration_mmol_l=metrics.real_concentration_mmol_l,
            real_amount_mmol=metrics.real_amount_mmol,
            critical_amount_mmol=metrics.critical_amount_mmol,
            missing_amount_mmol=metrics.missing_amount_mmol,
            excess_amount_mmol=metrics.excess_amount_mmol,
            visual_scale_factor=metrics.visual_scale_factor,
            morphology_hint=plan.morphology if plan.geometry_template else None,
        )

        prediction_note = None
        if metrics.ignored_components:
            prediction_note = ("visualização aproximada: ignora " + "; ".join(metrics.ignored_components)
                               + " no cálculo de c/CMC (Clint só com os componentes de CMC conhecida)")
        analysis = analysis.model_copy(update={
            "predicted_morphology": plan.morphology,
            "predicted_regime": plan.formation_phase,
            "measured_morphology": (max(analysis.independent_shape_distribution.items(), key=lambda item: item[1])[0]
                                    if analysis.independent_shape_distribution else "monômeros dispersos"),
            "morphology_basis": plan.morphology_basis,
            "representation_label": REPRESENTATION_LABEL,
            "validation_status": VALIDATION_STATUS,
            "ignored_components": list(metrics.ignored_components),
            "prediction_note": prediction_note,
            "c_over_cmc_parcial": metrics.partial_c_over_cmc,
            "c_over_cmc_proxy": metrics.c_over_cmc,   # total estrito (None se a mistura está incompleta)
        })

        notes = [
            "Motor CG: campo médio local com raio finito, orientação cabeça/cauda e restrições de comprimento; chunks continuam do último estado.",
            "Quantidade real em mmol determina concentração; count/visual_count controla apenas a amostra visual.",
            "Morfologia observada e fração organizada são medidas nas coordenadas, separadas da tendência prevista.",
            f"Tendência morfológica aproximada: {plan.morphology}. Regime de concentração: {plan.formation_phase}.",
            "CPP, CMC efetiva e forças são aproximações mesoscópicas; não determinam sozinhos a fase experimental de uma molécula arbitrária.",
            "Tempo, forças e índices do modelo CG não foram calibrados para dinâmica molecular experimental.",
        ]

        notes.extend(solvent_profile.notes)

        if ai_notes:
            notes.extend(ai_notes)

        if len(particles) >= request.max_particles:
            notes.append("Sistema truncado por max_particles. Aumente com cuidado ou use streaming.")

        if metrics.c_over_cmc is None and metrics.partial_c_over_cmc is not None:
            notes.append("c/CMC total da mistura desconhecido; a visualização usa o c/CMC parcial dos componentes com CMC.")
        elif metrics.c_over_cmc is None:
            notes.append("Sem CMC/concentração real suficiente; análise micelar quantitativa fica qualitativa.")

        if metrics.c_over_cmc is not None and metrics.c_over_cmc < 1.0:
            notes.append("C/CMC abaixo de 1: o motor mostra pré-agregação/dispersão, não força micela estável.")

        return MiceliumSimulationResponse(
            representation=representation,
            environment=request.environment,
            particles=particles,
            bonds=bonds,
            frames=frames,
            clusters=clusters,
            analysis=analysis,
            notes=notes,
        )
