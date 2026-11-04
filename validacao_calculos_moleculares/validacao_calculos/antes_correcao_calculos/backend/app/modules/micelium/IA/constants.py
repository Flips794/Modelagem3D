from __future__ import annotations

from typing import Final


AI_MODULE_VERSION: Final[str] = "0.2.0"

SUPPORTED_SURFACTANT_CLASSES: Final[set[str]] = {
    "anionic",
    "cationic",
    "nonionic",
    "zwitterionic",
    "amphoteric",
    "unknown",
}

COUNTERION_PATTERNS: Final[dict[str, list[str]]] = {
    "Na+": ["[Na+]", "Na+"],
    "K+": ["[K+]", "K+"],
    "Li+": ["[Li+]", "Li+"],
    "NH4+": ["[NH4+]", "NH4+"],
    "Br-": ["[Br-]", "Br-"],
    "Cl-": ["[Cl-]", "Cl-"],
    "I-": ["[I-]", "I-"],
    "Ca2+": ["[Ca+2]", "[Ca++]", "Ca2+"],
    "Mg2+": ["[Mg+2]", "[Mg++]", "Mg2+"],
}

COUNTERION_COMPONENT_PATTERNS: Final[dict[str, list[str]]] = {
    "Na+": ["[Na+]"],
    "K+": ["[K+]"],
    "Li+": ["[Li+]"],
    "NH4+": ["[NH4+]"],
    "Br-": ["[Br-]"],
    "Cl-": ["[Cl-]"],
    "I-": ["[I-]"],
    "Ca2+": ["[Ca+2]", "[Ca++]"],
    "Mg2+": ["[Mg+2]", "[Mg++]"],
}

ANIONIC_HEAD_PATTERNS: Final[dict[str, list[str]]] = {
    "sulfate": ["S(=O)(=O)[O-]", "OS(=O)(=O)[O-]", "S(=O)(=O)O"],
    "sulfonate": ["S(=O)(=O)[O-]", "S(=O)(=O)O", "S(=O)(=O)"],
    "carboxylate": ["C(=O)[O-]", "C(=O)O"],
    "phosphate": ["P(=O)", "OP(=O)", "P([O-])"],
}

CATIONIC_HEAD_PATTERNS: Final[dict[str, list[str]]] = {
    "quaternary_ammonium": ["[N+]", "N+(", "N(C)(C)C"],
    "pyridinium": ["[n+]", "c1cccc[n+]1"],
    "imidazolium": ["[nH+]", "n1cc[n+]"],
}

NONIONIC_HEAD_PATTERNS: Final[dict[str, list[str]]] = {
    "polyoxyethylene": ["OCCO", "COCCO", "OCCOCCO", "CCOCCO"],
    "sorbitan_ester": ["C1C(C(C(C(O1)O)O)O)O", "sorbitan"],
    "ester": ["C(=O)O"],
    "alcohol": ["CO", "CCO"],
    "amide": ["C(=O)N"],
}

ZWITTERIONIC_HEAD_PATTERNS: Final[dict[str, list[str]]] = {
    "betaine": ["[N+]", "C(=O)[O-]"],
    "sulfobetaine": ["[N+]", "S(=O)(=O)[O-]"],
    "phosphatidylcholine": ["P(=O)", "[N+]"],
    "amino_acid_like": ["N", "C(=O)O"],
}

KNOWN_CMC_MMOL_L: Final[dict[str, float]] = {
    "sds": 8.2,
    "sodium dodecyl sulfate": 8.2,
    "sodium lauryl sulfate": 8.2,
    "ctab": 0.92,
    "cetyltrimethylammonium bromide": 0.92,
    "cetrimonium bromide": 0.92,
    "ctac": 1.3,
    "cetrimonium chloride": 1.3,
    "dtab": 15.0,
    "dodecyltrimethylammonium bromide": 15.0,
    "tween 80": 0.012,
    "polysorbate 80": 0.012,
}
