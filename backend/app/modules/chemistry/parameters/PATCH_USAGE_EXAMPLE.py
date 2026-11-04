from __future__ import annotations

from app.modules.chemistry.parameters.electronic_descriptor_sanitizer import (
    neutralize_primary_ammonium_for_electronic_descriptors,
)
from app.modules.chemistry.parameters.surfactant_empirical_parameters import (
    cpp_from_tanford,
    klevens_cmc_mmol_l,
    resolve_empirical_parameters,
)


def corrected_octylammonium_example() -> dict[str, float | str]:
    smiles = "CCCCCCCC[NH3+].[Cl-]"
    params = resolve_empirical_parameters(smiles)

    cmc_mmol_l = klevens_cmc_mmol_l(
        tail_carbon_count=8,
        klevens_a=params.klevens_a,
        klevens_b=params.klevens_b,
    )

    cpp = cpp_from_tanford(
        tail_volume_a3=242.6,
        head_area_a2=params.head_area_a2,
        max_tail_length_a=11.62,
    )

    electronic_smiles = neutralize_primary_ammonium_for_electronic_descriptors(smiles)

    return {
        "classification": params.surfactant_type,
        "head_area_a2": params.head_area_a2,
        "cmc_mmol_l": cmc_mmol_l,
        "cpp": cpp,
        "electronic_smiles": electronic_smiles,
    }


