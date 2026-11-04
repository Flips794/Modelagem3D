from __future__ import annotations

from app.modules.micelium.IA.schemas import MiceliumAIEnvironment, MolecularIdentityResult
from app.modules.micelium.IA.specialized_base import SpecializedSurfactantAI


class NonionicSurfactantAI(SpecializedSurfactantAI):
    route = "nonionic_ai"
    surfactant_class = "nonionic"
    model_version = "nonionic_heuristic_v0.2.0"

    def heuristic_cmc(
        self,
        identity: MolecularIdentityResult,
        environment: MiceliumAIEnvironment,
    ) -> float | None:
        tail = identity.descriptors.tail_carbon_count or 12
        hba = identity.descriptors.hba or 2
        tpsa = identity.descriptors.tpsa or 45.0
        hydrophilic_term = max(0.35, min(2.2, (hba + tpsa / 45.0) / 4.0))
        tail_term = 2.0 ** (12 - tail)
        temperature_factor = 1.0 + 0.018 * max(0.0, environment.temperature_k - 298.15)

        return max(1e-6, 0.08 * tail_term * hydrophilic_term * temperature_factor)

    def heuristic_effective_hlb(
        self,
        identity: MolecularIdentityResult,
        environment: MiceliumAIEnvironment,
    ) -> float | None:
        tpsa = identity.descriptors.tpsa or 45.0
        molar_mass = identity.descriptors.active_component_molar_mass or identity.descriptors.molar_mass or 400.0
        tail = identity.descriptors.tail_carbon_count or 12
        hydrophilic_proxy = min(molar_mass * 0.75, tpsa * 4.8 + (identity.descriptors.hba or 0) * 18.0)
        lipophilic_proxy = max(1.0, molar_mass - hydrophilic_proxy + tail * 5.0)
        hlb = 20.0 * hydrophilic_proxy / max(1.0, hydrophilic_proxy + lipophilic_proxy)
        return max(0.0, min(20.0, hlb))

    def zeta_mv(
        self,
        identity: MolecularIdentityResult,
        environment: MiceliumAIEnvironment,
    ) -> float | None:
        return 0.0


