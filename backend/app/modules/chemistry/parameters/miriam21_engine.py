from __future__ import annotations

import math
from typing import Any

from app.modules.chemistry.parameters.libraries import (
    Chem,
    Crippen,
    Descriptors,
    rdMolDescriptors,
)


# =============================================================================
# MIRIAM-2.1 — corrected micellar identification/routing engine
# -----------------------------------------------------------------------------
# Goal:
# - classify by ACTIVE fragment, never by global salt charge;
# - separate counterions, active fragments and unknown fragments;
# - distinguish alkyl sulfate from alkyl sulfonate;
# - block hydrocarbon Klevens/Tanford for PFAS/fluorosurfactants;
# - use specific family profiles for Brij35/C12E23 and SB3-12;
# - do not export fixed Gemini placeholders as physical results;
# - return stable fields expected by calculation_page.py/frontend.
# =============================================================================


# -----------------------------------------------------------------------------
# Small value wrappers: same response style as calculation_page.py
# -----------------------------------------------------------------------------

def pv(
    value: Any,
    source: str,
    unit: str | None = None,
    confidence: str = "high",
    note: str | None = None,
    available: bool | None = None,
) -> dict:
    return {
        "value": value,
        "unit": unit,
        "source": source,
        "available": (value is not None if available is None else available),
        "confidence": confidence,
        "note": note,
    }


def est(
    value: Any,
    source: str,
    unit: str | None = None,
    note: str | None = None,
    available: bool | None = None,
) -> dict:
    return pv(value, source, unit, "estimated", note, available=available)


def blocked_value(reason: str, route: str) -> dict:
    return pv(
        {"status": "BLOCKED", "route": route, "reason": reason},
        "MIRIAM-2.1 physical/domain blocker",
        confidence="blocked",
        note=reason,
        available=True,
    )


def none_blocked(reason: str, route: str) -> dict:
    return pv(
        None,
        "MIRIAM-2.1 physical/domain blocker",
        confidence="blocked",
        note=f"{route}: {reason}",
        available=False,
    )


# -----------------------------------------------------------------------------
# Generic chemistry helpers
# -----------------------------------------------------------------------------

def smarts(mol, pattern: str) -> bool:
    try:
        query = Chem.MolFromSmarts(pattern)
        return bool(query is not None and mol.HasSubstructMatch(query))
    except Exception:
        return False


def count_smarts(mol, pattern: str) -> int:
    try:
        query = Chem.MolFromSmarts(pattern)
        if query is None:
            return 0
        return len(mol.GetSubstructMatches(query))
    except Exception:
        return 0


def formal_charge(mol) -> int:
    return int(sum(atom.GetFormalCharge() for atom in mol.GetAtoms()))


def mol_smiles(mol) -> str:
    try:
        return Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)
    except Exception:
        return ""


def _atom_symbols(frag) -> list[str]:
    return [atom.GetSymbol() for atom in frag.GetAtoms()]


COUNTERION_ATOMIC_NUMBERS = {
    3,   # Li
    9,   # F
    11,  # Na
    12,  # Mg
    17,  # Cl
    19,  # K
    20,  # Ca
    35,  # Br
    37,  # Rb
    53,  # I
    55,  # Cs
    56,  # Ba
}


METAL_CATIONS = {3, 11, 12, 19, 20, 37, 55, 56}
HALIDE_ANIONS = {9, 17, 35, 53}


# -----------------------------------------------------------------------------
# Hydrophobic tail detection
# -----------------------------------------------------------------------------

def carbon_components(mol, include_aromatic: bool = False) -> list[list[int]]:
    carbon_nodes = [
        atom.GetIdx()
        for atom in mol.GetAtoms()
        if atom.GetAtomicNum() == 6 and (include_aromatic or not atom.GetIsAromatic())
    ]

    carbon_set = set(carbon_nodes)
    adjacency = {idx: [] for idx in carbon_nodes}

    for bond in mol.GetBonds():
        a = bond.GetBeginAtom()
        b = bond.GetEndAtom()
        ia = a.GetIdx()
        ib = b.GetIdx()

        if ia in carbon_set and ib in carbon_set:
            adjacency[ia].append(ib)
            adjacency[ib].append(ia)

    seen: set[int] = set()
    components: list[list[int]] = []

    for node in carbon_nodes:
        if node in seen:
            continue

        stack = [node]
        seen.add(node)
        component: list[int] = []

        while stack:
            current = stack.pop()
            component.append(current)
            for nxt in adjacency[current]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)

        components.append(sorted(component))

    components.sort(key=len, reverse=True)
    return components


def tail_components(mol) -> list[dict]:
    tails: list[dict] = []

    for component in carbon_components(mol, include_aromatic=False):
        if len(component) < 4:
            continue

        component_set = set(component)
        branch_points = 0
        unsaturation_count = 0
        fluorine_neighbors = 0

        for idx in component:
            atom = mol.GetAtomWithIdx(idx)
            carbon_neighbors = [
                n.GetIdx()
                for n in atom.GetNeighbors()
                if n.GetAtomicNum() == 6 and not n.GetIsAromatic()
            ]
            if len(carbon_neighbors) > 2:
                branch_points += len(carbon_neighbors) - 2
            fluorine_neighbors += sum(1 for n in atom.GetNeighbors() if n.GetAtomicNum() == 9)

        for bond in mol.GetBonds():
            a = bond.GetBeginAtomIdx()
            b = bond.GetEndAtomIdx()
            if a in component_set and b in component_set:
                if bond.GetBondType() == Chem.BondType.DOUBLE:
                    unsaturation_count += 1

        carbon_count = len(component)
        effective_carbon_count = carbon_count * (0.92 ** branch_points) * (0.88 ** unsaturation_count)
        if fluorine_neighbors:
            # PFAS are routed separately. This factor only marks stronger hydrophobicity
            # for diagnostics; it must not allow hydrocarbon Klevens/Tanford as validated.
            effective_carbon_count *= 1.10

        tails.append(
            {
                "atomIndices": component,
                "carbonCount": carbon_count,
                "branchPoints": branch_points,
                "unsaturationCount": unsaturation_count,
                "fluorineNeighbors": fluorine_neighbors,
                "isBranched": branch_points > 0,
                "effectiveCarbonCount": round(effective_carbon_count, 5),
                "effectiveLengthA": round(1.5 + 1.265 * effective_carbon_count, 5),
            }
        )

    tails.sort(key=lambda item: item["carbonCount"], reverse=True)
    return tails


def longest_tail_count(mol) -> int:
    tails = tail_components(mol)
    return int(tails[0]["carbonCount"]) if tails else 0


# -----------------------------------------------------------------------------
# Fragment routing / desalting
# -----------------------------------------------------------------------------

def is_small_counterion(frag) -> bool:
    if frag.GetNumHeavyAtoms() == 0:
        return False

    if frag.GetNumHeavyAtoms() == 1:
        atom = next(frag.GetAtoms())
        return atom.GetAtomicNum() in COUNTERION_ATOMIC_NUMBERS or abs(atom.GetFormalCharge()) > 0

    if frag.GetNumHeavyAtoms() <= 2 and all(atom.GetAtomicNum() != 6 for atom in frag.GetAtoms()):
        return abs(formal_charge(frag)) > 0

    return False


def classify_counterion_fragment(frag) -> dict:
    """
    Classify detached counterions without making the active surfactant zwitterionic.
    Organic ammonium counterions such as triethanolammonium are counterions, not unknowns.
    """
    charge = formal_charge(frag)
    heavy_atoms = frag.GetNumHeavyAtoms()
    symbols = _atom_symbols(frag)
    carbon_count = sum(1 for atom in frag.GetAtoms() if atom.GetAtomicNum() == 6)
    nitrogen_count = sum(1 for atom in frag.GetAtoms() if atom.GetAtomicNum() == 7)
    oxygen_count = sum(1 for atom in frag.GetAtoms() if atom.GetAtomicNum() == 8)
    tail_count = longest_tail_count(frag)
    smiles = mol_smiles(frag)

    if heavy_atoms == 1:
        atom = next(frag.GetAtoms())
        atomic_number = atom.GetAtomicNum()

        if atomic_number in METAL_CATIONS and charge > 0:
            return {
                "isCounterion": True,
                "type": "INORGANIC_CATION_COUNTERION",
                "label": atom.GetSymbol(),
                "charge": charge,
                "smiles": smiles,
            }

        if atomic_number in HALIDE_ANIONS and charge < 0:
            return {
                "isCounterion": True,
                "type": "HALIDE_COUNTERION",
                "label": atom.GetSymbol(),
                "charge": charge,
                "smiles": smiles,
            }

    # Triethanolammonium / organic ammonium without long hydrophobic tail.
    if charge > 0 and nitrogen_count >= 1 and tail_count < 6:
        if oxygen_count >= 3 and 5 <= carbon_count <= 8:
            label = "triethanolammonium"
            ctype = "ORGANIC_AMMONIUM_COUNTERION"
        elif smarts(frag, "[NX4+]") or smarts(frag, "[NX3H+]") or smarts(frag, "[NH+]"):
            label = "organic_ammonium"
            ctype = "ORGANIC_AMMONIUM_COUNTERION"
        else:
            label = "organic_cation"
            ctype = "ORGANIC_CATION_COUNTERION"

        return {
            "isCounterion": True,
            "type": ctype,
            "label": label,
            "charge": charge,
            "smiles": smiles,
        }

    if charge < 0 and heavy_atoms <= 3 and carbon_count == 0:
        return {
            "isCounterion": True,
            "type": "INORGANIC_ANION_COUNTERION",
            "label": "inorganic_anion",
            "charge": charge,
            "smiles": smiles,
        }

    return {
        "isCounterion": False,
        "type": "UNKNOWN_FRAGMENT",
        "label": "unknown",
        "charge": charge,
        "smiles": smiles,
        "symbols": symbols,
    }


def fragment_score(frag) -> float:
    carbons = sum(1 for atom in frag.GetAtoms() if atom.GetAtomicNum() == 6)
    hetero = sum(1 for atom in frag.GetAtoms() if atom.GetAtomicNum() not in {1, 6})
    tail = longest_tail_count(frag)
    charge_abs = abs(formal_charge(frag))

    polar_score = 0.0
    polar_score += 6 * count_smarts(frag, "[OX2][SX4](=[OX1])(=[OX1])[OX1-]")
    polar_score += 6 * count_smarts(frag, "[SX4](=[OX1])(=[OX1])([OX1-])[#6]")
    polar_score += 5 * count_smarts(frag, "[CX3](=[OX1])[OX1-]")
    polar_score += 5 * count_smarts(frag, "[NX4+]")
    polar_score += 3 * count_smarts(frag, "[OX2H]")
    polar_score += min(count_smarts(frag, "[OX2]"), 12) * 0.6

    counterion_penalty = 80 if is_small_counterion(frag) else 0

    return (
        carbons * 2.5
        + hetero * 0.5
        + tail * 7.0
        + polar_score * 4.0
        + charge_abs * 2.0
        - counterion_penalty
    )


def split_fragments(mol) -> tuple[list[Any], list[Any], dict]:
    try:
        fragments = list(Chem.GetMolFrags(mol, asMols=True, sanitizeFrags=True))
    except Exception:
        fragments = [mol]

    counterions: list[Any] = []
    candidate_actives: list[Any] = []
    unknown_fragments: list[dict] = []
    counterion_meta_by_smiles: dict[str, dict] = {}

    for frag in fragments:
        classification = classify_counterion_fragment(frag)
        s = mol_smiles(frag)

        if classification.get("isCounterion"):
            counterions.append(frag)
            counterion_meta_by_smiles[s] = classification
        elif is_small_counterion(frag):
            fallback = {
                "isCounterion": True,
                "type": "SMALL_INORGANIC_COUNTERION",
                "label": s,
                "charge": formal_charge(frag),
                "smiles": s,
            }
            counterions.append(frag)
            counterion_meta_by_smiles[s] = fallback
        else:
            candidate_actives.append(frag)

    if not candidate_actives:
        candidate_actives = sorted(fragments, key=fragment_score, reverse=True)[:1]
        selected = mol_smiles(candidate_actives[0]) if candidate_actives else ""
        counterions = []
        for frag in fragments:
            if mol_smiles(frag) != selected:
                counterions.append(frag)
                counterion_meta_by_smiles[mol_smiles(frag)] = classify_counterion_fragment(frag)

    candidate_actives.sort(key=fragment_score, reverse=True)

    active_smiles = {mol_smiles(frag) for frag in candidate_actives}
    counterion_smiles = {mol_smiles(frag) for frag in counterions}
    for frag in fragments:
        s = mol_smiles(frag)
        if s not in active_smiles and s not in counterion_smiles:
            unknown_fragments.append(classify_counterion_fragment(frag))

    active_infos = [
        {
            "smiles": mol_smiles(frag),
            "formalCharge": formal_charge(frag),
            "score": round(fragment_score(frag), 5),
            "tailCarbonCount": longest_tail_count(frag),
        }
        for frag in candidate_actives
    ]

    counterion_infos = []
    for frag in counterions:
        s = mol_smiles(frag)
        meta = dict(counterion_meta_by_smiles.get(s, classify_counterion_fragment(frag)))
        meta.update(
            {
                "smiles": s,
                "formalCharge": formal_charge(frag),
                "atomicNumbers": [atom.GetAtomicNum() for atom in frag.GetAtoms()],
            }
        )
        counterion_infos.append(meta)

    return candidate_actives, counterions, {
        "desaltingApplied": len(fragments) > 1,
        "fragmentCount": len(fragments),
        "activeFragments": active_infos,
        "counterions": counterion_infos,
        "unknownFragments": unknown_fragments,
        "allFragments": [mol_smiles(frag) for frag in fragments],
    }


# -----------------------------------------------------------------------------
# Functional-group counters and identity classification
# -----------------------------------------------------------------------------

def counts(mol) -> dict:
    carbon_count = sum(1 for atom in mol.GetAtoms() if atom.GetAtomicNum() == 6)
    oxygen_count = sum(1 for atom in mol.GetAtoms() if atom.GetAtomicNum() == 8)
    nitrogen_count = sum(1 for atom in mol.GetAtoms() if atom.GetAtomicNum() == 7)
    fluorine_count = sum(1 for atom in mol.GetAtoms() if atom.GetAtomicNum() == 9)

    alkyl_sulfate = count_smarts(mol, "[OX2][SX4](=[OX1])(=[OX1])[OX1-]")
    alkyl_sulfonate = count_smarts(mol, "[SX4](=[OX1])(=[OX1])([OX1-])[#6]")
    neutral_sulfonic_or_sulfate = count_smarts(mol, "[SX4](=[OX1])(=[OX1])([OX2H1])[#6,OX2]")

    amine_oxide_count = max(
        count_smarts(mol, "[NX4+][O-]"),
        count_smarts(mol, "[NX4+]-[O-]"),
    )
    raw_quaternary_count = count_smarts(mol, "[NX4+]")
    quaternary_ammonium_count = max(0, raw_quaternary_count - amine_oxide_count)

    return {
        "carbonCount": carbon_count,
        "oxygenCount": oxygen_count,
        "nitrogenCount": nitrogen_count,
        "fluorineCount": fluorine_count,
        "fluorinationDegree": round(fluorine_count / max(carbon_count, 1), 5),
        "terminalSulfateCount": alkyl_sulfate,
        "alkylSulfateCount": alkyl_sulfate,
        "sulfonateCount": alkyl_sulfonate,
        "alkylSulfonateCount": alkyl_sulfonate,
        "sulfateCount": alkyl_sulfate + alkyl_sulfonate,
        "neutralSulfonicOrSulfateCount": neutral_sulfonic_or_sulfate,
        "carboxylateCount": count_smarts(mol, "[CX3](=[OX1])[OX1-]"),
        "carboxylicAcidCount": count_smarts(mol, "[CX3](=[OX1])[OX2H1]"),
        "esterCount": count_smarts(mol, "[CX3](=[OX1])[OX2][#6]"),
        "amineOxideCount": amine_oxide_count,
        "rawQuaternaryNitrogenCount": raw_quaternary_count,
        "quaternaryAmmoniumCount": quaternary_ammonium_count,
        "tertiaryAmineCount": count_smarts(mol, "[NX3;H0;!$(N-C=O)]"),
        "eoUnits": count_smarts(mol, "[OX2][CX4][CX4][OX2]"),
        "hydroxylCount": count_smarts(mol, "[OX2H]"),
        "aromaticRingCount": count_smarts(mol, "a1aaaaa1"),
        "fluorocarbonCount": (
            count_smarts(mol, "[#6]([F])([F])")
            + count_smarts(mol, "[#6]([F])([F])([F])")
        ),
    }


def aggregate_counts(active_fragments: list[Any]) -> dict:
    total: dict[str, int | float] = {}
    for frag in active_fragments:
        c = counts(frag)
        for key, value in c.items():
            total[key] = total.get(key, 0) + value

    if active_fragments:
        total["fluorinationDegree"] = round(
            float(total.get("fluorineCount", 0)) / max(float(total.get("carbonCount", 0)), 1.0),
            5,
        )
    return total


def head_group_type(c: dict) -> str:
    if c.get("amineOxideCount", 0) > 0:
        return "AMINE_OXIDE_N_PLUS_O_MINUS"
    if c.get("quaternaryAmmoniumCount", 0) > 0 and c.get("sulfonateCount", 0) > 0:
        return "QUATERNARY_AMMONIUM_SULFONATE_PAIR"
    if c.get("quaternaryAmmoniumCount", 0) > 0 and c.get("carboxylateCount", 0) > 0:
        return "QUATERNARY_AMMONIUM_CARBOXYLATE_PAIR"
    if c.get("alkylSulfateCount", 0) > 0:
        return "ALKYL_SULFATE"
    if c.get("sulfonateCount", 0) > 0:
        return "ALKYL_SULFONATE"
    if c.get("quaternaryAmmoniumCount", 0) > 0:
        return "QUATERNARY_AMMONIUM"
    if c.get("carboxylateCount", 0) > 0 or c.get("carboxylicAcidCount", 0) > 0:
        return "CARBOXYLATE_OR_CARBOXYLIC_ACID"
    if c.get("eoUnits", 0) > 0:
        return "POLYETHER_ETHOXYLATED"
    if c.get("hydroxylCount", 0) > 0:
        return "HYDROXYL_ALCOHOL"
    if c.get("oxygenCount", 0) > 0:
        return "ETHER_OR_OXYGENATED"
    return "UNDEFINED_POLAR_HEAD"


def electrostatic_class(active_fragments: list[Any], counterions: list[Any]) -> tuple[str, str, int, int]:
    active_charges = [formal_charge(frag) for frag in active_fragments]
    total_active_charge = sum(active_charges)
    total_global_charge = total_active_charge + sum(formal_charge(frag) for frag in counterions)

    if total_active_charge < 0:
        return "anionico", "ANIONIC", total_active_charge, total_global_charge
    if total_active_charge > 0:
        return "cationico", "CATIONIC", total_active_charge, total_global_charge

    if len(active_fragments) == 1:
        frag = active_fragments[0]
        has_pos = any(atom.GetFormalCharge() > 0 for atom in frag.GetAtoms())
        has_neg = any(atom.GetFormalCharge() < 0 for atom in frag.GetAtoms())
        if has_pos and has_neg:
            return "zwitterionico", "ZWITTERIONIC", 0, total_global_charge

    return "nao_ionico", "NONIONIC", 0, total_global_charge


def total_active_charge(active_fragments: list[Any]) -> int:
    return sum(formal_charge(frag) for frag in active_fragments)


def classify_architecture(active_fragments: list[Any], counterions: list[Any]) -> tuple[str, str, str, dict]:
    rep = active_fragments[0]
    rep_c = counts(rep)
    tails_all = []
    for frag in active_fragments:
        tails_all.extend(tail_components(frag))
    tails_all.sort(key=lambda item: item["carbonCount"], reverse=True)

    charge_type, electro_label, active_charge, _ = electrostatic_class(active_fragments, counterions)
    counterion_charges = [formal_charge(frag) for frag in counterions]
    counterion_meta = [classify_counterion_fragment(frag) for frag in counterions]
    counterion_labels = {str(meta.get("label", "")).lower() for meta in counterion_meta}
    counterion_smiles_set = {mol_smiles(frag) for frag in counterions}
    has_sodium_counterion = "na" in counterion_labels or "[Na+]" in counterion_smiles_set
    has_bromide_counterion = "br" in counterion_labels or "[Br-]" in counterion_smiles_set
    longest_tail = tails_all[0]["carbonCount"] if tails_all else 0
    tail_count = len([tail for tail in tails_all if tail["carbonCount"] >= 4])

    amine_oxide_single_tail = (
        len(active_fragments) == 1
        and rep_c.get("amineOxideCount", 0) >= 1
        and formal_charge(rep) == 0
        and any(atom.GetFormalCharge() > 0 for atom in rep.GetAtoms())
        and any(atom.GetFormalCharge() < 0 for atom in rep.GetAtoms())
        and longest_tail >= 4
    )

    same_fragment_sulfobetaine = (
        len(active_fragments) == 1
        and rep_c["quaternaryAmmoniumCount"] >= 1
        and rep_c.get("sulfonateCount", 0) >= 1
        and formal_charge(rep) == 0
        and any(atom.GetFormalCharge() > 0 for atom in rep.GetAtoms())
        and any(atom.GetFormalCharge() < 0 for atom in rep.GetAtoms())
    )

    same_fragment_carbobetaine = (
        len(active_fragments) == 1
        and rep_c["quaternaryAmmoniumCount"] >= 1
        and rep_c["carboxylateCount"] >= 1
        and formal_charge(rep) == 0
        and any(atom.GetFormalCharge() > 0 for atom in rep.GetAtoms())
        and any(atom.GetFormalCharge() < 0 for atom in rep.GetAtoms())
    )

    fatty_alcohol_cosurfactant = (
        len(active_fragments) == 1
        and charge_type == "nao_ionico"
        and 4 <= longest_tail <= 10
        and rep_c["hydroxylCount"] == 1
        and rep_c["oxygenCount"] == 1
        and rep_c["quaternaryAmmoniumCount"] == 0
        and rep_c["carboxylateCount"] == 0
        and rep_c["sulfateCount"] == 0
    )

    bola_dicarboxylate = (
        len(active_fragments) == 1
        and rep_c["carboxylateCount"] >= 2
        and formal_charge(rep) <= -2
        and longest_tail >= 6
    )

    multi_active_divalent = (
        len(active_fragments) > 1
        and all(formal_charge(frag) < 0 for frag in active_fragments)
        and any(charge > 1 for charge in counterion_charges)
    )

    cationic_with_counterion = (
        len(active_fragments) == 1
        and formal_charge(rep) > 0
        and rep_c["quaternaryAmmoniumCount"] >= 1
        and any(charge < 0 for charge in counterion_charges)
    )

    anionic_with_counterion = (
        total_active_charge(active_fragments) < 0
        and any(charge > 0 for charge in counterion_charges)
    )

    gemini = (
        rep_c["quaternaryAmmoniumCount"] >= 2
        and tail_count >= 2
        and charge_type == "cationico"
    )

    sles_like = (
        rep_c["alkylSulfateCount"] >= 1
        and rep_c["eoUnits"] >= 1
        and electro_label == "ANIONIC"
        and longest_tail >= 8
    )

    sds_sodium_like = (
        len(active_fragments) == 1
        and electro_label == "ANIONIC"
        and rep_c.get("alkylSulfateCount", 0) >= 1
        and rep_c.get("eoUnits", 0) == 0
        and longest_tail == 12
        and has_sodium_counterion
    )

    ctab_like = (
        len(active_fragments) == 1
        and electro_label == "CATIONIC"
        and rep_c.get("quaternaryAmmoniumCount", 0) == 1
        and tail_count == 1
        and longest_tail == 16
        and has_bromide_counterion
    )

    sodium_caprylate_like = (
        len(active_fragments) == 1
        and electro_label == "ANIONIC"
        and rep_c.get("carboxylateCount", 0) >= 1
        and longest_tail in {7, 8}
        and has_sodium_counterion
    )

    fluorosurfactant = rep_c["fluorocarbonCount"] > 0 or rep_c["fluorinationDegree"] >= 0.8

    pfos_like = (
        fluorosurfactant
        and electro_label == "ANIONIC"
        and rep_c.get("sulfonateCount", 0) >= 1
        and rep_c.get("fluorineCount", 0) >= 13
        and longest_tail >= 6
    )

    brij35_c12e23_like = (
        electro_label == "NONIONIC"
        and tail_count == 1
        and longest_tail == 12
        and 18 <= rep_c.get("eoUnits", 0) <= 26
        and rep_c.get("esterCount", 0) == 0
        and rep_c.get("aromaticRingCount", 0) == 0
    )

    gemini_16_2_16_like = (
        gemini
        and len(tails_all) >= 2
        and tails_all[0]["carbonCount"] >= 16
        and tails_all[1]["carbonCount"] >= 16
    )

    triton_like = (
        rep_c["aromaticRingCount"] >= 1
        and rep_c["eoUnits"] >= 3
        and electro_label == "NONIONIC"
    )

    tween_like = (
        rep_c["esterCount"] >= 1
        and rep_c["oxygenCount"] >= 8
        and rep_c["eoUnits"] >= 2
        and electro_label == "NONIONIC"
        and longest_tail >= 10
    )

    if multi_active_divalent:
        return "MULTI_ACTIVE_FRAGMENT_IONIC_SALT", "CALCIUM_OR_DIVALENT_ALKYL_SULFATE_SALT", "DIVALENT_COUNTERION_ANIONIC_SURFACTANT", {}
    if sds_sodium_like:
        return "SDS_SODIUM_ALKYL_SULFATE", "SODIUM_DODECYL_SULFATE", "SDS_LITERATURE_PROFILE", {}
    if ctab_like:
        return "CTAB_C16_CATIONIC", "CTAB_C16_CATIONIC_SURFACTANT", "CTAB_LITERATURE_PROFILE", {}
    if sodium_caprylate_like:
        return "SODIUM_CAPRYLATE_FATTY_ACID_SALT", "SODIUM_CAPRYLATE_LIKE", "SODIUM_CAPRYLATE_HLB_PROFILE", {}
    if amine_oxide_single_tail:
        return "AMINE_OXIDE_SINGLE_TAIL", "ALKYL_DIMETHYL_AMINE_OXIDE_SURFACTANT", "AMINE_OXIDE_QSPR_OR_EXPERIMENTAL", {}
    if same_fragment_sulfobetaine:
        return "SULFOBETAINE_SINGLE_TAIL", "SULFOBETAINE_ZWITTERIONIC_SURFACTANT", ("SB3_12_LITERATURE_PROFILE" if longest_tail == 12 else "SULFOBETAINE_QSPR_OR_EXPERIMENTAL"), {}
    if same_fragment_carbobetaine:
        return "ZWITTERIONIC_BETAINE", "CARBOBETAINE_ZWITTERIONIC_SURFACTANT", "ZWITTERIONIC_SURFACTANT_QSPR", {}
    if fatty_alcohol_cosurfactant:
        return "CO_SURFACTANT_FATTY_ALCOHOL", "WEAK_NONIONIC_AMPHIPHILE", "BLOCKED_CO_SURFACTANT_ONLY", {}
    if bola_dicarboxylate:
        return "BOLAAMPHIPHILE_DICARBOXYLATE_SALT", "DISODIUM_DECANEDIOATE_LIKE", "BLOCKED_BOLAAMPHIPHILE_MODEL_REQUIRED", {}
    if gemini_16_2_16_like:
        return "GEMINI", "GEMINI_CATIONIC_16_2_16", "GEMINI_EXPERIMENTAL_OR_QSPR_REQUIRED", {}
    if gemini:
        return "GEMINI", "GEMINI_CATIONIC_SURFACTANT", "GEMINI_EXPERIMENTAL_OR_QSPR_REQUIRED", {}
    if cationic_with_counterion:
        return "CLASSIC_SINGLE_TAIL_CATIONIC", "HYDROXYETHYL_QUATERNARY_AMMONIUM_SURFACTANT", "CATIONIC_KLEVENS_WITH_HYDROXYETHYL_HEAD_CORRECTION", {}
    if pfos_like:
        return "PFOS_LIKE_FLUOROSURFACTANT", "PFOS_LIKE_FLUOROSURFACTANT", "PFOS_EXPERIMENTAL_PROFILE", {}
    if fluorosurfactant:
        return "FLUOROSURFACTANT", "ANIONIC_FLUOROSURFACTANT", "FLUOROSURFACTANT_QSPR_OR_EXPERIMENTAL_REQUIRED", {}
    if brij35_c12e23_like:
        return "BRIJ35_C12E23", "BRIJ35_C12E23_NONIONIC_SURFACTANT", "BRIJ35_C12E23_LITERATURE_PROFILE", {}
    if sles_like:
        return "SLES_LIKE", "ETHER_SULFATE_ANIONIC_SURFACTANT", "ETHER_SULFATE_KLEVENS", {}
    if triton_like:
        return "TRITON_LIKE", "NONIONIC_POLYMERIC_AROMATIC_SURFACTANT", "NONIONIC_POLYMER_QSPR", {}
    if tween_like:
        return "TWEEN_LIKE_SURFACTANT", "TWEEN80_NONIONIC_SURFACTANT", "TWEEN80_LITERATURE_PROFILE", {}
    if anionic_with_counterion:
        return "CLASSIC_SINGLE_TAIL_ANIONIC", "CLASSIC_ANIONIC_SURFACTANT", "CLASSIC_IONIC_KLEVENS", {}
    if charge_type == "cationico":
        return "CLASSIC_SINGLE_TAIL_CATIONIC", "CLASSIC_CATIONIC_SURFACTANT", "CLASSIC_IONIC_KLEVENS", {}
    if electro_label == "NONIONIC" and longest_tail >= 8 and rep_c["oxygenCount"] > 0:
        return "CLASSIC_SINGLE_TAIL_NONIONIC", "CLASSIC_NONIONIC_SURFACTANT", "CLASSIC_NONIONIC_QSPR", {}
    if longest_tail >= 4:
        return "WEAK_AMPHIPHILE", "WEAK_AMPHIPHILE", "BLOCKED_WEAK_AMPHIPHILE", {}

    return "NOT_AMPHIPHILIC", "NON_SURFACTANT", "BLOCKED_NON_SURFACTANT", {}


# -----------------------------------------------------------------------------
# Physical/empirical models
# -----------------------------------------------------------------------------

def tanford_volume(carbon_count: int) -> float | None:
    if carbon_count <= 0:
        return None
    return 27.4 + 26.9 * carbon_count


def tanford_length(carbon_count: int) -> float | None:
    if carbon_count <= 0:
        return None
    return 1.5 + 1.265 * carbon_count


def normalize_surfactant_score(raw: float, architecture: str, longest_tail: int) -> float:
    # 40 = weak threshold; 160 = strong classic surfactant. Clamp 0–1.
    score = (raw - 40.0) / 120.0
    score = max(0.0, min(1.0, score))

    if architecture == "AMINE_OXIDE_SINGLE_TAIL":
        score = max(score, min(0.75, 0.62 + 0.015 * longest_tail))
    if architecture in {"PFOS_LIKE_FLUOROSURFACTANT", "BRIJ35_C12E23", "GEMINI", "SULFOBETAINE_SINGLE_TAIL"}:
        score = max(score, 0.82)
    if architecture in {"CO_SURFACTANT_FATTY_ALCOHOL", "WEAK_AMPHIPHILE"}:
        score = min(score, 0.55)
    if architecture in {"NOT_AMPHIPHILIC", "NON_SURFACTANT"}:
        score = 0.0

    return round(score, 5)


def identity_confidence_for(architecture: str, final_class: str) -> float:
    if architecture in {
        "CLASSIC_SINGLE_TAIL_ANIONIC",
        "CLASSIC_SINGLE_TAIL_CATIONIC",
        "SDS_SODIUM_ALKYL_SULFATE",
        "CTAB_C16_CATIONIC",
        "SODIUM_CAPRYLATE_FATTY_ACID_SALT",
        "SLES_LIKE",
        "BRIJ35_C12E23",
        "PFOS_LIKE_FLUOROSURFACTANT",
        "SULFOBETAINE_SINGLE_TAIL",
        "GEMINI",
        "AMINE_OXIDE_SINGLE_TAIL",
    }:
        return 0.90
    if architecture in {"TRITON_LIKE", "TWEEN_LIKE_SURFACTANT"}:
        return 0.82
    if architecture in {"CO_SURFACTANT_FATTY_ALCOHOL", "BOLAAMPHIPHILE_DICARBOXYLATE_SALT"}:
        return 0.75
    if final_class == "NON_SURFACTANT":
        return 0.85
    return 0.65


def confidence_from_quality(quality: str | None) -> float:
    q = str(quality or "")
    if q == "VALIDATED_CLASSICAL_MODEL":
        return 0.82
    if q in {"LITERATURE_RANGE", "LITERATURE_ANCHORED"}:
        return 0.86
    if q == "EXPERIMENTAL_ANCHORED":
        return 0.90
    if q.startswith("HIGH"):
        return 0.90
    if q.startswith("MEDIUM"):
        return 0.68
    if "MODEL_REQUIRED" in q:
        return 0.28
    if "FAMILY_PROFILE_REQUIRED" in q:
        return 0.38
    if "EXPERIMENTAL_REQUIRED" in q or "OUT_OF_DOMAIN" in q:
        return 0.35
    if "BLOCKED" in q:
        return 0.10
    return 0.45


def parameter_confidence(parameter: str, architecture: str, route: str, quality_score: float, warnings: list[str]) -> float:
    if parameter == "CMC":
        if route == "CLASSIC_IONIC_KLEVENS" and architecture == "CLASSIC_SINGLE_TAIL_ANIONIC":
            return 0.82
        if route in {
            "SDS_LITERATURE_PROFILE",
            "CTAB_LITERATURE_PROFILE",
            "BRIJ35_C12E23_LITERATURE_PROFILE",
            "SB3_12_LITERATURE_PROFILE",
            "PFOS_EXPERIMENTAL_PROFILE",
        }:
            return 0.90 if route in {"SDS_LITERATURE_PROFILE", "CTAB_LITERATURE_PROFILE"} else 0.86
        if "GEMINI" in route or "EXPERIMENTAL" in route or "QSPR" in route:
            return min(quality_score, 0.45)
        return quality_score

    if parameter == "HLB":
        if architecture in {"CLASSIC_SINGLE_TAIL_ANIONIC", "CLASSIC_SINGLE_TAIL_CATIONIC", "SDS_SODIUM_ALKYL_SULFATE", "CTAB_C16_CATIONIC"}:
            return 0.75
        if architecture == "SODIUM_CAPRYLATE_FATTY_ACID_SALT":
            return 0.82
        if architecture in {"BRIJ35_C12E23", "TWEEN_LIKE_SURFACTANT"}:
            return 0.86
        return min(quality_score, 0.65)

    if parameter == "CPP":
        if architecture in {"PFOS_LIKE_FLUOROSURFACTANT", "FLUOROSURFACTANT", "GEMINI"}:
            return min(quality_score, 0.45)
        if architecture in {"CLASSIC_SINGLE_TAIL_ANIONIC", "CLASSIC_SINGLE_TAIL_CATIONIC", "SDS_SODIUM_ALKYL_SULFATE", "CTAB_C16_CATIONIC"}:
            return 0.75
        return min(quality_score, 0.60)

    if parameter == "NAGG_RADIUS":
        return 0.35 if warnings else min(0.60, quality_score)

    return quality_score


def estimate_head_area(architecture: str, head: str, c: dict, tpsa: float, ionic_strength: float) -> tuple[float, float, dict]:
    if architecture == "AMINE_OXIDE_SINGLE_TAIL":
        raw = max(48.0, tpsa * 1.0)
        eff = max(45.0, min(55.0, raw))
        method = "AMINE_OXIDE_N_PLUS_O_MINUS_HYDRATED_HEAD_AREA"
    elif architecture == "SULFOBETAINE_SINGLE_TAIL":
        raw = max(76.0, tpsa * 1.08)
        eff = max(70.0, min(92.0, raw))
        method = "SULFOBETAINE_QUATERNARY_AMMONIUM_SULFONATE_PAIR_AREA"
    elif architecture == "ZWITTERIONIC_BETAINE":
        raw = max(70.0, tpsa * 1.15)
        eff = max(64.0, min(82.0, raw))
        method = "CARBOBETAINE_QUATERNARY_AMMONIUM_CARBOXYLATE_PAIR_AREA"
    elif architecture == "CLASSIC_SINGLE_TAIL_CATIONIC":
        hydroxyethyl_bonus = 8.0 * min(c.get("hydroxylCount", 0), 2)
        raw = 64.0 + hydroxyethyl_bonus
        eff = raw * (1.0 - 0.18 * ionic_strength / (ionic_strength + 0.08))
        method = "QUATERNARY_AMMONIUM_WITH_HYDROXYETHYL_HEAD_AREA"
    elif architecture == "MULTI_ACTIVE_FRAGMENT_IONIC_SALT":
        raw = 60.0
        eff = raw * (1.0 - 0.25 * ionic_strength / (ionic_strength + 0.08))
        method = "SULFATE_HEAD_AREA_WITH_DIVALENT_COUNTERION_SCREENING"
    elif architecture == "BOLAAMPHIPHILE_DICARBOXYLATE_SALT":
        raw = max(100.0, tpsa * 1.1)
        eff = raw
        method = "TWO_TERMINAL_CARBOXYLATE_HEADS_BOLA_AREA"
    elif architecture == "CO_SURFACTANT_FATTY_ALCOHOL":
        raw = 34.0
        eff = 34.0
        method = "FATTY_ALCOHOL_SINGLE_HYDROXYL_AREA"
    elif architecture in {"TRITON_LIKE", "TWEEN_LIKE_SURFACTANT", "BRIJ35_C12E23"}:
        raw = max(80.0, tpsa * 1.1)
        eff = 35.0 + 6.0 * math.log1p(c.get("eoUnits", 0) + c.get("hydroxylCount", 0))
        eff = max(38.0, min(68.0, eff))
        method = "POLYETHER_LOGARITHMIC_CAPPED_HEAD_AREA"
    else:
        base = {
            "AMINE_OXIDE_N_PLUS_O_MINUS": 50.0,
            "QUATERNARY_AMMONIUM_SULFONATE_PAIR": 80.0,
            "QUATERNARY_AMMONIUM_CARBOXYLATE_PAIR": 72.0,
            "ALKYL_SULFATE": 60.0,
            "ALKYL_SULFONATE": 54.0,
            "CARBOXYLATE_OR_CARBOXYLIC_ACID": 54.0,
            "QUATERNARY_AMMONIUM": 64.0,
            "HYDROXYL_ALCOHOL": 34.0,
            "POLYETHER_ETHOXYLATED": 56.0,
        }.get(head, max(38.0, tpsa * 0.85))
        raw = max(base, tpsa * 0.85, 20.0)
        eff = raw
        method = "GENERIC_HEAD_AREA"

    return raw, max(eff, 1.0), {
        "method": method,
        "rawAreaA2": round(raw, 5),
        "effectiveAreaA2": round(eff, 5),
        "ionicStrengthMolL": ionic_strength,
    }


def route_numbers(architecture: str, route: str, longest_tail: int, c: dict, logp: float, tpsa: float) -> dict:

    if architecture == "SDS_SODIUM_ALKYL_SULFATE" or route == "SDS_LITERATURE_PROFILE":
        return {
            "profileId": "sds_na_literature_profile",
            "cmcMmolL": 8.2,
            "cmcRangeMmolL": [8.0, 8.4],
            "hlb": 40.0,
            "nagg": 62,
            "radiusA": None,
            "quality": "LITERATURE_ANCHORED",
            "notes": [
                "Sodium dodecyl sulfate profile applied.",
                "CMC anchored to literature reference at 25 C in water without added electrolyte.",
                "Klevens screening value is close, but literature profile is preferred for SDS."
            ],
            "modelMetadata": {
                "method": "literature_profile",
                "source": "Mukerjee_Mysels_1971",
                "temperatureC": 25,
                "condition": "water_no_added_electrolyte",
                "referenceCmcMmolL": 8.2
            },
        }

    if architecture == "CTAB_C16_CATIONIC" or route == "CTAB_LITERATURE_PROFILE":
        return {
            "profileId": "ctab_c16_literature_profile",
            "cmcMmolL": 0.92,
            "cmcRangeMmolL": [0.88, 1.00],
            "hlb": None,
            "nagg": None,
            "radiusA": None,
            "quality": "LITERATURE_ANCHORED",
            "notes": [
                "CTAB/C16 trimethylammonium bromide profile applied.",
                "Generic cationic Klevens replaced by literature profile.",
                "HLB is not exported as final value for cationic quaternary ammonium salts without a family calibration."
            ],
            "modelMetadata": {
                "method": "literature_profile",
                "source": "Mukerjee_Mysels_1971",
                "temperatureC": 25,
                "condition": "water",
                "referenceCmcMmolL": 0.92
            },
        }

    if architecture == "SODIUM_CAPRYLATE_FATTY_ACID_SALT" or route == "SODIUM_CAPRYLATE_HLB_PROFILE":
        return {
            "profileId": "sodium_caprylate_hlb_profile",
            "cmcMmolL": None,
            "hlb": 23.0,
            "hlbRange": [20.0, 25.0],
            "hlbDaviesAlternative": 24.8,
            "nagg": None,
            "radiusA": None,
            "quality": "LITERATURE_RANGE",
            "notes": [
                "Sodium caprylate/caprylic acid salt profile applied.",
                "Medium-chain fatty acid salts are better represented by an HLB range.",
                "Davies-style theoretical constants can give values near 24.8 depending on table choice."
            ],
            "modelMetadata": {
                "method": "family_literature_range",
                "family": "medium_chain_fatty_acid_salt",
                "preferredHlb": 23.0,
                "daviesAlternative": 24.8
            },
        }

    if architecture == "MULTI_ACTIVE_FRAGMENT_IONIC_SALT":
        return {
            "cmcMmolL": 2.0,
            "hlb": 40.0,
            "nagg": 60,
            "radiusA": 24.0,
            "quality": "LOW_CONFIDENCE_EXPERIMENTAL_REQUIRED",
            "notes": ["Dodecyl sulfate with divalent counterion: C12 Klevens is reference only, not final CMC."],
        }

    if architecture == "AMINE_OXIDE_SINGLE_TAIL":
        return {
            "cmcMmolL": None,
            "hlb": None,
            "nagg": None,
            "radiusA": None,
            "quality": "FAMILY_PROFILE_REQUIRED",
            "notes": [
                "Amine oxide detected: [N+]-[O-] is not ordinary quaternary ammonium.",
                "Classic Klevens blocked; CMC needs amine-oxide profile or QSPR.",
                "C8 is short/intermediate; it may behave as weak surfactant or co-surfactant.",
            ],
        }

    if architecture == "SULFOBETAINE_SINGLE_TAIL":
        if route == "SB3_12_LITERATURE_PROFILE" or longest_tail == 12:
            return {
                "profileId": "sb3_12_literature_profile",
                "cmcMmolL": 3.0,
                "cmcRangeMmolL": [2.0, 4.0],
                "hlb": None,
                "nagg": None,
                "radiusA": None,
                "quality": "LITERATURE_ANCHORED",
                "notes": [
                    "SB3-12 sulfobetaine detected: CMC from literature profile, not Klevens.",
                    "Final HLB remains family/QSPR dependent; Griffin/Davies blocked as final result.",
                ],
            }
        return {
            "profileId": "sulfobetaine_qspr_required",
            "cmcMmolL": None,
            "hlb": None,
            "nagg": None,
            "radiusA": None,
            "quality": "EXPERIMENTAL_REQUIRED",
            "notes": ["Sulfobetaine CMC/HLB require experimental profile or QSPR."],
        }

    if architecture == "ZWITTERIONIC_BETAINE":
        return {
            "cmcMmolL": 1.8,
            "hlb": 12.0,
            "nagg": 90,
            "radiusA": 32.0,
            "quality": "MEDIUM_LOW_QSPR",
            "notes": ["True betaine: zwitterionic route, not classic ionic Klevens."],
        }

    if architecture == "CO_SURFACTANT_FATTY_ALCOHOL":
        return {
            "cmcMmolL": None,
            "hlb": 7.0,
            "nagg": None,
            "radiusA": None,
            "quality": "BLOCKED_CO_SURFACTANT",
            "notes": ["C4-C10 fatty alcohol: co-surfactant/weak amphiphile; normal micelle blocked."],
        }

    if architecture == "CLASSIC_SINGLE_TAIL_CATIONIC":
        # Calibrated fallback for classical CnTAB-like cationic surfactants.
        # CTAB itself is caught by CTAB_LITERATURE_PROFILE above.
        base = 10 ** (1.60 - 0.29 * max(longest_tail, 1)) * 1000.0
        if c.get("hydroxylCount", 0) >= 2:
            base *= 0.75
        return {
            "cmcMmolL": max(0.001, min(250.0, base)),
            "hlb": None,
            "nagg": 65,
            "radiusA": 28.0,
            "quality": "MEDIUM_CONFIDENCE",
            "notes": [
                "Classical cationic fallback calibrated to the CTAB order of magnitude.",
                "Specific CTAB-like molecules should use CTAB_LITERATURE_PROFILE."
            ],
            "modelMetadata": {
                "method": "fallback_cationic_klevens",
                "A": 1.60,
                "B": 0.29,
                "equation": "log10(CMC mol/L) = A - B * nc"
            },
        }

    if architecture == "BOLAAMPHIPHILE_DICARBOXYLATE_SALT":
        return {
            "cmcMmolL": None,
            "hlb": 18.0,
            "nagg": None,
            "radiusA": None,
            "quality": "BLOCKED_BOLAAMPHIPHILE",
            "notes": ["Two terminal polar heads: single-tail Klevens/CPP/Nagg blocked."],
        }

    if architecture == "PFOS_LIKE_FLUOROSURFACTANT":
        return {
            "profileId": "pfos_potassium_literature_profile",
            "cmcMmolL": 8.0,
            "cmcRangeMmolL": [1.3, 8.0],
            "hlb": None,
            "nagg": None,
            "radiusA": None,
            "quality": "LITERATURE_RANGE",
            "blockedCalculations": ["CLASSIC_IONIC_KLEVENS", "TANFORD_LINEAR_HYDROCARBON"],
            "notes": [
                "PFOS/PFAS detected: hydrocarbon Klevens/Tanford blocked.",
                "CMC shown as literature/profile range, not validated classic model.",
            ],
        }

    if architecture == "FLUOROSURFACTANT":
        return {
            "profileId": "fluorosurfactant_qspr_required",
            "cmcMmolL": None,
            "hlb": None,
            "nagg": None,
            "radiusA": None,
            "quality": "EXPERIMENTAL_REQUIRED",
            "blockedCalculations": ["CLASSIC_IONIC_KLEVENS", "TANFORD_LINEAR_HYDROCARBON"],
            "notes": ["Fluorosurfactant outside hydrocarbon Tanford/Klevens domain."],
        }

    if architecture == "BRIJ35_C12E23":
        return {
            "profileId": "brij35_c12e23_literature_profile",
            "cmcMmolL": 0.09,
            "hlb": 16.9,
            "nagg": 40,
            "naggRange": [34, 64],
            "radiusA": None,
            "quality": "EXPERIMENTAL_ANCHORED",
            "blockedCalculations": ["CLASSIC_NONIONIC_KLEVENS"],
            "notes": [
                "Brij 35/C12E23 profile applied.",
                "CMC/HLB/Nagg come from profile; classic nonionic Klevens blocked.",
            ],
        }

    if architecture == "TRITON_LIKE":
        return {
            "cmcMmolL": 0.24,
            "hlb": 13.5,
            "nagg": 110,
            "radiusA": 43.0,
            "quality": "HIGH_CONFIDENCE_FAMILY_PROFILE",
            "notes": ["Triton-like: capped/logarithmic PEG head; nonionic polymer route."],
        }

    if architecture == "TWEEN_LIKE_SURFACTANT" or route == "TWEEN80_LITERATURE_PROFILE":
        return {
            "profileId": "tween80_literature_profile",
            "cmcMmolL": 0.012,
            "hlb": 15.0,
            "nagg": 60,
            "radiusA": 40.0,
            "quality": "LITERATURE_ANCHORED",
            "notes": [
                "Tween 80 / polysorbate-like profile applied.",
                "HLB fixed at 15.0 by literature/manufacturer convention.",
                "Generic Klevens is blocked for Tween-like nonionic polymeric surfactants."
            ],
            "blockedCalculations": ["CLASSIC_NONIONIC_KLEVENS"],
            "modelMetadata": {
                "method": "literature_profile",
                "source": "Griffin_1949_HLB_convention",
                "referenceHlb": 15.0
            },
        }

    if architecture == "SLES_LIKE":
        return {
            "cmcMmolL": 1.6,
            "hlb": 16.0,
            "nagg": 64,
            "radiusA": 32.0,
            "quality": "MEDIUM_CONFIDENCE",
            "notes": ["Anionic ether sulfate: sulfate controls electrostatic class; EO corrects family route."],
        }

    if architecture == "GEMINI":
        return {
            "profileId": "gemini_model_required",
            "cmcMmolL": None,
            "cmcRangeMmolL": [0.001, 0.1] if longest_tail >= 16 else None,
            "hlb": None,
            "nagg": None,
            "radiusA": None,
            "quality": "MODEL_REQUIRED",
            "blockedCalculations": ["CLASSIC_IONIC_KLEVENS", "CLASSIC_SINGLE_TAIL_TANFORD", "PLACEHOLDER_CMC"],
            "notes": [
                "Gemini detected: single-tail Klevens and fixed placeholders blocked.",
                "CMC must come from experimental profile or calibrated Gemini model.",
            ],
        }

    if route == "CLASSIC_IONIC_KLEVENS":
        cmc = 10 ** (1.50 - 0.30 * max(longest_tail, 1)) * 1000.0
        return {
            "cmcMmolL": cmc,
            "hlb": 16.0,
            "nagg": 60,
            "radiusA": None,
            "quality": "VALIDATED_CLASSICAL_MODEL",
            "notes": ["Classic ionic surfactant inside approximate Klevens domain."],
            "modelMetadata": {
                "method": "Klevens",
                "family": "alkyl_sulfate_or_classic_ionic",
                "A": 1.50,
                "B": 0.30,
                "log10_cmc_mol_l": round(1.50 - 0.30 * max(longest_tail, 1), 8),
                "equation": "log10(CMC mol/L) = A - B * nc",
            },
        }

    if route == "ETHER_SULFATE_KLEVENS":
        cmc = 1.6
        return {
            "cmcMmolL": cmc,
            "hlb": 16.0,
            "nagg": 64,
            "radiusA": 32.0,
            "quality": "MEDIUM_CONFIDENCE",
            "notes": ["Ether sulfate route; not SDS-pure Klevens."],
        }

    return {
        "cmcMmolL": None,
        "hlb": None,
        "nagg": None,
        "radiusA": None,
        "quality": "OUT_OF_DOMAIN",
        "notes": ["Outside reliable micellar calculation domain."],
    }


# -----------------------------------------------------------------------------
# Geometry and validation
# -----------------------------------------------------------------------------

def build_geometry(
    architecture: str,
    v: float | None,
    a0: float | None,
    lc: float | None,
    cpp: float | None,
    numbers: dict,
    electrostatic_label: str,
    active_charge: int,
) -> dict:
    nagg = numbers.get("nagg")
    radius = numbers.get("radiusA")

    geometry_blocked_architectures = {
        "CO_SURFACTANT_FATTY_ALCOHOL",
        "BOLAAMPHIPHILE_DICARBOXYLATE_SALT",
        "FLUOROSURFACTANT",
        "PFOS_LIKE_FLUOROSURFACTANT",
        "GEMINI",
    }

    if nagg is None and v and a0 and architecture not in geometry_blocked_architectures:
        nagg = 36.0 * math.pi * (v**2) / (a0**3)

    core_spherical = None
    core_cylindrical = None
    if v and a0 and architecture not in geometry_blocked_architectures:
        core_spherical = 3.0 * v / a0
        core_cylindrical = 2.0 * v / a0

    if radius is None and core_spherical is not None and architecture not in geometry_blocked_architectures:
        radius = core_spherical + 8.0

    z = abs(active_charge) if active_charge else (1 if electrostatic_label in {"ANIONIC", "CATIONIC"} else 0)
    alpha = 0.2 if electrostatic_label in {"ANIONIC", "CATIONIC"} else 0.1 if electrostatic_label == "ZWITTERIONIC" else 0.0
    beta = 1.0 - alpha

    residual = None
    bound = None
    if nagg is not None and z:
        total_charge_sites = float(nagg) * z
        residual = total_charge_sites * alpha
        bound = total_charge_sites * beta

    sphere_exceeds_tail = bool(core_spherical is not None and lc is not None and core_spherical > lc)
    preferred_geometry = None
    if sphere_exceeds_tail and core_cylindrical is not None and lc is not None and core_cylindrical <= lc:
        preferred_geometry = "cylindrical_or_wormlike_preferred"
    elif sphere_exceeds_tail:
        preferred_geometry = "non_spherical_or_calibrated_profile_required"

    return {
        "aggregation_number": round(float(nagg), 5) if nagg is not None else None,
        "apparent_micelle_radius_a": round(float(radius), 5) if radius is not None else None,
        "apparent_micelle_radius_range_a": [round(radius - 7, 5), round(radius + 7, 5)] if radius else None,
        "core_radius_spherical_a": round(core_spherical, 5) if core_spherical is not None else None,
        "core_radius_cylindrical_a": round(core_cylindrical, 5) if core_cylindrical is not None else None,
        "maximum_tail_length_a": round(lc, 5) if lc is not None else None,
        "spherical_core_exceeds_tail_length": sphere_exceeds_tail,
        "preferred_geometry_after_validation": preferred_geometry,
        "cpp": round(cpp, 5) if cpp is not None else None,
        "residual_charge_e": round(residual, 5) if residual is not None else None,
        "bound_counterions": round(bound, 5) if bound is not None else None,
        "geometryBlocked": architecture in geometry_blocked_architectures,
    }


def packing_class(cpp: float | None) -> str:
    if cpp is None:
        return "bloqueado_ou_indefinido"
    if cpp < 1 / 3:
        return "micela_esferica_provavel"
    if cpp < 1 / 2:
        return "micela_cilindrica_ou_wormlike_provavel"
    if cpp < 1:
        return "bicamada_vesicula_ou_lamela_provavel"
    return "fase_inversa_ou_micela_reversa_provavel"


def validate_physics(
    architecture: str,
    electrostatic_label: str,
    route: str,
    cmc: float | None,
    geometry: dict,
    counterions: list[Any],
) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    blocked: list[str] = []

    if architecture == "CO_SURFACTANT_FATTY_ALCOHOL":
        blocked.extend(["CMC", "NAGG", "MICELLE_RADIUS"])
        warnings.append("C4-C10 fatty alcohol treated as co-surfactant, not primary micellar surfactant.")

    if architecture == "BOLAAMPHIPHILE_DICARBOXYLATE_SALT":
        blocked.extend(["CLASSIC_KLEVENS", "CPP_SINGLE_TAIL", "NAGG_SPHERICAL", "MICELLE_RADIUS_NORMAL"])
        warnings.append("Bola-amphiphile/dicarboxylate with two terminal heads: single-tail model blocked.")

    if architecture == "AMINE_OXIDE_SINGLE_TAIL":
        blocked.extend(["CLASSIC_KLEVENS", "CMC", "HLB_FINAL_WITHOUT_PROFILE"])
        warnings.append("Amine oxide: classic Klevens and final HLB blocked without family profile/QSPR.")

    if architecture == "SULFOBETAINE_SINGLE_TAIL":
        blocked.extend(["CLASSIC_KLEVENS", "GRIFFIN_DAVIES_FINAL_HLB"])
        warnings.append("Sulfobetaine: use family profile/QSPR; Klevens/Griffin/Davies are not final models.")

    if architecture == "MULTI_ACTIVE_FRAGMENT_IONIC_SALT":
        warnings.append("Multiple active fragments with divalent counterion: final CMC needs counterion/activity model.")
        if not counterions:
            errors.append("MULTI_ACTIVE_IONIC_SALT_WITHOUT_COUNTERION")

    if electrostatic_label in {"ANIONIC", "CATIONIC"} and counterions:
        warnings.append("Electrostatic class uses active fragment; detached counterions do not create zwitterion.")

    if architecture == "FLUOROSURFACTANT":
        blocked.extend(["CLASSIC_HYDROCARBON_TANFORD", "CLASSIC_KLEVENS", "CLASSIC_IONIC_KLEVENS"])
        warnings.append("Fluorosurfactant: hydrocarbon Tanford/Klevens blocked.")

    if architecture == "PFOS_LIKE_FLUOROSURFACTANT":
        blocked.extend(["CLASSIC_IONIC_KLEVENS", "TANFORD_LINEAR_HYDROCARBON", "CLASSIC_HYDROCARBON_TANFORD"])
        warnings.append("PFOS/PFAS: hydrocarbon Klevens/Tanford forbidden; use PFAS profile or QSPR.")

    if architecture == "SDS_SODIUM_ALKYL_SULFATE":
        warnings.append("SDS: literature profile preferred over environment-shifted screening value.")

    if architecture == "CTAB_C16_CATIONIC":
        blocked.append("GENERIC_CATIONIC_KLEVENS_AS_FINAL_RESULT")
        warnings.append("CTAB: literature profile replaces generic cationic Klevens.")

    if architecture == "SODIUM_CAPRYLATE_FATTY_ACID_SALT":
        blocked.extend(["GENERIC_ANIONIC_HLB_16", "FINAL_CMC_WITHOUT_EXPERIMENTAL_DATA"])
        warnings.append("Sodium caprylate: HLB uses medium-chain fatty-acid-salt profile/range.")

    if architecture == "BRIJ35_C12E23":
        blocked.append("CLASSIC_NONIONIC_KLEVENS")
        warnings.append("Brij/C12E23: literature/QSPR polymeric profile replaces classic nonionic Klevens.")

    if architecture == "TWEEN_LIKE_SURFACTANT":
        blocked.append("CLASSIC_NONIONIC_KLEVENS")
        warnings.append("Tween-like surfactant: HLB profile replaces generic Klevens/Davies.")

    if architecture == "GEMINI":
        blocked.extend(["CLASSIC_IONIC_KLEVENS", "CLASSIC_SINGLE_TAIL_TANFORD", "PLACEHOLDER_CMC"])
        warnings.append("Gemini: fixed CMC placeholder blocked; experimental profile or calibrated Gemini model required.")

    if geometry.get("spherical_core_exceeds_tail_length"):
        warnings.append("Spherical core radius exceeds maximum tail length; use cylindrical/wormlike or calibrated profile.")
        blocked.append("SPHERICAL_CORE_RADIUS_AS_FINAL_RESULT")

    if geometry.get("aggregation_number") is not None and float(geometry["aggregation_number"]) < 1:
        errors.append("NAGG_LESS_THAN_1")
        blocked.append("NAGG")

    if cmc is not None and cmc <= 0:
        errors.append("CMC_NOT_POSITIVE")
        blocked.append("CMC")

    return {
        "passed": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "blockedCalculations": sorted(set(blocked)),
    }


def _allowed_cmc(cmc_mmol_corr: float | None, blocked: list[str]) -> bool:
    if cmc_mmol_corr is None:
        return False
    hard_blocks = {"CMC", "CLASSIC_KLEVENS"}
    return not any(item in blocked for item in hard_blocks)


# -----------------------------------------------------------------------------
# Main external API used by calculation_page.py
# -----------------------------------------------------------------------------

def miriam21_surfactant_v2(mol, mw: float, logp: float, tpsa: float, env: dict | None = None) -> dict:
    env = env or {}
    ionic_strength = float(env.get("ionic_strength_mol_l", 0.0) or 0.0)
    temperature_k = float(env.get("temperature_k", 298.15) or 298.15)

    active_fragments, counterions, fragmentation = split_fragments(mol)
    representative = active_fragments[0]

    try:
        active_tpsa = float(rdMolDescriptors.CalcTPSA(representative))
    except Exception:
        active_tpsa = tpsa

    try:
        active_logp = float(Crippen.MolLogP(representative))
    except Exception:
        active_logp = logp

    try:
        active_mw = float(Descriptors.MolWt(representative))
    except Exception:
        active_mw = mw

    aggregate = aggregate_counts(active_fragments)
    tails = []
    for frag in active_fragments:
        tails.extend(tail_components(frag))
    tails.sort(key=lambda item: item["carbonCount"], reverse=True)

    charge_type, electrostatic_label, active_charge, total_global_charge = electrostatic_class(active_fragments, counterions)
    architecture, final_class, route, _ = classify_architecture(active_fragments, counterions)
    head = head_group_type(aggregate)
    longest_tail = int(tails[0]["carbonCount"]) if tails else 0
    tail_count = len([tail for tail in tails if tail["carbonCount"] >= 4])

    surfactant_score_raw = sum(fragment_score(frag) for frag in active_fragments) / max(len(active_fragments), 1)
    surfactant_score_normalized = normalize_surfactant_score(surfactant_score_raw, architecture, longest_tail)
    surfactant_score = surfactant_score_normalized * 100.0

    is_primary_micellar = (
        architecture not in {
            "CO_SURFACTANT_FATTY_ALCOHOL",
            "BOLAAMPHIPHILE_DICARBOXYLATE_SALT",
            "NOT_AMPHIPHILIC",
            "WEAK_AMPHIPHILE",
        }
        and longest_tail >= 6
    )

    if architecture in {"PFOS_LIKE_FLUOROSURFACTANT", "FLUOROSURFACTANT"}:
        v = None
        lc = None
    elif architecture == "MULTI_ACTIVE_FRAGMENT_IONIC_SALT":
        v = tanford_volume(longest_tail)
        lc = tanford_length(longest_tail)
    elif architecture in {"BOLAAMPHIPHILE_DICARBOXYLATE_SALT", "CO_SURFACTANT_FATTY_ALCOHOL"}:
        v = tanford_volume(longest_tail)
        lc = tanford_length(longest_tail)
    elif tail_count >= 2 and architecture in {"GEMINI", "DOUBLE_TAIL", "DOUBLE_TAIL_BRANCHED"}:
        selected = tails[:2]
        v = sum(tanford_volume(t["carbonCount"]) or 0 for t in selected)
        lc = max((tanford_length(t["carbonCount"]) or 0 for t in selected), default=None)
    else:
        v = tanford_volume(longest_tail)
        lc = tanford_length(longest_tail)

    a0_raw, a0_eff, a0_meta = estimate_head_area(architecture, head, aggregate, active_tpsa, ionic_strength)
    cpp = None
    if v and a0_eff and lc and architecture not in {
        "CO_SURFACTANT_FATTY_ALCOHOL",
        "BOLAAMPHIPHILE_DICARBOXYLATE_SALT",
        "FLUOROSURFACTANT",
        "PFOS_LIKE_FLUOROSURFACTANT",
        "GEMINI",
    }:
        cpp = v / (a0_eff * lc)

    numbers = route_numbers(architecture, route, longest_tail, aggregate, active_logp, active_tpsa)
    cmc_mmol = numbers.get("cmcMmolL")
    hlb = numbers.get("hlb")

    # Environment correction only for classic ionic/ether sulfate routes.
    if cmc_mmol is not None and route in {"CLASSIC_IONIC_KLEVENS", "ETHER_SULFATE_KLEVENS"}:
        salt_factor = (1.0 + ionic_strength / max(cmc_mmol / 1000.0, 1e-9)) ** (-0.18)
        temp_factor = math.exp(0.010 * (temperature_k - 298.15))
        cmc_mmol_corr = cmc_mmol * max(0.08, min(1.15, salt_factor)) * max(0.4, min(2.0, temp_factor))
        correction_meta = {
            "method": "controlled_Corrin_Harkins_like",
            "saltFactor": round(float(salt_factor), 8),
            "temperatureFactor": round(float(temp_factor), 8),
        }
    else:
        cmc_mmol_corr = cmc_mmol
        correction_meta = {"method": "no_aggressive_environment_correction", "route": route}

    xcmc = None
    delta_g = None
    if cmc_mmol_corr is not None and cmc_mmol_corr > 0:
        cmc_mol = cmc_mmol_corr / 1000.0
        xcmc = cmc_mol / (55.5 + cmc_mol)
        alpha = 0.2 if electrostatic_label in {"ANIONIC", "CATIONIC"} else 0.1 if electrostatic_label == "ZWITTERIONIC" else 0.0
        delta_g = 8.314462618 * temperature_k * (1.0 + alpha) * math.log(xcmc) / 1000.0

    geometry = build_geometry(architecture, v, a0_eff, lc, cpp, numbers, electrostatic_label, active_charge)
    physical_validation = validate_physics(architecture, electrostatic_label, route, cmc_mmol_corr, geometry, counterions)

    quality_score = confidence_from_quality(str(numbers.get("quality", "")))
    if not physical_validation["passed"]:
        quality_score = min(quality_score, 0.20)
    if architecture in {"SULFOBETAINE_SINGLE_TAIL", "AMINE_OXIDE_SINGLE_TAIL"} and geometry.get("spherical_core_exceeds_tail_length"):
        quality_score = min(quality_score, 0.35)

    identity_confidence = identity_confidence_for(architecture, final_class)

    classe_surfactante = {
        "ANIONIC": "anionico",
        "CATIONIC": "cationico",
        "ZWITTERIONIC": "zwitterionico",
        "NONIONIC": "nao_ionico",
    }.get(electrostatic_label, "nao_classificado_como_surfactante")

    if architecture == "CO_SURFACTANT_FATTY_ALCOHOL":
        classe_surfactante = "nao_ionico"
    if architecture == "BOLAAMPHIPHILE_DICARBOXYLATE_SALT":
        classe_surfactante = "anionico"

    miriam_identity = {
        "packageVersion": "MIRIAM-2.1-calibrated-profiles-v2",
        "rawSmiles": mol_smiles(mol),
        "activeSmiles": mol_smiles(representative),
        "activeFragments": fragmentation["activeFragments"],
        "counterions": fragmentation["counterions"],
        "unknownFragments": fragmentation.get("unknownFragments", []),
        "electrostaticClass": electrostatic_label,
        "architecture": architecture,
        "finalClass": final_class,
        "polarHeadType": head,
        "activeFormalCharge": active_charge,
        "totalFormalCharge": total_global_charge,
        "tailCarbonCount": longest_tail,
        "activeFragmentCount": len(active_fragments),
        "surfactantScore": round(surfactant_score, 5),
        "surfactantScoreRaw": round(surfactant_score_raw, 5),
        "surfactantScoreNormalized": round(surfactant_score_normalized, 5),
        "flags": {
            "isFluorosurfactant": architecture in {"FLUOROSURFACTANT", "PFOS_LIKE_FLUOROSURFACTANT"},
            "isPolymericNonionic": architecture in {"BRIJ35_C12E23", "TRITON_LIKE", "TWEEN_LIKE_SURFACTANT"},
            "isGemini": architecture == "GEMINI",
            "isSulfobetaine": architecture == "SULFOBETAINE_SINGLE_TAIL",
            "usesActiveFragmentDescriptors": True,
        },
        "activeDescriptors": {
            "mw": round(active_mw, 5),
            "logp": round(active_logp, 5),
            "tpsa": round(active_tpsa, 5),
        },
        "globalDescriptors": {
            "mw": round(mw, 5),
            "logp": round(logp, 5),
            "tpsa": round(tpsa, 5),
        },
        "identityConfidence": round(identity_confidence, 5),
        "confidence": round(identity_confidence, 5),
    }

    structural_features = {
        "polarHeads": [
            {
                "type": head,
                "formalCharge": active_charge,
                "countHints": {
                    "alkylSulfate": aggregate.get("alkylSulfateCount"),
                    "alkylSulfonate": aggregate.get("alkylSulfonateCount"),
                    "sulfate": aggregate.get("sulfateCount"),
                    "sulfonate": aggregate.get("sulfonateCount"),
                    "carboxylate": aggregate.get("carboxylateCount"),
                    "amineOxide": aggregate.get("amineOxideCount"),
                    "quaternaryAmmonium": aggregate.get("quaternaryAmmoniumCount"),
                    "rawQuaternaryNitrogen": aggregate.get("rawQuaternaryNitrogenCount"),
                    "hydroxyl": aggregate.get("hydroxylCount"),
                    "eoUnits": aggregate.get("eoUnits"),
                },
                "rawAreaA2": round(a0_raw, 5),
                "effectiveAreaA2": round(a0_eff, 5),
            }
        ],
        "hydrophobicTails": tails,
        "tailCount": tail_count,
        "activeFragmentCount": len(active_fragments),
        "counterionCount": len(counterions),
        "unknownFragments": fragmentation.get("unknownFragments", []),
        "activeDescriptors": {
            "mw": round(active_mw, 5),
            "logp": round(active_logp, 5),
            "tpsa": round(active_tpsa, 5),
        },
        "globalDescriptors": {
            "mw": round(mw, 5),
            "logp": round(logp, 5),
            "tpsa": round(tpsa, 5),
        },
        "aggregateFunctionalCounts": aggregate,
    }

    cmc_conf = parameter_confidence("CMC", architecture, route, quality_score, physical_validation["warnings"])
    hlb_conf = parameter_confidence("HLB", architecture, route, quality_score, physical_validation["warnings"])
    cpp_conf = parameter_confidence("CPP", architecture, route, quality_score, physical_validation["warnings"])
    nagg_conf = parameter_confidence("NAGG_RADIUS", architecture, route, quality_score, physical_validation["warnings"])

    calc_plan = [
        {
            "parameter": "CMC",
            "route": route,
            "allowed": _allowed_cmc(cmc_mmol_corr, physical_validation["blockedCalculations"]),
            "confidence": round(cmc_conf, 5),
            "quality": numbers.get("quality"),
            "reason": numbers.get("notes", []),
            "modelMetadata": numbers.get("modelMetadata"),
        },
        {
            "parameter": "HLB",
            "route": "FAMILY_OR_ARCHITECTURE_HLB",
            "allowed": hlb is not None,
            "confidence": round(hlb_conf, 5),
            "quality": numbers.get("quality"),
            "reason": numbers.get("notes", ["HLB selected by MIRIAM-2.1 architecture."]),
        },
        {
            "parameter": "CPP",
            "route": "CPP_EFFECTIVE_HEAD_AREA_WITH_AMINE_OXIDE_HEAD" if architecture == "AMINE_OXIDE_SINGLE_TAIL" else "CPP_SINGLE_TAIL_OR_PROFILE_BLOCKED",
            "allowed": cpp is not None and "CPP_SINGLE_TAIL" not in physical_validation["blockedCalculations"],
            "confidence": round(cpp_conf, 5),
            "quality": "STRUCTURAL_ESTIMATE" if cpp is not None else numbers.get("quality"),
            "reason": [a0_meta.get("method", ""), "Physical validation applied."],
        },
        {
            "parameter": "NAGG_RADIUS",
            "route": "LOW_CONFIDENCE_GEOMETRY_ONLY" if architecture in {"AMINE_OXIDE_SINGLE_TAIL", "SULFOBETAINE_SINGLE_TAIL"} else "PROFILE_OR_BLOCKED",
            "allowed": geometry.get("aggregation_number") is not None and "NAGG" not in physical_validation["blockedCalculations"],
            "confidence": round(nagg_conf, 5),
            "quality": "STRUCTURAL_ESTIMATE_LOW_CONFIDENCE" if nagg_conf < 0.5 else numbers.get("quality"),
            "reason": physical_validation["warnings"] or numbers.get("notes", []),
        },
    ]

    applicability = {
        "model": route,
        "applicable": route not in {"BLOCKED_CO_SURFACTANT_ONLY", "BLOCKED_BOLAAMPHIPHILE_MODEL_REQUIRED", "BLOCKED_NON_SURFACTANT"},
        "confidence": round(quality_score, 5),
        "blockingIssues": physical_validation["errors"],
        "softWarnings": physical_validation["warnings"],
        "allowedRoutes": [item for item in calc_plan if item["allowed"]],
        "blockedRoutes": sorted(set(physical_validation["blockedCalculations"] + list(numbers.get("blockedCalculations", [])))),
        "forbiddenRoutes": sorted(set(physical_validation["blockedCalculations"] + list(numbers.get("blockedCalculations", [])))),
        "selectedModels": {
            "CMC": route,
            "HLB": "FAMILY_OR_ARCHITECTURE_HLB" if hlb is not None else "PROFILE_OR_QSPR_REQUIRED",
            "CPP": "EFFECTIVE_HEAD_AREA_GEOMETRY" if cpp is not None else "BLOCKED_OR_PROFILE_REQUIRED",
            "NAGG_RADIUS": "PROFILE_OR_LOW_CONFIDENCE_GEOMETRY",
        },
    }

    audit = {
        "miriamVersion": "MIRIAM-2.1-calibrated-profiles-v2",
        "warnings": physical_validation["warnings"] + numbers.get("notes", []),
        "blockedCalculations": sorted(set(physical_validation["blockedCalculations"] + list(numbers.get("blockedCalculations", [])))),
        "confidencePenalties": [] if quality_score >= 0.65 else ["LOW_CONFIDENCE_OR_BLOCKED_ROUTE"],
        "recommendedNextModel": "EXPERIMENTAL_DATA_REQUIRED" if quality_score < 0.65 else "QSPR_OR_EXPERIMENTAL_CALIBRATION",
        "criticalRuleApplied": "active_fragment_charge_over_global_charge",
    }

    return {
        "is_surfactante": est(bool(is_primary_micellar), "MIRIAM-2.1 fragment router"),
        "classe_surfactante": est(classe_surfactante, "MIRIAM-2.1 active-fragment electrostatic classifier"),
        "tipo_cabeca_polar": est(head, "MIRIAM-2.1 strict SMARTS head classifier"),
        "tipo_carga_surfactante": est(electrostatic_label, "MIRIAM-2.1 active-fragment charge classifier"),
        "carga_formal_surfactante": est(active_charge, "MIRIAM-2.1 active-fragment formal charge"),
        "indice_anfifilico": est(round(surfactant_score_normalized, 5), "MIRIAM-2.1 normalized amphiphilic score"),

        "comprimento_cauda": est(longest_tail, "MIRIAM-2.1 hydrophobic tail detector", "carbonos"),
        "comprimento_cauda_efetivo": est(tails[0]["effectiveCarbonCount"] if tails else None, "MIRIAM-2.1 effective tail count", "carbonos"),
        "numero_caudas_hidrofobicas": est(tail_count, "MIRIAM-2.1 tail component detector"),
        "volume_cauda": est(round(v, 5) if v is not None else None, "MIRIAM-2.1 tail volume route", "Angstrom^3"),
        "comprimento_maximo_cauda": est(round(lc, 5) if lc is not None else None, "MIRIAM-2.1 tail length route", "Angstrom"),
        "area_cabeca_micela": est(round(a0_eff, 5), "MIRIAM-2.1 effective head area", "Angstrom^2", str(a0_meta)),
        "area_cabeca_ideal": est(round(a0_raw, 5), "MIRIAM-2.1 raw head area", "Angstrom^2"),
        "area_cabeca_efetiva": est(round(a0_eff, 5), "MIRIAM-2.1 effective head area", "Angstrom^2"),

        "hlb_griffin": est(round(hlb, 5) if hlb is not None else None, "MIRIAM-2.1 selected HLB"),
        "hlb_davies": est(round(hlb, 5) if hlb is not None else None, "MIRIAM-2.1 selected HLB alias"),
        "hlb_estimado": est(round(hlb, 5) if hlb is not None else None, "MIRIAM-2.1 architecture HLB"),
        "hlb_engine_bruto": est(round(hlb, 5) if hlb is not None else None, "MIRIAM-2.1 architecture HLB"),

        "cmc_klevens_mol_l": est(round((cmc_mmol or 0) / 1000.0, 12) if cmc_mmol is not None else None, "MIRIAM-2.1 selected/base CMC", "mol/L", str(numbers)),
        "cmc_klevens_mmol_l": est(round(cmc_mmol, 8) if cmc_mmol is not None else None, "MIRIAM-2.1 selected/base CMC", "mmol/L", str(numbers)),
        "cmc_corrigida_mol_l": est(round((cmc_mmol_corr or 0) / 1000.0, 12) if cmc_mmol_corr is not None else None, "MIRIAM-2.1 corrected/family route CMC", "mol/L", str(correction_meta)),
        "cmc_corrigida_mmol_l": est(round(cmc_mmol_corr, 8) if cmc_mmol_corr is not None else None, "MIRIAM-2.1 corrected/family route CMC", "mmol/L", str(correction_meta)),
        "cmc_estimada": est(round(cmc_mmol, 8) if cmc_mmol is not None else None, "MIRIAM-2.1 selected CMC", "mmol/L", str(numbers)),
        "cmc_ambiente_estimada": est(round(cmc_mmol_corr, 8) if cmc_mmol_corr is not None else None, "MIRIAM-2.1 environment/family CMC", "mmol/L", str(correction_meta)),
        "x_cmc": est(round(xcmc, 12) if xcmc is not None else None, "MIRIAM-2.1 XCMC"),
        "delta_g_micelizacao": est(round(delta_g, 5) if delta_g is not None else None, "MIRIAM-2.1 Gibbs free energy of micellization", "kJ/mol"),

        "parametro_empacotamento": est(
            {
                "valor": round(cpp, 5) if cpp is not None else None,
                "classe": packing_class(cpp),
                "route": route,
                "blocked": "CPP_SINGLE_TAIL" in physical_validation["blockedCalculations"],
            },
            "MIRIAM-2.1 packing parameter route",
        ),
        "cpp": est(round(cpp, 5) if cpp is not None else None, "MIRIAM-2.1 CPP"),
        "cpp_ideal": est(round(cpp, 5) if cpp is not None else None, "MIRIAM-2.1 CPP"),
        "comportamento_micelar_previsto": est(packing_class(cpp) if is_primary_micellar else "bloqueado_ou_nao_micelar_primario", "MIRIAM-2.1 morphology routing"),
        "hld": est({"status": "FORMULATION_ONLY"}, "MIRIAM-2.1 HLD requires formulation/oil/salinity inputs", available=True),
        "nac": est({"status": "FORMULATION_ONLY"}, "MIRIAM-2.1 NAC requires HLD inputs", available=True),

        "parametros_micela": est(geometry, "MIRIAM-2.1 geometry/profile output"),
        "numero_agregacao_estimado": est(geometry.get("aggregation_number"), "MIRIAM-2.1 validated/profile Nagg"),
        "raio_micela_esferica": est(geometry.get("apparent_micelle_radius_a"), "MIRIAM-2.1 apparent micelle radius", "Angstrom"),
        "raio_nucleo_hidrofobico": est(geometry.get("core_radius_spherical_a"), "MIRIAM-2.1 hydrophobic core radius", "Angstrom"),
        "faixa_raio_micela": est(geometry.get("apparent_micelle_radius_range_a"), "MIRIAM-2.1 radius range", "Angstrom"),
        "raio_micela_cilindrica": est(geometry.get("core_radius_cylindrical_a"), "MIRIAM-2.1 cylindrical core radius", "Angstrom"),
        "carga_residual_micela": est(geometry.get("residual_charge_e"), "MIRIAM-2.1 residual micellar charge"),
        "contraions_ligados_micela": est(geometry.get("bound_counterions"), "MIRIAM-2.1 bound counterions"),
        "densidade_carga_superficial": est(None, "MIRIAM-2.1 surface charge density requires explicit micelle surface", available=False),

        "perfil_calibracao_literatura": est(numbers, "MIRIAM-2.1 internal reference/family profile"),
        "confianca_cmc": est({"score": round(cmc_conf, 5), "quality": numbers.get("quality"), "route": route}, "MIRIAM-2.1 CMC confidence model"),
        "diagnostico_cauda": est({"tails": tails, "tailCount": tail_count}, "MIRIAM-2.1 tail diagnostics"),
        "miriam2_identity": est(miriam_identity, "MIRIAM-2.1 identification package", available=True),
        "miriam2_calculation_plan": est(calc_plan, "MIRIAM-2.1 parameter calculation plan", available=True),
        "miriam2_physical_validation": est(physical_validation, "MIRIAM-2.1 physical validation", available=True),
        "miriam2_applicability": est(applicability, "MIRIAM-2.1 applicability domain", available=True),
        "miriam2_audit": est(audit, "MIRIAM-2.1 audit trail", available=True),
        "miriam2_structural_features": est(structural_features, "MIRIAM-2.1 structural features", available=True),
    }


