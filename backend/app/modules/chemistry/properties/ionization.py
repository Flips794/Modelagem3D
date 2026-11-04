"""Sítios ionizáveis, pKa referenciado, carga líquida estimada e espécie predominante no pH.

Modelo e limites (declarados nos campos):
- pKa é o valor experimental do composto-modelo do grupo (ex.: ácido acético para
  carboxila), não uma medição da molécula analisada; erro típico de ±1 unidade.
- Ácidos fortes (sulfônico, monoéster sulfúrico, 1ª dissociação de fosfato monoéster)
  não recebem número: só um limite superior; abaixo dele a carga fica indisponível.
- Pares acoplados conhecidos usam os dois pKa medidos no mesmo composto (glicina,
  sarcosina, betaína, fosfato monoéster). Outros sítios tituláveis próximos
  (≤ 7 ligações) são marcados como acoplados e não recebem carga/espécie/LogD,
  porque presumir independência comprometeria o resultado.
- Henderson–Hasselbalch por sítio; sem tautomeria, atividade iônica ou temperatura.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Literal

from rdkit import Chem
from rdkit.Chem import Crippen

from app.modules.chemistry.properties.base import (
    PropertyBundle,
    PropertyContext,
    not_applicable,
    unavailable,
    value,
)

SiteKind = Literal["acid", "base", "permanent_cation", "permanent_anion"]
SOURCE = "Tabela SMARTS de pKa de compostos-modelo + Henderson–Hasselbalch"
# Quando há sítio ionizável, estes campos do painel vêm deste provedor (substituem o cálculo legado,
# que tratava LogD = logP em moléculas com ácido + amina, como a glicina).
AUTHORITATIVE_FIELDS = ("pka", "logd")
COUPLING_MAX_BONDS = 7
MODEL_NOTE = ("pKa do composto-modelo do grupo (referência indicada em cada sítio); não é medição desta molécula. "
              "Henderson–Hasselbalch por sítio, sem tautomeria nem atividade iônica; erro típico ±1 unidade de pKa.")

CRC = "CRC Handbook of Chemistry and Physics — Dissociation Constants of Organic Acids and Bases (25 °C)"
REF_BETAINE = "Glicina betaína, carboxila: pKa 1,83 (1,84 em outra fonte; medido a 0 °C)"
REF_SARCOSINE = "Sarcosina: carboxila 2,21; amina 10,1 (fontes: 10,01–10,2)"
REF_GLYCINE = f"Glicina: carboxila 2,34; amina 9,60 ({CRC})"
REF_TMAO = "N-óxido de trimetilamina: pKa 4,65 (valor experimental, FooDB)"
REF_DIMETHYL_PHOSPHATE = "Dimetil fosfato: pKa 1,29 (compilação de pKa Jencks–Westheimer, R. Williams)"
REF_METHYL_PHOSPHATE = "Metil fosfato: 2º pKa ≈ 6,3; 1ª dissociação forte (pKa < 2), sem valor numérico verificado"
REF_STRONG_SULFUR = "Ácidos alquilsulfônicos e monoésteres sulfúricos: ácidos fortes (pKa < 0); sem valor numérico atribuído"
REF_PERMANENT = "Carga permanente (sem próton titulável)"


@dataclass(frozen=True)
class IonizableSite:
    atom_idx: int
    group: str
    pka: float | None
    kind: SiteKind
    reference: str
    pka_upper_bound: float | None = None   # só para ácido forte sem pKa numérico
    pair_id: int | None = None             # par acoplado validado (mesmo composto-modelo)
    coupled: bool = False                  # acoplado a outro sítio sem padrão validado

    @property
    def titratable(self) -> bool:
        return self.kind in ("acid", "base")


# Pares validados: (grupo, SMARTS, [(posição do átomo-sítio, tipo, pKa, limite)], referência)
_ACID_O = "[OX2H1,OX1-]"
VALIDATED_PAIRS = [
    ("betaína", f"[NX4+;H0;!$(N-[O-]);!$(N-[OH])]-[CX4]-C(=O){_ACID_O}",
     [(0, "permanent_cation", None, None), (4, "acid", 1.83, None)], REF_BETAINE),
    ("α-aminoácido (glicina)", f"[NX3H2,NX4H3+;!$(N-C=O)]-[CX4]-C(=O){_ACID_O}",
     [(0, "base", 9.60, None), (4, "acid", 2.34, None)], REF_GLYCINE),
    ("N-alquil α-aminoácido (sarcosina)", f"[NX3H1,NX4H2+;!$(N-C=O)](-[#6])-[CX4]-C(=O){_ACID_O}",
     [(0, "base", 10.1, None), (5, "acid", 2.21, None)], REF_SARCOSINE),
    ("fosfato monoéster", f"[#6]-O-P(=O)({_ACID_O}){_ACID_O}",
     [(4, "acid", None, 2.0), (5, "acid", 6.3, None)], REF_METHYL_PHOSPHATE),
]

# Sítios isolados: (grupo, SMARTS cujo 1º átomo é o sítio, tipo, pKa, limite, referência). Ordem importa.
_NOT_AMIDE = "!$(N-C=[O,S,N]);!$(N-S(=O));!$(N-[!#6;!#1])"
SINGLE_SITES = [
    ("N-óxido de amina", "[OX1-,OX2H1;$(O-[NX4+;H0])]", "base", 4.65, None, REF_TMAO),
    ("ácido sulfônico/sulfato", "[OX2H1,OX1-;$(O-[SX4](=O)=O)]", "acid", None, 0.0, REF_STRONG_SULFUR),
    ("fosfato diéster", "[OX2H1,OX1-;$(O-P(=O)(O[#6])O[#6])]", "acid", 1.29, None, REF_DIMETHYL_PHOSPHATE),
    ("ácido carboxílico", "[OX2H1,OX1-;$(O-[CX3]=O);!$(O-C(=O)-[O,N])]", "acid", 4.76, None, f"Ácido acético 4,76 ({CRC})"),
    ("fenol", "[OX2H1,OX1-;$(O-c)]", "acid", 9.99, None, f"Fenol 9,99 ({CRC})"),
    ("imidazol", "[$([nX2;r5]:c:[nH1;r5]),$([nH1+;r5]:c:[nH1;r5])]", "base", 6.95, None, f"Imidazol 6,95 ({CRC})"),
    ("piridina", "[$([nX2;r6;!$(n:n)]),$([nH1+;r6])]", "base", 5.23, None, f"Piridina 5,23 ({CRC})"),
    ("anilina", f"[$([NX3;H2,H1,H0;{_NOT_AMIDE};$(N-c)]),$([NX4+;H3,H2,H1;$(N-c)])]", "base", 4.60, None,
     f"Anilina 4,60 ({CRC})"),
    ("amina primária", f"[$([NX3H2;{_NOT_AMIDE};!$(N-a)]),$([NX4H3+;!$(N-a)])]", "base", 10.66, None,
     f"Metilamina 10,66 ({CRC})"),
    ("amina secundária", f"[$([NX3H1;{_NOT_AMIDE};!$(N-a)]),$([NX4H2+;!$(N-a)])]", "base", 10.73, None,
     f"Dimetilamina 10,73 ({CRC})"),
    ("amina terciária", f"[$([NX3H0;{_NOT_AMIDE};!$(N-a);!$(N=*)]),$([NX4H1+;!$(N-a)])]", "base", 9.80, None,
     f"Trimetilamina 9,80 ({CRC})"),
    ("amônio quaternário", "[NX4+;H0;!$(N-[O-]);!$(N-[OH])]", "permanent_cation", None, None, REF_PERMANENT),
    ("piridínio N-substituído", "[n+;H0;!$(n-[O-])]", "permanent_cation", None, None, REF_PERMANENT),
    ("fosfônio", "[PX4+;H0]", "permanent_cation", None, None, REF_PERMANENT),
]
_COMPILED_PAIRS = [(g, Chem.MolFromSmarts(s), roles, r) for g, s, roles, r in VALIDATED_PAIRS]
_COMPILED_SINGLE = [(g, Chem.MolFromSmarts(s), k, p, b, r) for g, s, k, p, b, r in SINGLE_SITES]


def ionizable_sites(mol: Chem.Mol, atoms: set[int] | None = None) -> list[IonizableSite]:
    """Sítios ionizáveis (opcionalmente só entre `atoms`). Independe do estado de protonação desenhado."""
    allowed = set(range(mol.GetNumAtoms())) if atoms is None else set(atoms)
    taken: set[int] = set()
    found: list[IonizableSite] = []
    pair_counter = 0
    for group, pattern, roles, reference in _COMPILED_PAIRS:
        for match in mol.GetSubstructMatches(pattern):
            site_atoms = [match[pos] for pos, *_ in roles]
            if any(a in taken or a not in allowed for a in site_atoms):
                continue
            pair_counter += 1
            for (pos, kind, pka, bound), atom in zip(roles, site_atoms):
                found.append(IonizableSite(atom, group, pka, kind, reference, bound, pair_counter))
                taken.add(atom)
    for group, pattern, kind, pka, bound, reference in _COMPILED_SINGLE:
        for match in mol.GetSubstructMatches(pattern):
            atom = match[0]
            if atom in taken or atom not in allowed:
                continue
            found.append(IonizableSite(atom, group, pka, kind, reference, bound))
            taken.add(atom)
    found.sort(key=lambda s: s.atom_idx)
    return _mark_couplings(mol, found)


def _mark_couplings(mol: Chem.Mol, sites: list[IonizableSite]) -> list[IonizableSite]:
    if len(sites) < 2:
        return sites
    distance = Chem.GetDistanceMatrix(mol)
    coupled: set[int] = set()
    for i, a in enumerate(sites):
        for b in sites[i + 1:]:
            if a.pair_id is not None and a.pair_id == b.pair_id:
                continue
            if not (a.titratable or b.titratable):
                continue
            strong = lambda s: s.kind == "acid" and s.pka is None  # noqa: E731
            if strong(a) and strong(b):
                continue
            limit = COUPLING_MAX_BONDS if (a.titratable and b.titratable) else 3
            if distance[a.atom_idx][b.atom_idx] <= limit:
                coupled.update((a.atom_idx, b.atom_idx))
    return [replace(s, coupled=s.atom_idx in coupled) for s in sites]


def _protonated_fraction(site: IonizableSite, ph: float) -> float | None:
    if site.pka is not None:
        return 1.0 / (1.0 + 10.0 ** (ph - site.pka))
    if site.pka_upper_bound is not None and ph >= site.pka_upper_bound + 1.0:
        return 0.0
    return None


def _contributions(sites: list[IonizableSite], ph: float) -> list[float] | None:
    if any(s.coupled for s in sites):
        return None
    values: list[float] = []
    for site in sites:
        if site.kind == "permanent_cation":
            values.append(1.0)
        elif site.kind == "permanent_anion":
            values.append(-1.0)
        else:
            fraction = _protonated_fraction(site, ph)
            if fraction is None:
                return None
            values.append(fraction if site.kind == "base" else -(1.0 - fraction))
    return values


def net_charge_at_ph(sites: list[IonizableSite], ph: float) -> float | None:
    """Carga líquida média estimada; None se o modelo não se aplica (acoplamento, ácido forte fora da faixa)."""
    contributions = _contributions(sites, ph)
    return None if contributions is None else float(sum(contributions))


def effective_species(sites: list[IonizableSite], ph: float) -> Literal["anionic", "cationic", "nonionic", "zwitterionic"] | None:
    contributions = _contributions(sites, ph)
    if contributions is None:
        return None
    positive = sum(c for c in contributions if c > 0)
    negative = -sum(c for c in contributions if c < 0)
    if positive >= 0.5 and negative >= 0.5:
        return "zwitterionic"
    net = positive - negative
    if net <= -0.5:
        return "anionic"
    if net >= 0.5:
        return "cationic"
    return "nonionic"


def _set_state(atom: Chem.Atom, site: IonizableSite, protonated: bool) -> None:
    """Ajusta carga/H do átomo-sítio para o estado pedido (a partir do estado desenhado)."""
    hydrogens = atom.GetTotalNumHs()
    atom.SetNumExplicitHs(hydrogens)   # fixa os H atuais antes de desligar os implícitos
    atom.SetNoImplicit(True)
    if site.group == "N-óxido de amina":
        atom.SetFormalCharge(0 if protonated else -1)
        atom.SetNumExplicitHs(1 if protonated else 0)
    elif site.kind == "acid":
        if protonated and atom.GetFormalCharge() == -1:
            atom.SetFormalCharge(0)
            atom.SetNumExplicitHs(hydrogens + 1)
        elif not protonated and atom.GetFormalCharge() == 0 and hydrogens > 0:
            atom.SetFormalCharge(-1)
            atom.SetNumExplicitHs(hydrogens - 1)
    elif site.kind == "base":
        if protonated and atom.GetFormalCharge() == 0:
            atom.SetFormalCharge(1)
            atom.SetNumExplicitHs(hydrogens + 1)
        elif not protonated and atom.GetFormalCharge() == 1 and hydrogens > 0:
            atom.SetFormalCharge(0)
            atom.SetNumExplicitHs(hydrogens - 1)


def _species_mol(mol: Chem.Mol, states: dict[int, bool], sites: list[IonizableSite]) -> Chem.Mol | None:
    copy = Chem.RWMol(mol)
    for site in sites:
        if site.atom_idx in states:
            _set_state(copy.GetAtomWithIdx(site.atom_idx), site, states[site.atom_idx])
    try:
        result = copy.GetMol()
        Chem.SanitizeMol(result)
        return result
    except Exception:  # noqa: BLE001
        return None


def compute(ctx: PropertyContext) -> PropertyBundle:
    mol, ph = ctx.mol, float(ctx.env.get("ph", 7.0))
    active = set(ctx.active_atom_indices)
    sites = ionizable_sites(mol, active)
    bundle = PropertyBundle()
    note = MODEL_NOTE + " Só o fragmento ativo (contraíons não entram)."

    bundle.molecule["sitios_ionizaveis"] = value(
        [{"atom_idx": s.atom_idx, "grupo": s.group, "tipo": s.kind, "pka": s.pka,
          "pka_limite_superior": s.pka_upper_bound, "acoplado": s.coupled, "referencia": s.reference} for s in sites],
        SOURCE, confidence="estimated", note=note)

    if not sites:
        reason = "nenhum grupo ionizável reconhecido na faixa de pH 0–14"
        # pka/logd ficam com o cálculo legado (logD = logP para moléculas sem sítio ionizável).
        for key in ("estado_protonacao_ph", "especie_predominante_ph"):
            bundle.molecule[key] = not_applicable(reason, SOURCE)
        bundle.molecule["carga_liquida_ph"] = value(0.0, SOURCE, "e", confidence="estimated", note=note)
        return bundle

    coupled = [s for s in sites if s.coupled]
    if coupled:
        reason = (f"sítios ionizáveis acoplados (≤ {COUPLING_MAX_BONDS} ligações) sem pKa macroscópico validado; "
                  "presumir independência comprometeria o resultado")
        for key in ("carga_liquida_ph", "estado_protonacao_ph", "especie_predominante_ph", "logd"):
            bundle.molecule[key] = unavailable(reason, SOURCE, "e" if key == "carga_liquida_ph" else None)
        return bundle

    net = net_charge_at_ph(sites, ph)
    if net is None:
        reason = f"pH {ph:g} abaixo do limite em que a dissociação do ácido forte pode ser tratada como completa"
        for key in ("carga_liquida_ph", "estado_protonacao_ph", "especie_predominante_ph", "logd"):
            bundle.molecule[key] = unavailable(reason, SOURCE)
        return bundle

    states: dict[int, bool] = {}
    rows = []
    for site in sites:
        if site.titratable:
            fraction = _protonated_fraction(site, ph)
            states[site.atom_idx] = fraction >= 0.5
            rows.append({"atom_idx": site.atom_idx, "grupo": site.group, "pka": site.pka,
                         "fracao_protonada": round(fraction, 6),
                         "estado_predominante": "protonado" if fraction >= 0.5 else "desprotonado"})
        else:
            rows.append({"atom_idx": site.atom_idx, "grupo": site.group, "pka": None,
                         "fracao_protonada": None, "estado_predominante": "carga permanente"})
    bundle.molecule["carga_liquida_ph"] = value(round(net, 4), SOURCE, "e", confidence="estimated",
                                                note=f"Carga líquida média estimada no pH {ph:g} (difere da carga formal do desenho). " + note)
    bundle.molecule["estado_protonacao_ph"] = value(rows, SOURCE, confidence="estimated", note=f"pH {ph:g}. " + note)

    species_mol = _species_mol(mol, states, sites)
    species_smiles = (Chem.MolFragmentToSmiles(species_mol, atomsToUse=sorted(active))
                      if species_mol is not None else None)
    bundle.molecule["especie_predominante_ph"] = value(
        {"ph": ph, "classe": effective_species(sites, ph), "smiles": species_smiles}, SOURCE,
        confidence="estimated", note="Microespécie com cada sítio no estado predominante (>50 %). " + note)

    bundle.molecule["pka"] = _pka_field(sites, note)
    bundle.molecule["logd"] = _logd_field(mol, sites, states, active, ph, note)
    return bundle


def _pka_field(sites: list[IonizableSite], note: str):
    titratable = [s for s in sites if s.titratable]
    if len(titratable) == 1 and titratable[0].pka is not None:
        return value(titratable[0].pka, SOURCE, confidence="estimated", note=titratable[0].reference + ". " + note)
    if not titratable:
        return not_applicable("sem sítio titulável (apenas cargas permanentes)", SOURCE)
    return unavailable("mais de um sítio ou ácido forte: ver 'sitios_ionizaveis' para os pKa por sítio", SOURCE)


def _logd_field(mol, sites, states, active, ph: float, note: str):
    if any(not s.titratable for s in sites):
        return unavailable("íon permanente: LogD por Henderson–Hasselbalch não se aplica", SOURCE)
    if any(s.pka is None for s in sites):
        return unavailable("ácido forte sem pKa numérico", SOURCE)
    if {s.kind for s in sites} == {"acid", "base"}:
        return unavailable("anfotérico/zwitteriônico: forma neutra ambígua; LogD exige modelo de especiação", SOURCE)
    neutral_states = {s.atom_idx: (s.kind == "acid") for s in sites}   # ácido protonado, base desprotonada
    neutral = _species_mol(mol, neutral_states, sites)
    if neutral is None:
        return unavailable("não foi possível montar a forma neutra", SOURCE)
    fragment = Chem.MolFromSmiles(Chem.MolFragmentToSmiles(neutral, atomsToUse=sorted(active)))
    if fragment is None:
        return unavailable("não foi possível montar a forma neutra", SOURCE)
    neutral_fraction = 1.0
    for site in sites:
        fraction = _protonated_fraction(site, ph)
        neutral_fraction *= fraction if site.kind == "acid" else (1.0 - fraction)
    if neutral_fraction < 1e-12:
        return unavailable("espécie neutra desprezível neste pH", SOURCE)
    logd = Crippen.MolLogP(fragment) + math.log10(neutral_fraction)
    return value(round(logd, 5), SOURCE + " + logP Crippen da forma neutra", confidence="estimated",
                 note=f"LogD (pH {ph:g}) = logP(neutra) + log10(fração neutra); íons não particionam no modelo. " + note)
