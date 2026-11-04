from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class LibraryStatus:
    name: str
    installed: bool
    purpose: str
    error: str | None = None

def _try_import(name: str):
    try:
        return __import__(name), None
    except Exception as exc:
        return None, str(exc)

from rdkit import Chem
from rdkit.Chem import AllChem, Crippen, Descriptors, QED, rdMolDescriptors
try:
    from rdkit.Chem import rdDepictor
except Exception:
    rdDepictor = None

xtb, xtb_error = _try_import('xtb')
freesasa, freesasa_error = _try_import('freesasa')
openmm, openmm_error = _try_import('openmm')
pubchempy, pubchempy_error = _try_import('pubchempy')

LIBRARIES = {
    'rdkit': LibraryStatus('RDKit', True, 'grafo químico, descritores 2D/3D, cargas Gasteiger e coordenadas'),
    'xtb': LibraryStatus('xTB', xtb is not None, 'HOMO/LUMO real, Fukui real, cargas quânticas e termoquímica', xtb_error),
    'freesasa': LibraryStatus('FreeSASA', freesasa is not None, 'SASA global/local e área real de cabeça micelar', freesasa_error),
    'openmm': LibraryStatus('OpenMM', openmm is not None, 'forças reais e dinâmica molecular', openmm_error),
    'pubchempy': LibraryStatus('PubChemPy', pubchempy is not None, 'nome comum, CID e dados externos', pubchempy_error),
}

def library_snapshot() -> dict[str, dict[str, Any]]:
    return {k: v.__dict__ for k, v in LIBRARIES.items()}

