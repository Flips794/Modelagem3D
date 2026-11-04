from __future__ import annotations

from app.modules.chemistry.parameters.libraries import Chem
from app.modules.chemistry.parameters.miriam21_engine import miriam21_surfactant_v2


def ethoxylate_tail_smiles(tail_carbons: int, eo_units: int) -> str:
    return "C" * tail_carbons + "O" + "CCO" * eo_units


CASES = [
    {
        "name": "TEA lauryl sulfate",
        "smiles": "CCCCCCCCCCCCOS(=O)(=O)[O-].OCC[NH+](CCO)CCO",
        "architecture": "CLASSIC_SINGLE_TAIL_ANIONIC",
        "electrostatic": "ANIONIC",
        "counterion_type": "ORGANIC_AMMONIUM_COUNTERION",
    },
    {
        "name": "Brij 35 / C12E23",
        "smiles": ethoxylate_tail_smiles(12, 23),
        "architecture": "BRIJ35_C12E23",
        "electrostatic": "NONIONIC",
        "cmc_route": "BRIJ35_C12E23_LITERATURE_PROFILE",
    },
    {
        "name": "PFOS potassium",
        "smiles": "O=S(=O)([O-])C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)F.[K+]",
        "architecture": "PFOS_LIKE_FLUOROSURFACTANT",
        "electrostatic": "ANIONIC",
        "cmc_route": "PFOS_EXPERIMENTAL_PROFILE",
    },
    {
        "name": "Lauryl sulfobetaine / SB3-12",
        "smiles": "CCCCCCCCCCCC[N+](C)(C)CCCS(=O)(=O)[O-]",
        "architecture": "SULFOBETAINE_SINGLE_TAIL",
        "electrostatic": "ZWITTERIONIC",
        "cmc_route": "SB3_12_LITERATURE_PROFILE",
    },
    {
        "name": "Gemini 16-2-16",
        "smiles": "CCCCCCCCCCCCCCCC[N+](C)(C)CC[N+](C)(C)CCCCCCCCCCCCCCCC.[Br-].[Br-]",
        "architecture": "GEMINI",
        "electrostatic": "CATIONIC",
        "cmc_route": "GEMINI_EXPERIMENTAL_OR_QSPR_REQUIRED",
    },
    {
        "name": "C8 amine oxide",
        "smiles": "CCCCCCCC[N+](C)(C)[O-]",
        "architecture": "AMINE_OXIDE_SINGLE_TAIL",
        "electrostatic": "ZWITTERIONIC",
        "cmc_route": "AMINE_OXIDE_QSPR_OR_EXPERIMENTAL",
    },
    {
        "name": "Octan-1-ol",
        "smiles": "CCCCCCCCO",
        "architecture": "CO_SURFACTANT_FATTY_ALCOHOL",
        "electrostatic": "NONIONIC",
    },
    {
        "name": "Disodium decanedioate",
        "smiles": "O=C([O-])CCCCCCCCC(=O)[O-].[Na+].[Na+]",
        "architecture": "BOLAAMPHIPHILE_DICARBOXYLATE_SALT",
        "electrostatic": "ANIONIC",
    },
]


def value(result: dict, key: str):
    return result[key]["value"]


def first_plan_route(result: dict, parameter: str) -> str | None:
    for item in value(result, "miriam2_calculation_plan"):
        if item.get("parameter") == parameter:
            return item.get("route")
    return None


def main() -> None:
    for case in CASES:
        mol = Chem.MolFromSmiles(case["smiles"])
        if mol is None:
            raise AssertionError(f"SMILES inválido no teste: {case['name']}")

        result = miriam21_surfactant_v2(
            mol=mol,
            mw=1.0,
            logp=1.0,
            tpsa=50.0,
            env={"temperature_k": 298.15, "ionic_strength_mol_l": 0.01, "agitation_rpm": 0},
        )

        identity = value(result, "miriam2_identity")
        assert identity["architecture"] == case["architecture"], (case["name"], identity)
        assert identity["electrostaticClass"] == case["electrostatic"], (case["name"], identity)

        if "cmc_route" in case:
            assert first_plan_route(result, "CMC") == case["cmc_route"], (case["name"], first_plan_route(result, "CMC"), identity)

        if "counterion_type" in case:
            cts = identity.get("counterions", [])
            assert cts and cts[0].get("type") == case["counterion_type"], (case["name"], cts)
            assert identity.get("unknownFragments", []) == [], (case["name"], identity.get("unknownFragments"))

        validation = value(result, "miriam2_physical_validation")
        if identity["architecture"] == "PFOS_LIKE_FLUOROSURFACTANT":
            assert "CLASSIC_IONIC_KLEVENS" in validation["blockedCalculations"], validation
        if identity["architecture"] == "BRIJ35_C12E23":
            assert "CLASSIC_NONIONIC_KLEVENS" in validation["blockedCalculations"], validation
        if identity["architecture"] == "GEMINI":
            assert "PLACEHOLDER_CMC" in validation["blockedCalculations"], validation

        print(f"OK - {case['name']}: {identity['electrostaticClass']} / {identity['architecture']}")

    print("MIRIAM-2.1 domain hardening acceptance checks passed.")


if __name__ == "__main__":
    main()


