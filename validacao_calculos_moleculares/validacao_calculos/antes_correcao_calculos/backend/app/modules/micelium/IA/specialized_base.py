from __future__ import annotations

from abc import ABC, abstractmethod

from app.modules.micelium.IA.chemistry_rules import (
    amount_from_concentration,
    classic_hlb_from_effective,
    clamp,
    safe_log10,
)
from app.modules.micelium.IA.feature_builder import build_feature_vector
from app.modules.micelium.IA.model_registry import ModelRegistry
from app.modules.micelium.IA.schemas import (
    AIRoute,
    MiceliumAIEnvironment,
    MolecularIdentityResult,
    SpecializedAIPrediction,
    SurfactantClass,
)


class SpecializedSurfactantAI(ABC):
    route: AIRoute
    surfactant_class: SurfactantClass
    model_version = "heuristic_v0.2.0"

    def __init__(self, registry: ModelRegistry | None = None) -> None:
        self.registry = registry or ModelRegistry()

    def predict(
        self,
        *,
        identity: MolecularIdentityResult,
        environment: MiceliumAIEnvironment,
    ) -> SpecializedAIPrediction:
        features = build_feature_vector(identity, environment)

        predicted_cmc = self.registry.predict_one(
            route=self.route,
            target="cmc_mmol_l",
            features=features,
        )

        predicted_effective_hlb = self.registry.predict_one(
            route=self.route,
            target="effective_hlb",
            features=features,
        )

        predicted_hlb = self.registry.predict_one(
            route=self.route,
            target="hlb",
            features=features,
        )

        if predicted_cmc is None:
            predicted_cmc = self.heuristic_cmc(identity, environment)

        if predicted_effective_hlb is None:
            predicted_effective_hlb = self.heuristic_effective_hlb(identity, environment)

        if predicted_hlb is None:
            predicted_hlb = classic_hlb_from_effective(predicted_effective_hlb)

        predicted_cmc = max(1e-9, predicted_cmc) if predicted_cmc is not None else None
        predicted_log_cmc = safe_log10(predicted_cmc)

        concentration = environment.surfactant_concentration_mmol_l
        c_over_cmc = (
            concentration / predicted_cmc
            if concentration is not None and predicted_cmc and predicted_cmc > 0
            else None
        )

        critical_amount = amount_from_concentration(
            predicted_cmc,
            environment.volume_ml,
        )

        actual_amount = amount_from_concentration(
            concentration,
            environment.volume_ml,
        )

        missing_amount = (
            max(0.0, (critical_amount or 0.0) - actual_amount)
            if critical_amount is not None and actual_amount is not None
            else None
        )

        excess_amount = (
            max(0.0, actual_amount - (critical_amount or 0.0))
            if critical_amount is not None and actual_amount is not None
            else None
        )

        probability = self.micelle_probability(
            identity=identity,
            environment=environment,
            c_over_cmc=c_over_cmc,
        )

        stability = self.stability_score(
            identity=identity,
            environment=environment,
            c_over_cmc=c_over_cmc,
        )

        aggregation_number = self.aggregation_number(
            identity=identity,
            environment=environment,
            c_over_cmc=c_over_cmc,
        )

        radius = self.radius_nm(
            identity=identity,
            environment=environment,
            aggregation_number=aggregation_number,
        )

        zeta = self.zeta_mv(identity, environment)

        warnings: list[str] = []

        if concentration is None:
            warnings.append("Concentração real não informada; C/CMC e probabilidade micelar ficam qualitativos.")

        if identity.descriptors.is_commercial_mixture:
            warnings.append("Surfactante comercial/mistura provável; confiança quantitativa reduzida.")

        return SpecializedAIPrediction(
            ai_route=self.route,
            surfactant_class=self.surfactant_class,
            model_version=self.model_version,
            predicted_cmc_mmol_l=predicted_cmc,
            predicted_log_cmc=predicted_log_cmc,
            predicted_hlb=predicted_hlb,
            predicted_effective_hlb=predicted_effective_hlb,
            c_over_cmc=c_over_cmc,
            missing_amount_mmol=missing_amount,
            excess_amount_mmol=excess_amount,
            critical_amount_mmol=critical_amount,
            micelle_expected=bool(c_over_cmc is not None and c_over_cmc >= 1.0),
            micelle_probability=probability,
            predicted_aggregation_number=aggregation_number,
            predicted_radius_nm=radius,
            predicted_zeta_mv=zeta,
            stability_score=stability,
            warnings=warnings,
            prediction_json={
                "heuristic": True,
                "hlb_note": "predicted_hlb é escala clássica limitada; predicted_effective_hlb pode passar de 20 para uso interno.",
            },
        )

    @abstractmethod
    def heuristic_cmc(
        self,
        identity: MolecularIdentityResult,
        environment: MiceliumAIEnvironment,
    ) -> float | None:
        raise NotImplementedError

    @abstractmethod
    def heuristic_effective_hlb(
        self,
        identity: MolecularIdentityResult,
        environment: MiceliumAIEnvironment,
    ) -> float | None:
        raise NotImplementedError

    def micelle_probability(
        self,
        *,
        identity: MolecularIdentityResult,
        environment: MiceliumAIEnvironment,
        c_over_cmc: float | None,
    ) -> float:
        if c_over_cmc is None:
            base = 0.18 + 0.45 * identity.descriptors.amphiphilicity_score
        else:
            base = (c_over_cmc - 0.55) / 2.2

        polarity_bonus = 0.12 * environment.solvent_polarity_index
        tail_bonus = 0.10 * clamp(((identity.descriptors.tail_carbon_count or 0) - 6) / 12)

        return clamp(base + polarity_bonus + tail_bonus)

    def stability_score(
        self,
        *,
        identity: MolecularIdentityResult,
        environment: MiceliumAIEnvironment,
        c_over_cmc: float | None,
    ) -> float:
        ccmc_term = 0.30 if c_over_cmc is None else clamp((c_over_cmc - 0.65) / 2.0)
        amph_term = identity.descriptors.amphiphilicity_score
        ionic_term = clamp(environment.ionic_strength_mol_l * 4.0)
        temperature_penalty = clamp(abs(environment.temperature_k - 298.15) / 95.0) * 0.16

        return clamp(0.42 * ccmc_term + 0.36 * amph_term + 0.18 * ionic_term - temperature_penalty)

    def aggregation_number(
        self,
        *,
        identity: MolecularIdentityResult,
        environment: MiceliumAIEnvironment,
        c_over_cmc: float | None,
    ) -> float | None:
        tail = identity.descriptors.tail_carbon_count or 8
        ratio = c_over_cmc if c_over_cmc is not None else 1.0
        return max(5.0, min(160.0, 16.0 + tail * 3.0 + ratio * 10.0))

    def radius_nm(
        self,
        *,
        identity: MolecularIdentityResult,
        environment: MiceliumAIEnvironment,
        aggregation_number: float | None,
    ) -> float | None:
        tail = identity.descriptors.tail_carbon_count or 8
        aggregation = aggregation_number or 24
        return max(0.8, min(8.0, 0.45 + 0.095 * tail + 0.006 * aggregation))

    def zeta_mv(
        self,
        identity: MolecularIdentityResult,
        environment: MiceliumAIEnvironment,
    ) -> float | None:
        return None
