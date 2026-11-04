from __future__ import annotations

from rdkit import Chem
from rdkit.Chem import AllChem, rdDepictor

from app.modules.chemistry.rdkit_engine.hydrogens_2d.schemas import (
    Hydrogens2DRequest,
)
from app.modules.chemistry.rdkit_engine.optimize_2d.schemas import (
    Optimize2DRequest,
)
from app.modules.chemistry.rdkit_engine.optimize_2d.service import (
    _build_response,
    _mol_from_payload,
)


def _compute_2d_coords_safely(molecule: Chem.Mol) -> None:
    """
    Recalcula coordenadas 2D de forma segura.

    O usuário pediu o padrão RDKit com AllChem.Compute2DCoords.
    Em algumas versões do RDKit, rdDepictor.Compute2DCoords é mais estável
    para argumentos como canonOrient/clearConfs. Por isso usamos AllChem
    primeiro e caímos para rdDepictor se necessário.
    """
    try:
        AllChem.Compute2DCoords(
            molecule,
            canonOrient=True,
            clearConfs=True,
        )
        return
    except Exception:
        rdDepictor.Compute2DCoords(
            molecule,
            canonOrient=True,
            clearConfs=True,
        )


def toggle_hydrogens_2d(payload: Hydrogens2DRequest) -> dict:
    """
    Alterna hidrogênios explícitos usando RDKit como fonte da verdade.

    explicit_hs=True:
      Chem.AddHs(mol, addCoords=True)

    explicit_hs=False:
      Chem.RemoveHs(mol, sanitize=True)

    Depois recalcula coordenadas 2D para evitar sobreposição visual.
    """
    base_payload = Optimize2DRequest(
        internal_molecule=payload.internal_molecule,
        graph=payload.graph,
        smiles=payload.smiles,
        width=payload.width,
        height=payload.height,
    )

    molecule = _mol_from_payload(base_payload)
    Chem.SanitizeMol(molecule)

    if payload.explicit_hs:
        molecule = Chem.AddHs(molecule, addCoords=True)
    else:
        molecule = Chem.RemoveHs(molecule, sanitize=True)

    Chem.SanitizeMol(molecule)
    _compute_2d_coords_safely(molecule)

    response = _build_response(base_payload, molecule)

    response["input_type"] = (
        "INTERNAL_2D_EXPLICIT_HS"
        if payload.explicit_hs
        else "INTERNAL_2D_IMPLICIT_HS"
    )

    response["internal_molecule"]["metadata"]["source_format"] = response[
        "input_type"
    ]

    return response


