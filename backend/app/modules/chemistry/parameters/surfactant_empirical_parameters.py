from __future__ import annotations

from dataclasses import dataclass
import math

from app.modules.chemistry.parameters.surfactant_head_classifier import (
    CATIONIC_HEAD_PARAMS,
    classify_cationic_headgroup,
)


@dataclass(frozen=True, slots=True)
class EmpiricalSurfactantParameters:
    surfactant_type: str
    head_area_a2: float
    klevens_a: float
    klevens_b: float
    notes: list[str]


def resolve_empirical_parameters(smiles: str) -> EmpiricalSurfactantParameters:
    classification = classify_cationic_headgroup(smiles)

    if classification.head_group and classification.head_group in CATIONIC_HEAD_PARAMS:
        params = CATIONIC_HEAD_PARAMS[classification.head_group]

        return EmpiricalSurfactantParameters(
            surfactant_type=classification.head_group,
            head_area_a2=params["head_area_a2"],
            klevens_a=params["klevens_a"],
            klevens_b=params["klevens_b"],
            notes=classification.notes,
        )

    return EmpiricalSurfactantParameters(
        surfactant_type="UNKNOWN_OR_NON_CATIONIC_SURFACTANT",
        head_area_a2=50.0,
        klevens_a=1.60,
        klevens_b=0.29,
        notes=["Fallback genérico: revisar classificação estrutural."],
    )


def klevens_cmc_mmol_l(
    *,
    tail_carbon_count: int,
    klevens_a: float,
    klevens_b: float,
) -> float:
    log_cmc_mol_l = klevens_a - klevens_b * tail_carbon_count

    return (10.0 ** log_cmc_mol_l) * 1000.0


def cpp_from_tanford(
    *,
    tail_volume_a3: float,
    head_area_a2: float,
    max_tail_length_a: float,
) -> float:
    denominator = head_area_a2 * max_tail_length_a

    if denominator <= 0:
        return 0.0

    return tail_volume_a3 / denominator


