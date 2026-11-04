from __future__ import annotations

from app.modules.micelium.IA.schemas import MiceliumAIEnvironment, MolecularIdentityResult
from app.modules.micelium.IA.specialized_base import SpecializedSurfactantAI


class AmphotericSurfactantAI(SpecializedSurfactantAI):
    """IA especializada em surfactantes anfotéricos — preparada, sem treinamento (Web Lite v1).

    Sem modelo .joblib em trained_models/amphoteric_ai/, usa só os cálculos compartilhados
    (validated_calculations); não há fórmula própria de CMC/HLB para anfotéricos.
    """

    route = "amphoteric_ai"
    surfactant_class = "amphoteric"
    model_version = "amphoteric_baseline_v0.1.0"

    def heuristic_cmc(
        self,
        identity: MolecularIdentityResult,
        environment: MiceliumAIEnvironment,
    ) -> float | None:
        return None

    def heuristic_effective_hlb(
        self,
        identity: MolecularIdentityResult,
        environment: MiceliumAIEnvironment,
    ) -> float | None:
        return None
