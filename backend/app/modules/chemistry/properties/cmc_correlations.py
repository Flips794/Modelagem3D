"""CMC por família de homólogos, ajustada a dados experimentais do NSRDS-NBS 36 (NIST).

log10(CMC / mol·L⁻¹) = a + b·n            (famílias de cauda única)
log10(CMC / mol·L⁻¹) = a + b·n + c·m      (álcoois etoxilados CnEm)

- Dados: data/cmc_homologs.json (água pura, sem aditivo, 20–30 °C), cada ponto com
  referência, condição, unidade e página do PDF do NIST conferida visualmente.
- Validação: leave-one-out (LOO). LOO máx. ≤ 0,3 em log10 → confiança "estimated";
  0,3–0,5 → "low"; > 0,5 → família excluída. Mín. 3 homólogos (5 pontos para CnEm).
- Sem extrapolação: n e m precisam estar dentro da faixa dos dados da família.
- Famílias SDS/CTAB continuam no cálculo existente (validated_calculations); aqui
  os dados delas servem só para validar e como CMC experimental de referência.

Uso: python -m app.modules.chemistry.properties.cmc_correlations --relatorio CAMINHO.md
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from rdkit import Chem

from app.modules.chemistry.properties.base import PropertyBundle, PropertyContext, not_applicable, value

DATA_PATH = Path(__file__).parent / "data" / "cmc_homologs.json"
SOURCE_LABEL = "NSRDS-NBS 36 (Mukerjee & Mysels 1971, NIST)"
GLUCOSIDE_BETA_D = "O[C@@H]1O[C@H](CO)[C@@H](O)[C@H](O)[C@H]1O"   # (2R,3S,4S,5R,6R), conferido por CIP
LOO_ESTIMATED = 0.3
LOO_LOW = 0.5
T_MIN_K, T_MAX_K = 293.15, 303.15
IONIC_MAX_I = 0.01
NONIONIC_MAX_I = 0.1

# família → (modelo de SMILES do fragmento ativo, contraíons, iônica?, usa m?)
FAMILY_TEMPLATES = {
    "sodium_alkanesulfonate": (lambda n, m: "C" * n + "S(=O)(=O)[O-]", {"[Na+]"}, True, False),
    "alkyltrimethylammonium_chloride": (lambda n, m: "C" * n + "[N+](C)(C)C", {"[Cl-]"}, True, False),
    "alkylpyridinium_chloride": (lambda n, m: "C" * n + "[n+]1ccccc1", {"[Cl-]"}, True, False),
    "alkyl_beta_glucoside": (lambda n, m: "C" * n + GLUCOSIDE_BETA_D, set(), False, False),
    "alcohol_ethoxylate": (lambda n, m: "C" * n + "OCC" * m + "O", set(), False, True),
    # Só validação/consulta experimental (o cálculo destas fica em validated_calculations):
    "sodium_alkyl_sulfate": (lambda n, m: "C" * n + "OS(=O)(=O)[O-]", {"[Na+]"}, True, False),
    "alkyltrimethylammonium_bromide": (lambda n, m: "C" * n + "[N+](C)(C)C", {"[Br-]"}, True, False),
}
FIT_FAMILIES = ("sodium_alkanesulfonate", "alkyltrimethylammonium_chloride", "alkylpyridinium_chloride",
                "alkyl_beta_glucoside", "alcohol_ethoxylate")
EXCLUDED_FAMILIES = {
    "alquilcarboxilato de sódio": "só 2 homólogos na tabela recomendada (C10, C12; qualidade DB)",
    "óxido de alquildimetilamina": "só 2 homólogos (C9 a 25 °C; C12 a 27 °C)",
    "alquilbenzenossulfonato de sódio": "homólogos em temperaturas diferentes (C10 a 50 °C, C12 a 25 °C)",
    "brometo de alquilpiridínio": "só 2 homólogos (C12, C16)",
    "alquilbetaína / sulfobetaína": "sem valores na tabela recomendada",
}


@dataclass(frozen=True)
class FamilyFit:
    family: str
    a: float
    b: float
    c: float | None
    n_min: int
    n_max: int
    m_min: int | None
    m_max: int | None
    points: int
    loo_errors: tuple[float, ...]
    loo_max_abs_log_error: float
    confidence: str
    ionic: bool


@lru_cache(maxsize=1)
def _raw() -> dict:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def dataset() -> list[dict]:
    return list(_raw()["pontos"])


def _design(rows: list[dict], uses_m: bool) -> tuple[np.ndarray, np.ndarray]:
    x = np.array([[1.0, r["n"]] + ([r["m"]] if uses_m else []) for r in rows])
    y = np.array([math.log10(r["cmc_mol_l"]) for r in rows])
    return x, y


@lru_cache(maxsize=1)
def fitted_constants() -> dict[str, FamilyFit]:
    fits: dict[str, FamilyFit] = {}
    for family in FIT_FAMILIES:
        rows = [r for r in dataset() if r["family"] == family and r["uso"] == "fit"]
        uses_m = FAMILY_TEMPLATES[family][3]
        minimum = 5 if uses_m else 3
        if len(rows) < minimum or (uses_m and len({r["m"] for r in rows}) < 2):
            continue
        x, y = _design(rows, uses_m)
        coef = np.linalg.lstsq(x, y, rcond=None)[0]
        errors = []
        for i in range(len(rows)):
            keep = [j for j in range(len(rows)) if j != i]
            loo_coef = np.linalg.lstsq(x[keep], y[keep], rcond=None)[0]
            errors.append(float(abs(x[i] @ loo_coef - y[i])))
        worst = max(errors)
        if worst > LOO_LOW:
            continue
        fits[family] = FamilyFit(
            family, float(coef[0]), float(coef[1]), float(coef[2]) if uses_m else None,
            min(r["n"] for r in rows), max(r["n"] for r in rows),
            min(r["m"] for r in rows) if uses_m else None, max(r["m"] for r in rows) if uses_m else None,
            len(rows), tuple(round(e, 4) for e in errors), round(worst, 4),
            "estimated" if worst <= LOO_ESTIMATED else "low", FAMILY_TEMPLATES[family][2])
    return fits


@lru_cache(maxsize=1)
def _template_index() -> dict[tuple[str, frozenset], tuple[str, int, int | None]]:
    index = {}
    for family, (template, counterions, _ionic, uses_m) in FAMILY_TEMPLATES.items():
        for n in range(4, 25):
            for m in (range(1, 41) if uses_m else [None]):
                mol = Chem.MolFromSmiles(template(n, m))
                index[(Chem.MolToSmiles(mol), frozenset(counterions))] = (family, n, m)
    return index


def detect_family(p) -> tuple[str, int, int | None] | None:
    """Família/homólogo por igualdade de SMILES (isomérico: anômero do glicosídeo importa)."""
    active = Chem.MolToSmiles(p.active)
    others = frozenset(Chem.MolToSmiles(f) for f in p.others)
    return _template_index().get((active, others))


def _range_text(fit: FamilyFit) -> str:
    text = f"faixa de n {fit.n_min}–{fit.n_max}"
    if fit.c is not None:
        text += f", m {fit.m_min}–{fit.m_max}"
    return text


def family_cmc(p, env: dict) -> dict:
    """Mesmo formato de validated.cmc_estimate, com 'confidence' e 'origin'."""
    unavailable = {"reference_mmol_l": None, "value": None, "method": "not_available", "confidence": "unavailable",
                   "origin": "indisponível", "note": "Família sem correlação de CMC verificada na v1."}
    detected = detect_family(p)
    if detected is None or detected[0] not in fitted_constants():
        return unavailable
    family, n, m = detected
    fit = fitted_constants()[family]
    method = f"{SOURCE_LABEL} homolog fit: {family}"
    base_note = (f"Correlação log10(CMC) = a + b·n{' + c·m' if fit.c is not None else ''} ajustada a dados "
                 f"experimentais {SOURCE_LABEL} em água pura (20–30 °C); {_range_text(fit)}; "
                 f"erro LOO máx. {fit.loo_max_abs_log_error:.2f} em log10 ({fit.points} pontos).")
    out_of_range = not fit.n_min <= n <= fit.n_max or (fit.c is not None and not fit.m_min <= m <= fit.m_max)
    if out_of_range:
        return {**unavailable, "method": method, "note": f"Homólogo fora da faixa dos dados ({_range_text(fit)}); sem extrapolação."}
    solvent = str(env.get("solvent_name", env.get("solvent", "water"))).strip().lower()
    if (solvent not in {"water", "água", "agua", "h2o"} or float(env.get("dielectric_constant", 78.5)) < 60
            or float(env.get("solvent_polarity_index", 1)) < 0.9):
        return {**unavailable, "method": method, "note": "Correlação válida só em água; outro solvente não é extrapolado."}
    temperature = float(env.get("temperature_k", 298.15))
    if not T_MIN_K <= temperature <= T_MAX_K:
        return {**unavailable, "method": method, "note": "Dados a 20–30 °C; outra temperatura não é extrapolada."}
    ionic = float(env.get("ionic_strength_mol_l", 0.01))
    note = base_note
    if fit.ionic and ionic > IONIC_MAX_I:
        return {**unavailable, "method": method,
                "note": f"Família iônica sem dados com sal: só para força iônica ≤ {IONIC_MAX_I} mol/L."}
    if not fit.ionic:
        if ionic > NONIONIC_MAX_I:
            return {**unavailable, "method": method, "note": f"Força iônica acima de {NONIONIC_MAX_I} mol/L não é extrapolada."}
        if ionic > IONIC_MAX_I:
            note += " Efeito do sal desprezado (não iônico, força iônica ≤ 0,1 mol/L)."
    log_cmc = fit.a + fit.b * n + (fit.c * m if fit.c is not None else 0.0)
    cmc_mmol_l = 10 ** log_cmc * 1000.0
    if fit.confidence == "low":
        note += " Erro de validação alto: estimativa de baixa confiança."
    return {"reference_mmol_l": cmc_mmol_l, "value": cmc_mmol_l, "method": method, "confidence": fit.confidence,
            "origin": "calculada (correlação ajustada a dados experimentais NSRDS-NBS 36)", "note": note}


def experimental_cmc(p) -> dict | None:
    detected = detect_family(p)
    if detected is None:
        return None
    family, n, m = detected
    rows = [r for r in dataset() if r["family"] == family and r["n"] == n and r["m"] == m]
    if not rows:
        return None
    row = rows[0]
    return {"value_mmol_l": round(row["cmc_mol_l"] * 1000.0, 6), "t_c": row["t_c"], "referencia": row["referencia_nsrds"],
            "unidade_original": row["unidade_original"], "avaliacao": row["avaliacao_nsrds"],
            "pagina": row["pagina_livro"], "metodo": row["metodo"]}


def compute(ctx: PropertyContext) -> PropertyBundle:
    from app.modules.chemistry.parameters import validated_calculations as validated   # evita ciclo
    bundle = PropertyBundle()
    structure = ctx.structure
    estimate = validated.cmc_estimate(structure, ctx.env)
    bundle.molecule["cmc_origem"] = value(estimate.get("origin", "indisponível"), "Web Lite v1", confidence="high",
                                          note="experimental = medido (NSRDS); calculada = correlação ajustada a dados; "
                                               "estimada = âncora + inclinação de homólogos com correção empírica.")
    experimental = experimental_cmc(structure)
    if experimental is None:
        bundle.molecule["cmc_experimental"] = not_applicable(
            "composto sem medição na tabela recomendada do NSRDS-NBS 36", SOURCE_LABEL, "mmol/L")
    else:
        bundle.molecule["cmc_experimental"] = value(
            experimental["value_mmol_l"], SOURCE_LABEL, "mmol/L", confidence="experimental",
            note=(f"Medido em água pura, sem sal, a {experimental['t_c']:g} °C ({experimental['metodo']}); "
                  f"{SOURCE_LABEL}, ref. {experimental['referencia']}, p. {experimental['pagina']}, avaliação "
                  f"{experimental['avaliacao']}, unidade original {experimental['unidade_original']}. "
                  "Pode diferir do ambiente atual (temperatura, sal)."))
    return bundle


def report_markdown() -> str:
    lines = ["# CMC por família — validação (Web Lite v1)", "",
             f"Fonte: {SOURCE_LABEL}, tabela de valores recomendados e selecionados; cada ponto conferido na imagem da página.",
             "", "| Família | a | b (por C) | c (por EO) | Faixa | Pontos | Erros LOO (log10) | LOO máx. | Confiança |",
             "|---|---|---|---|---|---|---|---|---|"]
    for family, fit in fitted_constants().items():
        lines.append(f"| {family} | {fit.a:.4f} | {fit.b:.4f} | {'' if fit.c is None else f'{fit.c:.4f}'} | "
                     f"{_range_text(fit)} | {fit.points} | {', '.join(f'{e:.2f}' for e in fit.loo_errors)} | "
                     f"{fit.loo_max_abs_log_error:.2f} | {fit.confidence} |")
    lines += ["", "## Famílias excluídas", ""] + [f"- {k}: {v} (excluída)." for k, v in EXCLUDED_FAMILIES.items()]
    lines += ["", "## Validação das correlações existentes (SDS/CTAB, não alteradas)", "",
              "| Composto | NSRDS (mmol/L) | Correlação existente (mmol/L) | Erro log10 |", "|---|---|---|---|"]
    from app.modules.chemistry.parameters import validated_calculations as validated
    env = {"solvent_name": "water", "temperature_k": 298.15, "ionic_strength_mol_l": 0.01}
    for row in [r for r in dataset() if r["uso"] == "validacao"]:
        template, counterions, _ionic, _m = FAMILY_TEMPLATES[row["family"]]
        smiles = ".".join([template(row["n"], None)] + sorted(counterions))
        reference = validated.cmc_estimate(validated.profile(Chem.MolFromSmiles(smiles)), env)["reference_mmol_l"]
        measured = row["cmc_mol_l"] * 1000
        lines.append(f"| {row['family']} C{row['n']} | {measured:.4g} | {reference:.4g} | {math.log10(reference / measured):+.2f} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--relatorio", required=True)
    Path(parser.parse_args().relatorio).write_text(report_markdown(), encoding="utf-8")
