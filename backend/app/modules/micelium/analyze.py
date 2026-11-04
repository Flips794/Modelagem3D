from __future__ import annotations

from app.modules.micelium.schemas import MiceliumSimulationRequest, MiceliumSimulationResponse
from app.modules.micelium.service import run_micelium_simulation


def analyze_micelium(payload: MiceliumSimulationRequest) -> MiceliumSimulationResponse:
    """
    Entrada programática mantida para compatibilidade com imports existentes.
    """
    return run_micelium_simulation(payload)


