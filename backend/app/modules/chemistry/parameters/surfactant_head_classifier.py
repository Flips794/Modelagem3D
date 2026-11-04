from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


AmmoniumSubType = Literal[
    "primary_ammonium",
    "secondary_ammonium",
    "tertiary_ammonium",
    "quaternary_ammonium",
    "hydroxyethyl_quaternary_ammonium",
    "not_ammonium",
]


@dataclass(frozen=True, slots=True)
class HeadGroupClassification:
    head_group: str | None
    surfactant_class: str
    confidence: float
    ammonium_subtype: AmmoniumSubType
    head_area_a2: float | None
    klevens_a: float | None
    klevens_b: float | None
    notes: list[str]


try:
    from rdkit import Chem
except Exception:  # pragma: no cover
    Chem = None


AMMONIUM_SMARTS: dict[AmmoniumSubType, str] = {
    "primary_ammonium": "[NX4H3+]",
    "secondary_ammonium": "[NX4H2+]",
    "tertiary_ammonium": "[NX4H1+]",
    "quaternary_ammonium": "[NX4H0+]",
}

# Valores iniciais calibráveis. A meta aqui é corrigir a seleção da família,
# não afirmar calibração final de literatura para todos os sais.
CATIONIC_HEAD_PARAMS: dict[str, dict[str, float]] = {
    "PRIMARY_ALKYLAMMONIUM_SURFACTANT": {
        "head_area_a2": 36.0,
        "klevens_a": 1.62,
        "klevens_b": 0.29,
    },
    "SECONDARY_ALKYLAMMONIUM_SURFACTANT": {
        "head_area_a2": 42.0,
        "klevens_a": 1.56,
        "klevens_b": 0.29,
    },
    "TERTIARY_ALKYLAMMONIUM_SURFACTANT": {
        "head_area_a2": 50.0,
        "klevens_a": 1.50,
        "klevens_b": 0.29,
    },
    "QUATERNARY_AMMONIUM_SURFACTANT": {
        "head_area_a2": 64.0,
        "klevens_a": 1.60,
        "klevens_b": 0.29,
    },
    "HYDROXYETHYL_QUATERNARY_AMMONIUM_SURFACTANT": {
        "head_area_a2": 72.0,
        "klevens_a": 1.72,
        "klevens_b": 0.285,
    },
}


def _mol_from_smiles(smiles: str):
    if Chem is None:
        return None

    try:
        return Chem.MolFromSmiles(smiles)
    except Exception:
        return None


def _has_smarts(mol, smarts: str) -> bool:
    if Chem is None or mol is None:
        return False

    pattern = Chem.MolFromSmarts(smarts)

    if pattern is None:
        return False

    return bool(mol.HasSubstructMatch(pattern))


def _has_oxygen(mol, smiles: str) -> bool:
    if mol is not None:
        return any(atom.GetAtomicNum() == 8 for atom in mol.GetAtoms())

    return "O" in smiles or "o" in smiles


def _detect_ammonium_subtype_rdkit(mol) -> AmmoniumSubType:
    if mol is None:
        return "not_ammonium"

    # Ordem explícita: nunca deixe [N+] genérico capturar [NH3+].
    for subtype in [
        "primary_ammonium",
        "secondary_ammonium",
        "tertiary_ammonium",
        "quaternary_ammonium",
    ]:
        if _has_smarts(mol, AMMONIUM_SMARTS[subtype]):
            return subtype

    return "not_ammonium"


def _detect_ammonium_subtype_fallback(smiles: str) -> AmmoniumSubType:
    if "[NH3+]" in smiles or "[N+H3]" in smiles:
        return "primary_ammonium"

    if "[NH2+]" in smiles or "[N+H2]" in smiles:
        return "secondary_ammonium"

    if "[NH+]" in smiles or "[N+H]" in smiles:
        return "tertiary_ammonium"

    if "[N+]" in smiles or "N+" in smiles:
        return "quaternary_ammonium"

    return "not_ammonium"


def _has_hydroxyethyl_quaternary_pattern(mol, smiles: str) -> bool:
    if not _has_oxygen(mol, smiles):
        return False

    if mol is not None:
        # N+ ligado a cadeia C-C-O. Evita flag hydroxyethyl em molécula sem oxigênio.
        return any(
            _has_smarts(mol, smarts)
            for smarts in [
                "[NX4H0+]CCO",
                "[NX4H0+]CC[OH]",
                "OCC[NX4H0+]",
                "[OH]CC[NX4H0+]",
            ]
        )

    return any(token in smiles for token in ["N+CCO", "[N+]CCO", "OCC[N+]", "OCCN+"])


def classify_cationic_headgroup(smiles: str) -> HeadGroupClassification:
    mol = _mol_from_smiles(smiles)
    notes: list[str] = []
    subtype = _detect_ammonium_subtype_rdkit(mol)

    if subtype == "not_ammonium":
        subtype = _detect_ammonium_subtype_fallback(smiles)

    if subtype == "not_ammonium":
        return HeadGroupClassification(
            head_group=None,
            surfactant_class="unknown",
            confidence=0.0,
            ammonium_subtype="not_ammonium",
            head_area_a2=None,
            klevens_a=None,
            klevens_b=None,
            notes=[],
        )

    if subtype == "primary_ammonium":
        key = "PRIMARY_ALKYLAMMONIUM_SURFACTANT"
        confidence = 0.93
        notes.append("Detectado [NX4H3+]: amônio primário, não quaternário.")

    elif subtype == "secondary_ammonium":
        key = "SECONDARY_ALKYLAMMONIUM_SURFACTANT"
        confidence = 0.90
        notes.append("Detectado [NX4H2+]: amônio secundário.")

    elif subtype == "tertiary_ammonium":
        key = "TERTIARY_ALKYLAMMONIUM_SURFACTANT"
        confidence = 0.88
        notes.append("Detectado [NX4H1+]: amônio terciário protonado.")

    else:
        if _has_hydroxyethyl_quaternary_pattern(mol, smiles):
            key = "HYDROXYETHYL_QUATERNARY_AMMONIUM_SURFACTANT"
            subtype = "hydroxyethyl_quaternary_ammonium"
            confidence = 0.91
            notes.append("Detectado quaternário com motivo hidroxi-etil confirmado por oxigênio.")
        else:
            key = "QUATERNARY_AMMONIUM_SURFACTANT"
            confidence = 0.89

            if not _has_oxygen(mol, smiles):
                notes.append(
                    "Molécula sem oxigênio: bloqueada classificação hydroxyethyl_quaternary."
                )

    params = CATIONIC_HEAD_PARAMS[key]

    return HeadGroupClassification(
        head_group=key,
        surfactant_class="cationic",
        confidence=confidence,
        ammonium_subtype=subtype,
        head_area_a2=params["head_area_a2"],
        klevens_a=params["klevens_a"],
        klevens_b=params["klevens_b"],
        notes=notes,
    )


