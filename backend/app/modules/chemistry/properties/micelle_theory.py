"""Teoria micelar leve: geometria de Tanford e ΔG de micelização (pseudofase).

- Tanford (cadeia hidrocarbonada saturada, ~25 °C):
  l_max = 0,154 + 0,1265·n  (nm)      v = 0,0274 + 0,0269·n  (nm³)
- Limite geométrico da esfera: N ≤ (4/3)·π·l_max³ / v (Israelachvili–Mitchell–Ninham, 1976).
  É um limite superior de empacotamento, não o número de agregação.
- ΔG°mic (pseudofase, X = c/(55,5 + c)): não iônico ΔG = RT·ln X; iônico ΔG = (1+β)·RT·ln X,
  que exige β — sem β de referência, fica indisponível.
- β e espessura da cabeça só a partir de data/micelle_reference.json (vazio na v1).
Previsões teóricas: não são resultado de simulação nem de dinâmica molecular.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

from app.modules.chemistry.properties.base import (
    PropertyBundle,
    PropertyContext,
    not_applicable,
    unavailable,
    value,
)

SOURCE = "Tanford (1972) + Israelachvili–Mitchell–Ninham (1976); pseudofase"
R_GAS = 8.31446261815324
WATER_MOLARITY = 55.5
NOT_MD = "Modelo teórico geométrico/termodinâmico; não é resultado de dinâmica molecular nem de simulação."
REFERENCE_PATH = Path(__file__).parent / "data" / "micelle_reference.json"
RADIUS_FIELDS = ("raio_micela_esferica", "raio_aparente_micela", "faixa_raio_micela")
BETA_FIELDS = {"carga_residual_micela": "e", "contraions_ligados_micela": None, "densidade_carga_superficial": "C/m^2"}


def tanford(n: int) -> tuple[float, float]:
    """(l_max em nm, v em nm³) de uma cadeia saturada com n carbonos."""
    return 0.154 + 0.1265 * n, 0.0274 + 0.0269 * n


def nagg_upper_sphere(n: int) -> float:
    length, volume = tanford(n)
    return 4.0 / 3.0 * math.pi * length ** 3 / volume


def delta_g_mic_kj_mol(cmc_mmol_l: float, temperature_k: float, beta: float | None, ionic: bool) -> float | None:
    if cmc_mmol_l is None or cmc_mmol_l <= 0 or temperature_k <= 0:
        return None
    cmc_mol_l = cmc_mmol_l / 1000.0
    rt_ln_x = R_GAS * temperature_k * math.log(cmc_mol_l / (WATER_MOLARITY + cmc_mol_l)) / 1000.0
    if ionic:
        return None if beta is None else (1.0 + beta) * rt_ln_x
    return rt_ln_x


@lru_cache(maxsize=1)
def micelle_reference() -> dict:
    return json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))


def compute(ctx: PropertyContext) -> PropertyBundle:
    from app.modules.chemistry.parameters import validated_calculations as validated   # evita ciclo
    p = ctx.structure
    bundle = PropertyBundle()
    fields = bundle.molecule
    geometric = ("numero_agregacao_estimado", "nagg_maximo_geometrico_esfera", "raio_nucleo_hidrofobico",
                 "raio_micela_cilindrica", *RADIUS_FIELDS)

    if not p.is_surfactant or p.amphiphile_role != "surfactant":
        reason = ("anfifílico de cabeça fraca (surfactante ou cossurfactante): teoria micelar não aplicada"
                  if p.amphiphile_role == "surfactant_or_cosurfactant" else "não surfactante")
        for key in geometric + tuple(BETA_FIELDS) + ("delta_g_micelizacao", "teoria_micelar_info"):
            fields[key] = not_applicable(reason, SOURCE)
        return bundle

    ionic = p.chemical_class in ("anionic", "cationic")
    for key, unit in BETA_FIELDS.items():
        fields[key] = (unavailable("requer β (fração de contraíons ligados) sem valor de referência verificado", SOURCE, unit)
                       if ionic else not_applicable("micela sem contraíons ligados (grandeza de micelas iônicas)", SOURCE, unit))

    cmc = validated.cmc_estimate(p, ctx.env).get("value")
    temperature = float(ctx.env.get("temperature_k", 298.15))
    if ionic:
        fields["delta_g_micelizacao"] = unavailable(
            "surfactante iônico: ΔG = (1+β)·RT·ln X_cmc requer β sem valor de referência verificado", SOURCE, "kJ/mol")
    elif cmc is None:
        fields["delta_g_micelizacao"] = unavailable("sem CMC no domínio de aplicação", SOURCE, "kJ/mol")

    packing = validated.packing_estimate(p)
    cpp = packing.get("cpp")
    if not (p.linear_hydrocarbon and p.tail_count == 1 and cpp is not None):
        reason = "requer cauda hidrocarbonada linear única (ramificada, múltiplas caudas ou fora do domínio do CPP)"
        for key in geometric:
            fields[key] = unavailable(reason, SOURCE)
        fields["teoria_micelar_info"] = unavailable(reason, SOURCE)
        return bundle

    n = p.tail_c
    length, volume = tanford(n)
    temp_note = "" if 283.15 <= temperature <= 333.15 else " Constantes de Tanford são de ~25 °C; temperatura fora de 10–60 °C."
    fields["numero_agregacao_estimado"] = unavailable(
        "requer modelo adicional fundamentado (termodinâmica de micelização); a v1 informa só o limite geométrico", SOURCE)
    fields["nagg_maximo_geometrico_esfera"] = value(
        round(nagg_upper_sphere(n), 4), SOURCE, confidence="estimated",
        note=f"Limite superior geométrico (4/3·π·l_max³/v) para esfera de cadeias estendidas; não é o número de agregação. {NOT_MD}{temp_note}")
    head_area = packing.get("head_area_a2")
    head_note = (f" Escolha esfera/cilindro pelo CPP com área da cabeça fixa por classe ({head_area:g} Å², não medida "
                 "para esta molécula): indicativa.") if head_area else ""
    if p.chemical_class not in {"anionic", "cationic"}:
        # Não iônicos e zwitteriônicos: a área da cabeça depende do grupo polar (ex.: nº de EO) e não é calculada.
        reason = ("área da cabeça polar deste tipo de surfactante depende do tamanho do grupo polar e não é calculada; "
                  "sem base para decidir entre micela esférica e cilíndrica")
        fields["raio_nucleo_hidrofobico"] = unavailable(reason, SOURCE, "nm")
        fields["raio_micela_cilindrica"] = unavailable(reason, SOURCE, "nm")
    elif cpp < 1 / 3:
        fields["raio_nucleo_hidrofobico"] = value(round(length, 4), SOURCE, "nm", confidence="estimated",
                                                  note=f"Limite superior do raio do núcleo (= l_max de Tanford, n = {n}).{head_note} {NOT_MD}{temp_note}")
        fields["raio_micela_cilindrica"] = not_applicable("CPP não indica micela cilíndrica", SOURCE, "nm")
    elif cpp < 1 / 2:
        fields["raio_micela_cilindrica"] = value(round(length, 4), SOURCE, "nm", confidence="estimated",
                                                 note=f"Limite superior do raio do núcleo cilíndrico (= l_max, n = {n}).{head_note} {NOT_MD}{temp_note}")
        fields["raio_nucleo_hidrofobico"] = not_applicable("CPP indica geometria não esférica", SOURCE, "nm")
    else:
        reason = "CPP indica bicamada/vesícula, não micela esférica ou cilíndrica"
        fields["raio_nucleo_hidrofobico"] = not_applicable(reason, SOURCE, "nm")
        fields["raio_micela_cilindrica"] = not_applicable(reason, SOURCE, "nm")
    for key in RADIUS_FIELDS:
        fields[key] = unavailable("raio total requer espessura da cabeça polar sem valor de referência verificado", SOURCE, "nm")
    fields["teoria_micelar_info"] = value(
        {"modelo": "Tanford + empacotamento geométrico", "n_carbonos": n, "l_max_nm": round(length, 4),
         "v_nm3": round(volume, 4), "cpp": round(cpp, 5), "temperatura_k": temperature},
        SOURCE, confidence="estimated", note=NOT_MD + temp_note)
    return bundle
