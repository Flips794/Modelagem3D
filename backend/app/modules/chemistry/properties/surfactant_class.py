"""Classificação de surfactantes por regras químicas verificáveis (sem IA treinada).

- Classe estrutural: definida pelos grupos ionizáveis e pela carga permanente; não
  muda com o pH.
- Espécie no pH: calculada à parte, pelo modelo de ionização (pode faltar, quando o
  modelo não se aplica, ex.: sítios acoplados).
- Classes não exclusivas: `compatible_classes` lista as classificações que a
  literatura usa para a mesma estrutura (ex.: betaína carboxílica é zwitteriônica e
  também tratada como anfotérica, porque a carboxila protona em pH ácido).
- Papel anfifílico: anfifílicos de cabeça fraca (um único –OH, –COOH neutro ou amina
  neutra) ficam como "surfactant_or_cosurfactant", sem classificação absoluta.
"""
from __future__ import annotations

from dataclasses import dataclass

from rdkit import Chem

from app.modules.chemistry.properties.base import PropertyBundle, PropertyContext, value
from app.modules.chemistry.properties.ionization import (
    IonizableSite,
    effective_species,
    ionizable_sites,
    net_charge_at_ph,
)

SOURCE = "Regras químicas (SMARTS + sítios ionizáveis), sem IA treinada"
CLASS_LABEL_PT = {"anionic": "aniônico", "cationic": "catiônico", "nonionic": "não iônico",
                  "zwitterionic": "zwitteriônico", "amphoteric": "anfotérico", "unknown": "não surfactante"}
WEAK_HEAD_NOTE = ("Cabeça polar fraca: pode atuar como surfactante ou cossurfactante, conforme o sistema "
                  "(outros surfactantes, óleo, concentração). A v1 não decide esse papel.")


@dataclass(frozen=True)
class SurfactantClassification:
    structural_class: str
    compatible_classes: tuple[str, ...]
    amphiphile_role: str            # surfactant | surfactant_or_cosurfactant | none
    confidence: str                 # high | medium | low
    rules_fired: tuple[str, ...]
    justification: str


def _describe(site: IonizableSite) -> str:
    if site.kind == "permanent_cation":
        return f"{site.group} (carga positiva permanente)"
    if site.pka is not None:
        return f"{site.group} ({'ácido' if site.kind == 'acid' else 'base'}, pKa {site.pka:g} do composto-modelo)"
    if site.pka_upper_bound is not None:
        return f"{site.group} (ácido forte, pKa < {site.pka_upper_bound:g})"
    return site.group


def _weak_head(active: Chem.Mol, sites: list[IonizableSite]) -> str | None:
    """Tipo de cabeça fraca (alcohol/acid/amine) ou None."""
    hetero = [a for a in active.GetAtoms() if a.GetAtomicNum() not in (1, 6)]
    if any(a.GetFormalCharge() for a in active.GetAtoms()):
        return None
    oxygens = [a for a in hetero if a.GetAtomicNum() == 8]
    nitrogens = [a for a in hetero if a.GetAtomicNum() == 7]
    if len(hetero) == 1 and oxygens and oxygens[0].GetTotalNumHs() == 1 and not oxygens[0].GetIsAromatic():
        return "alcohol"
    if len(hetero) == 2 and len(oxygens) == 2 and len(sites) == 1 and sites[0].group == "ácido carboxílico":
        return "acid"
    if len(hetero) == 1 and nitrogens and len(sites) == 1 and sites[0].group.startswith("amina"):
        return "amine"
    return None


def classify(active: Chem.Mol, is_surfactant: bool, head: str, tail_c: int) -> SurfactantClassification:
    sites = ionizable_sites(active)
    acids = [s for s in sites if s.kind == "acid"]
    bases = [s for s in sites if s.kind == "base"]
    permanent_pos = [s for s in sites if s.kind == "permanent_cation"]
    titratable_acid = [s for s in acids if s.pka is not None]
    groups = "; ".join(_describe(s) for s in sites) or "nenhum grupo ionizável"
    rules: list[str] = [f"{s.kind}:{s.group}" for s in sites]

    if permanent_pos and acids:
        cls, conf = "zwitterionic", "high"
        compatible = ("zwitterionic", "amphoteric") if titratable_acid else ("zwitterionic",)
        rule = "cátion permanente + grupo aniônico → zwitteriônico"
        if titratable_acid:
            rule += "; grupo ácido protonável em pH baixo → também tratado como anfotérico"
    elif any(s.group == "N-óxido de amina" for s in bases) and not acids:
        cls, conf, compatible = "amphoteric", "medium", ("amphoteric", "nonionic")
        rule = "N-óxido de amina: catiônico em pH ácido (N–OH⁺), não iônico em pH neutro/básico"
    elif bases and acids:
        cls, conf, compatible = "amphoteric", "medium", ("amphoteric", "zwitterionic")
        rule = "base ionizável + ácido ionizável → anfotérico (zwitteriônico perto do ponto isoelétrico)"
    elif acids:
        cls, conf, compatible = "anionic", "high", ("anionic",)
        rule = "somente grupos ácidos → aniônico"
    elif bases or permanent_pos:
        cls, conf, compatible = "cationic", ("high" if permanent_pos else "medium"), ("cationic",)
        rule = "carga positiva permanente → catiônico" if permanent_pos else \
            "somente base ionizável → catiônico quando protonada (depende do pH)"
    elif head != "none":
        cls, conf, compatible = "nonionic", "high", ("nonionic",)
        rule = "cabeça polar sem grupo ionizável na faixa de pH 0–14 → não iônico"
        rules.append(f"polar:{head}")
    else:
        cls, conf, compatible = "unknown", "high", ()
        rule = "sem cabeça polar reconhecida"
        rules.append("sem_cabeca_polar")
    rules.append(f"regra:{cls}")

    if not is_surfactant:
        reason = ("cauda hidrofóbica curta" if tail_c < 8 else "estrutura fora do critério anfifílico")
        return SurfactantClassification(
            "unknown", (), "none", "high" if tail_c < 6 else "medium", tuple(rules) + ("nao_surfactante",),
            f"Não surfactante: {reason} (maior cadeia carbônica: {tail_c} C). Grupos: {groups}. "
            f"Tipo químico dos grupos: {rule}.")

    weak = _weak_head(active, sites)
    if weak is not None:
        return SurfactantClassification(
            cls, compatible, "surfactant_or_cosurfactant", "low", tuple(rules) + (f"cabeca_fraca:{weak}",),
            f"{WEAK_HEAD_NOTE} Grupos: {groups}. Classe pelo grupo: {rule}.")

    multiple_heads = len({s.group for s in sites if s.kind != "permanent_cation"}) > 2
    if multiple_heads and conf == "high":
        conf = "medium"
    if any(s.coupled for s in sites) and conf == "high":
        conf = "medium"
    return SurfactantClassification(cls, compatible, "surfactant", conf, tuple(rules),
                                    f"Grupos: {groups}. Regra: {rule}. Cauda: {tail_c} C.")


def species_at_ph(active: Chem.Mol, ph: float) -> dict:
    sites = ionizable_sites(active)
    titratable = [s for s in sites if s.kind in ("acid", "base")]
    statuses = {s.reference_status for s in titratable}
    status = ("a revisar" if "a revisar" in statuses else
              "sem valor numérico" if "sem valor numérico" in statuses else
              "consolidada" if titratable else "não se aplica")
    species = effective_species(sites, ph)
    net = net_charge_at_ph(sites, ph)
    if any(s.coupled for s in sites):
        note = "sítios ionizáveis acoplados sem pKa macroscópico validado: espécie não estimada"
    elif species is None:
        note = "pH fora da faixa em que o modelo de ionização se aplica"
    else:
        note = "pKa de compostos-modelo; não é medição desta molécula"
    return {"ph": ph, "species": species, "net_charge": None if net is None else round(net, 4),
            "reference_status": status, "note": note}


def compute(ctx: PropertyContext) -> PropertyBundle:
    classification = getattr(ctx.structure, "classification", None)
    bundle = PropertyBundle()
    if classification is None:
        return bundle
    species = species_at_ph(ctx.structure.active, float(ctx.env.get("ph", 7.0)))
    bundle.molecule["classificacao_surfactante"] = value(
        {"classe": classification.structural_class,
         "classe_pt": CLASS_LABEL_PT[classification.structural_class],
         "classes_compativeis": list(classification.compatible_classes),
         "papel": classification.amphiphile_role, "confianca": classification.confidence,
         "justificativa": classification.justification, "regras": list(classification.rules_fired),
         "especie_no_ph": species},
        SOURCE, confidence=classification.confidence,
        note="Classe estrutural (não muda com o pH) separada da espécie no pH; confiança qualitativa, não calibrada.")
    return bundle
