from __future__ import annotations


try:
    from rdkit import Chem
except Exception:  # pragma: no cover
    Chem = None


COUNTERION_ATOMIC_NUMBERS = {
    3,   # Li
    11,  # Na
    12,  # Mg
    17,  # Cl
    19,  # K
    20,  # Ca
    35,  # Br
    53,  # I
}


def split_smiles_components(smiles: str) -> list[str]:
    return [component.strip() for component in (smiles or "").split(".") if component.strip()]


def is_counterion_component(smiles_component: str) -> bool:
    if not smiles_component:
        return False

    if Chem is None:
        return smiles_component in {
            "[Na+]",
            "[K+]",
            "[Li+]",
            "[Cl-]",
            "[Br-]",
            "[I-]",
            "[Ca+2]",
            "[Mg+2]",
        }

    mol = Chem.MolFromSmiles(smiles_component)

    if mol is None:
        return False

    atoms = list(mol.GetAtoms())

    if not atoms:
        return False

    return all(atom.GetAtomicNum() in COUNTERION_ATOMIC_NUMBERS for atom in atoms)


def active_component_for_electronic_descriptors(smiles: str) -> str:
    """
    Remove contraíons antes de descritores eletrônicos.

    Evita dipolos artificiais gigantes quando o sal inteiro é calculado no vácuo.
    """
    components = split_smiles_components(smiles)

    if not components:
        return smiles

    active = [
        component
        for component in components
        if not is_counterion_component(component)
    ]

    if not active:
        return max(components, key=len)

    return max(active, key=len)


def neutralize_primary_ammonium_for_electronic_descriptors(smiles: str) -> str:
    """
    Neutralização textual conservadora para descritores eletrônicos aproximados.

    O objetivo não é alterar a identidade química principal do banco, apenas evitar
    que dipolo/HOMO/LUMO sejam calculados sobre cargas isoladas do sal.
    """
    active = active_component_for_electronic_descriptors(smiles)

    replacements = {
        "[NH3+]": "N",
        "[N+H3]": "N",
        "[NH2+]": "N",
        "[N+H2]": "N",
        "[NH+]": "N",
        "[N+H]": "N",
        "[O-]": "O",
    }

    for charged, neutral in replacements.items():
        active = active.replace(charged, neutral)

    return active


