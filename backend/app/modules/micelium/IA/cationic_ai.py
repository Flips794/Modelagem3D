from __future__ import annotations

from app.modules.micelium.IA.headgroup_classifier import CATIONIC_HEAD_PARAMS
from app.modules.micelium.IA.schemas import MiceliumAIEnvironment, MolecularIdentityResult
from app.modules.micelium.IA.specialized_base import SpecializedSurfactantAI


class CationicSurfactantAI(SpecializedSurfactantAI):
    route = "cationic_ai"
    surfactant_class = "cationic"
    model_version = "cationic_heuristic_v0.3.0"

    def _head_params(self, identity: MolecularIdentityResult) -> dict[str, float]:
        head_group = identity.descriptors.head_group or "QUATERNARY_AMMONIUM_SURFACTANT"

        return CATIONIC_HEAD_PARAMS.get(
            head_group,
            CATIONIC_HEAD_PARAMS["QUATERNARY_AMMONIUM_SURFACTANT"],
        )

    def heuristic_cmc(
        self,
        identity: MolecularIdentityResult,
        environment: MiceliumAIEnvironment,
    ) -> float | None:
        tail = identity.descriptors.tail_carbon_count or 12
        params = self._head_params(identity)

        # Klevens: log10(CMC mol/L) = A - B*n
        log_cmc_mol_l = params["klevens_a"] - params["klevens_b"] * tail
        cmc_mmol_l = (10.0 ** log_cmc_mol_l) * 1000.0

        ionic_factor = 1.0 / (1.0 + 4.4 * environment.ionic_strength_mol_l)
        temperature_factor = 1.0 + 0.010 * abs(environment.temperature_k - 298.15)

        counterion_factor = 1.0
        counterion = identity.descriptors.counterion

        if counterion == "Cl-":
            counterion_factor = 1.08
        elif counterion == "Br-":
            counterion_factor = 1.0
        elif counterion == "I-":
            counterion_factor = 0.88

        return max(1e-5, cmc_mmol_l * ionic_factor * temperature_factor * counterion_factor)

    def heuristic_effective_hlb(
        self,
        identity: MolecularIdentityResult,
        environment: MiceliumAIEnvironment,
    ) -> float | None:
        tail = identity.descriptors.tail_carbon_count or 12
        head_group = identity.descriptors.head_group or ""
        params = self._head_params(identity)

        base = 24.0 + params["head_area_a2"] / 4.2

        if "PRIMARY_ALKYLAMMONIUM" in head_group:
            base -= 7.5
        elif "SECONDARY_ALKYLAMMONIUM" in head_group:
            base -= 5.0
        elif "TERTIARY_ALKYLAMMONIUM" in head_group:
            base -= 2.5
        elif "HYDROXYETHYL" in head_group:
            base += 4.0

        tail_penalty = max(0, tail - 8) * 0.72

        return max(1.0, min(45.0, base - tail_penalty))

    def zeta_mv(
        self,
        identity: MolecularIdentityResult,
        environment: MiceliumAIEnvironment,
    ) -> float | None:
        screening = 1.0 / (1.0 + 8.0 * environment.ionic_strength_mol_l)
        head_group = identity.descriptors.head_group or ""

        base = 42.0

        if "PRIMARY_ALKYLAMMONIUM" in head_group:
            base = 34.0
        elif "SECONDARY_ALKYLAMMONIUM" in head_group:
            base = 38.0
        elif "TERTIARY_ALKYLAMMONIUM" in head_group:
            base = 42.0
        elif "QUATERNARY" in head_group:
            base = 48.0

        return base * screening


