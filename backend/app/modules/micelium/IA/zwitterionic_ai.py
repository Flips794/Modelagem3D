from __future__ import annotations

from app.modules.micelium.IA.schemas import MiceliumAIEnvironment, MolecularIdentityResult
from app.modules.micelium.IA.specialized_base import SpecializedSurfactantAI


class ZwitterionicSurfactantAI(SpecializedSurfactantAI):
    route = "zwitterionic_ai"
    surfactant_class = "zwitterionic"
    model_version = "zwitterionic_heuristic_v0.2.0"

    def heuristic_cmc(
        self,
        identity: MolecularIdentityResult,
        environment: MiceliumAIEnvironment,
    ) -> float | None:
        tail = identity.descriptors.tail_carbon_count or 12
        base = 2.5 * (2.0 ** (12 - tail))
        ph_penalty = 1.0 + 0.06 * abs(environment.ph - 7.0)
        ionic_factor = 1.0 / (1.0 + 2.2 * environment.ionic_strength_mol_l)

        return max(1e-5, base * ph_penalty * ionic_factor)

    def heuristic_effective_hlb(
        self,
        identity: MolecularIdentityResult,
        environment: MiceliumAIEnvironment,
    ) -> float | None:
        tail = identity.descriptors.tail_carbon_count or 12
        ph_balance = max(0.0, 1.0 - abs(environment.ph - 7.0) / 7.0)
        return max(1.0, min(42.0, 26.0 + 7.0 * ph_balance - max(0, tail - 10) * 0.45))

    def zeta_mv(
        self,
        identity: MolecularIdentityResult,
        environment: MiceliumAIEnvironment,
    ) -> float | None:
        ph_offset = environment.ph - 7.0
        return max(-35.0, min(35.0, ph_offset * -5.0))


