"""Exemplos documentados de morfologias (complemento da Web Lite 1.0).

Cinco exemplos fixos com condições tiradas de referências experimentais. Cada condição declara a sua
natureza: "experimental" (medida ou observada na referência), "protocol" (prática de preparo citada) ou
"technical" (tolerância de entrada, limite físico do meio ou concordância com o modelo — nunca faixa
experimental). Só o SDS é previsão do motor; os demais são demonstrações representativas: a forma vem
do catálogo, não de CMC/CPP calculados. Spec: docs/superpowers/specs/2026-11-05-exemplos-documentados-morfologias-design.md
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal

from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors

from app.modules.micelium.schemas import MiceliumSimulationRequest

DocumentedExampleId = Literal[
    "sds_esferica", "ctab_nasal_vermiforme", "dppc_bicamada_hidratacao", "dppc_vesicula_extrusao",
    "aot_inversa_isooctano",
]
ConditionBasis = Literal["experimental", "protocol", "technical"]
ExampleRole = Literal["core_water", "interfacial_aromatic_anion"]

EXAMPLE_VERSION = "1.0.0"
LAST_REVIEWED_AT = "2026-11-05"
OUT_OF_RANGE_PREFIX = "fora das condições documentadas: "


@dataclass(frozen=True)
class Reference:
    label: str
    url: str | None = None


@dataclass(frozen=True)
class Condition:
    """Linha de condição. Sem limites nem `allowed`, é só informativa (não é conferida)."""
    parameter: str
    label: str
    basis: ConditionBasis
    source: str
    minimum: float | None = None
    maximum: float | None = None
    allowed: tuple[str, ...] | None = None
    exclusive_minimum: bool = False
    exclusive_maximum: bool = False

    @property
    def enforced(self) -> bool:
        return self.minimum is not None or self.maximum is not None or self.allowed is not None


@dataclass(frozen=True)
class ExampleComponent:
    key: str
    name: str
    smiles: str
    role: Literal["reagent", "solvent"]
    amount_mmol: float | None
    is_surfactant: bool | None = None
    tail_carbon_count: int | None = None
    tail_chain_count: int | None = None
    example_role: ExampleRole | None = None
    derived_from_w0: bool = False


@dataclass(frozen=True)
class DocumentedExample:
    id: str
    title: str
    kind: Literal["validated_prediction", "representative_demo"]
    documented_morphology: str
    components: tuple[ExampleComponent, ...]
    environment: dict[str, float | str]
    conditions: tuple[Condition, ...]
    protocol: str
    references: tuple[Reference, ...]
    notes: tuple[str, ...]
    w0: float | None = None
    example_version: str = EXAMPLE_VERSION
    last_reviewed_at: str = LAST_REVIEWED_AT


@dataclass(frozen=True)
class ExampleVerdict:
    within_range: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)
    w0: float | None = None


SDS = "CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]"
CTAB = "CCCCCCCCCCCCCCCC[N+](C)(C)C.[Br-]"
NASAL = "O=C([O-])c1ccccc1O.[Na+]"
DPPC = "CCCCCCCCCCCCCCCC(=O)OCC(COP(=O)([O-])OCC[N+](C)(C)C)OC(=O)CCCCCCCCCCCCCCC"
AOT = "CCCCC(CC)COC(=O)CC(C(=O)OCC(CC)CCCC)S(=O)(=O)[O-].[Na+]"
WATER = "O"
ISOOCTANE = "CC(C)CC(C)(C)C"

WATER_SOLVENT = ExampleComponent("agua", "Água", WATER, "solvent", None)

REF_NSRDS = Reference("Mukerjee & Mysels, NSRDS-NBS 36 (1971): CMC de 8,16 mM a 25 °C", None)
REF_SDS_SANS = Reference("SANS de micelas de SDS em água sem sal (elipsoide levemente achatado)",
                         "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4487321/")
REF_LAM = Reference("Lam, Hong, Do & Chen (ORNL), Evolution of CTAB/NaSal Micelles: Structural Analysis by SANS",
                    "https://arxiv.org/abs/1812.07138")
REF_NMR_SAL = Reference("Olsson, Söderman & Guéring, J. Phys. Chem. 90 (1986) 5223; Rao, Manohar et al., "
                        "J. Phys. Chem. 91 (1987) 3286 — RMN: anel do salicilato inserido, carboxilato para fora", None)
REF_TM = Reference("Transição principal do DPPC (Tm = 41 °C) e extrusão 10–20 °C acima de Tm",
                   "https://pmc.ncbi.nlm.nih.gov/articles/PMC3508262/")
REF_BANGHAM = Reference("Bangham, Standish & Watkins, J. Mol. Biol. 13 (1965) 238–252: lamelas de fosfolipídio hidratado",
                        None)
REF_HOPE = Reference("Hope, Bally, Webb & Cullis, Biochim. Biophys. Acta 812 (1985) 55–65: extrusão por 100 nm, "
                     "vesículas unilamelares de 60–100 nm", "https://pubmed.ncbi.nlm.nih.gov/23008845/")
REF_POSITRON = Reference("Aniquilação de pósitrons em água/AOT/isooctano, 0,1 M de AOT: raio do núcleo ≈ 0,186·w0 nm "
                         "a 298 K", "https://baes.uc.pt/bitstream/10316/10313/1/Four-Component%20Analysis%20and%20Modeling%20of%20Positron%20Annihilation.pdf")
REF_BOHIDAR = Reference("Bohidar & Behboudnia, Colloids Surf. A (2001): gotas esféricas até w0 ≤ 20 com 100 mM de AOT (DLS)",
                        None)
REF_ABEL = Reference("Abel et al., J. Phys. Chem. B (2004): gotas levemente elipsoidais (eixos 1,24–1,41)",
                     "https://pubs.acs.org/doi/10.1021/jp047138e")
REF_FAYER = Reference("Fayer et al.: em w0 = 10, água de núcleo e interfacial com dinâmicas distintas",
                      "https://pmc.ncbi.nlm.nih.gov/articles/PMC2721765")
REF_STENUTZ = Reference("Constante dielétrica do isooctano 1,94 (tabela Stenutz, fonte secundária)",
                        "https://www.stenutz.eu/chem/solv23.php?s=3&p=1")

DPPC_COMPONENT = ExampleComponent("dppc", "DPPC", DPPC, "reagent", 1.0, is_surfactant=True, tail_carbon_count=16,
                                  tail_chain_count=2)

EXAMPLES: dict[str, DocumentedExample] = {
    "sds_esferica": DocumentedExample(
        id="sds_esferica",
        title="SDS — micela esférica (aproximação)",
        kind="validated_prediction",
        documented_morphology="micela esférica",
        components=(ExampleComponent("sds", "SDS", SDS, "reagent", 3.0), WATER_SOLVENT),
        environment={"volume_ml": 100.0, "temperature_k": 298.15, "ionic_strength_mol_l": 0.01,
                     "solvent_name": "água", "dielectric_constant": 78.5, "solvent_polarity_index": 1.0},
        conditions=(
            Condition("solvent", "solvente: água", "experimental", REF_SDS_SANS.label, allowed=("água",)),
            Condition("c_over_cmc", "c/CMC > 1", "experimental", REF_NSRDS.label, minimum=1.0, exclusive_minimum=True),
            Condition("temperature_c", "20–30 °C (limite técnico: domínio da correlação de CMC do projeto)",
                      "technical", "domínio da correlação de CMC do projeto", minimum=20.0, maximum=30.0),
            Condition("ionic_strength", "força iônica ≤ 0,07 mol/L (limite técnico: concordância do modelo atual)",
                      "technical", "maior força iônica em que o modelo atual ainda prevê esfera; a literatura situa "
                      "a transição esfera→bastão acima de ~0,2–0,3 mol/L de NaCl (pendência registrada)",
                      maximum=0.07),
        ),
        protocol="SDS 3 mmol em 100 mL de água (30 mM), 25 °C, sem sal adicionado.",
        references=(REF_NSRDS, REF_SDS_SANS),
        notes=("Forma prevista pelo cálculo atual (CMC experimental e CPP do motor).",
               "Os estudos de SANS descrevem a micela de SDS em água sem sal como elipsoide levemente achatado: "
               "'esférica' é uma aproximação."),
    ),
    "ctab_nasal_vermiforme": DocumentedExample(
        id="ctab_nasal_vermiforme",
        title="CTAB + salicilato de sódio — micela cilíndrica/vermiforme",
        kind="representative_demo",
        documented_morphology="micela cilíndrica/wormlike",
        components=(
            ExampleComponent("ctab", "CTAB", CTAB, "reagent", 1.0),
            ExampleComponent("nasal", "Salicilato de sódio", NASAL, "reagent", 5.0,
                             example_role="interfacial_aromatic_anion"),
            WATER_SOLVENT,
        ),
        environment={"volume_ml": 100.0, "temperature_k": 293.15, "ionic_strength_mol_l": 0.06,
                     "solvent_name": "água", "dielectric_constant": 78.5, "solvent_polarity_index": 1.0},
        conditions=(
            Condition("ctab_mm", "CTAB 2,5–15 mM", "experimental", REF_LAM.label, minimum=2.5, maximum=15.0),
            Condition("nasal_ratio", "razão NaSal/CTAB 2,5–10", "experimental",
                      REF_LAM.label + ": vermiformes nessa razão em todas as concentrações de CTAB estudadas",
                      minimum=2.5, maximum=10.0),
            Condition("temperature_c", "temperatura 20,0 °C (único valor medido)", "experimental", REF_LAM.label),
            Condition("temperature_c", "tolerância de entrada ± 0,5 K em torno de 20,0 °C (limite técnico)",
                      "technical", "só arredondamento do campo; o estudo não mediu outras temperaturas",
                      minimum=19.5, maximum=20.5),
            Condition("solvent", "solvente: água (amostras do estudo em D₂O)", "experimental", REF_LAM.label,
                      allowed=("água",)),
        ),
        protocol="CTAB 10 mM e salicilato de sódio 50 mM (razão 5) em água a 20 °C. Força iônica 0,06 mol/L "
                 "derivada de ½Σcz² com dissociação completa.",
        references=(REF_LAM, REF_NMR_SAL),
        notes=("Demonstração representativa: a forma vem do estudo de SANS, não de CMC/CPP calculados.",
               "Raio da seção transversal medido ≈ 22 Å; CMC do CTAB em água 0,9 mM a 25 °C (citada no mesmo artigo).",
               "Salicilato na interface, anel para dentro e carboxilato para o meio: regra representativa baseada em RMN.",
               "As amostras do estudo foram feitas em D₂O."),
    ),
    "dppc_bicamada_hidratacao": DocumentedExample(
        id="dppc_bicamada_hidratacao",
        title="DPPC — recorte de bicamada de uma estrutura lamelar (hidratação)",
        kind="representative_demo",
        documented_morphology="bicamada plana/lamelar",
        components=(DPPC_COMPONENT, WATER_SOLVENT),
        environment={"volume_ml": 100.0, "temperature_k": 328.15, "ionic_strength_mol_l": 0.01,
                     "solvent_name": "água", "dielectric_constant": 78.5, "solvent_polarity_index": 1.0},
        conditions=(
            Condition("temperature_c", "temperatura > 41 °C (Tm)", "experimental", REF_TM.label, minimum=41.0,
                      exclusive_minimum=True),
            Condition("method", "método: hidratação de filme seco, sem extrusão", "protocol", REF_BANGHAM.label),
            Condition("solvent", "solvente: água", "protocol", REF_BANGHAM.label, allowed=("água",)),
            Condition("temperature_c", "temperatura < 100 °C (limite técnico: água líquida a 1 atm)", "technical",
                      "limite físico do meio; não há limite superior experimental documentado aqui",
                      maximum=100.0, exclusive_maximum=True),
        ),
        protocol="Filme seco de DPPC hidratado em água acima de Tm (55 °C), sem extrusão.",
        references=(REF_BANGHAM, REF_TM),
        notes=("Demonstração por protocolo: a forma não é previsão espontânea do motor; CMC não é usada.",
               "A hidratação produz uma dispersão multilamelar (lamelas concêntricas), não uma bicamada plana isolada: "
               "a cena mostra um recorte representativo de uma lamela.",
               "Quantidade ilustrativa (1 mmol em 100 mL): o protocolo não fixa uma concentração única.",
               "Duas caudas palmitoíla (16 C) por molécula."),
    ),
    "dppc_vesicula_extrusao": DocumentedExample(
        id="dppc_vesicula_extrusao",
        title="DPPC — vesícula unilamelar (extrusão)",
        kind="representative_demo",
        documented_morphology="vesícula/bicamada fechada",
        components=(DPPC_COMPONENT, WATER_SOLVENT),
        environment={"volume_ml": 100.0, "temperature_k": 328.15, "ionic_strength_mol_l": 0.01,
                     "solvent_name": "água", "dielectric_constant": 78.5, "solvent_polarity_index": 1.0},
        conditions=(
            Condition("method", "método: extrusão repetida por filtro de policarbonato de 100 nm", "experimental",
                      REF_HOPE.label),
            Condition("temperature_c", "temperatura de extrusão 51–61 °C (10–20 °C acima de Tm)", "protocol",
                      REF_TM.label, minimum=51.0, maximum=61.0),
            Condition("solvent", "solvente: água", "protocol", REF_HOPE.label, allowed=("água",)),
        ),
        protocol="Dispersão de DPPC hidratada e extrudada repetidamente por membrana de 100 nm a 55 °C.",
        references=(REF_HOPE, REF_TM),
        notes=("Demonstração por protocolo: a forma não é previsão espontânea do motor; CMC não é usada.",
               "Vesículas unilamelares de 60–100 nm na referência; a cena mostra uma vesícula em escala reduzida.",
               "Quantidade ilustrativa (1 mmol em 100 mL): o protocolo não fixa uma concentração única.",
               "Duas caudas palmitoíla (16 C) por molécula."),
    ),
    "aot_inversa_isooctano": DocumentedExample(
        id="aot_inversa_isooctano",
        title="AOT em isooctano — micela inversa com núcleo aquoso (w0 = 10)",
        kind="representative_demo",
        documented_morphology="micela inversa",
        components=(
            ExampleComponent("aot", "AOT", AOT, "reagent", 10.0, is_surfactant=True, tail_carbon_count=8,
                             tail_chain_count=2),
            ExampleComponent("agua", "Água (núcleo, derivada de w0)", WATER, "reagent", 100.0,
                             example_role="core_water", derived_from_w0=True),
            ExampleComponent("isooctano", "Isooctano", ISOOCTANE, "solvent", None),
        ),
        environment={"volume_ml": 100.0, "temperature_k": 298.15, "ionic_strength_mol_l": 0.0,
                     "solvent_name": "isooctano", "dielectric_constant": 1.94},
        conditions=(
            Condition("w0", "w0 = 10", "experimental", REF_POSITRON.label + "; " + REF_FAYER.label),
            Condition("w0", "tolerância de entrada de w0 ± 0,5 (limite técnico)", "technical",
                      "só arredondamento do campo; abaixo de 10 a forma tende a elipsoidal e a água a interfacial, "
                      "acima de 20 as gotas se deformam ou alongam", minimum=9.5, maximum=10.5),
            Condition("aot_m", "AOT 0,1 M", "experimental", REF_POSITRON.label + "; " + REF_BOHIDAR.label),
            Condition("aot_m", "tolerância de entrada de AOT ± 1 % (limite técnico)", "technical",
                      "só arredondamento do campo", minimum=0.099, maximum=0.101),
            Condition("temperature_c", "temperatura 25 °C", "experimental", REF_POSITRON.label),
            Condition("temperature_c", "tolerância de entrada ± 0,5 K (limite técnico)", "technical",
                      "só arredondamento do campo", minimum=24.5, maximum=25.5),
            Condition("solvent", "solvente: isooctano", "experimental", REF_POSITRON.label, allowed=("isooctano",)),
        ),
        protocol="AOT 0,1 M em isooctano com água em w0 = [H₂O]/[AOT] = 10, a 25 °C.",
        references=(REF_POSITRON, REF_BOHIDAR, REF_ABEL, REF_FAYER, REF_STENUTZ),
        notes=("Demonstração representativa: a forma vem dos estudos citados; CMC não se aplica (meio apolar).",
               "Forma aproximadamente esférica (pode ser levemente elipsoidal). Raio do núcleo aquoso ≈ 1,9 nm em w0 = 10.",
               "A água é derivada de w0 (n(água) = w0 × n(AOT)); a contagem visual de águas é sublinear e não representa "
               "w0 numericamente.",
               "Duas caudas 2-etil-hexila (8 C) por molécula; a ramificação não é representada."),
        w0=10.0,
    ),
}


@lru_cache(maxsize=256)
def canonical_smiles(smiles: str) -> str | None:
    mol = Chem.MolFromSmiles(smiles or "")
    return Chem.MolToSmiles(mol) if mol is not None else None


_SOLVENT_NAMES = {canonical_smiles(WATER): "água", canonical_smiles(ISOOCTANE): "isooctano"}


def _solvent_label(request: MiceliumSimulationRequest) -> str:
    solvents = [m for m in request.molecules if m.role == "solvent"]
    if solvents:
        return _SOLVENT_NAMES.get(canonical_smiles(solvents[0].smiles), (solvents[0].name or "").strip().lower())
    name = (request.environment.solvent_name or "").strip().lower()
    return "água" if name in {"água", "agua", "water", "h2o"} else name


def _reagent_amounts(example: DocumentedExample, request: MiceliumSimulationRequest) -> tuple[dict[str, float], bool]:
    """mmol por chave de componente; False se houver reagente fora do exemplo."""
    by_smiles = {canonical_smiles(c.smiles): c.key for c in example.components if c.role == "reagent"}
    amounts: dict[str, float] = {}
    extra = False
    for molecule in request.molecules:
        if molecule.role == "solvent":
            continue
        key = by_smiles.get(canonical_smiles(molecule.smiles))
        if key is None:
            extra = True
            continue
        volume_l = request.environment.volume_ml / 1000.0
        mmol = molecule.real_amount_mmol
        if mmol is None and molecule.real_concentration_mmol_l is not None:
            mmol = molecule.real_concentration_mmol_l * volume_l
        amounts[key] = amounts.get(key, 0.0) + float(mmol or 0.0)
    return amounts, not extra


def example_context(example: DocumentedExample, request: MiceliumSimulationRequest,
                    c_over_cmc: float | None) -> dict[str, float | str | None]:
    env = request.environment
    volume_l = env.volume_ml / 1000.0
    amounts, _ = _reagent_amounts(example, request)
    mm = {key: value / volume_l for key, value in amounts.items()}
    context: dict[str, float | str | None] = {
        "temperature_c": round(env.temperature_k - 273.15, 6),
        "ionic_strength": env.ionic_strength_mol_l,
        "c_over_cmc": c_over_cmc,
        "solvent": _solvent_label(request),
        "ctab_mm": mm.get("ctab"),
        "nasal_ratio": mm["nasal"] / mm["ctab"] if mm.get("ctab") and "nasal" in mm else None,
        "aot_m": mm["aot"] / 1000.0 if "aot" in mm else None,
        "w0": amounts["agua"] / amounts["aot"] if amounts.get("aot") and amounts.get("agua") else None,
    }
    return context


def _check(condition: Condition, value) -> bool:
    if value is None:
        return False
    if condition.allowed is not None:
        return str(value) in condition.allowed
    if condition.minimum is not None:
        if value < condition.minimum or (condition.exclusive_minimum and value == condition.minimum):
            return False
    if condition.maximum is not None:
        if value > condition.maximum or (condition.exclusive_maximum and value == condition.maximum):
            return False
    return True


_PARAMETER_WORDS = {"temperature_c": "temperatura", "ionic_strength": "força iônica", "c_over_cmc": "c/CMC",
                    "solvent": "solvente", "ctab_mm": "CTAB", "nasal_ratio": "razão NaSal/CTAB", "aot_m": "AOT",
                    "w0": "w0"}


def evaluate(example: DocumentedExample, request: MiceliumSimulationRequest, c_over_cmc: float | None) -> ExampleVerdict:
    amounts, only_known = _reagent_amounts(example, request)
    expected = {c.key for c in example.components if c.role == "reagent"}
    missing = expected - set(amounts)
    context = example_context(example, request, c_over_cmc)
    w0 = context["w0"] if isinstance(context["w0"], float) else None
    reasons: list[str] = []
    derived = {c.key for c in example.components if c.derived_from_w0}
    if not only_known or (missing - derived):
        reasons.append("componentes diferentes do exemplo")
    elif missing & derived:
        reasons.append("w0 indefinido")
    if not reasons:
        for condition in example.conditions:
            if not condition.enforced:
                continue
            value = context.get(condition.parameter)
            if not _check(condition, value):
                word = _PARAMETER_WORDS.get(condition.parameter, condition.parameter)
                shown = f"{value:.4g}" if isinstance(value, float) else (value if value is not None else "indefinido")
                reasons.append(f"{word} = {shown} fora de: {condition.label}")
    return ExampleVerdict(within_range=not reasons, reasons=tuple(reasons), w0=w0)


def _formula_and_mass(smiles: str) -> tuple[str, float]:
    mol = Chem.MolFromSmiles(smiles)
    return rdMolDescriptors.CalcMolFormula(mol), round(float(Descriptors.MolWt(mol)), 3)


def catalog_payload() -> list[dict]:
    """Catálogo para o painel 2D→3D (fórmula e massa molar calculadas pelo RDKit)."""
    out = []
    for example in EXAMPLES.values():
        components = []
        for c in example.components:
            formula, molar_mass = _formula_and_mass(c.smiles)
            components.append({"key": c.key, "name": c.name, "smiles": c.smiles, "role": c.role,
                               "amount_mmol": c.amount_mmol, "formula": formula, "molar_mass": molar_mass,
                               "is_surfactant": c.is_surfactant, "tail_carbon_count": c.tail_carbon_count,
                               "tail_chain_count": c.tail_chain_count, "example_role": c.example_role,
                               "derived_from_w0": c.derived_from_w0})
        out.append({
            "id": example.id, "title": example.title, "kind": example.kind,
            "example_version": example.example_version, "last_reviewed_at": example.last_reviewed_at,
            "documented_morphology": example.documented_morphology, "components": components,
            "environment": dict(example.environment),
            "conditions": [condition_payload(c) for c in example.conditions],
            "protocol": example.protocol,
            "references": [{"label": r.label, "url": r.url} for r in example.references],
            "notes": list(example.notes), "w0": example.w0,
        })
    return out


def condition_payload(condition: Condition) -> dict:
    return {"parameter": condition.parameter, "label": condition.label, "basis": condition.basis,
            "source": condition.source, "minimum": condition.minimum, "maximum": condition.maximum,
            "allowed": list(condition.allowed) if condition.allowed is not None else None}
