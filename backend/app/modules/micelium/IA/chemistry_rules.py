from __future__ import annotations

import hashlib
import math
import re

from app.modules.micelium.IA.headgroup_classifier import classify_cationic_headgroup
from app.modules.micelium.IA.constants import (
    ANIONIC_HEAD_PATTERNS,
    CATIONIC_HEAD_PATTERNS,
    COUNTERION_COMPONENT_PATTERNS,
    COUNTERION_PATTERNS,
    NONIONIC_HEAD_PATTERNS,
    ZWITTERIONIC_HEAD_PATTERNS,
)
from app.modules.micelium.IA.schemas import AIRoute, SurfactantClass


def stable_hash(*parts: object) -> str:
    raw = "|".join(str(part) for part in parts if part is not None)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def normalize_smiles_text(smiles: str) -> str:
    return " ".join((smiles or "").strip().split())


def split_salt_components(smiles: str) -> list[str]:
    normalized = normalize_smiles_text(smiles)
    if not normalized:
        return []
    return [part.strip() for part in normalized.split(".") if part.strip()]


def detect_counterion_component(component: str) -> str | None:
    for counterion, patterns in COUNTERION_COMPONENT_PATTERNS.items():
        if any(pattern in component for pattern in patterns):
            return counterion
    return None


def detect_counterion(smiles: str) -> str | None:
    for counterion, patterns in COUNTERION_PATTERNS.items():
        if any(pattern in smiles for pattern in patterns):
            return counterion
    return None


def split_active_and_counterion(smiles: str) -> tuple[str, str | None, str | None, list[str]]:
    components = split_salt_components(smiles)

    if not components:
        return smiles, None, None, []

    counterion_component = None
    counterion_label = None
    active_components: list[str] = []

    for component in components:
        detected = detect_counterion_component(component)

        if detected and counterion_component is None:
            counterion_component = component
            counterion_label = detected
        else:
            active_components.append(component)

    if not active_components:
        active_components = components

    active_component = max(active_components, key=len)

    return active_component, counterion_component, counterion_label, components


def detect_pattern_group(
    smiles: str,
    pattern_table: dict[str, list[str]],
) -> str | None:
    lowered = smiles.lower()
    for group, patterns in pattern_table.items():
        for pattern in patterns:
            if pattern.lower() in lowered:
                return group
    return None


def max_consecutive_carbon_run(smiles: str) -> int:
    if not smiles:
        return 0

    matches = re.findall(r"C{4,}", smiles)
    if not matches:
        return 0

    return max(len(match) for match in matches)


def estimate_tail_count(smiles: str) -> int:
    runs = re.findall(r"C{8,}", smiles or "")
    if not runs:
        return 0
    return len(runs)


def estimate_tail_type(smiles: str) -> str | None:
    tail = max_consecutive_carbon_run(smiles)
    if tail <= 0:
        return None
    if "c1" in smiles.lower():
        return "aryl_alkyl"
    if "(" in smiles and tail >= 8:
        return "branched_alkyl"
    return "linear_alkyl"


def detect_head_group(smiles: str) -> tuple[str | None, SurfactantClass, float]:
    cationic_classification = classify_cationic_headgroup(smiles)
    anionic = detect_pattern_group(smiles, ANIONIC_HEAD_PATTERNS)
    nonionic = detect_pattern_group(smiles, NONIONIC_HEAD_PATTERNS)

    if anionic == "carboxylate":
        # C(=O)O also occurs in neutral esters; inspect the oxygen before
        # assigning the molecule to the anionic specialist.
        from rdkit import Chem

        mol = Chem.MolFromSmiles(smiles)
        acid = Chem.MolFromSmarts("[CX3](=[OX1])[OX2H1]")
        carboxylate = Chem.MolFromSmarts("[CX3](=[OX1])[O-]")
        if mol is not None and not (
            mol.HasSubstructMatch(acid) or mol.HasSubstructMatch(carboxylate)
        ):
            anionic = None

    has_anionic = anionic is not None or "[O-]" in smiles

    if has_anionic and ("[N+]" in smiles or "[n+]" in smiles):
        zwitter = detect_pattern_group(smiles, ZWITTERIONIC_HEAD_PATTERNS)
        return zwitter or anionic or "zwitterionic_head", "zwitterionic", 0.88

    if cationic_classification.head_group:
        return (
            cationic_classification.head_group,
            "cationic",
            cationic_classification.confidence,
        )

    if has_anionic:
        return anionic or "anionic_head", "anionic", 0.86

    if nonionic:
        return nonionic, "nonionic", 0.72

    return None, "unknown", 0.0


def route_for_class(surfactant_class: SurfactantClass) -> AIRoute:
    if surfactant_class == "anionic":
        return "anionic_ai"
    if surfactant_class == "cationic":
        return "cationic_ai"
    if surfactant_class == "nonionic":
        return "nonionic_ai"
    if surfactant_class in {"zwitterionic", "amphoteric"}:
        return "zwitterionic_ai"
    return "unknown_ai"


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    if not math.isfinite(value):
        return low
    return max(low, min(high, value))


def estimate_amphiphilicity(
    *,
    tail_carbon_count: int | None,
    head_group: str | None,
    logp: float | None,
    tpsa: float | None,
) -> float:
    tail_term = clamp((tail_carbon_count or 0) / 16.0)
    head_term = 1.0 if head_group else 0.0
    logp_term = clamp(((logp or 0.0) + 1.0) / 6.0)
    tpsa_term = clamp((tpsa or 0.0) / 120.0)
    balance = 1.0 - abs(logp_term - tpsa_term)

    return clamp(0.36 * tail_term + 0.30 * head_term + 0.18 * balance + 0.16 * logp_term)


def is_probable_commercial_mixture(name: str | None, smiles: str) -> bool:
    label = f"{name or ''} {smiles}".lower()
    return any(
        token in label
        for token in [
            "tween",
            "span",
            "brij",
            "triton",
            "polysorbate",
            "commercial",
            "mixture",
        ]
    )


def safe_log10(value: float | None) -> float | None:
    if value is None or value <= 0:
        return None
    return math.log10(value)


def amount_from_concentration(
    concentration_mmol_l: float | None,
    volume_ml: float,
) -> float | None:
    if concentration_mmol_l is None:
        return None
    return max(0.0, concentration_mmol_l) * max(volume_ml, 0.0) / 1000.0


def classic_hlb_from_effective(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(20.0, value))


