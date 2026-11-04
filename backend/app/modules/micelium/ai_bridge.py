from __future__ import annotations

from dataclasses import dataclass

try:
    from app.modules.micelium.IA.prediction_service import MiceliumAIService
    from app.modules.micelium.IA.schemas import (
        MiceliumAIEnvironment,
        MiceliumAIPredictionRequest,
        MiceliumAIPredictionResponse,
    )
except Exception:  # IA opcional: o motor 3D não deve cair se os modelos ainda não estiverem aplicados.
    MiceliumAIService = None  # type: ignore[assignment]
    MiceliumAIEnvironment = None  # type: ignore[assignment]
    MiceliumAIPredictionRequest = None  # type: ignore[assignment]
    MiceliumAIPredictionResponse = None  # type: ignore[assignment]
from app.modules.micelium.schemas import (
    MiceliumEnvironment,
    MiceliumMoleculeInput,
)


_ai_service: MiceliumAIService | None = None


@dataclass(slots=True)
class AIEnrichmentResult:
    molecule: MiceliumMoleculeInput
    notes: list[str]
    prediction: MiceliumAIPredictionResponse | None = None


def get_ai_service() -> MiceliumAIService:
    global _ai_service

    if MiceliumAIService is None:
        raise RuntimeError("Módulo de IA micelar não está disponível; simulação seguirá sem enriquecimento automático.")

    if _ai_service is None:
        _ai_service = MiceliumAIService()

    return _ai_service


def concentration_from_molecule(
    molecule: MiceliumMoleculeInput,
    environment: MiceliumEnvironment,
) -> float | None:
    if molecule.real_concentration_mmol_l is not None:
        return float(molecule.real_concentration_mmol_l)

    if molecule.real_amount_mmol is not None:
        volume_l = max(environment.volume_ml / 1000.0, 1e-12)
        return float(molecule.real_amount_mmol) / volume_l

    return None


def build_ai_environment(
    molecule: MiceliumMoleculeInput,
    environment: MiceliumEnvironment,
) -> MiceliumAIEnvironment:
    return MiceliumAIEnvironment(
        temperature_k=environment.temperature_k,
        pressure_atm=environment.pressure_atm,
        ph=environment.ph,
        ionic_strength_mol_l=environment.ionic_strength_mol_l,
        solvent_polarity_index=environment.solvent_polarity_index,
        dielectric_constant=environment.dielectric_constant,
        agitation_rpm=environment.agitation_rpm,
        volume_ml=environment.volume_ml,
        solvent=environment.solvent_name,
        salt_type=None,
        salt_concentration_mol_l=None,
        surfactant_concentration_mmol_l=concentration_from_molecule(
            molecule,
            environment,
        ),
    )


def molecule_needs_ai(molecule: MiceliumMoleculeInput) -> bool:
    if molecule.role == "solvent":
        return False

    return (
        molecule.cmc_mmol_l is None
        or molecule.hlb is None
        or molecule.effective_hlb is None
        or molecule.surfactant_class is None
        or molecule.is_surfactant is None
        or molecule.tail_carbon_count is None
    )


def enrich_molecule_with_ai_detailed(
    molecule: MiceliumMoleculeInput,
    environment: MiceliumEnvironment,
    *,
    force_analysis: bool = False,
) -> AIEnrichmentResult:
    if molecule.role == "solvent":
        return AIEnrichmentResult(molecule=molecule, notes=[], prediction=None)

    if not force_analysis and not molecule_needs_ai(molecule):
        return AIEnrichmentResult(molecule=molecule, notes=[], prediction=None)

    notes: list[str] = []

    try:
        ai_environment = build_ai_environment(molecule, environment)
        request = MiceliumAIPredictionRequest(
            name=molecule.name,
            smiles=molecule.smiles,
            concentration=ai_environment.surfactant_concentration_mmol_l,
            unit="mmol/L" if ai_environment.surfactant_concentration_mmol_l is not None else None,
            environment=ai_environment,
        )

        response = get_ai_service().predict(request, save=False)
    except Exception as exc:
        notes.append(
            f"IA micelar indisponível para {molecule.name or molecule.smiles}: {type(exc).__name__}: {exc}"
        )
        return AIEnrichmentResult(molecule=molecule, notes=notes, prediction=None)

    identity = response.molecule
    prediction = response.prediction
    descriptors = identity.descriptors

    update_data: dict[str, object] = {}

    if molecule.is_surfactant is None:
        update_data["is_surfactant"] = identity.is_surfactant

    if molecule.surfactant_class is None and identity.surfactant_class != "unknown":
        update_data["surfactant_class"] = identity.surfactant_class

    if molecule.logp is None and descriptors.logp is not None:
        update_data["logp"] = descriptors.logp

    if molecule.tpsa is None and descriptors.tpsa is not None:
        update_data["tpsa"] = descriptors.tpsa

    if molecule.tail_carbon_count is None and descriptors.tail_carbon_count is not None:
        update_data["tail_carbon_count"] = descriptors.tail_carbon_count

    if molecule.head_area_a2 is None and descriptors.head_area_a2 is not None:
        update_data["head_area_a2"] = descriptors.head_area_a2

    packing = descriptors.raw_descriptors.get("packing_estimate", {})
    if molecule.tail_volume_a3 is None and packing.get("tail_volume_a3") is not None:
        update_data["tail_volume_a3"] = packing["tail_volume_a3"]
    if molecule.packing_parameter is None and packing.get("cpp") is not None:
        area = molecule.head_area_a2 or packing["head_area_a2"]
        volume = molecule.tail_volume_a3 or packing["tail_volume_a3"]
        update_data["packing_parameter"] = volume / (area * packing["tail_length_a"])

    if molecule.cmc_mmol_l is None and prediction.predicted_cmc_mmol_l is not None:
        update_data["cmc_mmol_l"] = prediction.predicted_cmc_mmol_l

    if molecule.hlb is None and prediction.predicted_hlb is not None:
        update_data["hlb"] = prediction.predicted_hlb

    if molecule.effective_hlb is None and prediction.predicted_effective_hlb is not None:
        update_data["effective_hlb"] = prediction.predicted_effective_hlb

    if molecule.micellar_behavior is None:
        update_data["micellar_behavior"] = (
            "ai_predicted_micellar_behavior"
            if identity.is_surfactant
            else "not_predicted_as_surfactant"
        )

    enriched = molecule.model_copy(update=update_data) if update_data else molecule

    action = "analisou/salvou snapshot de" if force_analysis else "preencheu dados de"

    notes.append(
        f"IA micelar {action} "
        f"{molecule.name or molecule.smiles}: "
        f"class={identity.surfactant_class}, "
        f"CMC={prediction.predicted_cmc_mmol_l}, "
        f"HLB={prediction.predicted_hlb}, "
        f"HLB efetivo={prediction.predicted_effective_hlb}."
    )

    return AIEnrichmentResult(
        molecule=enriched,
        notes=notes,
        prediction=response,
    )


def enrich_molecule_with_ai(
    molecule: MiceliumMoleculeInput,
    environment: MiceliumEnvironment,
) -> tuple[MiceliumMoleculeInput, list[str]]:
    result = enrich_molecule_with_ai_detailed(
        molecule=molecule,
        environment=environment,
        force_analysis=False,
    )

    return result.molecule, result.notes


def enrich_molecules_with_ai_detailed(
    molecules: list[MiceliumMoleculeInput],
    environment: MiceliumEnvironment,
    *,
    force_analysis: bool = False,
) -> tuple[list[MiceliumMoleculeInput], list[str], list[MiceliumAIPredictionResponse]]:
    enriched: list[MiceliumMoleculeInput] = []
    notes: list[str] = []
    predictions: list[MiceliumAIPredictionResponse] = []

    for molecule in molecules:
        result = enrich_molecule_with_ai_detailed(
            molecule=molecule,
            environment=environment,
            force_analysis=force_analysis,
        )
        enriched.append(result.molecule)
        notes.extend(result.notes)

        if result.prediction is not None:
            predictions.append(result.prediction)

    return enriched, notes, predictions


def enrich_molecules_with_ai(
    molecules: list[MiceliumMoleculeInput],
    environment: MiceliumEnvironment,
) -> tuple[list[MiceliumMoleculeInput], list[str]]:
    enriched, notes, _predictions = enrich_molecules_with_ai_detailed(
        molecules=molecules,
        environment=environment,
        force_analysis=False,
    )

    return enriched, notes
