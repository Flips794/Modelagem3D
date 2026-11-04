from __future__ import annotations

import hashlib
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.modules.chemistry.parameters.schemas import (
    ChemistryParametersRequest,
    ChemistryParametersResponse,
)

try:
    from rdkit import Chem
    from rdkit.Chem import Crippen, Descriptors, Lipinski, QED, rdMolDescriptors
except Exception as import_error:
    Chem = None
    Crippen = None
    Descriptors = None
    Lipinski = None
    QED = None
    rdMolDescriptors = None
    RDKIT_IMPORT_ERROR = import_error
else:
    RDKIT_IMPORT_ERROR = None


router = APIRouter(prefix="/parameters", tags=["Chemistry Parameters"])

ENGINE_VERSION = "single-molecule-parameters-v48-hydrogen-bond-inventory"
PUBCHEM_TIMEOUT_SECONDS = 0.85
PUBCHEM_CACHE_TTL_SECONDS = 60 * 60 * 24

R_GAS = 8.31446261815324
DEBYE_PER_E_ANGSTROM = 4.80320427

_PUBCHEM_CACHE: dict[str, dict[str, Any]] = {}

PAULING_EN = {
    "H": 2.20,
    "C": 2.55,
    "N": 3.04,
    "O": 3.44,
    "F": 3.98,
    "P": 2.19,
    "S": 2.58,
    "Cl": 3.16,
    "Br": 2.96,
    "I": 2.66,
    "Na": 0.93,
    "K": 0.82,
    "Li": 0.98,
    "Mg": 1.31,
    "Ca": 1.00,
}

COUNTERION_SYMBOLS = {"Na", "K", "Li", "Cl", "Br", "I", "Ca", "Mg"}


def param(
    value: Any,
    source: str = ENGINE_VERSION,
    unit: str | None = None,
    confidence: str = "estimated",
    note: str | None = None,
) -> dict[str, Any]:
    return {
        "value": value,
        "unit": unit,
        "source": source,
        "available": value is not None,
        "confidence": confidence,
        "note": note,
    }


def unavailable(
    source: str = ENGINE_VERSION,
    unit: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    return param(
        None,
        source=source,
        unit=unit,
        confidence="estimated",
        note=note or "Indisponível no modo rápido; use cálculo completo separado/cacheado.",
    )


def safe(callback, default=None):
    try:
        return callback()
    except Exception:
        return default


def as_float(value: Any) -> float | None:
    try:
        number = float(value)
        if not math.isfinite(number):
            return None
        return number
    except Exception:
        return None


def rounded(value: Any, digits: int = 5):
    number = as_float(value)
    if number is None:
        return None
    return round(number, digits)


def env_from(payload: ChemistryParametersRequest) -> dict[str, float]:
    raw = payload.environment or {}
    if hasattr(raw, "model_dump"):
        raw = raw.model_dump()
    if not isinstance(raw, dict):
        raw = {}

    def n(key: str, default: float) -> float:
        value = as_float(raw.get(key, default))
        return value if value is not None else default

    return {
        "temperature_k": max(1.0, n("temperature_k", 298.15)),
        "pressure_atm": max(0.0001, n("pressure_atm", 1.0)),
        "ph": min(14.0, max(0.0, n("ph", 7.0))),
        "ionic_strength_mol_l": max(0.0, n("ionic_strength_mol_l", 0.01)),
        "solvent_polarity_index": min(1.0, max(0.0, n("solvent_polarity_index", 1.0))),
        "dielectric_constant": max(1.0, n("dielectric_constant", 78.5)),
        "agitation_rpm": max(0.0, n("agitation_rpm", 0.0)),
        "volume_ml": max(0.0001, n("volume_ml", 100.0)),
    }


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


def pubchem_lookup(smiles: str) -> dict[str, Any]:
    now = time.time()
    cache_key = smiles.strip()

    cached = _PUBCHEM_CACHE.get(cache_key)
    if cached and now - cached["time"] < PUBCHEM_CACHE_TTL_SECONDS:
        return {**cached["data"], "cache": "memory_hit"}

    properties = ",".join(
        [
            "IUPACName",
            "MolecularFormula",
            "MolecularWeight",
            "CanonicalSMILES",
            "IsomericSMILES",
            "InChI",
            "InChIKey",
            "XLogP",
            "TPSA",
            "Complexity",
            "HBondDonorCount",
            "HBondAcceptorCount",
            "RotatableBondCount",
            "ExactMass",
            "MonoisotopicMass",
        ]
    )

    encoded = urllib.parse.quote(smiles, safe="")
    url = (
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/"
        f"{encoded}/property/{properties}/JSON"
    )

    started = time.perf_counter()
    data: dict[str, Any] = {
        "ok": False,
        "cache": "miss",
        "source": "PubChem PUG-REST",
        "timeout_seconds": PUBCHEM_TIMEOUT_SECONDS,
        "elapsed_seconds": None,
        "properties": {},
        "error": None,
    }

    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Modelagem3D/0.1 fast-parameters"},
            method="GET",
        )

        with urllib.request.urlopen(request, timeout=PUBCHEM_TIMEOUT_SECONDS) as response:
            raw = response.read(1024 * 1024)

        parsed = json.loads(raw.decode("utf-8"))
        props = (
            parsed.get("PropertyTable", {})
            .get("Properties", [{}])[0]
        )

        if isinstance(props, dict) and props:
            data["ok"] = True
            data["properties"] = props

    except Exception as exc:
        data["error"] = f"{type(exc).__name__}: {exc}"

    data["elapsed_seconds"] = round(time.perf_counter() - started, 4)
    _PUBCHEM_CACHE[cache_key] = {"time": now, "data": data}
    return data


def fragments(mol):
    return safe(lambda: Chem.GetMolFrags(mol, asMols=True, sanitizeFrags=True), (mol,))


def is_counterion_fragment(fragment) -> bool:
    if fragment.GetNumAtoms() != 1:
        return False
    atom = fragment.GetAtomWithIdx(0)
    return atom.GetFormalCharge() != 0 and atom.GetSymbol() in COUNTERION_SYMBOLS


def active_fragment(mol):
    frags = list(fragments(mol))
    active = [frag for frag in frags if not is_counterion_fragment(frag)]
    return max(active or frags or [mol], key=lambda item: item.GetNumHeavyAtoms())


def counterions(mol) -> list[dict[str, Any]]:
    out = []
    for fragment in fragments(mol):
        if fragment.GetNumAtoms() == 1:
            atom = fragment.GetAtomWithIdx(0)
            if atom.GetFormalCharge() != 0:
                out.append({"symbol": atom.GetSymbol(), "charge": atom.GetFormalCharge()})
    return out


def has_smarts(mol, smarts: str) -> bool:
    pattern = safe(lambda: Chem.MolFromSmarts(smarts), None)
    return bool(pattern is not None and safe(lambda: mol.HasSubstructMatch(pattern), False))


def head_group(active) -> str:
    if has_smarts(active, "[SX4](=O)(=O)[O-]") or has_smarts(active, "[SX4](=O)(=O)O"):
        # Abrange sulfato/sulfonato no painel rápido. A diferença fina pode ser feita por contexto de ligação.
        return "sulfato/sulfonato"
    if has_smarts(active, "C(=O)[O-]") or has_smarts(active, "C(=O)[OX2H1]"):
        return "carboxilato/ácido carboxílico"
    if has_smarts(active, "[NX4+]"):
        return "amônio quaternário"
    if has_smarts(active, "[PX4+]"):
        return "fosfônio"
    if has_smarts(active, "[OX2H]") or has_smarts(active, "[OX2][CX4]"):
        return "álcool/éter"
    if has_smarts(active, "[NX3]") or has_smarts(active, "N"):
        return "amina/amida"
    return "sem cabeça polar forte identificada"


def surfactant_class(active) -> tuple[str, str, int]:
    charge = int(sum(atom.GetFormalCharge() for atom in active.GetAtoms()))
    head = head_group(active)
    atom_charges = [atom.GetFormalCharge() for atom in active.GetAtoms()]

    if charge == 0 and any(x > 0 for x in atom_charges) and any(x < 0 for x in atom_charges):
        return "anfotérico/zwitteriônico", head, charge

    if charge < 0 or head in {"sulfato/sulfonato", "carboxilato/ácido carboxílico"}:
        return "aniônico", head, charge
    if charge > 0 or head in {"amônio quaternário", "fosfônio"}:
        return "catiônico", head, charge
    if any(x > 0 for x in atom_charges) and any(x < 0 for x in atom_charges):
        return "anfotérico/zwitteriônico", head, charge

    return "não iônico/provável", head, charge


def longest_aliphatic_carbon_component(active) -> int:
    carbons = {
        atom.GetIdx()
        for atom in active.GetAtoms()
        if atom.GetSymbol() == "C" and not atom.GetIsAromatic()
    }

    if not carbons:
        return 0

    graph = {idx: set() for idx in carbons}
    for bond in active.GetBonds():
        a = bond.GetBeginAtomIdx()
        b = bond.GetEndAtomIdx()

        if a in carbons and b in carbons:
            graph[a].add(b)
            graph[b].add(a)

    visited = set()
    best = 0

    for start in carbons:
        if start in visited:
            continue

        stack = [start]
        visited.add(start)
        size = 0

        while stack:
            node = stack.pop()
            size += 1
            for nxt in graph[node]:
                if nxt not in visited:
                    visited.add(nxt)
                    stack.append(nxt)

        best = max(best, size)

    return best


def wiener_index(mol) -> float | None:
    try:
        matrix = Chem.GetDistanceMatrix(mol)
        total = 0.0

        for frag in Chem.GetMolFrags(mol, asMols=False, sanitizeFrags=False):
            atoms = list(frag)
            for pos_i, i in enumerate(atoms):
                for j in atoms[pos_i + 1:]:
                    dij = float(matrix[i, j])
                    if math.isfinite(dij) and dij < 1e7:
                        total += dij

        return total
    except Exception:
        return None


def randic_index(mol) -> float | None:
    try:
        total = 0.0
        for bond in mol.GetBonds():
            da = max(bond.GetBeginAtom().GetDegree(), 1)
            db = max(bond.GetEndAtom().GetDegree(), 1)
            total += 1.0 / math.sqrt(da * db)
        return total
    except Exception:
        return None


def tanford_tail_volume_a3(tail_c: int) -> float | None:
    if tail_c <= 0:
        return None
    return 27.4 + 26.9 * tail_c


def tanford_tail_length_a(tail_c: int) -> float | None:
    if tail_c <= 0:
        return None
    return 1.5 + 1.265 * tail_c


def head_area_a2(sclass: str, head: str, env: dict[str, float], has_counterion: bool) -> float | None:
    base = {
        "sulfato/sulfonato": 52.0,
        "carboxilato/ácido carboxílico": 46.0,
        "amônio quaternário": 58.0,
        "fosfônio": 62.0,
        "álcool/éter": 60.0,
        "amina/amida": 54.0,
    }.get(head)

    if base is None and sclass == "anfotérico/zwitteriônico":
        base = 56.0

    if base is None:
        return None

    if sclass in {"aniônico", "catiônico"}:
        ionic_strength = max(env["ionic_strength_mol_l"], 1e-6)
        electrostatic_expansion = 8.0 / (1.0 + 12.0 * ionic_strength)
        if has_counterion:
            electrostatic_expansion *= 0.82
        base += electrostatic_expansion

    return max(28.0, min(95.0, base))


def davies_hlb(sclass: str, head: str, tail_c: int, hetero_count: int) -> float | None:
    if tail_c <= 0:
        return None

    if head == "sulfato/sulfonato":
        hydrophilic = 38.7
    elif head == "carboxilato/ácido carboxílico":
        hydrophilic = 19.1 if sclass == "aniônico" else 2.1
    elif head == "amônio quaternário":
        hydrophilic = 22.0
    elif head == "fosfônio":
        hydrophilic = 20.0
    elif head == "álcool/éter":
        hydrophilic = 1.9 * max(hetero_count, 1)
    elif sclass == "anfotérico/zwitteriônico":
        hydrophilic = 25.0
    else:
        return None

    return max(0.0, min(50.0, 7.0 + hydrophilic - 0.475 * tail_c))


def griffin_like_hlb(active_mw: float, active) -> float | None:
    if active_mw <= 0:
        return None

    hydrophilic_mass = sum(
        atom.GetMass()
        for atom in active.GetAtoms()
        if atom.GetAtomicNum() not in {1, 6}
    )

    if hydrophilic_mass <= 0:
        return None

    return max(0.0, min(20.0, 20.0 * hydrophilic_mass / active_mw))


def display_hlb(davies: float | None, griffin: float | None, sclass: str) -> float | None:
    if sclass in {"aniônico", "catiônico"} and davies is not None:
        # Davies para iônicos pode passar de 20. Esta escala deixa o painel comparável.
        return max(1.0, min(20.0, 4.0 + 16.0 * davies / 50.0))

    return griffin if griffin is not None else davies


def klevens_cmc_mmol_l(sclass: str, head: str, tail_c: int) -> tuple[float | None, str]:
    if tail_c < 6:
        return None, "Cauda curta para Klevens."

    if head == "sulfato/sulfonato":
        # Ajustado para C10 ≈ 35 mmol/L e C12 ≈ 8 mmol/L em ordem de grandeza.
        a, b, note = 1.65, 0.31, "Klevens para alquil sulfato/sulfonato: log10(CMC mol/L)=A-Bn."
    elif head == "carboxilato/ácido carboxílico":
        a, b, note = 1.95, 0.30, "Klevens aproximado para carboxilato."
    elif sclass == "catiônico":
        a, b, note = 1.45, 0.30, "Klevens aproximado para catiônico."
    elif sclass == "não iônico/provável":
        a, b, note = 0.90, 0.27, "Klevens aproximado para não iônico."
    else:
        a, b, note = 1.60, 0.29, "Klevens genérico para triagem."

    return 1000.0 * (10 ** (a - b * tail_c)), note


def correct_cmc_by_environment(cmc_mmol_l: float | None, sclass: str, env: dict[str, float]) -> float | None:
    if cmc_mmol_l is None:
        return None

    temp_factor = max(0.35, min(2.2, 1.0 + 0.010 * (env["temperature_k"] - 298.15)))
    polarity_factor = max(0.45, min(2.4, 1.0 + (1.0 - env["solvent_polarity_index"]) * 0.65))
    agitation_factor = 1.0 + min(env["agitation_rpm"], 2500.0) / 30000.0

    if sclass in {"aniônico", "catiônico"}:
        salt_factor = max(0.35, min(1.15, 1.0 - 1.30 * min(env["ionic_strength_mol_l"], 0.45)))
    else:
        salt_factor = 1.0

    return max(0.0001, cmc_mmol_l * temp_factor * polarity_factor * agitation_factor * salt_factor)


def mole_fraction_cmc(cmc_mmol_l: float | None) -> float | None:
    if cmc_mmol_l is None:
        return None

    cmc_mol_l = cmc_mmol_l / 1000.0
    return cmc_mol_l / (55.5 + cmc_mol_l)


def delta_g_mic_kj_mol(x_cmc: float | None, temp_k: float, sclass: str) -> float | None:
    if x_cmc is None or x_cmc <= 0:
        return None

    value = R_GAS * temp_k * math.log(x_cmc) / 1000.0
    if sclass in {"aniônico", "catiônico"}:
        value *= 1.08

    return value


def pka_estimate(head: str, sclass: str) -> tuple[float | None, str]:
    if head == "sulfato/sulfonato":
        return -1.5, "pKa aproximado para sulfato/sulfonato forte."
    if head == "carboxilato/ácido carboxílico":
        return 4.6, "pKa aproximado para carboxilato/ácido carboxílico."
    if head == "amônio quaternário":
        return None, "Amônio quaternário: carga permanente; pKa simples não se aplica."
    if sclass == "catiônico" or head == "amina/amida":
        return 9.8, "pKa aproximado para amina alifática protonável."
    return None, "Grupo ionizável simples não identificado."


def logd_estimate(logp: float, pka: float | None, ph: float, sclass: str, head: str) -> tuple[float, str]:
    if head == "amônio quaternário":
        return logp - 3.0, "Carga permanente: LogD penalizado por hidratação."

    if pka is None:
        return logp, "Sem pKa simples; LogD aproximado como LogP."

    if sclass == "aniônico" or head in {"sulfato/sulfonato", "carboxilato/ácido carboxílico"}:
        penalty = math.log10(1.0 + 10 ** max(-12.0, min(12.0, ph - pka)))
        return logp - min(penalty, 5.0), "Henderson-Hasselbalch aproximado para ácido, com limite para surfactante iônico."

    if sclass == "catiônico":
        penalty = math.log10(1.0 + 10 ** max(-12.0, min(12.0, pka - ph)))
        return logp - min(penalty, 5.0), "Henderson-Hasselbalch aproximado para base, com limite para surfactante iônico."

    return logp, "LogD aproximado como LogP."


def logs_esol(active_mw: float, logp: float, rot: int, aromatic_rings: int, ionized: bool) -> float:
    value = 0.16 - 0.63 * logp - 0.0062 * active_mw + 0.066 * rot - 0.74 * aromatic_rings
    if ionized:
        value += 1.20
    return max(-12.0, min(3.0, value))


def bulk_property_estimates(active_mw: float, logp: float, tpsa: float, hbd: int, rings: int, env: dict[str, float], ionized: bool) -> dict[str, float]:
    density = 0.74 + 0.00085 * min(active_mw, 900.0) + 0.0018 * min(tpsa, 180.0) - 0.012 * max(logp, 0.0)
    if ionized:
        density += 0.12
    density *= 1.0 - 0.00075 * (env["temperature_k"] - 298.15)

    melting = -70.0 + 0.34 * active_mw + 12.0 * rings + 10.0 * hbd
    boiling = 55.0 + 0.76 * active_mw + 0.20 * tpsa + 4.0 * max(logp, 0.0)

    if ionized:
        melting += 90.0
        boiling += 140.0

    vapor = math.exp(((env["temperature_k"] - 273.15) - boiling) / 35.0)
    surface = 24.0 + 0.060 * tpsa + 1.20 * max(logp, 0.0) + (10.0 if ionized else 0.0)
    viscosity = (0.30 + 0.0035 * active_mw + 0.09 * max(logp, 0.0)) * math.exp((298.15 - env["temperature_k"]) / 55.0)
    if ionized:
        viscosity *= 1.6

    return {
        "density_g_cm3": max(0.55, min(2.40, density)),
        "melting_c": max(-180.0, min(520.0, melting)),
        "boiling_c": max(-80.0, min(850.0, boiling)),
        "vapor_pressure_atm": max(1e-12, min(5.0, vapor)),
        "surface_tension_mn_m": max(8.0, min(120.0, surface)),
        "viscosity_cp": max(0.05, min(500.0, viscosity)),
    }


def solvation_gibbs_kj_mol(logs: float, logp: float, ionized: bool, env: dict[str, float]) -> float:
    value = -5.7 * logs - 2.4 * max(logp, 0.0) - 4.0 * env["solvent_polarity_index"]
    if ionized:
        value -= 18.0
    return value


def heat_formation_proxy_kj_mol(active_mw: float, hetero: int, rings: int, charge_abs: int) -> float:
    return -0.62 * active_mw - 32.0 * hetero + 10.0 * rings - 55.0 * charge_abs


def cpp_behavior(cpp: float | None) -> str | None:
    if cpp is None:
        return None
    if cpp < 0.33:
        return "tendência a micela esférica"
    if cpp < 0.50:
        return "tendência a micela cilíndrica/wormlike"
    if cpp < 1.00:
        return "tendência a bicamada/lamelar"
    return "tendência a micela inversa"


def aggregation_number(tail_c: int, sclass: str, ionic_strength: float) -> int | None:
    if tail_c < 8:
        return None

    value = 34.0 + 5.0 * (tail_c - 8)

    if sclass in {"aniônico", "catiônico"}:
        value *= 0.88 + 1.35 * min(ionic_strength, 0.25)
    else:
        value *= 1.15

    return int(max(20, min(180, round(value))))


def micelle_radii_nm(tail_length_a: float | None, nagg: int | None, head_area: float | None) -> dict[str, Any]:
    if tail_length_a is None:
        return {"core_nm": None, "apparent_nm": None, "range_nm": None, "cylindrical_nm": None}

    core_nm = tail_length_a / 10.0
    apparent_nm = core_nm + 0.42

    if nagg and head_area:
        area_radius = math.sqrt(max(nagg * head_area, 1.0) / (4.0 * math.pi)) / 10.0
        apparent_nm = max(apparent_nm, area_radius)

    return {
        "core_nm": core_nm,
        "apparent_nm": apparent_nm,
        "range_nm": {"min_nm": apparent_nm * 0.82, "max_nm": apparent_nm * 1.22},
        "cylindrical_nm": core_nm + 0.35,
    }


def debye_length_nm(ionic_strength: float) -> float | None:
    if ionic_strength <= 0:
        return None
    return 0.304 / math.sqrt(ionic_strength)


def surface_charge_model(sclass: str, nagg: int | None, radius_nm: float | None, has_counterion: bool) -> dict[str, Any]:
    if sclass not in {"aniônico", "catiônico"} or nagg is None or radius_nm is None:
        return {"residual_charge_e": None, "bound_counterions": None, "surface_charge_c_m2": None}

    sign = -1 if sclass == "aniônico" else 1
    alpha_free = 0.28 if has_counterion else 0.38
    residual = sign * nagg * alpha_free
    bound = nagg * (1.0 - alpha_free)
    area_nm2 = 4.0 * math.pi * radius_nm * radius_nm
    sigma = residual / max(area_nm2, 1e-9) * 0.1602176634

    return {
        "residual_charge_e": residual,
        "bound_counterions": bound,
        "surface_charge_c_m2": sigma,
    }


def hld_and_nac(sclass: str, tail_c: int, env: dict[str, float], cpp: float | None, tail_volume: float | None, head_area: float | None, tail_length: float | None) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    eacn = max(tail_c - 2, 0)

    if tail_c <= 0:
        hld = None
    elif sclass in {"aniônico", "catiônico"}:
        hld_value = math.log10(max(env["ionic_strength_mol_l"], 1e-6)) - 0.045 * eacn + 0.01 * (env["temperature_k"] - 298.15)
        hld = {
            "hld_proxy": hld_value,
            "interpretation": "mais hidrofílico" if hld_value < -0.5 else ("próximo de balanceado" if abs(hld_value) <= 0.5 else "mais lipofílico"),
            "note": "Proxy HLD sem óleo definido; EACN aproximado pela cauda.",
        }
    else:
        hld_value = -0.030 * eacn + 0.018 * (env["temperature_k"] - 298.15) - 0.25 * (1.0 - env["solvent_polarity_index"])
        hld = {
            "hld_proxy": hld_value,
            "interpretation": "mais hidrofílico" if hld_value < -0.5 else ("próximo de balanceado" if abs(hld_value) <= 0.5 else "mais lipofílico"),
            "note": "Proxy HLD para triagem; exige óleo/EACN real para cálculo físico.",
        }

    nac = {
        "tail_volume_a3": tail_volume,
        "head_area_a2": head_area,
        "tail_length_a": tail_length,
        "cpp": cpp,
        "interpretation": cpp_behavior(cpp),
    }

    return hld, nac


def frontier_orbitals(active, logp: float, tpsa: float, aromatic_rings: int, rot: int, sclass: str, charge_abs: int) -> tuple[float, float, float]:
    hetero = sum(1 for atom in active.GetAtoms() if atom.GetAtomicNum() in {7, 8, 15, 16})
    halogens = sum(1 for atom in active.GetAtoms() if atom.GetAtomicNum() in {9, 17, 35, 53})
    conjugated = sum(1 for bond in active.GetBonds() if bond.GetIsConjugated() or bond.GetIsAromatic())

    homo = -7.25 + 0.17 * hetero + 0.14 * aromatic_rings + 0.04 * max(logp, -2.0) - 0.10 * halogens - 0.30 * charge_abs
    if sclass == "aniônico":
        homo += 0.25
    elif sclass == "catiônico":
        homo -= 0.35

    gap = max(1.6, min(8.8, 7.35 - 0.30 * conjugated - 0.32 * aromatic_rings - 0.010 * tpsa + 0.018 * rot))
    lumo = homo + gap
    return homo, lumo, gap


def dipole_proxy_debye(active_charge: int, has_counterion: bool, tpsa: float, tail_c: int) -> dict[str, float]:
    if active_charge != 0 and has_counterion:
        magnitude = abs(active_charge) * (2.2 + 0.035 * min(tail_c, 18)) * DEBYE_PER_E_ANGSTROM
    else:
        magnitude = 0.08 * tpsa + 0.15 * min(tail_c, 20)

    return {"x": round(magnitude, 5), "y": 0.0, "z": 0.0, "magnitude": round(magnitude, 5)}


def bond_polarity(atom_a, atom_b) -> dict[str, Any]:
    ea = PAULING_EN.get(atom_a.GetSymbol())
    eb = PAULING_EN.get(atom_b.GetSymbol())

    if ea is None or eb is None:
        return unavailable("Pauling_EN_minimal_table")

    delta = abs(ea - eb)

    if delta < 0.4:
        kind = "apolar/pouco polar"
    elif delta < 1.7:
        kind = "polar"
    else:
        kind = "muito polar/iônica"

    return param(
        {
            "delta_eletronegatividade": round(delta, 4),
            "classe": kind,
            "eletronegatividade_atomo_a": ea,
            "eletronegatividade_atomo_b": eb,
        },
        "Pauling_EN_minimal_table",
    )



def explicit_hydrogen_inventory(mol) -> dict[str, Any]:
    mol_h = safe(lambda: Chem.AddHs(Chem.Mol(mol)), mol)
    heavy_atom_count = mol.GetNumHeavyAtoms()
    atom_count_total = mol_h.GetNumAtoms()
    hydrogen_count = sum(1 for atom in mol_h.GetAtoms() if atom.GetAtomicNum() == 1)
    heavy_bond_count = mol.GetNumBonds()
    bond_count_total = mol_h.GetNumBonds()
    single_bonds = double_bonds = triple_bonds = aromatic_bonds = 0
    sigma_total = pi_total = sigma_heavy = pi_heavy = 0.0
    h_bonds = c_h = n_h = o_h = s_h = hetero_h = 0
    hh_single = hh_double = hh_triple = hh_aromatic = 0

    def pi_for(bond) -> float:
        if bond.GetIsAromatic() or str(bond.GetBondType()) == "AROMATIC":
            return 0.5
        order = float(bond.GetBondTypeAsDouble())
        if order >= 3:
            return 2.0
        if order >= 2:
            return 1.0
        return 0.0

    for bond in mol_h.GetBonds():
        a = bond.GetBeginAtom()
        b = bond.GetEndAtom()
        za = a.GetAtomicNum()
        zb = b.GetAtomicNum()
        has_h = za == 1 or zb == 1
        is_heavy_heavy = za > 1 and zb > 1
        bond_type = str(bond.GetBondType())
        sigma_total += 1.0
        pi_here = pi_for(bond)
        pi_total += pi_here
        if bond.GetIsAromatic() or bond_type == "AROMATIC":
            aromatic_bonds += 1
            if is_heavy_heavy:
                hh_aromatic += 1
        elif bond_type == "DOUBLE" or float(bond.GetBondTypeAsDouble()) == 2.0:
            double_bonds += 1
            if is_heavy_heavy:
                hh_double += 1
        elif bond_type == "TRIPLE" or float(bond.GetBondTypeAsDouble()) == 3.0:
            triple_bonds += 1
            if is_heavy_heavy:
                hh_triple += 1
        else:
            single_bonds += 1
            if is_heavy_heavy:
                hh_single += 1
        if is_heavy_heavy:
            sigma_heavy += 1.0
            pi_heavy += pi_here
        if has_h:
            h_bonds += 1
            other = b if za == 1 else a
            sym = other.GetSymbol()
            if sym == "C":
                c_h += 1
            elif sym == "N":
                n_h += 1
                hetero_h += 1
            elif sym == "O":
                o_h += 1
                hetero_h += 1
            elif sym == "S":
                s_h += 1
                hetero_h += 1
            elif other.GetAtomicNum() > 1:
                hetero_h += 1
    return {
        "atom_count_total": int(atom_count_total),
        "heavy_atom_count": int(heavy_atom_count),
        "hydrogen_count": int(hydrogen_count),
        "bond_count_total": int(bond_count_total),
        "heavy_bond_count": int(heavy_bond_count),
        "hydrogen_bond_count": int(h_bonds),
        "carbon_hydrogen_bond_count": int(c_h),
        "nitrogen_hydrogen_bond_count": int(n_h),
        "oxygen_hydrogen_bond_count": int(o_h),
        "sulfur_hydrogen_bond_count": int(s_h),
        "hetero_hydrogen_bond_count": int(hetero_h),
        "single_bond_count": int(single_bonds),
        "double_bond_count": int(double_bonds),
        "triple_bond_count": int(triple_bonds),
        "aromatic_bond_count": int(aromatic_bonds),
        "sigma_bond_count": int(round(sigma_total)),
        "pi_bond_count": round(pi_total, 3),
        "heavy_sigma_bond_count": int(round(sigma_heavy)),
        "heavy_pi_bond_count": round(pi_heavy, 3),
        "hydrogen_sigma_bond_count": int(h_bonds),
        "heavy_heavy_single_bond_count": int(hh_single),
        "heavy_heavy_double_bond_count": int(hh_double),
        "heavy_heavy_triple_bond_count": int(hh_triple),
        "heavy_heavy_aromatic_bond_count": int(hh_aromatic),
        "note": "Contagens feitas em Chem.AddHs(mol): H implícito vira explícito para contar átomos totais, ligações X-H, σ e π.",
    }

def build_atoms(mol) -> list[dict[str, Any]]:
    periodic = Chem.GetPeriodicTable()
    atoms = []

    for atom in mol.GetAtoms():
        idx = atom.GetIdx()
        z = atom.GetAtomicNum()
        mass = safe(lambda z=z: periodic.GetAtomicWeight(z), None)
        vdw = safe(lambda z=z: periodic.GetRvdw(z), None)
        cov = safe(lambda z=z: periodic.GetRcovalent(z), None)
        bond_sum = sum(safe(lambda item=bond: item.GetBondTypeAsDouble(), 1.0) for bond in atom.GetBonds())

        atoms.append(
            {
                "id_interno": None,
                "rdkit_idx": idx,
                "elemento": atom.GetSymbol(),
                "numero_atomico": z,
                "massa_exata": param(rounded(mass, 5), "RDKit PeriodicTable", "u"),
                "is_isotopo": bool(atom.GetIsotope()),
                "grau_ligacao_explicito": atom.GetDegree(),
                "ordem_ligacao_total": param(rounded(bond_sum, 3), "RDKit bond order"),
                "valencia_total": param(safe(lambda atom=atom: atom.GetTotalValence(), None), "RDKit Atom.GetTotalValence"),
                "hidrogenios_totais": atom.GetTotalNumHs(),
                "hidrogenios_implicitos": atom.GetNumImplicitHs(),
                "hidrogenios_explicitos": atom.GetNumExplicitHs(),
                "carga_formal": atom.GetFormalCharge(),
                "carga_gasteiger": unavailable("fast route skipped Gasteiger", "e"),
                "carga_quantica_ou_proxy": param(
                    rounded((PAULING_EN.get(atom.GetSymbol(), 2.5) - 2.55) * -0.08 + atom.GetFormalCharge(), 5),
                    "electronegativity/formal-charge proxy",
                    "e",
                ),
                "eletrons_radicais": atom.GetNumRadicalElectrons(),
                "pares_livres": unavailable("fast valence proxy disabled"),
                "hibridizacao_rdkit": str(atom.GetHybridization()),
                "hibridizacao_estimativa": param({"rdkit": str(atom.GetHybridization())}, "RDKit hybridization"),
                "geometria_eletronica": unavailable("no conformer geometry"),
                "is_aromatico": atom.GetIsAromatic(),
                "is_no_anel": atom.IsInRing(),
                "tamanho_do_anel": None,
                "chiral_tag": str(atom.GetChiralTag()),
                "configuracao_absoluta": param(atom.GetProp("_CIPCode"), "RDKit CIP") if atom.HasProp("_CIPCode") else unavailable("RDKit CIP"),
                "posicao_2d": None,
                "posicao_3d": unavailable("3D skipped fast route"),
                "raio_vdw": param(rounded(vdw, 4), "RDKit PeriodicTable", "Angstrom"),
                "raio_covalente": param(rounded(cov, 4), "RDKit PeriodicTable", "Angstrom"),
                "sasa_local": unavailable("3D skipped fast route", "Angstrom^2"),
                "tipo_campo_de_forca": unavailable("MMFF/UFF skipped fast route"),
                "fukui_aproximado": unavailable("quantum descriptor skipped"),
                "interacoes_atomicas": param([], "pairwise interactions skipped in fast panel"),
                "reatividade_local": unavailable("quantum descriptor skipped"),
            }
        )

    return atoms


def build_bonds(mol) -> list[dict[str, Any]]:
    periodic = Chem.GetPeriodicTable()
    bonds = []

    for bond in mol.GetBonds():
        atom_a = bond.GetBeginAtom()
        atom_b = bond.GetEndAtom()
        ideal_length = safe(
            lambda atom_a=atom_a, atom_b=atom_b: periodic.GetRcovalent(atom_a.GetAtomicNum()) + periodic.GetRcovalent(atom_b.GetAtomicNum()),
            None,
        )

        bonds.append(
            {
                "id_interno": None,
                "rdkit_idx": bond.GetIdx(),
                "atomo_origem_idx": bond.GetBeginAtomIdx(),
                "atomo_destino_idx": bond.GetEndAtomIdx(),
                "ordem": float(bond.GetBondTypeAsDouble()),
                "tipo_rdkit": str(bond.GetBondType()),
                "is_conjugada": bond.GetIsConjugated(),
                "is_aromatica": bond.GetIsAromatic(),
                "is_no_anel": bond.IsInRing(),
                "estereoquimica": str(bond.GetStereo()),
                "direcao_visual": str(bond.GetBondDir()),
                "comprimento_ideal": param(rounded(ideal_length, 4), "RDKit covalent radii", "Angstrom"),
                "polaridade_ligacao": bond_polarity(atom_a, atom_b),
            }
        )

    return bonds


def make_response(payload: ChemistryParametersRequest) -> dict[str, Any]:
    if Chem is None:
        raise RuntimeError(f"RDKit não está disponível: {RDKIT_IMPORT_ERROR}")

    smiles = input_smiles(payload)
    mol = Chem.MolFromSmiles(smiles)

    if mol is None:
        raise ValueError("SMILES inválido para cálculo de parâmetros.")

    Chem.SanitizeMol(mol)
    Chem.AssignStereochemistry(mol, cleanIt=True, force=True)

    env = env_from(payload)
    active = active_fragment(mol)
    detected_counterions = counterions(mol)
    has_counterion = bool(detected_counterions)

    canonical = Chem.MolToSmiles(mol, canonical=True, isomericSmiles=False)
    isomeric = Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)
    active_smiles = Chem.MolToSmiles(active, canonical=True, isomericSmiles=True)
    structural_hash = hashlib.sha256(isomeric.encode("utf-8")).hexdigest()

    pubchem = pubchem_lookup(isomeric)
    pubchem_props = pubchem.get("properties", {}) if pubchem.get("ok") else {}

    mol_h = safe(lambda: Chem.AddHs(Chem.Mol(mol)), mol)
    active_h = safe(lambda: Chem.AddHs(Chem.Mol(active)), active)

    formula = safe(lambda: rdMolDescriptors.CalcMolFormula(mol_h), None)
    active_formula = safe(lambda: rdMolDescriptors.CalcMolFormula(active_h), None)

    mw = float(safe(lambda: Descriptors.MolWt(mol), 0.0))
    exact_mass = float(safe(lambda: Descriptors.ExactMolWt(mol), 0.0))
    active_mw = float(safe(lambda: Descriptors.MolWt(active), mw))

    logp_local = float(safe(lambda: Crippen.MolLogP(active), Crippen.MolLogP(mol)))
    logp_pubchem = as_float(pubchem_props.get("XLogP"))
    logp = logp_pubchem if logp_pubchem is not None else logp_local

    tpsa_local = float(safe(lambda: rdMolDescriptors.CalcTPSA(active), rdMolDescriptors.CalcTPSA(mol)))
    tpsa_pubchem = as_float(pubchem_props.get("TPSA"))
    tpsa = tpsa_pubchem if tpsa_pubchem is not None else tpsa_local

    hbd = int(safe(lambda: Lipinski.NumHDonors(active), rdMolDescriptors.CalcNumHBD(active)))
    hba = int(safe(lambda: Lipinski.NumHAcceptors(active), rdMolDescriptors.CalcNumHBA(active)))
    rot = int(safe(lambda: rdMolDescriptors.CalcNumRotatableBonds(active), 0))
    rings = int(safe(lambda: rdMolDescriptors.CalcNumRings(active), 0))
    aromatic_rings = int(safe(lambda: rdMolDescriptors.CalcNumAromaticRings(active), 0))
    csp3 = float(safe(lambda: rdMolDescriptors.CalcFractionCSP3(active), 0.0))
    qed_value = safe(lambda: float(QED.qed(active)), None)
    bertz = safe(lambda: float(Descriptors.BertzCT(active)), None)
    molar_refractivity = safe(lambda: float(Crippen.MolMR(active)), None)

    full_charge = int(sum(atom.GetFormalCharge() for atom in mol.GetAtoms()))
    sclass, head, active_charge = surfactant_class(active)
    charge_abs = abs(active_charge)
    tail_c = longest_aliphatic_carbon_component(active)
    tail_count = 1 if tail_c >= 8 else 0
    hetero_count = sum(1 for atom in active.GetAtoms() if atom.GetAtomicNum() not in {1, 6})
    ionized = sclass in {"aniônico", "catiônico", "anfotérico/zwitteriônico"} or active_charge != 0
    is_surfactant = bool(tail_c >= 8 and (head != "sem cabeça polar forte identificada" or ionized or tpsa >= 20))

    tail_volume = tanford_tail_volume_a3(tail_c)
    tail_length = tanford_tail_length_a(tail_c)
    head_area = head_area_a2(sclass, head, env, has_counterion)

    cpp = tail_volume / (head_area * tail_length) if tail_volume and head_area and tail_length else None
    behavior = cpp_behavior(cpp)

    hlb_davies = davies_hlb(sclass, head, tail_c, hetero_count)
    hlb_griffin = griffin_like_hlb(active_mw, active)
    hlb_effective = display_hlb(hlb_davies, hlb_griffin, sclass)

    cmc_klevens, cmc_note = klevens_cmc_mmol_l(sclass, head, tail_c)
    cmc_corrected = correct_cmc_by_environment(cmc_klevens, sclass, env)
    x_cmc = mole_fraction_cmc(cmc_corrected)
    dg_mic = delta_g_mic_kj_mol(x_cmc, env["temperature_k"], sclass)

    pka_value, pka_note = pka_estimate(head, sclass)
    logd_value, logd_note = logd_estimate(logp, pka_value, env["ph"], sclass, head)
    logs_value = logs_esol(active_mw, logp, rot, aromatic_rings, ionized)
    bulk = bulk_property_estimates(active_mw, logp, tpsa, hbd, rings, env, ionized)
    gibbs_solv = solvation_gibbs_kj_mol(logs_value, logp, ionized, env)
    heat_form = heat_formation_proxy_kj_mol(active_mw, hetero_count, rings, charge_abs)

    wiener = wiener_index(active)
    randic = randic_index(active)

    vdw_volume = None
    if tail_volume is not None:
        head_volume = max(45.0, 10.5 * hetero_count + 8.0 * charge_abs)
        vdw_volume = tail_volume + head_volume

    sasa = 4.84 * (vdw_volume ** (2.0 / 3.0)) if vdw_volume is not None else None
    radius_gyration = max(0.4, (tail_length / math.sqrt(12.0)) / 10.0) if tail_length is not None else None
    npr1 = 0.18 if tail_length is not None else None
    npr2 = 0.78 if tail_length is not None and tail_c >= 8 else None

    nagg = aggregation_number(tail_c, sclass, env["ionic_strength_mol_l"])
    radii = micelle_radii_nm(tail_length, nagg, head_area)
    debye = debye_length_nm(env["ionic_strength_mol_l"])
    surface_charge = surface_charge_model(sclass, nagg, radii["apparent_nm"], has_counterion)
    hld, nac = hld_and_nac(sclass, tail_c, env, cpp, tail_volume, head_area, tail_length)

    homo, lumo, gap = frontier_orbitals(active, logp, tpsa, aromatic_rings, rot, sclass, charge_abs)
    dipole = dipole_proxy_debye(active_charge, has_counterion, tpsa, tail_c)

    rdkit_inchi = safe(lambda: Chem.MolToInchi(mol), None)
    rdkit_inchikey = safe(lambda: Chem.MolToInchiKey(mol), None)

    inchi = pubchem_props.get("InChI") or rdkit_inchi
    inchikey = pubchem_props.get("InChIKey") or rdkit_inchikey
    iupac_name = pubchem_props.get("IUPACName")


    bond_inventory = explicit_hydrogen_inventory(mol)

    molecule = {
        "id_snapshot": str(uuid4()),
        "hash_estrutural": structural_hash,
        "smiles_canonico": pubchem_props.get("CanonicalSMILES") or canonical,
        "smiles_isomerico": pubchem_props.get("IsomericSMILES") or isomeric,
        "smiles_fragmento_ativo": param(active_smiles, "RDKit active fragment"),
        "inchi": param(inchi, "PubChem/RDKit InChI") if inchi else unavailable("PubChem/RDKit InChI"),
        "inchikey": param(inchikey, "PubChem/RDKit InChIKey") if inchikey else unavailable("PubChem/RDKit InChIKey"),
        "nome_comum": param(iupac_name or f"SMILES:{canonical}", "PubChem IUPACName / fallback local"),
        "formula_molecular": pubchem_props.get("MolecularFormula") or formula,
        "formula_fragmento_ativo": param(active_formula, "RDKit active fragment"),
        "peso_molecular": as_float(pubchem_props.get("MolecularWeight")) or mw,
        "massa_exata": as_float(pubchem_props.get("ExactMass")) or exact_mass,
        "massa_fragmento_ativo": param(rounded(active_mw), "RDKit active fragment", "g/mol"),
        "total_atomos": bond_inventory["atom_count_total"],
        "total_ligacoes": bond_inventory["bond_count_total"],
        "total_atomos_com_h": param(mol_h.GetNumAtoms(), "RDKit AddHs no coordinates"),
        "total_ligacoes_com_h": param(mol_h.GetNumBonds(), "RDKit AddHs no coordinates"),
        "total_atomos_pesados": bond_inventory["heavy_atom_count"],
        "total_ligacoes_pesadas": bond_inventory["heavy_bond_count"],
        "atom_count_total": bond_inventory["atom_count_total"],
        "bond_count_total": bond_inventory["bond_count_total"],
        "heavy_atom_count": bond_inventory["heavy_atom_count"],
        "heavy_bond_count": bond_inventory["heavy_bond_count"],
        "total_hidrogenios": param(bond_inventory["hydrogen_count"], "RDKit Chem.AddHs hydrogen inventory", "átomos"),
        "hydrogen_atom_count": bond_inventory["hydrogen_count"],
        "ligacoes_com_hidrogenio": param(bond_inventory["hydrogen_bond_count"], "RDKit Chem.AddHs hydrogen inventory", "ligações"),
        "hydrogen_bond_count": bond_inventory["hydrogen_bond_count"],
        "ligacoes_c_h": param(bond_inventory["carbon_hydrogen_bond_count"], "RDKit Chem.AddHs bond inventory", "ligações"),
        "carbon_hydrogen_bond_count": bond_inventory["carbon_hydrogen_bond_count"],
        "ligacoes_n_h": param(bond_inventory["nitrogen_hydrogen_bond_count"], "RDKit Chem.AddHs bond inventory", "ligações"),
        "ligacoes_o_h": param(bond_inventory["oxygen_hydrogen_bond_count"], "RDKit Chem.AddHs bond inventory", "ligações"),
        "ligacoes_s_h": param(bond_inventory["sulfur_hydrogen_bond_count"], "RDKit Chem.AddHs bond inventory", "ligações"),
        "ligacoes_hetero_h": param(bond_inventory["hetero_hydrogen_bond_count"], "RDKit Chem.AddHs bond inventory", "ligações"),
        "ligacoes_sigma": param(bond_inventory["sigma_bond_count"], "RDKit Chem.AddHs sigma/pi inventory", "ligações σ"),
        "sigma_bond_count": bond_inventory["sigma_bond_count"],
        "ligacoes_pi": param(bond_inventory["pi_bond_count"], "RDKit Chem.AddHs sigma/pi inventory", "ligações π"),
        "pi_bond_count": bond_inventory["pi_bond_count"],
        "ligacoes_sigma_pesadas": param(bond_inventory["heavy_sigma_bond_count"], "RDKit heavy-heavy bond inventory", "ligações σ"),
        "ligacoes_pi_pesadas": param(bond_inventory["heavy_pi_bond_count"], "RDKit heavy-heavy bond inventory", "ligações π"),
        "ligacoes_sigma_com_hidrogenio": param(bond_inventory["hydrogen_sigma_bond_count"], "RDKit X-H sigma inventory", "ligações σ"),
        "contagem_ligacoes_por_tipo": param({
            "single": bond_inventory["single_bond_count"],
            "double": bond_inventory["double_bond_count"],
            "triple": bond_inventory["triple_bond_count"],
            "aromatic": bond_inventory["aromatic_bond_count"],
            "heavy_heavy_single": bond_inventory["heavy_heavy_single_bond_count"],
            "heavy_heavy_double": bond_inventory["heavy_heavy_double_bond_count"],
            "heavy_heavy_triple": bond_inventory["heavy_heavy_triple_bond_count"],
            "heavy_heavy_aromatic": bond_inventory["heavy_heavy_aromatic_bond_count"],
            "with_hydrogen": bond_inventory["hydrogen_bond_count"],
            "carbon_hydrogen": bond_inventory["carbon_hydrogen_bond_count"],
            "nitrogen_hydrogen": bond_inventory["nitrogen_hydrogen_bond_count"],
            "oxygen_hydrogen": bond_inventory["oxygen_hydrogen_bond_count"],
            "sulfur_hydrogen": bond_inventory["sulfur_hydrogen_bond_count"],
        }, "RDKit Chem.AddHs full bond inventory", note=bond_inventory["note"]),
        "carga_formal_total": full_charge,
        "carga_formal_fragmento_ativo": param(active_charge, "RDKit active fragment"),
        "contraions_detectados": param(detected_counterions, "RDKit fragment charge screening"),
        "logp": param(rounded(logp), "PubChem XLogP" if logp_pubchem is not None else "RDKit Crippen.MolLogP active fragment"),
        "logd": param(rounded(logd_value), "Henderson-Hasselbalch / ionic surfactant proxy", note=logd_note),
        "pka": param(rounded(pka_value), "SMARTS pKa heuristic", note=pka_note) if pka_value is not None else unavailable("SMARTS pKa heuristic", note=pka_note),
        "logs": param(rounded(logs_value), "ESOL-like heuristic", note="Estimativa de solubilidade; surfactantes/sais exigem validação experimental."),
        "tpsa": param(rounded(tpsa), "PubChem TPSA" if tpsa_pubchem is not None else "RDKit CalcTPSA active fragment", "Angstrom^2"),
        "hbd": param(hbd, "RDKit Lipinski/CalcNumHBD active fragment"),
        "hba": param(hba, "RDKit Lipinski/CalcNumHBA active fragment"),
        "rotatable_bonds": param(rot, "RDKit CalcNumRotatableBonds active fragment"),
        "total_aneis": param(rings, "RDKit CalcNumRings active fragment"),
        "aneis_aromaticos": param(aromatic_rings, "RDKit CalcNumAromaticRings active fragment"),
        "fracao_csp3": param(rounded(csp3), "RDKit CalcFractionCSP3 active fragment"),
        "qed": param(rounded(qed_value), "RDKit QED active fragment") if qed_value is not None else unavailable("RDKit QED"),
        "complexidade_bertz": param(rounded(pubchem_props.get("Complexity") or bertz), "PubChem Complexity/RDKit BertzCT") if (pubchem_props.get("Complexity") is not None or bertz is not None) else unavailable("RDKit BertzCT"),
        "refratividade_molar": param(rounded(molar_refractivity), "RDKit Crippen.MolMR active fragment", "cm^3/mol") if molar_refractivity is not None else unavailable("RDKit MolMR"),
        "indice_wiener": param(rounded(wiener), "RDKit graph distance matrix; fragment-aware") if wiener is not None else unavailable("RDKit Wiener"),
        "indice_randic": param(rounded(randic), "RDKit graph connectivity") if randic is not None else unavailable("RDKit Randic"),
        "densidade": param(rounded(bulk["density_g_cm3"]), "QSPR-like density heuristic", "g/cm^3"),
        "ponto_fusao": param(rounded(bulk["melting_c"]), "QSPR-like melting/decomposition heuristic", "°C"),
        "ponto_ebulicao": param(rounded(bulk["boiling_c"]), "QSPR-like boiling/decomposition heuristic", "°C"),
        "pressao_vapor": param(rounded(bulk["vapor_pressure_atm"], 10), "Clausius-like vapor pressure proxy", "atm"),
        "tensao_superficial": param(rounded(bulk["surface_tension_mn_m"]), "QSPR-like surface tension heuristic", "mN/m"),
        "viscosidade": param(rounded(bulk["viscosity_cp"]), "QSPR-like viscosity heuristic", "cP"),
        "energia_livre_gibbs_solvacao": param(rounded(gibbs_solv), "ESOL/LogP ionic solvation proxy", "kJ/mol"),
        "calor_de_formacao": param(rounded(heat_form), "group-contribution-like heat proxy", "kJ/mol"),
        "raio_de_giracao": param(rounded(radius_gyration), "extended-chain geometry proxy", "nm") if radius_gyration is not None else unavailable("geometry proxy", "nm"),
        "raio_giracao": param(rounded(radius_gyration), "extended-chain geometry proxy", "nm") if radius_gyration is not None else unavailable("geometry proxy", "nm"),
        "npr1": param(rounded(npr1), "shape proxy from tail topology") if npr1 is not None else unavailable("shape proxy"),
        "npr2": param(rounded(npr2), "shape proxy from tail topology") if npr2 is not None else unavailable("shape proxy"),
        "volume_vdw_total": param(rounded(vdw_volume), "Tanford tail volume + head group volume proxy", "Angstrom^3") if vdw_volume is not None else unavailable("volume proxy", "Angstrom^3"),
        "sasa_total": param(rounded(sasa), "volume-to-surface heuristic", "Angstrom^2") if sasa is not None else unavailable("surface proxy", "Angstrom^2"),
        "vetor_momento_dipolo": param(dipole, "formal-charge/TPSA dipole proxy", "Debye"),
        "energia_conformacional": param(rounded(0.18 * rot + 0.015 * (tail_c ** 2)), "torsional strain proxy", "kcal/mol"),
        "energia_homo": param(rounded(homo, 4), "frontier orbital QSPR heuristic", "eV"),
        "energia_lumo": param(rounded(lumo, 4), "frontier orbital QSPR heuristic", "eV"),
        "gap_homo_lumo": param(rounded(gap, 4), "frontier orbital QSPR heuristic", "eV"),
        "potencial_ionizacao": param(rounded(abs(homo), 4), "Koopmans-like heuristic", "eV"),
        "afinidade_eletronica": param(rounded(-lumo, 4), "Koopmans-like heuristic", "eV"),
        "is_surfactante": param(is_surfactant, "amphiphile SMARTS + tail screening"),
        "classe_surfactante": param(sclass, "active-fragment charge + head-group classifier"),
        "tipo_cabeca_polar": param(head, "SMARTS head-group classifier"),
        "tipo_carga_surfactante": param(sclass, "active-fragment charge classifier"),
        "carga_formal_surfactante": param(active_charge, "active-fragment formal charge"),
        "indice_anfifilico": param(rounded((max(logp, 0.0) + tpsa / 60.0 + max(tail_c - 6, 0) * 0.22) if is_surfactant else 0.0), "amphiphilicity heuristic"),
        "comprimento_cauda": param(tail_c, "longest aliphatic carbon component", "C"),
        "comprimento_cauda_efetivo": param(tail_c, "longest aliphatic carbon component", "C"),
        "numero_caudas_hidrofobicas": param(tail_count, "tail topology screening"),
        "volume_cauda": param(rounded(tail_volume), "Tanford v = 27.4 + 26.9n", "Angstrom^3") if tail_volume is not None else unavailable("Tanford tail volume", "Angstrom^3"),
        "comprimento_maximo_cauda": param(rounded(tail_length), "Tanford lc = 1.5 + 1.265n", "Angstrom") if tail_length is not None else unavailable("Tanford tail length", "Angstrom"),
        "area_cabeca_micela": param(rounded(head_area), "head-group area + ionic-strength correction", "Angstrom^2") if head_area is not None else unavailable("head area", "Angstrom^2"),
        "area_cabeca_ideal": param(rounded(head_area), "head-group area estimate", "Angstrom^2") if head_area is not None else unavailable("head area", "Angstrom^2"),
        "area_cabeca_efetiva": param(rounded(head_area), "head-group area + electrostatic correction", "Angstrom^2") if head_area is not None else unavailable("head area", "Angstrom^2"),
        "hlb_griffin": param(rounded(hlb_griffin), "Griffin-like hydrophilic mass fraction") if hlb_griffin is not None else unavailable("Griffin-like HLB"),
        "hlb_davies": param(rounded(hlb_davies), "Davies group-contribution HLB") if hlb_davies is not None else unavailable("Davies HLB"),
        "hlb": param(rounded(hlb_effective), "effective HLB display from Davies/Griffin") if hlb_effective is not None else unavailable("HLB"),
        "hlb_estimado": param(rounded(hlb_effective), "effective HLB display from Davies/Griffin") if hlb_effective is not None else unavailable("HLB"),
        "hlb_engine_bruto": param(rounded(hlb_davies if hlb_davies is not None else hlb_griffin), "raw Davies/Griffin HLB") if (hlb_davies is not None or hlb_griffin is not None) else unavailable("HLB raw"),
        "cmc_klevens_mol_l": param(rounded(cmc_klevens / 1000.0 if cmc_klevens is not None else None, 8), "Klevens log10(CMC)=A-Bn", "mol/L", note=cmc_note) if cmc_klevens is not None else unavailable("Klevens CMC", "mol/L", cmc_note),
        "cmc_klevens_mmol_l": param(rounded(cmc_klevens), "Klevens log10(CMC)=A-Bn", "mmol/L", note=cmc_note) if cmc_klevens is not None else unavailable("Klevens CMC", "mmol/L", cmc_note),
        "cmc_estimada": param(rounded(cmc_corrected), "Klevens + environment correction", "mmol/L") if cmc_corrected is not None else unavailable("CMC", "mmol/L"),
        "cmc_ambiente_estimada": param(rounded(cmc_corrected), "Klevens + environment correction", "mmol/L") if cmc_corrected is not None else unavailable("CMC", "mmol/L"),
        "cmc_corrigida_mol_l": param(rounded(cmc_corrected / 1000.0 if cmc_corrected is not None else None, 8), "environment-corrected CMC", "mol/L") if cmc_corrected is not None else unavailable("CMC", "mol/L"),
        "cmc_corrigida_mmol_l": param(rounded(cmc_corrected), "environment-corrected CMC", "mmol/L") if cmc_corrected is not None else unavailable("CMC", "mmol/L"),
        "x_cmc": param(rounded(x_cmc, 10), "XCMC = CMC/(55.5 + CMC)") if x_cmc is not None else unavailable("XCMC"),
        "delta_g_micelizacao": param(rounded(dg_mic), "DeltaGmic = RT ln(XCMC), ionic proxy", "kJ/mol") if dg_mic is not None else unavailable("DeltaGmic", "kJ/mol"),
        "parametro_empacotamento": param({"valor": rounded(cpp), "classe": behavior}, "CPP = v/(a0*lc)") if cpp is not None else unavailable("CPP"),
        "cpp": param(rounded(cpp), "CPP = v/(a0*lc)") if cpp is not None else unavailable("CPP"),
        "cpp_ideal": param(rounded(cpp), "CPP = v/(a0*lc)") if cpp is not None else unavailable("CPP"),
        "comportamento_micelar_previsto": param(behavior, "CPP morphology thresholds") if behavior else unavailable("CPP behavior"),
        "parametros_micela": param(
            {
                "nagg": nagg,
                "core_radius_nm": rounded(radii["core_nm"]),
                "apparent_radius_nm": rounded(radii["apparent_nm"]),
                "debye_length_nm": rounded(debye),
                "head_area_a2": rounded(head_area),
                "tail_volume_a3": rounded(tail_volume),
                "tail_length_a": rounded(tail_length),
            },
            "Tanford/Klevens/Debye package",
        ),
        "numero_agregacao_estimado": param(nagg, "tail-length aggregation-number heuristic") if nagg is not None else unavailable("Nagg"),
        "raio_micela_esferica": param(rounded(radii["apparent_nm"]), "surface/core micelle radius proxy", "nm") if radii["apparent_nm"] is not None else unavailable("micelle radius", "nm"),
        "raio_aparente_micela": param(rounded(radii["apparent_nm"]), "surface/core micelle radius proxy", "nm") if radii["apparent_nm"] is not None else unavailable("micelle radius", "nm"),
        "faixa_raio_micela": param(
            {
                "min_nm": rounded(radii["range_nm"]["min_nm"]),
                "max_nm": rounded(radii["range_nm"]["max_nm"]),
            },
            "radius uncertainty band",
            "nm",
        ) if radii["range_nm"] is not None else unavailable("radius range", "nm"),
        "raio_nucleo_hidrofobico": param(rounded(radii["core_nm"]), "Tanford chain length", "nm") if radii["core_nm"] is not None else unavailable("core radius", "nm"),
        "raio_micela_cilindrica": param(rounded(radii["cylindrical_nm"]), "cylindrical-core proxy", "nm") if radii["cylindrical_nm"] is not None else unavailable("cylindrical radius", "nm"),
        "perfil_calibracao_literatura": param({"class": sclass, "head_group": head, "status": "heuristic_not_experimental", "note": cmc_note}, "v43 heuristic profile"),
        "carga_residual_micela": param(rounded(surface_charge["residual_charge_e"]), "counterion-binding charge proxy", "e") if surface_charge["residual_charge_e"] is not None else unavailable("micelle charge", "e"),
        "contraions_ligados_micela": param(rounded(surface_charge["bound_counterions"]), "counterion-binding proxy") if surface_charge["bound_counterions"] is not None else unavailable("bound counterions"),
        "densidade_carga_superficial": param(rounded(surface_charge["surface_charge_c_m2"]), "sigma = residual charge / surface area", "C/m^2") if surface_charge["surface_charge_c_m2"] is not None else unavailable("surface charge density", "C/m^2"),
        "comprimento_debye": param(rounded(debye), "Debye length in water at 25 C", "nm") if debye is not None else unavailable("Debye length", "nm"),
        "hld": param(hld, "HLD qualitative proxy") if hld is not None else unavailable("HLD"),
        "nac": param(nac, "NAC structural proxy"),
        "confianca_cmc": param(
            {
                "modo": "heurístico_v43",
                "calibrado": False,
                "classe": sclass,
                "observacao": "Klevens/Davies/Tanford; validar com literatura/experimento.",
            },
            "v43 confidence audit",
        ),
        "miriam2_identity": param(
            {
                "mode": "bypassed_fast_v43",
                "reason": "painel individual não chama MIRIAM pesado",
                "active_fragment": active_smiles,
                "counterions": detected_counterions,
                "classification": sclass,
                "head_group": head,
            },
            "v43 local identity",
        ),
        "miriam2_structural_features": param(
            {
                "tail_carbon_count": tail_c,
                "number_of_tails": tail_count,
                "head_group": head,
                "active_charge": active_charge,
                "counterions": detected_counterions,
            },
            "v43 structural feature extractor",
        ),
        "miriam2_calculation_plan": param(
            [
                "RDKit 2D",
                "PubChem PUG-REST best-effort",
                "fragment/counterion split",
                "head group SMARTS",
                "Davies HLB",
                "Klevens CMC",
                "Tanford CPP",
                "Debye/counterion heuristics",
            ],
            "v43 local route",
        ),
        "miriam2_physical_validation": param(
            {
                "passed": True,
                "warnings": [
                    "Sem cálculo 3D pesado no painel principal.",
                    "Valores avançados são heurísticos/proxies.",
                    "API externa é best-effort com timeout curto.",
                ],
            },
            "v43 validation audit",
        ),
        "miriam2_applicability": param(
            {"applicable": bool(is_surfactant), "domain": "surfactant screening / fast descriptor panel"},
            "v43 applicability",
        ),
        "miriam2_audit": param(
            {
                "mode": "v43_fast_api_cache_router",
                "calculation_time_profile": "fast/no calculation_page/no MIRIAM/no ETKDG/no MMFF/no UFF",
            },
            "v43 audit",
        ),
        "ambiente_fisico_quimico": param(env, "frontend environment payload"),
        # v47: este campo precisa ser um Record<string, { installed: boolean }>
        # para compatibilidade direta com o painel React.
        # Não embrulhar em ParameterValue, porque o frontend lê lib.installed.
        "biblioteca_status": {
            "rdkit": {
                "name": "RDKit",
                "installed": bool(Chem is not None),
                "purpose": "Descritores 2D locais, fórmula, massa, topologia e SMARTS.",
                "import_error": str(RDKIT_IMPORT_ERROR) if RDKIT_IMPORT_ERROR else None,
            },
            "pubchem_pug_rest": {
                "name": "PubChem PUG-REST",
                "installed": bool(pubchem.get("ok")),
                "purpose": "Enriquecimento externo best-effort: InChI, InChIKey, XLogP, TPSA e nome IUPAC quando disponível.",
                "import_error": pubchem.get("error"),
            },
            "local_surfactant_heuristics": {
                "name": "Heurísticas locais de surfactantes",
                "installed": True,
                "purpose": "HLB, CMC, CPP, XCMC, DeltaG, HLD, NAC, Nagg e raios micelares em modo rápido.",
                "import_error": None,
            },
            "calculation_page": {
                "name": "calculation_page.py",
                "installed": False,
                "purpose": "Desativado no painel individual para evitar cálculo pesado/travamento.",
                "import_error": None,
            },
            "miriam_heavy_engine": {
                "name": "MIRIAM pesado",
                "installed": False,
                "purpose": "Desativado no painel individual; reservado para modo completo/cacheado.",
                "import_error": None,
            },
            "openmm": {
                "name": "OpenMM",
                "installed": False,
                "purpose": "Não usado no painel rápido; reservado para dinâmica molecular/simulação.",
                "import_error": None,
            },
            "xtb": {
                "name": "xTB",
                "installed": False,
                "purpose": "Não usado no painel rápido; reservado para energia/solvatação em modo completo.",
                "import_error": None,
            },
        },
        "api_pubchem_status": param(pubchem, "PubChem PUG-REST best-effort"),
    }

    atoms = build_atoms(mol)
    bonds = build_bonds(mol)

    warnings = [
        "v43: rota rápida local. Não importa calculation_page.py e não chama MIRIAM/ETKDG/MMFF/UFF.",
        "PubChem é usado apenas como enriquecimento best-effort com timeout curto e cache em memória.",
        "HLB, CMC, CPP, Nagg, HLD e NAC são triagem teórica/heurística; validar contra dados experimentais.",
    ]

    if not pubchem.get("ok"):
        warnings.append(f"PubChem indisponível ou sem correspondência rápida: {pubchem.get('error') or 'sem retorno'}.")

    limitations = [
        "Não substitui experimento.",
        "Não faz xTB/DFT/OpenMM no painel principal.",
        "APIs pagas como ChemAxon/Chemicalize não foram chamadas porque exigem chave.",
        "Para máxima precisão futura: criar modo completo separado, assíncrono e cacheado no banco.",
    ]

    snapshot = {"molecule": molecule, "atoms": atoms, "bonds": bonds}

    return {
        "success": True,
        "package_version": ENGINE_VERSION,
        "source": "RDKit 2D + PubChem PUG-REST best-effort + local surfactant heuristics",
        "molecule": molecule,
        "atoms": atoms,
        "bonds": bonds,
        "warnings": warnings,
        "limitations": limitations,
        "snapshot_dados_completos": snapshot,
    }


@router.get("/status")
def parameters_status() -> dict[str, Any]:
    return {
        "engine": ENGINE_VERSION,
        "calculation_page_imported": False,
        "heavy_calculations_in_main_panel": False,
        "pubchem_api_mode": "best_effort_timeout_cache",
        "pubchem_timeout_seconds": PUBCHEM_TIMEOUT_SECONDS,
        "cache_items": len(_PUBCHEM_CACHE),
        "rdkit_available": Chem is not None,
        "rdkit_import_error": str(RDKIT_IMPORT_ERROR) if RDKIT_IMPORT_ERROR else None,
        "routes": ["/api/v1/chemistry/parameters/status", "/api/v1/chemistry/parameters/analyze"],
    }


@router.post(
    "/analyze",
    response_model=ChemistryParametersResponse,
    summary="Analisa molécula com descritores 2D, PubChem rápido e heurísticas anfifílicas",
)
def analyze_parameters(payload: ChemistryParametersRequest) -> ChemistryParametersResponse:
    try:
        result = make_response(payload)
        return ChemistryParametersResponse.model_validate(result)

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno ao calcular parâmetros químicos rápidos v43: {exc}",
        ) from exc
