"""Casos compartilhados pela bateria de estabilidade (tarefa 1) e por tarefas seguintes."""
from __future__ import annotations

import json
from pathlib import Path

CATALOG_PATH = Path(__file__).parent / "fixtures" / "molecular_catalog.json"
CATALOG: list[dict] = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
CATALOG_CASES: list[tuple[str, str]] = [(item["id"], item["smiles"]) for item in CATALOG]

SDS = "CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]"
CTAB = "CCCCCCCCCCCCCCCC[N+](C)(C)C.[Br-]"
C12E5 = "CCCCCCCCCCCCOCCOCCOCCOCCOCCO"
BETAINE = "CCCCCCCCCCCC[N+](C)(C)CC(=O)[O-]"
AMPHOTERIC_GLYCINE = "CCCCCCCCCCCCNCC(=O)O"
AMINE_OXIDE = "CCCCCCCCCCCC[N+](C)(C)[O-]"

EDGE_CASES: list[tuple[str, str]] = [
    ("radical", "[CH3]"),
    ("metal", "[Fe+2].[Cl-].[Cl-]"),
    ("isotopo", "[13CH4]"),
    ("estereo", "C[C@H](N)C(=O)O"),
    ("cadeia160", "C" * 160),
    ("peptideo", "CC(C)C[C@H](NC(=O)[C@@H](N)Cc1ccccc1)C(=O)O"),
    ("etoxilado", "CCCCCCCCC=CCCCCCCCC(=O)OCCOCCOCCOCCOCCO"),
    ("multi_sal", "CCCCCCCCCCCC[N+](C)(C)C.[Br-].[Na+].[Cl-]"),
    ("macrociclo", "C1CCCCCCCCCCCCCCCCCCCCCCCCCCCCC1"),
    ("contraion_organico", "CCCCCCCCCCCCOS(=O)(=O)[O-].CC[NH+](CC)CC"),
    ("betaina_amida", "CCCCCCCCCCCC(=O)NCC[N+](C)(C)CC(=O)[O-]"),
    ("monooleato_glicerila", "CCCCCCCC=CCCCCCCCC(=O)OCC(O)CO"),
    ("oxido_amina", AMINE_OXIDE),
    ("n_alquilglicina", AMPHOTERIC_GLYCINE),
    ("gas_nobre", "[Ar]"),
    ("ion_isolado", "[Na+]"),
    ("carga_alta", "[O-]S(=O)(=O)[O-].[Ca+2]"),
    ("boro", "B(O)(O)c1ccccc1"),
    ("selenio", "C[Se]C"),
]

# (nome, moléculas como [(smiles, mmol em 100 mL)], solvente)
MIXTURE_CASES: list[tuple[str, list[tuple[str, float]], str]] = [
    ("sds_acima_cmc", [(SDS, 3.0)], "water"),
    ("sds_abaixo_cmc", [(SDS, 0.1)], "water"),
    ("sds_c12e5", [(SDS, 3.0), (C12E5, 3.0)], "water"),
    ("sds_hexano", [(SDS, 3.0), ("CCCCCC", 1.0)], "water"),
    ("so_hexano", [("CCCCCC", 3.0)], "water"),
    ("sds_em_hexano", [(SDS, 3.0)], "hexane"),
    ("betaina", [(BETAINE, 3.0)], "water"),
    ("ctab", [(CTAB, 3.0)], "water"),
]


def molecule_graph_from_parse(parse_response: dict) -> dict:
    """Reproduz rdkitMoleculeToEditableGraph do frontend (rdkitApi.ts)."""
    internal = parse_response["internal_molecule"]
    atoms = [
        {
            "index": atom["rdkit_index"],
            "symbol": atom["element"],
            "formal_charge": atom["formal_charge"],
            "is_aromatic": atom["is_aromatic"],
            "x": atom["position_2d"]["x"],
            "y": atom["position_2d"]["y"],
        }
        for atom in internal["atoms"]
    ]
    bonds = []
    for bond in internal["bonds"]:
        style = bond.get("visual_style")
        order = 1 if style == "single-resonance" else 2 if style == "double-resonance" else bond["order"]
        bonds.append({
            "begin_atom_index": bond["atom_a_rdkit_index"],
            "end_atom_index": bond["atom_b_rdkit_index"],
            "order": order,
            "is_aromatic": style == "aromatic" or bond["is_aromatic"],
            "visual_style": style,
            "bond_role": bond.get("bond_role"),
        })
    return {"atoms": atoms, "bonds": bonds}


def _atom(i: int, symbol: str, charge: int = 0, aromatic: bool = False) -> dict:
    return {"index": i, "symbol": symbol, "formal_charge": charge, "is_aromatic": aromatic, "x": float(i), "y": 0.0}


def _bond(a: int, b: int, order: float = 1, aromatic: bool = False) -> dict:
    return {"begin_atom_index": a, "end_atom_index": b, "order": order, "is_aromatic": aromatic}


# Grafos que um usuário consegue montar no editor e que o RDKit não aceita ou trata mal.
EDITOR_BAD_GRAPHS: list[tuple[str, dict]] = [
    ("vazio", {"atoms": [], "bonds": []}),
    ("carbono_pentavalente", {"atoms": [_atom(0, "C")] + [_atom(i, "C") for i in range(1, 6)],
                              "bonds": [_bond(0, i) for i in range(1, 6)]}),
    ("aromatico_fora_de_anel", {"atoms": [_atom(0, "C", aromatic=True), _atom(1, "C", aromatic=True)],
                                "bonds": [_bond(0, 1, 1.5, aromatic=True)]}),
    ("indice_inexistente", {"atoms": [_atom(0, "C"), _atom(1, "O")], "bonds": [_bond(0, 7)]}),
    ("elemento_desconhecido", {"atoms": [_atom(0, "Xx")], "bonds": []}),
    ("ligacao_consigo", {"atoms": [_atom(0, "C"), _atom(1, "C")], "bonds": [_bond(0, 0), _bond(0, 1)]}),
    ("ordem_invalida", {"atoms": [_atom(0, "C"), _atom(1, "C")], "bonds": [_bond(0, 1, 7)]}),
    ("ligacao_duplicada", {"atoms": [_atom(0, "C"), _atom(1, "C")], "bonds": [_bond(0, 1), _bond(1, 0)]}),
    ("carga_absurda", {"atoms": [_atom(0, "O", charge=-9)], "bonds": []}),
]
