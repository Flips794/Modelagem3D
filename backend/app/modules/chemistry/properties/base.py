"""Contrato comum dos provedores de propriedades."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rdkit import Chem

ParamDict = dict[str, Any]


def value(v: Any, source: str, unit: str | None = None, confidence: str = "estimated",
          note: str | None = None) -> ParamDict:
    """Valor calculado ou estimado. `confidence` diz qual dos dois e com que grau."""
    return {"value": v, "unit": unit, "source": source, "available": v is not None,
            "confidence": confidence, "note": note}


def not_applicable(reason: str, source: str, unit: str | None = None) -> ParamDict:
    """A propriedade não tem sentido para esta estrutura (ex.: R/S de átomo aquiral)."""
    return {"value": None, "unit": unit, "source": source, "available": False,
            "confidence": "not_applicable", "note": f"não se aplica: {reason}"}


def unavailable(reason: str, source: str, unit: str | None = None) -> ParamDict:
    """A propriedade existe, mas não há método válido ou dado para calculá-la aqui."""
    return {"value": None, "unit": unit, "source": source, "available": False,
            "confidence": "unavailable", "note": f"indisponível: {reason}"}


@dataclass(frozen=True)
class PropertyContext:
    mol: Chem.Mol                          # entrada completa, sanitizada
    structure: Any                         # validated_calculations.StructuralProfile
    env: dict[str, Any]
    active_atom_indices: tuple[int, ...]   # índices em `mol` do fragmento ativo


@dataclass
class PropertyBundle:
    molecule: dict[str, ParamDict] = field(default_factory=dict)
    atoms: dict[int, dict[str, ParamDict]] = field(default_factory=dict)
    bonds: dict[int, dict[str, ParamDict]] = field(default_factory=dict)

    def update(self, other: "PropertyBundle") -> None:
        self.molecule.update(other.molecule)
        for index, fields in other.atoms.items():
            self.atoms.setdefault(index, {}).update(fields)
        for index, fields in other.bonds.items():
            self.bonds.setdefault(index, {}).update(fields)
