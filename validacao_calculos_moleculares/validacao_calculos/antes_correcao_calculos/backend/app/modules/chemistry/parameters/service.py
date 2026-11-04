from __future__ import annotations

from app.modules.chemistry.parameters.calculation_page import (
    analyze_single_molecule_parameters,
)
from app.modules.chemistry.parameters.schemas import ChemistryParametersRequest


def analyze_parameters(payload: ChemistryParametersRequest) -> dict:
    """
    Compatibilidade com as rotas atuais.

    O schemas.py NÃO deve importar calculation_page.py.
    A ordem correta é:
    schemas.py -> define modelos Pydantic
    calculation_page.py -> importa schemas.py e executa cálculos
    service.py -> importa calculation_page.py e expõe analyze_parameters()
    """
    return analyze_single_molecule_parameters(payload)
