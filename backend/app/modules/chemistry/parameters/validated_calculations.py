"""Shared, deterministic 2D/3D calculations and explicit applicability limits.

RDKit descriptors are calculations, empirical correlations are estimates, and no
quantum or experimental validation is implied. Concentrations are in mmol/L.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from rdkit import Chem
from rdkit.Chem import Crippen, Descriptors, rdMolDescriptors

VERSION = "validated-calculations-1.0"
CLASS_PT = {"anionic": "aniônico", "cationic": "catiônico", "nonionic": "não iônico",
            "zwitterionic": "zwitteriônico", "amphoteric": "anfotérico", "unknown": "não surfactante identificado"}
HEAD_PT = {"sulfate": "sulfato", "sulfonate": "sulfonato", "carboxylate": "carboxilato",
           "carboxylic_acid": "ácido carboxílico", "quaternary_ammonium": "amônio quaternário",
           "protonated_amine": "amina protonada", "amine": "amina", "amide": "amida",
           "phosphate": "fosfato", "amine_oxide": "óxido de amina", "zwitterion": "cabeça zwitteriônica",
           "alcohol_ether": "álcool/éter", "polar": "cabeça polar", "none": "sem cabeça polar forte identificada"}


def matches(mol, smarts: str):
    return mol.GetSubstructMatches(Chem.MolFromSmarts(smarts))


def split_active(mol):
    """Pick the organic amphiphile by hydrophobic chain, then carbon/atom count.

    All remaining fragments are retained; organic counterions are not silently
    mistaken for the active merely because their SMILES text is longer.
    """
    fragments = list(Chem.GetMolFrags(mol, asMols=True, sanitizeFrags=True))
    def rank(fragment):
        tails = carbon_tails(fragment)
        return (max((t[0] for t in tails), default=0),
                sum(a.GetAtomicNum() == 6 for a in fragment.GetAtoms()), fragment.GetNumHeavyAtoms(),
                Chem.MolToSmiles(fragment))
    active = max(fragments, key=rank)
    return active, [f for f in fragments if f is not active]


def carbon_tails(mol) -> list[tuple[int, int, bool]]:
    """(longest carbon path, component size, branched); exclude carbonyl/ring C.

    Remaining graph is a forest, so two BFS traversals give an exact diameter.
    EO carbons occur as disconnected C2 units and are not counted as tails.
    """
    indices = {a.GetIdx() for a in mol.GetAtoms() if a.GetAtomicNum() == 6 and not a.IsInRing()
               and not any(b.GetBondTypeAsDouble() >= 2 and b.GetOtherAtom(a).GetAtomicNum() != 6
                           for b in a.GetBonds())}
    adjacency = {i: {n.GetIdx() for n in mol.GetAtomWithIdx(i).GetNeighbors()} & indices for i in indices}
    pending, result = set(indices), []
    def farthest(start):
        distance, queue = {start: 0}, [start]
        for i in queue:
            for j in adjacency[i]:
                if j not in distance:
                    distance[j] = distance[i] + 1
                    queue.append(j)
        end = max(distance, key=distance.get)
        return end, distance
    while pending:
        start = min(pending)
        end, component = farthest(start)
        _, distance = farthest(end)
        pending.difference_update(component)
        result.append((max(distance.values()) + 1, len(component), any(len(adjacency[i]) > 2 for i in component)))
    return sorted(result, reverse=True)


@dataclass
class StructuralProfile:
    active: Any
    others: list[Any]
    head: str
    charge: int
    chemical_class: str
    surfactant_class: str
    is_surfactant: bool
    tail_c: int
    tail_count: int
    linear_hydrocarbon: bool
    ambiguous_mixture: bool
    # Web Lite v1: classe estrutural por regras + papel anfifílico (ver properties/surfactant_class.py).
    amphiphile_role: str = "none"
    rules_fired: tuple[str, ...] = ()
    classification: Any = None


def profile(mol) -> StructuralProfile:
    active, others = split_active(mol)
    charge = sum(a.GetFormalCharge() for a in active.GetAtoms())
    # Adjacent formal +/- pairs in nitro/N-oxide/sulfoxide resonance forms do
    # not by themselves make an amphoteric/zwitterionic surfactant.
    residual = {a.GetIdx(): a.GetFormalCharge() for a in active.GetAtoms()}
    for atom in active.GetAtoms():
        if residual[atom.GetIdx()] <= 0:
            continue
        for neighbor in atom.GetNeighbors():
            if residual[neighbor.GetIdx()] < 0:
                paired = min(residual[atom.GetIdx()], -residual[neighbor.GetIdx()])
                residual[atom.GetIdx()] -= paired
                residual[neighbor.GetIdx()] += paired
    pos = any(value > 0 for value in residual.values())
    neg = any(value < 0 for value in residual.values())
    amine_oxide = bool(matches(active, "[N+X4]-[O-]"))
    if amine_oxide:
        head = "amine_oxide"
    elif pos and neg and charge == 0:
        head = "zwitterion"
    elif matches(active, "[O;X2]-[S](=[O])(=[O])-[O-]"):
        head = "sulfate"
    elif matches(active, "[C]-[S](=[O])(=[O])-[O-]"):
        head = "sulfonate"
    elif matches(active, "[CX3](=[OX1])[O-]"):
        head = "carboxylate"
    elif matches(active, "[CX3](=[OX1])[OX2H1]"):
        head = "carboxylic_acid"
    elif matches(active, "[P](=[O])([O])([O])"):
        head = "phosphate"
    elif matches(active, "[N+X4;H0]"):
        head = "quaternary_ammonium"
    elif matches(active, "[N+;!H0]"):
        head = "protonated_amine"
    elif matches(active, "[NX3;!$(N-C=O);!$(N-S(=O)=O)]"):
        head = "amine"
    elif matches(active, "[NX3]-[CX3]=[OX1]"):
        head = "amide"
    elif matches(active, "[OX2H1;!$(O-C=O)]") or matches(active, "[OD2]([#6])[#6]"):
        head = "alcohol_ether"
    else:
        head = "polar" if rdMolDescriptors.CalcTPSA(active) >= 20 else "none"
    chemical_class = ("anionic" if charge < 0 else "cationic" if charge > 0 else
                      "zwitterionic" if pos and neg and not amine_oxide else "nonionic")
    tails = carbon_tails(active)
    tail_c = max((t[0] for t in tails), default=0)
    tail_count = sum(t[0] >= 4 for t in tails)
    polar = head != "none" or charge != 0
    rigid = rdMolDescriptors.CalcNumRings(active) >= 3 and sum(a.GetAtomicNum() == 6 for a in active.GetAtoms()) >= 12
    minimum_tail = 7 if head in {"carboxylate", "carboxylic_acid"} else 8
    is_surfactant = bool(polar and (tail_c >= minimum_tail or (rigid and rdMolDescriptors.CalcTPSA(active) >= 40)))
    linear = (tail_count == 1 and not any(t[2] for t in tails if t[0] >= 4)
              and rdMolDescriptors.CalcNumRings(active) == 0
              and all(a.GetAtomicNum() in {1, 6, 7, 8, 16} for a in active.GetAtoms())
              and not any(b.GetBondTypeAsDouble() > 1 and b.GetBeginAtom().GetAtomicNum() == 6
                          and b.GetEndAtom().GetAtomicNum() == 6 for b in active.GetBonds()))
    # Two hydrophobic organic components describe a mixture, not a single salt.
    ambiguous = any(max((t[0] for t in carbon_tails(f)), default=0) >= 6 for f in others)
    from app.modules.chemistry.properties.surfactant_class import classify  # import local: evita ciclo
    classification = classify(active, is_surfactant, head, tail_c)
    return StructuralProfile(active, others, head, charge, chemical_class,
                             classification.structural_class if is_surfactant else "unknown", is_surfactant,
                             tail_c, tail_count, linear, ambiguous,
                             classification.amphiphile_role, classification.rules_fired, classification)


def packing_estimate(p: StructuralProfile) -> dict:
    """Tanford for one linear hydrocarbon tail; head area is a CG heuristic.

    This is a shared structural screening value, not a measured interfacial area
    or a validated phase prediction. Complex/branched/multitail domains block it.
    """
    result = {"tail_volume_a3": None, "tail_length_a": None, "head_area_a2": None, "cpp": None,
              "method": "Tanford + uncalibrated CG head area"}
    if not p.is_surfactant or not p.linear_hydrocarbon or p.ambiguous_mixture:
        return result
    volume = 27.4 + 26.9 * p.tail_c
    length = 1.5 + 1.265 * p.tail_c
    area = 72.0 if p.chemical_class in {"anionic", "cationic"} else 56.0 if p.chemical_class == "zwitterionic" else 60.0
    return {**result, "tail_volume_a3": volume, "tail_length_a": length, "head_area_a2": area,
            "cpp": volume / (area * length)}


def hlb_values(p: StructuralProfile) -> dict:
    unavailable = {"davies": None, "griffin": None, "value": None, "method": "not_available"}
    if not p.is_surfactant or p.ambiguous_mixture:
        return unavailable
    a = p.active
    hydrophobic = sum(atom.GetAtomicNum() == 6 and not any(
        b.GetBondTypeAsDouble() >= 2 and b.GetOtherAtom(atom).GetAtomicNum() != 6 for b in atom.GetBonds())
        for atom in a.GetAtoms())
    davies = griffin = None
    # Tables are deliberately restricted; no invented ammonium/zwitterion groups.
    if p.linear_hydrocarbon and p.head in {"sulfate", "carboxylate", "carboxylic_acid", "alcohol_ether"}:
        oh = len(matches(a, "[OX2H1;!$(O-C=O)]"))
        ether = len(matches(a, "[OD2]([#6])[#6]"))
        group = {"sulfate": 38.7, "sulfonate": 38.7, "carboxylate": 19.1,
                 "carboxylic_acid": 2.1, "alcohol_ether": 0.0}[p.head]
        if p.head == "carboxylate" and any(f.GetNumAtoms() == 1 and f.GetAtomWithIdx(0).GetSymbol() == "K" for f in p.others):
            group = 21.1
        others = {Chem.MolToSmiles(f) for f in p.others}
        oxygen_count = sum(atom.GetAtomicNum() == 8 for atom in a.GetAtoms())
        sulfur_count = sum(atom.GetAtomicNum() == 16 for atom in a.GetAtoms())
        head_supported = (
            p.head == "sulfate" and others == {"[Na+]"} and sulfur_count == 1 and oxygen_count == 4 + oh + ether
            or p.head == "carboxylate" and others in ({"[Na+]"}, {"[K+]"}) and len(matches(a, "[CX3](=O)[O-]")) == 1 and oxygen_count == 2 + oh + ether and sulfur_count == 0
            or p.head == "carboxylic_acid" and len(matches(a, "[CX3](=O)[OH]")) == 1 and oxygen_count == 2 + oh + ether and sulfur_count == 0
            or p.head == "alcohol_ether" and not matches(a, "[CX3]=O") and sulfur_count == 0
        )
        if head_supported and all(atom.GetAtomicNum() in {6, 8, 16} for atom in a.GetAtoms()):
            davies = 7.0 + group + 1.9 * oh + 1.3 * ether - 0.475 * hydrophobic
    # Griffin E/5 for linear alcohol ethoxylates only (mass % EO / 5).
    oxygens = [atom for atom in a.GetAtoms() if atom.GetAtomicNum() == 8]
    ether_count = len(matches(a, "[OD2]([#6])[#6]"))
    if (p.linear_hydrocarbon and p.head == "alcohol_ether" and ether_count >= 1
            and len(oxygens) == ether_count + 1
            and sum(atom.GetAtomicNum() == 6 for atom in a.GetAtoms()) == p.tail_c + 2 * ether_count
            and all(atom.GetAtomicNum() in {6, 8} for atom in a.GetAtoms())
            and len(matches(a, "[OX2H1]")) == 1):
        griffin = 20.0 * (ether_count * Descriptors.MolWt(Chem.MolFromSmiles("C1CO1"))) / Descriptors.MolWt(a)
    value = griffin if griffin is not None else davies
    return {"davies": davies, "griffin": griffin, "value": value,
            "method": "Griffin E/5 (alcohol ethoxylate)" if griffin is not None else "Davies group contributions" if davies is not None else "not_available"}


def cmc_estimate(p: StructuralProfile, env: dict) -> dict:
    """Restricted aqueous homolog correlation, not a trained predictive model.

    Anchors: Sigma 71729 (SDS 7–10 mM), H6269 (CTAB .92–1 mM), 20–25 C.
    Salt response is explicitly an uncalibrated empirical screening correction.
    No agitation, volume, particle count or visual speed enters equilibrium CMC.
    """
    result = {"reference_mmol_l": None, "value": None, "method": "not_available", "note": "Fora do domínio: requer CMC experimental ou modelo treinado validado."}
    if not p.is_surfactant or not p.linear_hydrocarbon or p.ambiguous_mixture:
        return result
    if p.amphiphile_role == "surfactant_or_cosurfactant":
        result["note"] = ("Cabeça polar fraca (surfactante ou cossurfactante, conforme o sistema): "
                          "sem correlação de CMC fundamentada na v1.")
        return result
    others = {Chem.MolToSmiles(f) for f in p.others}
    anchor = None
    if p.head == "sulfate" and others == {"[Na+]"} and 8 <= p.tail_c <= 18:
        if Chem.MolToSmiles(p.active) == Chem.MolToSmiles(Chem.MolFromSmiles("C" * p.tail_c + "OS(=O)(=O)[O-]")):
            anchor = (8.2, 12, 0.31, "SDS/sodium alkyl sulfate homolog")
    if p.head == "quaternary_ammonium" and others == {"[Br-]"} and 8 <= p.tail_c <= 18:
        if Chem.MolToSmiles(p.active) == Chem.MolToSmiles(Chem.MolFromSmiles("C" * p.tail_c + "[N+](C)(C)C")):
            anchor = (0.92, 16, 0.30, "CTAB/alkyltrimethylammonium bromide homolog")
    if anchor is None:
        return result
    value, n_ref, slope, family = anchor
    reference = value * 10 ** (slope * (n_ref - p.tail_c))
    result.update(reference_mmol_l=reference, method=family)
    solvent = str(env.get("solvent_name", env.get("solvent", "water"))).strip().lower()
    ionic = float(env.get("ionic_strength_mol_l", 0.01))
    temperature = float(env.get("temperature_k", 298.15))
    if (solvent not in {"water", "água", "agua", "h2o"} or not 293.15 <= temperature <= 298.15
            or not 0 <= ionic <= 0.1 or float(env.get("dielectric_constant", 78.5)) < 60
            or float(env.get("solvent_polarity_index", 1)) < 0.9):
        result["note"] = "Referência aquosa 20–25 °C; sem extrapolação para este solvente, temperatura ou força iônica."
        return result
    salt_coefficient = 5.8 if p.head == "sulfate" else 4.4
    result.update(value=reference / (1 + salt_coefficient * ionic),
                  note="Referência aquosa 20–25 °C; homólogos por Klevens. Correção salina empírica não calibrada; não é medição nem IA treinada.")
    return result


def acid_base_estimates(p: StructuralProfile, ph: float) -> dict:
    """Single-site Henderson–Hasselbalch with an explicitly approximate pKa.

    No arbitrary cap on logD; polyprotic/permanent ions return no estimate.
    """
    a = p.active
    if p.chemical_class == "zwitterionic" or p.head in {"amine_oxide", "quaternary_ammonium"}:
        return {"pka": None, "logd": None, "kind": None, "note": "Íons permanentes e zwitterions requerem modelo específico de especiação/partição."}
    acid = matches(a, "[CX3](=[OX1])[O;H1,-1]")
    amine = matches(a, "[N;X3,X4;!$(N-C=O);!$(N-S(=O)=O);!$(N=O);!$(N-[O-]);!$([N+;H0])]")
    phenol = matches(a, "[c]-[OX2H1]")
    pka, kind = (4.8, "acid") if len(acid) == 1 and not amine else (None, None)
    if len(amine) == 1 and not acid and p.head in {"amine", "protonated_amine"}:
        n = a.GetAtomWithIdx(amine[0][0])
        pka, kind = (4.6 if any(x.GetIsAromatic() for x in n.GetNeighbors()) else 10.6), "base"
    if not acid and not amine and len(phenol) == 1:
        pka, kind = 10.0, "acid"
    logd = None
    if pka is not None:
        neutral = Chem.Mol(a)
        for atom in neutral.GetAtoms():
            if atom.GetFormalCharge() == -1 and kind == "acid":
                atom.SetFormalCharge(0)
                atom.SetNumExplicitHs(atom.GetNumExplicitHs() + 1)
            elif atom.GetFormalCharge() == 1 and kind == "base" and atom.GetTotalNumHs() > 0:
                atom.SetFormalCharge(0)
                atom.SetNumExplicitHs(max(0, atom.GetTotalNumHs() - 1))
                atom.SetNoImplicit(True)
        try:
            Chem.SanitizeMol(neutral)
            logp_neutral = Crippen.MolLogP(neutral)
            exponent = ph - pka if kind == "acid" else pka - ph
            logd = logp_neutral - math.log10(1 + 10 ** exponent)
        except (ValueError, RuntimeError):
            logd = None
    elif len(acid) <= 1 and len(amine) <= 1 and len(phenol) <= 1 and p.charge == 0 and not any(atom.GetFormalCharge() != 0 for atom in a.GetAtoms()):
        logd = Crippen.MolLogP(a)
    return {"pka": pka, "logd": logd, "kind": kind,
            "note": "pKa por família, não experimental; Henderson–Hasselbalch monoprótico, logP da forma neutra. Não representa especiação completa." if pka is not None else
                    "Sem pKa aplicável a sítio monoprótico suportado; logD indisponível para íons permanentes/polipróticos."}


def esol_estimate(p: StructuralProfile) -> float | None:
    a = p.active
    if any(atom.GetFormalCharge() or atom.GetNumRadicalElectrons() for atom in a.GetAtoms()) or Descriptors.MolWt(a) > 1000:
        return None
    aromatic_proportion = sum(atom.GetIsAromatic() for atom in a.GetAtoms()) / max(1, a.GetNumHeavyAtoms())
    return 0.16 - 0.63 * Crippen.MolLogP(a) - 0.0062 * Descriptors.MolWt(a) + 0.066 * rdMolDescriptors.CalcNumRotatableBonds(a) - 0.74 * aromatic_proportion


def debye_nm(env: dict) -> float | None:
    ionic = float(env.get("ionic_strength_mol_l", 0.01))
    eps = float(env.get("dielectric_constant", 78.5))
    temperature = float(env.get("temperature_k", 298.15))
    if ionic <= 0 or ionic > 0.1:
        return None  # Infinite at I=0; dilute-solution approximation otherwise.
    return math.sqrt(eps * 8.8541878128e-12 * 1.380649e-23 * temperature /
                     (2 * 6.02214076e23 * 1.602176634e-19 ** 2 * 1000 * ionic)) * 1e9


def concentration_mmol_l(value: float, unit: str | None, volume_ml: float, molar_mass: float) -> float:
    token = (unit or "mmol/L").strip().lower().replace("μ", "u").replace("µ", "u").replace(" ", "")
    factors = {"mmol/l": 1, "mm": 1, "mol/l": 1000, "m": 1000, "umol/l": .001,
               "mmol": 1000 / volume_ml, "mol": 1e6 / volume_ml, "umol": 1 / volume_ml,
               "g/l": 1000 / molar_mass, "mg/l": 1 / molar_mass, "g": 1e6 / (molar_mass * volume_ml),
               "mg": 1000 / (molar_mass * volume_ml)}
    if token not in factors:
        raise ValueError(f"Unidade de concentração/quantidade não suportada: {unit}")
    return value * factors[token]
