from __future__ import annotations

import hashlib
import math
from typing import Any
from uuid import uuid4

from app.modules.chemistry.parameters.libraries import (
    AllChem,
    Chem,
    Crippen,
    Descriptors,
    LIBRARIES,
    QED,
    library_snapshot,
    pubchempy,
    rdDepictor,
    rdMolDescriptors,
)
from app.modules.chemistry.parameters.schemas import (
    ChemistryParametersRequest,
    ChemistryParametersResponse,
)

from app.modules.chemistry.parameters.miriam21_engine import (
    miriam21_surfactant_v2,
)

from app.modules.reference_data.electronic_properties import (
    get_electronegativity,
    get_electronic_property_cache_status,
)

DEBYE_PER_E_ANGSTROM = 4.80320427
MAX_3D_ATOMS = 90
MAX_PAIRWISE_INTERACTION_ATOMS = 300




# v33: modo rápido para /chemistry/parameters/analyze.
# O painel individual não deve executar conformer 3D, ETKDG, MMFF ou UFF.
FAST_ANALYZE_MODE = True


def pv(
    value: Any,
    source: str,
    unit: str | None = None,
    confidence: str = "high",
    note: str | None = None,
) -> dict:
    return {
        "value": value,
        "unit": unit,
        "source": source,
        "available": value is not None,
        "confidence": confidence,
        "note": note,
    }


def est(
    value: Any,
    source: str,
    unit: str | None = None,
    note: str | None = None,
) -> dict:
    return pv(value, source, unit, "estimated", note)


def proxy(
    value: Any,
    source: str,
    unit: str | None = None,
    note: str | None = None,
) -> dict:
    return pv(value, source, unit, "proxy", note)


def safe_float(x: Any) -> float | None:
    try:
        v = float(x)
        return None if math.isnan(v) or math.isinf(v) else v
    except Exception:
        return None


def round_or_none(value: float | None, digits: int = 5) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    return round(float(value), digits)


def input_smiles(payload: ChemistryParametersRequest) -> str:
    if payload.smiles and payload.smiles.strip():
        return payload.smiles.strip()

    metadata = (payload.internal_molecule or {}).get("metadata", {})
    smiles = (
        metadata.get("canonical_smiles")
        or metadata.get("smiles_canonico")
        or metadata.get("smiles")
    )

    if smiles:
        return str(smiles).strip()

    raise ValueError("Envie smiles ou internal_molecule.metadata.canonical_smiles.")


def mol_from_payload(payload: ChemistryParametersRequest):
    mol = Chem.MolFromSmiles(input_smiles(payload))

    if mol is None:
        raise ValueError("SMILES inválido para cálculo de parâmetros.")

    Chem.SanitizeMol(mol)
    Chem.AssignStereochemistry(mol, cleanIt=True, force=True)

    return mol


def explicit_h_mol(mol):
    if FAST_ANALYZE_MODE:
        # v33: evita AddHs(addCoords=True) no painel individual.
        return Chem.Mol(mol)

    return Chem.AddHs(Chem.Mol(mol), addCoords=True)

def compute_2d(mol):
    m = Chem.Mol(mol)

    try:
        if rdDepictor is not None:
            rdDepictor.Compute2DCoords(m, canonOrient=True, clearConfs=True)
        else:
            AllChem.Compute2DCoords(m)
    except Exception:
        AllChem.Compute2DCoords(m)

    return m


def positions_2d(mol):
    m = compute_2d(mol)

    if m.GetNumConformers() == 0:
        return {}

    conf = m.GetConformer()

    return {
        a.GetIdx(): {
            "x": float(conf.GetAtomPosition(a.GetIdx()).x),
            "y": float(conf.GetAtomPosition(a.GetIdx()).y),
        }
        for a in m.GetAtoms()
    }


def compute_3d(mol, generate_3d: bool):
    if FAST_ANALYZE_MODE or not generate_3d:
        # v33: cálculo individual rápido; sem ETKDG/MMFF/UFF.
        return None, None, "3D_SKIPPED_FAST_MODE"

    if not generate_3d:
        return None, None, "3D desligado; descritores 3D ficam indisponíveis."

    mol_h = explicit_h_mol(mol)

    if mol_h.GetNumAtoms() > MAX_3D_ATOMS:
        return (
            None,
            None,
            f"3D desligado: {mol_h.GetNumAtoms()} átomos totais acima do limite {MAX_3D_ATOMS}.",
        )

    try:
        params = AllChem.ETKDGv3()
        params.randomSeed = 0xF00D
        r = AllChem.EmbedMolecule(mol_h, params)

        if r != 0:
            r = AllChem.EmbedMolecule(mol_h, randomSeed=0xF00D)

        if r != 0:
            return None, None, "RDKit não conseguiu gerar conformação 3D."

        energy = None

        try:
            props = AllChem.MMFFGetMoleculeProperties(mol_h)
            ff = (
                AllChem.MMFFGetMoleculeForceField(mol_h, props)
                if props is not None
                else AllChem.UFFGetMoleculeForceField(mol_h)
            )

            if ff is not None:
                ff.Minimize(maxIts=350)
                energy = float(ff.CalcEnergy())
        except Exception:
            try:
                ff = AllChem.UFFGetMoleculeForceField(mol_h)
                if ff is not None:
                    ff.Minimize(maxIts=350)
                    energy = float(ff.CalcEnergy())
            except Exception:
                pass

        return mol_h, energy, None
    except Exception as exc:
        return None, None, str(exc)


def positions_3d(m3d, heavy_count):
    if FAST_ANALYZE_MODE or m3d is None or m3d.GetNumConformers() == 0:
        return None

    if m3d is None or m3d.GetNumConformers() == 0:
        return None

    conf = m3d.GetConformer()
    out = {}

    for i in range(min(heavy_count, m3d.GetNumAtoms())):
        p = conf.GetAtomPosition(i)
        out[i] = {"x": float(p.x), "y": float(p.y), "z": float(p.z)}

    return out


def interaction_coords(mol, m3d):
    p3 = positions_3d(m3d, mol.GetNumAtoms())

    if p3 and len(p3) == mol.GetNumAtoms():
        return p3, "3D_RDKit_ETKDG_MMFF_UFF", "Coordenadas 3D RDKit."

    p2 = positions_2d(mol)

    if p2 and len(p2) == mol.GetNumAtoms():
        return (
            {i: {"x": p["x"], "y": p["y"], "z": 0.0} for i, p in p2.items()},
            "2D_RDKit_fallback",
            "Sem 3D seguro; fallback 2D.",
        )

    n = max(mol.GetNumAtoms(), 1)
    r = max(1.5, n * 0.35)

    return (
        {
            a.GetIdx(): {
                "x": r * math.cos(2 * math.pi * a.GetIdx() / n),
                "y": r * math.sin(2 * math.pi * a.GetIdx() / n),
                "z": 0.0,
            }
            for a in mol.GetAtoms()
        },
        "backend_circular_fallback",
        "Fallback circular determinístico.",
    )


def get_charges(mol):
    m = explicit_h_mol(mol)

    try:
        AllChem.ComputeGasteigerCharges(m)
    except Exception:
        return {a.GetIdx(): None for a in mol.GetAtoms()}

    out = {}

    for a in mol.GetAtoms():
        try:
            out[a.GetIdx()] = safe_float(
                m.GetAtomWithIdx(a.GetIdx()).GetProp("_GasteigerCharge")
            )
        except Exception:
            out[a.GetIdx()] = None

    return out


def direct_bonds(mol):
    return {
        tuple(sorted((b.GetBeginAtomIdx(), b.GetEndAtomIdx())))
        for b in mol.GetBonds()
    }


def components(mol):
    out = {}

    for ci, frag in enumerate(Chem.GetMolFrags(mol, asMols=False, sanitizeFrags=False)):
        for ai in frag:
            out[int(ai)] = ci

    return out


def classify_interaction(e):
    if e < -0.005:
        return "atração"
    if e > 0.005:
        return "repulsão"
    return "quase_neutra"


def atom_interactions(mol, m3d, charges, top_k: int = 20):
    if mol.GetNumAtoms() > MAX_PAIRWISE_INTERACTION_ATOMS:
        return {
            a.GetIdx(): est(
                [],
                "backend_safety_limit",
                note="Matriz par-a-par desligada por limite de segurança.",
            )
            for a in mol.GetAtoms()
        }

    pt = Chem.GetPeriodicTable()
    coords, src, note = interaction_coords(mol, m3d)
    bonds = direct_bonds(mol)
    comps = components(mol)
    k = 332.06371
    dielectric = 78.5
    result = {}

    for ai in mol.GetAtoms():
        i = ai.GetIdx()
        pi = coords[i]
        qi = charges.get(i)
        rows = []

        for aj in mol.GetAtoms():
            j = aj.GetIdx()

            if i == j:
                continue

            pj = coords[j]
            qj = charges.get(j)
            dx = pi["x"] - pj["x"]
            dy = pi["y"] - pj["y"]
            dz = pi["z"] - pj["z"]
            d = max(math.sqrt(dx * dx + dy * dy + dz * dz), 0.15)

            coul = k * qi * qj / (dielectric * d) if qi is not None and qj is not None else None
            f_coul = abs(k * qi * qj / (dielectric * d * d)) if qi is not None and qj is not None else None

            try:
                sigma = max(
                    (pt.GetRvdw(ai.GetAtomicNum()) + pt.GetRvdw(aj.GetAtomicNum())) / 2,
                    0.1,
                )
                eps = 0.08
                ratio = sigma / d
                vdw = 4 * eps * (ratio**12 - ratio**6)
                f_vdw = abs(24 * eps * (2 * ratio**12 - ratio**6) / d)
            except Exception:
                vdw = None
                f_vdw = None

            total = (coul or 0) + (vdw or 0)
            key = tuple(sorted((i, j)))

            # Ligações covalentes diretas já aparecem em bond_rows().
            # Aqui retornamos apenas interações não ligadas mais relevantes.
            if key in bonds:
                continue

            rows.append(
                {
                    "atomo_alvo_idx": j,
                    "elemento_alvo": aj.GetSymbol(),
                    "distancia_angstrom": round(d, 5),
                    "carga_origem": round(qi, 6) if qi is not None else None,
                    "carga_alvo": round(qj, 6) if qj is not None else None,
                    "energia_coulomb_kcal_mol": round(coul, 6) if coul is not None else None,
                    "forca_coulomb_aproximada": round(f_coul, 6) if f_coul is not None else None,
                    "energia_vdw_kcal_mol": round(vdw, 6) if vdw is not None else None,
                    "forca_vdw_aproximada": round(f_vdw, 6) if f_vdw is not None else None,
                    "energia_total_kcal_mol": round(total, 6),
                    "tipo_interacao": classify_interaction(total),
                    "mesmo_fragmento": comps.get(i) == comps.get(j),
                    "ligacao_direta": key in bonds,
                    "coordinate_source": src,
                }
            )

        rows.sort(key=lambda x: abs(x["energia_total_kcal_mol"]), reverse=True)
        rows = rows[: max(1, int(top_k))]
        result[i] = est(
            rows,
            "backend_pairwise_Gasteiger_Coulomb_LJ_top_k",
            note=f"Top-k de interações não ligadas. {note}",
        )

    return result


def bond_order(b):
    if b.GetIsAromatic() or b.GetBondType() == Chem.BondType.AROMATIC:
        return 1.5
    return float(b.GetBondTypeAsDouble())


def bond_sum(a):
    return float(sum(bond_order(b) for b in a.GetBonds()))


def lone_pairs(a):
    try:
        ve = Chem.GetPeriodicTable().GetNOuterElecs(a.GetAtomicNum())
    except Exception:
        ve = 0

    return max(0, int(round((ve - bond_sum(a) - a.GetFormalCharge()) / 2)))


def hybrid_detail(a):
    lp = lone_pairs(a)
    sigma = a.GetDegree()
    domains = lp + sigma
    has_double = any(
        b.GetBondType() == Chem.BondType.DOUBLE or b.GetIsAromatic()
        for b in a.GetBonds()
    )
    has_triple = any(b.GetBondType() == Chem.BondType.TRIPLE for b in a.GetBonds())

    if has_triple:
        h, g = "SP", "linear"
    elif has_double or a.GetIsAromatic():
        h, g = "SP2", "trigonal_planar"
    elif domains <= 2:
        h, g = "SP", "linear"
    elif domains == 3:
        h, g = "SP2", "trigonal_planar"
    elif domains == 4:
        h, g = "SP3", "tetraedrica"
    elif domains == 5:
        h, g = "SP3D", "bipiramidal_trigonal"
    else:
        h, g = "SP3D2", "octaedrica"

    return {
        "rdkit": str(a.GetHybridization()),
        "estimada": h,
        "dominios_eletronicos": domains,
        "grau_sigma_aproximado": sigma,
        "pares_livres_estimados": lp,
        "geometria_eletronica": g,
    }


def min_ring_size(mol, idx):
    sizes = [len(r) for r in mol.GetRingInfo().AtomRings() if idx in r]
    return min(sizes) if sizes else None


def fukui_reactivity(a, q, lp):
    q = q or 0.0
    hetero = 1.0 if a.GetAtomicNum() in {7, 8, 15, 16, 9, 17, 35, 53} else 0.35
    aro = 0.15 if a.GetIsAromatic() else 0.0
    fp = max(q, 0) * hetero + aro
    fm = max(-q, 0) * hetero + 0.04 * lp
    f0 = abs(fp - fm) * 0.5

    if fp > fm and fp > 0.05:
        cls = "mais_eletrofilico"
    elif fm > fp and fm > 0.05:
        cls = "mais_nucleofilico"
    else:
        cls = "reatividade_baixa_ou_mista"

    return (
        proxy(
            {
                "f_plus_aproximado": round(fp, 6),
                "f_minus_aproximado": round(fm, 6),
                "f_zero_aproximado": round(f0, 6),
            },
            "Gasteiger_Fukui_proxy",
            note="Fukui real exige N, N+1, N-1 via xTB/DFT.",
        ),
        est(
            {
                "classe": cls,
                "score_nucleofilico": round(fm, 6),
                "score_eletrofilico": round(fp, 6),
                "score_radicalar": round(f0, 6),
            },
            "backend_local_reactivity_proxy",
        ),
    )


def atom_rows(mol, m3d, internal):
    pt = Chem.GetPeriodicTable()
    lookup = {
        int(a.get("rdkit_index", i)): a
        for i, a in enumerate((internal or {}).get("atoms", []))
    }
    p2 = positions_2d(mol)
    p3 = positions_3d(m3d, mol.GetNumAtoms())
    charges = get_charges(mol)
    ints = atom_interactions(mol, m3d, charges)

    mmff = None

    if not FAST_ANALYZE_MODE:
        try:
            mmff_mol = explicit_h_mol(mol)
            mmff = AllChem.MMFFGetMoleculeProperties(mmff_mol)
        except Exception:
            mmff = None

    rows = []

    for a in mol.GetAtoms():
        i = a.GetIdx()
        internal_atom = lookup.get(i, {})

        try:
            mass = (
                pt.GetMassForIsotope(a.GetAtomicNum(), a.GetIsotope())
                if a.GetIsotope()
                else pt.GetMostCommonIsotopeMass(a.GetAtomicNum())
            )
        except Exception:
            mass = a.GetMass()

        lp = lone_pairs(a)
        q = charges.get(i)
        fuk, react = fukui_reactivity(a, q, lp)
        hd = hybrid_detail(a)

        try:
            mmff_type = mmff.GetMMFFAtomType(i) if mmff is not None else None
        except Exception:
            mmff_type = None

        rows.append(
            {
                "id_interno": internal_atom.get("id"),
                "rdkit_idx": i,
                "elemento": a.GetSymbol(),
                "numero_atomico": a.GetAtomicNum(),
                "massa_exata": pv(float(mass), "RDKit PeriodicTable", "u"),
                "is_isotopo": bool(a.GetIsotope()),
                "grau_ligacao_explicito": a.GetDegree(),
                "ordem_ligacao_total": pv(round(bond_sum(a), 4), "RDKit bond order sum"),
                "valencia_total": pv(a.GetTotalValence(), "RDKit Atom.GetTotalValence"),
                "hidrogenios_totais": a.GetTotalNumHs(),
                "hidrogenios_implicitos": a.GetNumImplicitHs(),
                "hidrogenios_explicitos": a.GetNumExplicitHs(),
                "carga_formal": a.GetFormalCharge(),
                "carga_gasteiger": est(q, "RDKit Gasteiger", "e"),
                "carga_quantica_ou_proxy": proxy(
                    q,
                    "Gasteiger_proxy_for_quantum_charge",
                    "e",
                    "Carga quântica real exige xTB/DFT.",
                ),
                "eletrons_radicais": a.GetNumRadicalElectrons(),
                "pares_livres": est(lp, "backend_valence_electron_estimate"),
                "hibridizacao_rdkit": str(a.GetHybridization()),
                "hibridizacao_estimativa": est(hd, "RDKit + backend electron-domain estimate"),
                "geometria_eletronica": est(
                    hd.get("geometria_eletronica"),
                    "backend electron-domain estimate",
                ),
                "is_aromatico": a.GetIsAromatic(),
                "is_no_anel": a.IsInRing(),
                "tamanho_do_anel": min_ring_size(mol, i),
                "chiral_tag": str(a.GetChiralTag()),
                "configuracao_absoluta": pv(a.GetProp("_CIPCode"), "RDKit CIP")
                if a.HasProp("_CIPCode")
                else est(None, "RDKit CIP", note="Sem centro R/S."),
                "posicao_2d": p2.get(i),
                "posicao_3d": est(p3[i], "RDKit ETKDG/MMFF", "Angstrom")
                if p3 and i in p3
                else est(None, "no_3d_position", note="Sem 3D; 2D disponível."),
                "raio_vdw": pv(pt.GetRvdw(a.GetAtomicNum()), "RDKit GetRvdw", "Angstrom"),
                "raio_covalente": pv(
                    pt.GetRcovalent(a.GetAtomicNum()),
                    "RDKit GetRcovalent",
                    "Angstrom",
                ),
                "sasa_local": est(
                    None,
                    "FreeSASA_required",
                    "Angstrom^2",
                    "Valor real por átomo exige FreeSASA.",
                ),
                "tipo_campo_de_forca": pv(mmff_type, "RDKit MMFF atom type")
                if mmff_type is not None
                else est(None, "MMFF_unassigned"),
                "fukui_aproximado": fuk,
                "interacoes_atomicas": ints.get(i),
                "reatividade_local": react,
            }
        )

    return rows


def bond_length(mol, b):
    pt = Chem.GetPeriodicTable()

    try:
        return float(
            pt.GetRcovalent(b.GetBeginAtom().GetAtomicNum())
            + pt.GetRcovalent(b.GetEndAtom().GetAtomicNum())
        )
    except Exception:
        return None


def bond_polarity(b):
    atom_a_number = int(b.GetBeginAtom().GetAtomicNum())
    atom_b_number = int(b.GetEndAtom().GetAtomicNum())

    en_a = get_electronegativity(atom_a_number)
    en_b = get_electronegativity(atom_b_number)
    status = get_electronic_property_cache_status()

    source = (
        f"reference_data.element_electronic_properties"
        f":{status.get('schema') or 'schema_indefinido'}"
    )

    if en_a is None or en_b is None:
        return {
            "delta_eletronegatividade": None,
            "classe": "indefinida",
            "eletronegatividade_atomo_a": en_a,
            "eletronegatividade_atomo_b": en_b,
            "atomic_number_a": atom_a_number,
            "atomic_number_b": atom_b_number,
            "source": source,
            "source_status": status,
            "note": (
                "Eletronegatividade ausente para um dos elementos. "
                "Isso pode ser esperado para gases nobres/superpesados ou indicar "
                "coluna/tabela não encontrada no banco."
            ),
        }

    delta = abs(float(en_a) - float(en_b))

    if delta < 0.4:
        cls = "apolar_ou_pouco_polar"
    elif delta < 1.7:
        cls = "polar"
    else:
        cls = "muito_polar_ou_ionica"

    return {
        "delta_eletronegatividade": round(delta, 4),
        "classe": cls,
        "eletronegatividade_atomo_a": round(float(en_a), 5),
        "eletronegatividade_atomo_b": round(float(en_b), 5),
        "atomic_number_a": atom_a_number,
        "atomic_number_b": atom_b_number,
        "source": source,
        "source_status": status,
    }


def bond_rows(mol, internal):
    lookup = {}

    for b in (internal or {}).get("bonds", []):
        a = b.get("atom_a_rdkit_index")
        c = b.get("atom_b_rdkit_index")

        if a is not None and c is not None:
            lookup[tuple(sorted((int(a), int(c))))] = b

    rows = []

    for b in mol.GetBonds():
        a = b.GetBeginAtomIdx()
        c = b.GetEndAtomIdx()
        ib = lookup.get(tuple(sorted((a, c))), {})
        ideal_length = bond_length(mol, b)

        rows.append(
            {
                "id_interno": ib.get("id"),
                "rdkit_idx": b.GetIdx(),
                "atomo_origem_idx": a,
                "atomo_destino_idx": c,
                "ordem": bond_order(b),
                "tipo_rdkit": str(b.GetBondType()),
                "is_conjugada": b.GetIsConjugated(),
                "is_aromatica": b.GetIsAromatic(),
                "is_no_anel": b.IsInRing(),
                "estereoquimica": str(b.GetStereo()),
                "direcao_visual": ib.get("visual_style") or str(b.GetBondDir()),
                "comprimento_ideal": est(
                    round(ideal_length, 4) if ideal_length is not None else None,
                    "RDKit covalent radii sum",
                    "Angstrom",
                ),
                "polaridade_ligacao": est(
                    bond_polarity(b),
                    "backend electronegativity table",
                ),
            }
        )

    return rows


# =============================================================================
# Bloco micelar removido deste arquivo
# -----------------------------------------------------------------------------
# O calculation_page.py deve atuar apenas como orquestrador:
# - ler payload;
# - calcular descritores RDKit globais;
# - montar átomos/ligações;
# - chamar o motor micelar externo MIRIAM-2.1.
#
# O motor de surfactante/micela fica exclusivamente em:
# app.modules.chemistry.parameters.miriam21_engine
#
# Isso evita regressões por funções antigas de carga global, desalting incompleto,
# HLD/NAC silencioso e aplicação indevida de Klevens/Tanford fora do domínio.
# =============================================================================


def dipole(m3d):
    if FAST_ANALYZE_MODE or m3d is None or m3d.GetNumConformers() == 0:
        return est(None, "3D_SKIPPED_FAST_MODE", "Debye")

    if m3d is None or m3d.GetNumConformers() == 0:
        return est(
            {"x": 0, "y": 0, "z": 0, "magnitude": 0},
            "backend_zero_fallback",
            "Debye",
            "Sem 3D.",
        )

    try:
        AllChem.ComputeGasteigerCharges(m3d)
    except Exception:
        return est(
            {"x": 0, "y": 0, "z": 0, "magnitude": 0},
            "backend_zero_fallback",
            "Debye",
            "Falha no Gasteiger.",
        )

    conf = m3d.GetConformer()
    vec = [0.0, 0.0, 0.0]

    for a in m3d.GetAtoms():
        q = safe_float(a.GetProp("_GasteigerCharge")) if a.HasProp("_GasteigerCharge") else None

        if q is None:
            continue

        p = conf.GetAtomPosition(a.GetIdx())
        vec[0] += q * p.x
        vec[1] += q * p.y
        vec[2] += q * p.z

    v = [x * DEBYE_PER_E_ANGSTROM for x in vec]
    mag = math.sqrt(sum(x * x for x in v))

    return est(
        {"x": round(v[0], 5), "y": round(v[1], 5), "z": round(v[2], 5), "magnitude": round(mag, 5)},
        "Gasteiger charges + RDKit conformer",
        "Debye",
    )


def descriptors_3d(m3d, energy):
    if FAST_ANALYZE_MODE or m3d is None or m3d.GetNumConformers() == 0:
        return {
            "volume_3d": est(None, "3D_SKIPPED_FAST_MODE"),
            "area_superficial_3d": est(None, "3D_SKIPPED_FAST_MODE"),
            "raio_giracao": est(None, "3D_SKIPPED_FAST_MODE"),
            "energia_conformacional": est(None, "3D_SKIPPED_FAST_MODE", "kcal/mol"),
        }

    if m3d is None:
        return {
            "raio_de_giracao": est(None, "no_3d", "Angstrom"),
            "npr1": est(None, "no_3d"),
            "npr2": est(None, "no_3d"),
            "volume_vdw_total": est(None, "no_3d", "Angstrom^3"),
            "sasa_total": est(None, "no_3d", "Angstrom^2"),
            "vetor_momento_dipolo": dipole(None),
            "energia_conformacional": est(None, "no_force_field", "kcal/mol"),
        }

    def td(func, unit=None):
        try:
            return est(round(float(func(m3d)), 5), "RDKit 3D descriptor", unit)
        except Exception as exc:
            return est(None, "RDKit 3D descriptor failed", unit, str(exc))

    try:
        vol = est(round(float(AllChem.ComputeMolVolume(m3d)), 5), "RDKit ComputeMolVolume", "Angstrom^3")
    except Exception as exc:
        vol = est(None, "RDKit volume failed", "Angstrom^3", str(exc))

    try:
        sasa = est(
            round(float(rdMolDescriptors.CalcLabuteASA(m3d)), 5),
            "RDKit LabuteASA",
            "Angstrom^2",
            "FreeSASA dará valor físico melhor.",
        )
    except Exception as exc:
        sasa = est(None, "RDKit LabuteASA failed", "Angstrom^2", str(exc))

    return {
        "raio_de_giracao": td(rdMolDescriptors.CalcRadiusOfGyration, "Angstrom"),
        "npr1": td(rdMolDescriptors.CalcNPR1),
        "npr2": td(rdMolDescriptors.CalcNPR2),
        "volume_vdw_total": vol,
        "sasa_total": sasa,
        "vetor_momento_dipolo": dipole(m3d),
        "energia_conformacional": est(round(energy, 5), "RDKit MMFF94/UFF", "kcal/mol")
        if energy is not None
        else est(None, "RDKit force field", "kcal/mol"),
    }


def orbitals(mol, logp, tpsa, arom, rot):
    hetero = sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() in {7, 8, 15, 16})
    hal = sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() in {9, 17, 35, 53})
    charge = sum(abs(a.GetFormalCharge()) for a in mol.GetAtoms())
    conj = sum(1 for b in mol.GetBonds() if b.GetIsConjugated() or b.GetIsAromatic())
    homo = -7.3 + 0.18 * hetero + 0.15 * arom + 0.05 * max(logp, -2) - 0.12 * hal - 0.25 * charge
    gap = max(1.8, min(8.5, 7.2 - 0.28 * conj - 0.35 * arom - 0.012 * tpsa + 0.02 * rot))
    lumo = homo + gap
    note = "Estimativa heurística. Valor real exige xTB/DFT."

    return {
        "energia_homo": est(round(homo, 4), "backend_frontier_orbital_heuristic", "eV", note),
        "energia_lumo": est(round(lumo, 4), "backend_frontier_orbital_heuristic", "eV", note),
        "gap_homo_lumo": est(round(gap, 4), "backend_frontier_orbital_heuristic", "eV", note),
        "potencial_ionizacao": est(round(abs(homo), 4), "Koopmans-like backend heuristic", "eV", note),
        "afinidade_eletronica": est(round(-lumo, 4), "Koopmans-like backend heuristic", "eV", note),
    }


def heat(mol, mw, exact, logp):
    hetero = sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() not in {1, 6})
    rings = mol.GetRingInfo().NumRings()
    val = -0.18 * exact - 4.5 * hetero + 2 * rings + 1.2 * logp

    return est(
        round(val, 4),
        "backend_group_like_placeholder",
        "kcal/mol",
        "Calor real exige xTB/DFT ou banco experimental.",
    )


def common_name(smiles):
    if pubchempy is None:
        return est(
            f"SMILES:{smiles}",
            "backend_fallback_no_pubchempy",
            note="PubChemPy não instalado. Use banco local/cache.",
        )

    try:
        comps = pubchempy.get_compounds(smiles, namespace="smiles")

        if comps:
            c = comps[0]
            name = c.iupac_name or (c.synonyms[0] if c.synonyms else None)

            if name:
                return pv(name, "PubChemPy", confidence="medium")
    except Exception:
        pass

    return est(f"SMILES:{smiles}", "backend_fallback_pubchem_failed")


def inchi_key(mol):
    try:
        mi = getattr(Chem, "MolToInchi", None)
        mk = getattr(Chem, "MolToInchiKey", None)
        iv = mi(mol) if mi else None
        kv = mk(mol) if mk else None

        return (
            pv(iv, "RDKit InChI") if iv else est(None, "no_inchi_support"),
            pv(kv, "RDKit InChIKey") if kv else est(None, "no_inchi_support"),
        )
    except Exception:
        return est(None, "no_inchi_support"), est(None, "no_inchi_support")


def environment_from_payload(payload: ChemistryParametersRequest) -> dict[str, float]:
    raw = payload.environment or {}

    if hasattr(raw, "model_dump"):
        raw = raw.model_dump()

    if not isinstance(raw, dict):
        raw = {}

    def n(key: str, default: float) -> float:
        try:
            v = float(raw.get(key, default))
            return v if math.isfinite(v) else default
        except Exception:
            return default

    return {
        "temperature_k": max(1.0, n("temperature_k", 298.15)),
        "pressure_atm": max(0.0001, n("pressure_atm", 1.0)),
        "ph": max(0.0, min(14.0, n("ph", 7.0))),
        "ionic_strength_mol_l": max(0.0, n("ionic_strength_mol_l", 0.0)),
        "solvent_polarity_index": max(0.0, min(1.0, n("solvent_polarity_index", 1.0))),
        "dielectric_constant": max(1.0, n("dielectric_constant", 78.5)),
        "agitation_rpm": max(0.0, n("agitation_rpm", 0.0)),
        "volume_ml": max(0.0001, n("volume_ml", 100.0)),
    }


def stable_environment_label(env: dict[str, float]) -> str:
    stable = (
        abs(env["temperature_k"] - 298.15) <= 0.01
        and abs(env["pressure_atm"] - 1) <= 0.01
        and abs(env["ph"] - 7) <= 0.01
        and abs(env["ionic_strength_mol_l"] - 0.0) <= 0.0001
    )

    return "ambiente_estavel_padrao" if stable else "ambiente_ajustado_pelo_usuario"


def has_substructure(mol, smarts: str) -> bool:
    try:
        patt = Chem.MolFromSmarts(smarts)
        return bool(patt is not None and mol.HasSubstructMatch(patt))
    except Exception:
        return False


def ionization_class(mol) -> str:
    if (
        has_substructure(mol, "C(=O)[OX1H0-,OX2H1]")
        or has_substructure(mol, "c[OX2H]")
        or has_substructure(mol, "S(=O)(=O)[OX1-,OX2H1]")
    ):
        return "acid"

    if has_substructure(mol, "[NX3;H2,H1;!$(NC=O)]") or has_substructure(mol, "[nH]"):
        return "base"

    if any(a.GetFormalCharge() != 0 for a in mol.GetAtoms()):
        return "fixed_charge_or_zwitterion"

    return "neutral"


def estimate_pka(mol) -> tuple[float | None, str]:
    if has_substructure(mol, "S(=O)(=O)[OX1-,OX2H1]"):
        return -1.5, "Estimativa por grupo sulfato/sulfonato."

    if has_substructure(mol, "C(=O)[OX1H0-,OX2H1]"):
        return 4.5, "Estimativa por grupo carboxílico."

    if has_substructure(mol, "c[OX2H]"):
        return 10.0, "Estimativa por fenol."

    if has_substructure(mol, "[NX3;H2,H1;!$(NC=O)]"):
        return 9.8, "Estimativa por amina alifática."

    if has_substructure(mol, "[nH]"):
        return 5.2, "Estimativa por heteroaromático protonável."

    if has_substructure(mol, "[NX4+]"):
        return None, "Amônio quaternário: sem pKa ácido/base simples."

    return None, "Nenhum grupo ionizável simples detectado."


def estimate_logd(logp: float, pka: float | None, ph: float, ion_cls: str) -> tuple[float, str]:
    if pka is None or ion_cls in {"neutral", "fixed_charge_or_zwitterion"}:
        return logp, "Sem pKa simples; LogD aproximado como LogP."

    if ion_cls == "acid":
        return logp - math.log10(1.0 + 10 ** (ph - pka)), "Henderson-Hasselbalch aproximado para ácido."

    if ion_cls == "base":
        return logp - math.log10(1.0 + 10 ** (pka - ph)), "Henderson-Hasselbalch aproximado para base."

    return logp, "LogD aproximado como LogP."


def aromatic_ratio(mol) -> float:
    heavy = [a for a in mol.GetAtoms() if a.GetAtomicNum() > 1]
    return 0.0 if not heavy else len([a for a in heavy if a.GetIsAromatic()]) / len(heavy)


def estimate_logs(mw: float, logp: float, rot: float, arom: float) -> float:
    return 0.16 - 0.63 * logp - 0.0062 * mw + 0.066 * rot - 0.74 * arom


def wiener_index(mol) -> float | None:
    """
    Índice de Wiener robusto para moléculas com fragmentos desconectados.

    RDKit usa distâncias muito grandes entre fragmentos desconectados. Se somarmos
    a matriz inteira em sais como SDS.Na, PFOS.K ou Gemini dibrometo, o índice
    explode artificialmente. Por isso, somamos apenas pares dentro do mesmo
    fragmento conectado.
    """
    try:
        dmat = Chem.GetDistanceMatrix(mol)
        total = 0.0

        fragments = Chem.GetMolFrags(mol, asMols=False, sanitizeFrags=False)
        for frag in fragments:
            atoms = [int(i) for i in frag]
            for pos_i, i in enumerate(atoms):
                for j in atoms[pos_i + 1:]:
                    dij = float(dmat[i, j])
                    if math.isfinite(dij) and dij < 1e7:
                        total += dij

        return total
    except Exception:
        return None


def randic_index(mol) -> float | None:
    try:
        total = 0.0

        for b in mol.GetBonds():
            da = max(b.GetBeginAtom().GetDegree(), 1)
            db = max(b.GetEndAtom().GetDegree(), 1)
            total += 1.0 / math.sqrt(da * db)

        return total
    except Exception:
        return None


def dynamic_density(mw: float, logp: float, tpsa: float, env: dict[str, float]) -> float:
    v = 0.72 + 0.0008 * min(mw, 650) + 0.002 * min(tpsa, 140) - 0.015 * max(logp, 0)
    v *= 1.0 - (env["temperature_k"] - 298.15) * 0.00075
    return max(0.55, min(1.85, v))


def dynamic_boiling_point(mw: float, logp: float, tpsa: float, env: dict[str, float]) -> float:
    v = 70.0 + 0.82 * mw + 5.5 * max(logp, 0) + 0.22 * tpsa + 18.0 * math.log10(max(env["pressure_atm"], 0.0001))
    return max(-80.0, min(650.0, v))


def dynamic_melting_point(mw: float, rings: int, hbd: int) -> float:
    return max(-180.0, min(420.0, -65.0 + 0.42 * mw + 18.0 * rings + 12.0 * hbd))


def dynamic_vapor_pressure(bp_c: float, env: dict[str, float]) -> float:
    temp_c = env["temperature_k"] - 273.15
    return max(1e-8, min(10.0, math.exp((temp_c - bp_c) / 38.0)))


def dynamic_surface_tension(logp: float, tpsa: float, env: dict[str, float]) -> float:
    v = (28.0 + 0.055 * tpsa + 1.8 * max(logp, 0)) * (1.0 - (env["temperature_k"] - 298.15) * 0.0016)
    v *= 0.92 + 0.08 * env["solvent_polarity_index"]
    return max(8.0, min(85.0, v))


def dynamic_viscosity(mw: float, logp: float, env: dict[str, float]) -> float:
    v = (0.45 + 0.0042 * mw + 0.12 * max(logp, 0)) * math.exp((298.15 - env["temperature_k"]) / 55.0)
    v *= 1.0 + min(env["ionic_strength_mol_l"], 2.0) * 0.15
    return max(0.05, min(200.0, v))


def gibbs_solvation_estimate(logs: float, logp: float, env: dict[str, float]) -> float:
    return -1.36 * logs - 0.65 * max(logp, 0) - 0.8 * env["solvent_polarity_index"]


def cmc_environment_factor(base_cmc: float | None, env: dict[str, float], charged: bool) -> float | None:
    if base_cmc is None:
        return None

    temp_factor = max(0.25, min(2.5, 1.0 + (env["temperature_k"] - 298.15) * 0.012))
    salt_factor = max(0.38, min(1.0, 1.0 - env["ionic_strength_mol_l"] * 1.6)) if charged else 1.0
    agitation_factor = 1.0 + min(env["agitation_rpm"], 2500.0) / 25000.0

    return max(0.0001, base_cmc * temp_factor * salt_factor * agitation_factor)


def parameter_value_number(parameter: Any) -> float | None:
    if isinstance(parameter, dict):
        return safe_float(parameter.get("value"))

    return safe_float(parameter)


MICELLAR_OUTPUT_KEYS = [
    "is_surfactante",
    "classe_surfactante",
    "tipo_cabeca_polar",
    "tipo_carga_surfactante",
    "carga_formal_surfactante",
    "indice_anfifilico",
    "comprimento_cauda",
    "comprimento_cauda_efetivo",
    "numero_caudas_hidrofobicas",
    "volume_cauda",
    "comprimento_maximo_cauda",
    "area_cabeca_micela",
    "area_cabeca_ideal",
    "area_cabeca_efetiva",
    "hlb_griffin",
    "hlb_davies",
    "hlb_estimado",
    "hlb_engine_bruto",
    "cmc_klevens_mol_l",
    "cmc_klevens_mmol_l",
    "cmc_corrigida_mol_l",
    "cmc_corrigida_mmol_l",
    "cmc_estimada",
    "cmc_ambiente_estimada",
    "x_cmc",
    "delta_g_micelizacao",
    "parametro_empacotamento",
    "cpp",
    "cpp_ideal",
    "comportamento_micelar_previsto",
    "hld",
    "nac",
    "parametros_micela",
    "numero_agregacao_estimado",
    "raio_micela_esferica",
    "raio_nucleo_hidrofobico",
    "faixa_raio_micela",
    "raio_micela_cilindrica",
    "carga_residual_micela",
    "contraions_ligados_micela",
    "densidade_carga_superficial",
    "perfil_calibracao_literatura",
    "confianca_cmc",
    "diagnostico_cauda",
    "miriam2_identity",
    "miriam2_calculation_plan",
    "miriam2_physical_validation",
    "miriam2_applicability",
    "miriam2_audit",
    "miriam2_structural_features",
]


def safe_miriam21_surfactant(mol, mw: float, logp: float, tpsa: float, env: dict[str, float]) -> dict[str, dict]:
    """
    Chama o motor MIRIAM-2.1 sem deixar o endpoint cair.

    O cálculo micelar é cientificamente importante, mas não deve derrubar a
    resposta inteira de parâmetros moleculares quando houver uma exceção no
    roteamento. Em caso de falha, retornamos os mesmos campos esperados pelo
    frontend como indisponíveis e registramos a falha na auditoria MIRIAM.
    """
    try:
        result = miriam21_surfactant_v2(
            mol=mol,
            mw=mw,
            logp=logp,
            tpsa=tpsa,
            env=env,
        )

        if not isinstance(result, dict):
            raise TypeError(
                "miriam21_surfactant_v2 deve retornar dict, "
                f"mas retornou {type(result).__name__}."
            )

        # Garante compatibilidade com frontend/schema mesmo se o engine omitir
        # algum campo em rotas bloqueadas.
        normalized = dict(result)
        for key in MICELLAR_OUTPUT_KEYS:
            normalized.setdefault(
                key,
                est(
                    None,
                    "MIRIAM-2.1 external engine",
                    note=f"Campo {key} não foi retornado pelo motor MIRIAM.",
                ),
            )

        return normalized

    except Exception as exc:
        error_message = f"{type(exc).__name__}: {exc}"

        unavailable = {
            key: est(
                None,
                "MIRIAM-2.1 external engine failed",
                note=error_message,
            )
            for key in MICELLAR_OUTPUT_KEYS
        }

        unavailable.update(
            {
                "is_surfactante": est(
                    False,
                    "MIRIAM-2.1 external engine failed",
                    note="Cálculo micelar bloqueado porque o motor MIRIAM falhou.",
                ),
                "miriam2_identity": est(
                    {
                        "packageVersion": "MIRIAM-2.1",
                        "error": error_message,
                    },
                    "MIRIAM-2.1 identification package",
                    note="Falha durante identificação/roteamento.",
                ),
                "miriam2_calculation_plan": est(
                    [],
                    "MIRIAM-2.1 parameter calculation plan",
                    note="Plano de cálculo indisponível porque o MIRIAM falhou.",
                ),
                "miriam2_physical_validation": est(
                    {
                        "passed": False,
                        "errors": [error_message],
                        "warnings": [],
                        "blockedCalculations": ["ALL_MICELLAR_PARAMETERS"],
                        "correctedRoutes": [],
                    },
                    "MIRIAM-2.1 physical validation",
                ),
                "miriam2_applicability": est(
                    {
                        "applicable": False,
                        "blockingIssues": [error_message],
                    },
                    "MIRIAM-2.1 applicability domain",
                ),
                "miriam2_audit": est(
                    {
                        "warnings": [],
                        "blockedCalculations": ["ALL_MICELLAR_PARAMETERS"],
                        "confidencePenalties": ["MIRIAM_ENGINE_EXCEPTION"],
                        "recommendedNextModel": "FIX_MIRIAM_ENGINE",
                        "miriamVersion": "MIRIAM-2.1",
                        "error": error_message,
                    },
                    "MIRIAM-2.1 audit",
                ),
            }
        )

        return unavailable


def dynamic_extra_fields(mol, mw: float, logp: float, tpsa: float, hbd: int, rot: int, rings: int, payload: ChemistryParametersRequest) -> dict[str, dict]:
    env = environment_from_payload(payload)
    pka, pka_note = estimate_pka(mol)
    logd, logd_note = estimate_logd(logp, pka, env["ph"], ionization_class(mol))
    logs = estimate_logs(mw, logp, rot, aromatic_ratio(mol))
    bp = dynamic_boiling_point(mw, logp, tpsa, env)
    wi = wiener_index(mol)
    ri = randic_index(mol)

    return {
        "ambiente_fisico_quimico": pv(
            {**env, "estado": stable_environment_label(env)},
            "frontend_mixture_environment",
            note="Condições usadas para estimativas dinâmicas.",
        ),
        "logd": est(round(logd, 5), "backend_Henderson_Hasselbalch_estimator", note=logd_note),
        "pka": est(round(pka, 5) if pka is not None else None, "backend_SMARTS_pKa_estimator", note=pka_note),
        "logs": est(round(logs, 5), "backend_ESOL_simplified_estimator", note="Estimativa de solubilidade aquosa LogS."),
        "densidade": est(round(dynamic_density(mw, logp, tpsa, env), 5), "backend_environment_density_estimator", "g/cm^3"),
        "ponto_fusao": est(round(dynamic_melting_point(mw, rings, hbd), 5), "backend_melting_point_estimator", "°C"),
        "ponto_ebulicao": est(round(bp, 5), "backend_boiling_point_estimator", "°C"),
        "pressao_vapor": est(round(dynamic_vapor_pressure(bp, env), 8), "backend_vapor_pressure_estimator", "atm"),
        "tensao_superficial": est(round(dynamic_surface_tension(logp, tpsa, env), 5), "backend_surface_tension_estimator", "mN/m"),
        "viscosidade": est(round(dynamic_viscosity(mw, logp, env), 5), "backend_viscosity_estimator", "cP"),
        "energia_livre_gibbs_solvacao": est(round(gibbs_solvation_estimate(logs, logp, env), 5), "backend_solvation_free_energy_proxy", "kcal/mol"),
        "indice_wiener": pv(round(wi, 5), "RDKit molecular graph distance matrix") if wi is not None else est(None, "RDKit Wiener index failed"),
        "indice_randic": pv(round(ri, 5), "RDKit molecular graph connectivity") if ri is not None else est(None, "RDKit Randic index failed"),
    }


def molecule_row(mol, payload, m3d, energy):
    mol_h = explicit_h_mol(mol)

    can = Chem.MolToSmiles(mol, canonical=True, isomericSmiles=False)
    iso = Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)
    h = hashlib.sha256(iso.encode()).hexdigest()
    formula = rdMolDescriptors.CalcMolFormula(mol_h)
    mw = float(Descriptors.MolWt(mol))
    exact = float(Descriptors.ExactMolWt(mol))
    logp = float(Crippen.MolLogP(mol))
    tpsa = float(rdMolDescriptors.CalcTPSA(mol))
    hbd = int(rdMolDescriptors.CalcNumHBD(mol))
    hba = int(rdMolDescriptors.CalcNumHBA(mol))
    rot = int(rdMolDescriptors.CalcNumRotatableBonds(mol))
    rings = int(mol.GetRingInfo().NumRings())

    try:
        arom = int(rdMolDescriptors.CalcNumAromaticRings(mol))
    except Exception:
        arom = 0

    try:
        csp3 = float(rdMolDescriptors.CalcFractionCSP3(mol))
    except Exception:
        csp3 = 0.0

    try:
        qed = float(QED.qed(mol))
    except Exception:
        qed = None

    try:
        bertz = float(Descriptors.BertzCT(mol))
    except Exception:
        bertz = None

    try:
        mr = float(Crippen.MolMR(mol))
    except Exception:
        mr = None

    inc, ik = inchi_key(mol)
    env = environment_from_payload(payload)
    miriam_result = safe_miriam21_surfactant(
        mol=mol,
        mw=mw,
        logp=logp,
        tpsa=tpsa,
        env=env,
    )

    row = {
        "id_snapshot": str(uuid4()),
        "hash_estrutural": h,
        "smiles_canonico": can,
        "smiles_isomerico": iso,
        "inchi": inc,
        "inchikey": ik,
        "nome_comum": common_name(can),
        "formula_molecular": formula,
        "peso_molecular": mw,
        "massa_exata": exact,

        # CORREÇÃO PRINCIPAL:
        # total_atomos e total_ligacoes agora contam H explícito.
        "total_atomos": mol_h.GetNumAtoms(),
        "total_ligacoes": mol_h.GetNumBonds(),

        # Mantém os pesados separados.
        "total_atomos_pesados": mol.GetNumHeavyAtoms(),
        "total_ligacoes_pesadas": mol.GetNumBonds(),

        # Aliases úteis para frontends diferentes.
        "atom_count_total": mol_h.GetNumAtoms(),
        "bond_count_total": mol_h.GetNumBonds(),
        "heavy_atom_count": mol.GetNumHeavyAtoms(),
        "heavy_bond_count": mol.GetNumBonds(),

        "carga_formal_total": sum(a.GetFormalCharge() for a in mol.GetAtoms()),
        "logp": pv(round(logp, 5), "RDKit Crippen.MolLogP"),
        "tpsa": pv(round(tpsa, 5), "RDKit CalcTPSA", "Angstrom^2"),
        "hbd": pv(hbd, "RDKit CalcNumHBD"),
        "hba": pv(hba, "RDKit CalcNumHBA"),
        "rotatable_bonds": pv(rot, "RDKit CalcNumRotatableBonds"),
        "total_aneis": pv(rings, "RDKit RingInfo.NumRings"),
        "aneis_aromaticos": pv(arom, "RDKit CalcNumAromaticRings"),
        "fracao_csp3": pv(round(csp3, 5), "RDKit CalcFractionCSP3"),
        "qed": pv(round(qed, 6), "RDKit QED") if qed is not None else est(None, "RDKit QED failed"),
        "complexidade_bertz": pv(round(bertz, 5), "RDKit BertzCT") if bertz is not None else est(None, "RDKit BertzCT failed"),
        "refratividade_molar": pv(round(mr, 5), "RDKit Crippen.MolMR") if mr is not None else est(None, "RDKit MolMR failed"),
        **miriam_result,
        **descriptors_3d(m3d, energy),
        **orbitals(mol, logp, tpsa, arom, rot),
        "calor_de_formacao": heat(mol, mw, exact, logp),
        "geometry3DStatus": pv(
            {
                "generated": m3d is not None,
                "usedForMicelleCalculation": False,
                "reason": "MIRIAM-2.1 usa grafo 2D/fragmentação/rotas físico-químicas; 3D RDKit é descritor auxiliar.",
            },
            "backend_orchestration_policy",
        ),
        "biblioteca_status": library_snapshot(),
        "element_electronic_properties_status": pv(
            get_electronic_property_cache_status(),
            "reference_data.element_electronic_properties",
            note="Status da fonte usada para eletronegatividade e polaridade de ligação.",
        ),
        **dynamic_extra_fields(mol, mw, logp, tpsa, hbd, rot, rings, payload),
    }

    return row


def analyze_single_molecule_parameters(payload: ChemistryParametersRequest) -> dict[str, Any]:
    mol = mol_from_payload(payload)
    m3d, energy, w3d = compute_3d(mol, payload.generate_3d)
    molecule = molecule_row(mol, payload, m3d, energy)
    atoms = atom_rows(mol, m3d, payload.internal_molecule)
    bonds = bond_rows(mol, payload.internal_molecule)

    warnings = []

    if w3d:
        warnings.append(w3d)

    if not LIBRARIES["xtb"].installed:
        warnings.append("xTB não instalado: HOMO/LUMO, Fukui e cargas quânticas reais foram preenchidos por estimativas/proxies.")

    if not LIBRARIES["freesasa"].installed:
        warnings.append("FreeSASA não instalado: SASA local e área de cabeça micelar usam estimativas.")

    if not LIBRARIES["openmm"].installed:
        warnings.append("OpenMM não instalado: forças são aproximações Gasteiger+Coulomb+VDW, não dinâmica molecular.")

    if not LIBRARIES["pubchempy"].installed:
        warnings.append("PubChemPy não instalado: nome comum usa fallback local.")

    electronic_status = get_electronic_property_cache_status()
    if not electronic_status.get("table_found"):
        warnings.append(
            "Tabela element_electronic_properties não encontrada pelo backend; "
            "polaridade de ligação usa fallback local mínimo."
        )
    elif not electronic_status.get("electronegativity_column"):
        warnings.append(
            "Tabela element_electronic_properties encontrada, mas nenhuma coluna de eletronegatividade compatível foi identificada."
        )

    limitations = [
        "A molécula isolada agora separa total com H explícito de átomos/ligações pesadas.",
        "Todos os campos ficam preenchidos quando há suporte RDKit; alguns são estimativas/proxies quando biblioteca pesada não está integrada.",
        "CMC/HLB/CPP/Nagg/raio são roteados pelo MIRIAM-2.1 externo; perfis calibrados de literatura têm prioridade sobre Klevens/Davies quando disponíveis.",
        "Forças átomo-átomo são qualitativas para uma molécula; força real dinâmica deve usar OpenMM depois.",
        "Eletronegatividade e polaridade de ligação usam reference_data.element_electronic_properties quando a tabela/colunas existem; fallback local mínimo só evita quebra do cálculo.",
    ]

    snap = {"molecule": molecule, "atoms": atoms, "bonds": bonds}

    resp = {
        "success": True,
        "package_version": "single-molecule-parameters-v7-orchestrated-miriam21",
        "source": "RDKit + explicit hydrogen accounting + MIRIAM-2.1 external micellar engine",
        "molecule": molecule,
        "atoms": atoms,
        "bonds": bonds,
        "warnings": warnings,
        "limitations": limitations,
        "snapshot_dados_completos": snap,
    }

    ChemistryParametersResponse.model_validate(resp)

    return resp
# =============================================================================
# FIM DO calculation_page.py
# -----------------------------------------------------------------------------
# Não há alias global `surfactant = ...` aqui.
# A função molecule_row(...) chama miriam21_surfactant_v2(...) diretamente.
# =============================================================================


# ============================================================================
# v35 FAST OVERRIDE
# ============================================================================
# Este bloco substitui a função pesada analyze_single_molecule_parameters()
# definida acima. Em Python, a última definição com o mesmo nome prevalece.
#
# Objetivo:
# - impedir que o painel "Molécula individual" fique preso em cálculo 3D;
# - não chamar ETKDG/MMFF/UFF/conformer;
# - não chamar PubChem online;
# - não chamar MIRIAM completo no painel individual;
# - retornar um pacote compatível com o frontend usando descritores 2D rápidos.
# ============================================================================


def _fast_param(value, source="v35_fast_2d", unit=None, confidence="estimated", note=None):
    return {
        "value": value,
        "unit": unit,
        "source": source,
        "available": value is not None,
        "confidence": confidence,
        "note": note,
    }


def _fast_none(source="v35_fast_2d", unit=None, note="Campo não calculado no modo rápido."):
    return _fast_param(None, source, unit, "estimated", note)


def _fast_round(value, digits=5):
    try:
        if value is None:
            return None
        value = float(value)
        if not math.isfinite(value):
            return None
        return round(value, digits)
    except Exception:
        return None


def _fast_compute_2d_positions(mol):
    try:
        m = Chem.Mol(mol)

        try:
            if rdDepictor is not None:
                rdDepictor.Compute2DCoords(m, canonOrient=True, clearConfs=True)
            else:
                AllChem.Compute2DCoords(m)
        except Exception:
            AllChem.Compute2DCoords(m)

        if m.GetNumConformers() == 0:
            return {}

        conf = m.GetConformer()

        return {
            atom.GetIdx(): {
                "x": float(conf.GetAtomPosition(atom.GetIdx()).x),
                "y": float(conf.GetAtomPosition(atom.GetIdx()).y),
            }
            for atom in m.GetAtoms()
        }
    except Exception:
        return {}


def _fast_ring_size_for_atom(mol, atom_idx: int):
    try:
        rings = mol.GetRingInfo().AtomRings()
        sizes = [len(ring) for ring in rings if atom_idx in ring]
        return min(sizes) if sizes else None
    except Exception:
        return None


def _fast_lone_pairs(atom):
    symbol = atom.GetSymbol()
    degree = atom.GetTotalDegree()
    charge = atom.GetFormalCharge()

    if symbol == "O":
        return max(0, 2 - max(degree - 1, 0) - max(charge, 0))
    if symbol == "N":
        return 0 if degree >= 4 else 1
    if symbol in {"F", "Cl", "Br", "I"}:
        return 3
    if symbol == "S":
        return 2
    if symbol == "P":
        return 1 if degree <= 3 else 0

    return 0


def _fast_tail_carbon_count(mol):
    carbon_indices = {a.GetIdx() for a in mol.GetAtoms() if a.GetSymbol() == "C"}

    if not carbon_indices:
        return 0

    adjacency = {idx: set() for idx in carbon_indices}

    for bond in mol.GetBonds():
        a = bond.GetBeginAtomIdx()
        b = bond.GetEndAtomIdx()

        if a in carbon_indices and b in carbon_indices:
            adjacency[a].add(b)
            adjacency[b].add(a)

    visited = set()
    best = 0

    for start in carbon_indices:
        if start in visited:
            continue

        stack = [start]
        visited.add(start)
        count = 0

        while stack:
            node = stack.pop()
            count += 1

            for nxt in adjacency.get(node, ()):
                if nxt not in visited:
                    visited.add(nxt)
                    stack.append(nxt)

        best = max(best, count)

    return best


def _fast_surfactant_estimates(mol, logp, tpsa, mw):
    tail_c = _fast_tail_carbon_count(mol)
    hetero = sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() in {7, 8, 15, 16})
    formal_charge = sum(a.GetFormalCharge() for a in mol.GetAtoms())
    is_surf = bool(tail_c >= 8 and (hetero > 0 or abs(formal_charge) > 0 or tpsa >= 20))

    if formal_charge < 0:
        sclass = "aniônico"
    elif formal_charge > 0:
        sclass = "catiônico"
    elif is_surf:
        sclass = "não iônico/provável"
    else:
        sclass = "não surfactante/provável"

    hlb = None
    if is_surf:
        hlb = max(1.0, min(20.0, 7.0 + 0.10 * tpsa - 0.65 * max(logp, 0)))

    cpp = None
    if is_surf:
        cpp = max(0.12, min(1.25, 0.18 + 0.028 * min(tail_c, 24) - 0.015 * max((hlb or 10) - 10, 0)))

    cmc_mmol_l = None
    if is_surf:
        cmc_mmol_l = max(0.02, min(120.0, 250.0 * (10 ** (-0.16 * max(tail_c, 1)))))

    comportamento = None
    if cpp is not None:
        if cpp < 0.33:
            comportamento = "tendência a micela esférica"
        elif cpp < 0.50:
            comportamento = "tendência a micela cilíndrica"
        elif cpp < 1.00:
            comportamento = "tendência a bicamada/lamelar"
        else:
            comportamento = "tendência a micela inversa"

    return {
        "is_surfactante": is_surf,
        "classe": sclass,
        "tail_c": tail_c,
        "hlb": hlb,
        "cpp": cpp,
        "cmc_mmol_l": cmc_mmol_l,
        "comportamento": comportamento,
    }


def _fast_orbitals(mol, logp, tpsa, arom, rot):
    hetero = sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() in {7, 8, 15, 16})
    hal = sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() in {9, 17, 35, 53})
    charge = sum(abs(a.GetFormalCharge()) for a in mol.GetAtoms())
    conj = sum(1 for b in mol.GetBonds() if b.GetIsConjugated() or b.GetIsAromatic())

    homo = -7.3 + 0.18 * hetero + 0.15 * arom + 0.05 * max(logp, -2) - 0.12 * hal - 0.25 * charge
    gap = max(1.8, min(8.5, 7.2 - 0.28 * conj - 0.35 * arom - 0.012 * tpsa + 0.02 * rot))
    lumo = homo + gap

    return homo, lumo, gap


def _fast_bond_polarity(atom_a, atom_b):
    try:
        ea = get_electronegativity(atom_a.GetSymbol())
        eb = get_electronegativity(atom_b.GetSymbol())

        if ea is None or eb is None:
            return _fast_none("v35_fast_electronegativity")

        delta = abs(float(ea) - float(eb))
        if delta < 0.4:
            kind = "apolar/fraca"
        elif delta < 1.7:
            kind = "polar"
        else:
            kind = "muito polar/iônica"

        return _fast_param(
            {"delta_eletronegatividade": round(delta, 4), "classe": kind},
            "v35_fast_electronegativity",
        )
    except Exception:
        return _fast_none("v35_fast_electronegativity")


def analyze_single_molecule_parameters(payload: ChemistryParametersRequest) -> dict[str, Any]:
    from app.modules.chemistry.parameters.router import make_response
    return make_response(payload)
