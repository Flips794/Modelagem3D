from __future__ import annotations

import math
from typing import Any

from app.modules.micelium.IA.schemas import (
    MiceliumAIEnvironment,
    MolecularIdentityResult,
)


FEATURE_ORDER = [
    "molar_mass",
    "exact_mass",
    "active_component_molar_mass",
    "formal_charge",
    "active_component_formal_charge",
    "hetero_atom_count",
    "hbd",
    "hba",
    "tpsa",
    "logp",
    "rotatable_bonds",
    "rings",
    "aromatic_rings",
    "fraction_csp3",
    "tail_carbon_count",
    "tail_count",
    "amphiphilicity_score",
    "polarity_score",
    "hydrophobicity_score",
    "temperature_k",
    "pressure_atm",
    "ph",
    "ionic_strength_mol_l",
    "solvent_polarity_index",
    "dielectric_constant",
    "salt_concentration_mol_l",
    "surfactant_concentration_mmol_l",
]


def number_or_zero(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0

    if not math.isfinite(parsed):
        return 0.0

    return parsed


def build_feature_dict(
    identity: MolecularIdentityResult,
    environment: MiceliumAIEnvironment,
) -> dict[str, float]:
    descriptors = identity.descriptors

    feature_dict = {
        "molar_mass": descriptors.molar_mass,
        "exact_mass": descriptors.exact_mass,
        "active_component_molar_mass": descriptors.active_component_molar_mass,
        "formal_charge": descriptors.formal_charge,
        "active_component_formal_charge": descriptors.active_component_formal_charge,
        "hetero_atom_count": descriptors.hetero_atom_count,
        "hbd": descriptors.hbd,
        "hba": descriptors.hba,
        "tpsa": descriptors.tpsa,
        "logp": descriptors.logp,
        "rotatable_bonds": descriptors.rotatable_bonds,
        "rings": descriptors.rings,
        "aromatic_rings": descriptors.aromatic_rings,
        "fraction_csp3": descriptors.fraction_csp3,
        "tail_carbon_count": descriptors.tail_carbon_count,
        "tail_count": descriptors.tail_count,
        "amphiphilicity_score": descriptors.amphiphilicity_score,
        "polarity_score": descriptors.polarity_score,
        "hydrophobicity_score": descriptors.hydrophobicity_score,
        "temperature_k": environment.temperature_k,
        "pressure_atm": environment.pressure_atm,
        "ph": environment.ph,
        "ionic_strength_mol_l": environment.ionic_strength_mol_l,
        "solvent_polarity_index": environment.solvent_polarity_index,
        "dielectric_constant": environment.dielectric_constant,
        "salt_concentration_mol_l": environment.salt_concentration_mol_l,
        "surfactant_concentration_mmol_l": environment.surfactant_concentration_mmol_l,
    }

    return {key: number_or_zero(value) for key, value in feature_dict.items()}


def build_feature_vector(
    identity: MolecularIdentityResult,
    environment: MiceliumAIEnvironment,
) -> list[float]:
    feature_dict = build_feature_dict(identity, environment)
    return [feature_dict[key] for key in FEATURE_ORDER]


def descriptor_snapshot_json(
    identity: MolecularIdentityResult,
    environment: MiceliumAIEnvironment,
) -> dict[str, Any]:
    return {
        "molecule": identity.model_dump(),
        "environment": environment.model_dump(),
        "features": build_feature_dict(identity, environment),
        "feature_order": FEATURE_ORDER,
    }
