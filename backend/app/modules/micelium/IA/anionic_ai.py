from __future__ import annotations

from app.modules.micelium.IA.schemas import MiceliumAIEnvironment, MolecularIdentityResult
from app.modules.micelium.IA.specialized_base import SpecializedSurfactantAI


class AnionicSurfactantAI(SpecializedSurfactantAI):
    route = "anionic_ai"
    surfactant_class = "anionic"
    model_version = "anionic_heuristic_v0.2.0"

    def heuristic_cmc(
        self,
        identity: MolecularIdentityResult,
        environment: MiceliumAIEnvironment,
    ) -> float | None:
        tail = identity.descriptors.tail_carbon_count or 12
        base = 8.2 * (2.0 ** (12 - tail))
        ionic_factor = 1.0 / (1.0 + 5.8 * environment.ionic_strength_mol_l)
        temperature_factor = 1.0 + 0.012 * abs(environment.temperature_k - 298.15)
        dielectric_factor = max(0.45, min(1.8, 78.5 / environment.dielectric_constant))

        return max(1e-5, base * ionic_factor * temperature_factor * dielectric_factor)

    def heuristic_effective_hlb(
        self,
        identity: MolecularIdentityResult,
        environment: MiceliumAIEnvironment,
    ) -> float | None:
        tail = identity.descriptors.tail_carbon_count or 12
        charge_bonus = 14.0
        head_bonus = 6.0 if identity.descriptors.head_group else 0.0
        tail_penalty = max(0.0, tail - 8) * 0.55

        return max(1.0, min(50.0, 18.0 + charge_bonus + head_bonus - tail_penalty))

    def zeta_mv(
        self,
        identity: MolecularIdentityResult,
        environment: MiceliumAIEnvironment,
    ) -> float | None:
        screening = 1.0 / (1.0 + 8.0 * environment.ionic_strength_mol_l)
        return -52.0 * screening


