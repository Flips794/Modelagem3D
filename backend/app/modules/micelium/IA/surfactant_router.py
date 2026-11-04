from __future__ import annotations

from app.modules.micelium.IA.schemas import AIRoute, MolecularIdentityResult


class SurfactantAIRouter:
    def route(self, identity: MolecularIdentityResult) -> AIRoute:
        if not identity.is_surfactant:
            return "unknown_ai"

        if identity.surfactant_class == "anionic":
            return "anionic_ai"

        if identity.surfactant_class == "cationic":
            return "cationic_ai"

        if identity.surfactant_class == "nonionic":
            return "nonionic_ai"

        if identity.surfactant_class == "zwitterionic":
            return "zwitterionic_ai"

        if identity.surfactant_class == "amphoteric":
            return "amphoteric_ai"

        return "unknown_ai"


