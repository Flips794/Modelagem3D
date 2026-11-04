from __future__ import annotations

from app.modules.chemistry.parameters.router import make_response as analyze_single_molecule_parameters
from app.modules.chemistry.parameters.schemas import ChemistryParametersRequest


def analyze_parameters(payload: ChemistryParametersRequest) -> dict:
    """Compatibilidade: usa a mesma implementação da rota HTTP ativa."""
    return analyze_single_molecule_parameters(payload)
