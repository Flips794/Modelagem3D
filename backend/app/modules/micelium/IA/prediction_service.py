from __future__ import annotations

import math
from app.modules.chemistry.parameters.validated_calculations import concentration_mmol_l

from app.modules.micelium.IA.amphoteric_ai import AmphotericSurfactantAI
from app.modules.micelium.IA.anionic_ai import AnionicSurfactantAI
from app.modules.micelium.IA.cationic_ai import CationicSurfactantAI
from app.modules.micelium.IA.chemistry_rules import clamp
from app.modules.micelium.IA.model_registry import ModelRegistry
from app.modules.micelium.IA.molecular_identity_ai import MolecularIdentityAI
from app.modules.micelium.IA.nonionic_ai import NonionicSurfactantAI
from app.modules.micelium.IA.schemas import (
    MiceliumAIPredictionRequest,
    MiceliumAIPredictionResponse,
    PredictionConfidence,
    SpecializedAIPrediction,
)
from app.modules.micelium.IA.surfactant_router import SurfactantAIRouter
from app.modules.micelium.IA.zwitterionic_ai import ZwitterionicSurfactantAI


class MiceliumAIService:
    def __init__(self, registry: ModelRegistry | None = None) -> None:
        self.registry = registry or ModelRegistry()
        self.identity_ai = MolecularIdentityAI()
        self.router = SurfactantAIRouter()
        self.models = {
            "anionic_ai": AnionicSurfactantAI(self.registry),
            "cationic_ai": CationicSurfactantAI(self.registry),
            "nonionic_ai": NonionicSurfactantAI(self.registry),
            "zwitterionic_ai": ZwitterionicSurfactantAI(self.registry),
            "amphoteric_ai": AmphotericSurfactantAI(self.registry),
        }

    def analyze_identity(self, request: MiceliumAIPredictionRequest):
        return self.identity_ai.analyze(request)

    def predict(
        self,
        request: MiceliumAIPredictionRequest,
        *,
        save: bool = False,
    ) -> MiceliumAIPredictionResponse:
        identity = self.identity_ai.analyze(request)
        environment = request.environment
        if request.concentration is not None:
            converted = concentration_mmol_l(request.concentration, request.unit, environment.volume_ml,
                                             identity.descriptors.molar_mass or 1.0)
            supplied = environment.surfactant_concentration_mmol_l
            if supplied is not None and not math.isclose(converted, supplied, rel_tol=1e-7, abs_tol=1e-10):
                raise ValueError("Concentrações contraditórias na entrada e no ambiente.")
            environment = environment.model_copy(update={"surfactant_concentration_mmol_l": converted})
        if request.model_override is not None:
            raise ValueError("model_override não é suportado por esta versão; use o roteamento por identidade.")
        route = self.router.route(identity)
        model = self.models.get(route)

        if model is None:
            prediction = SpecializedAIPrediction(
                ai_route="unknown_ai",
                surfactant_class="unknown",
                model_version="unknown_heuristic_v0.2.0",
                micelle_expected=False,
                micelle_probability=0.0,
                stability_score=0.0,
                warnings=["Molécula não classificada como surfactante confiável."],
            )
        else:
            prediction = model.predict(
                identity=identity,
                environment=environment,
            )

        confidence = self._confidence(
            identity_confidence=identity.class_confidence,
            prediction=prediction,
        )

        return MiceliumAIPredictionResponse(
            molecule=identity,
            environment=environment,
            prediction=prediction,
            confidence=confidence,
            route={
                "main_ai": "molecular_identity_ai",
                "specialized_ai": prediction.ai_route,
                "model_version": prediction.model_version,
                "confidence_calibrated": False,
            },
            saved=False,
            database_ids={},
        )

    def _confidence(
        self,
        *,
        identity_confidence: float,
        prediction: SpecializedAIPrediction,
    ) -> PredictionConfidence:
        has_cmc = prediction.predicted_cmc_mmol_l is not None
        has_hlb = prediction.predicted_hlb is not None
        warning_penalty = min(0.35, len(prediction.warnings) * 0.08)

        cmc_conf = clamp(identity_confidence * (0.82 if has_cmc else 0.20) - warning_penalty)
        hlb_conf = clamp(identity_confidence * (0.72 if has_hlb else 0.18) - warning_penalty)
        behavior_conf = clamp(identity_confidence * 0.78 + prediction.stability_score * 0.18 - warning_penalty)
        overall = clamp(0.38 * cmc_conf + 0.24 * hlb_conf + 0.38 * behavior_conf)

        return PredictionConfidence(
            overall=overall,
            cmc=cmc_conf,
            hlb=hlb_conf,
            behavior=behavior_conf,
        )
