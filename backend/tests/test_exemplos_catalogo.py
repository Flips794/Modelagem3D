"""Exemplos documentados, tarefa 3: catálogo versionado, condições com natureza e rota de leitura."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://validation:validation@127.0.0.1/validation")

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.modules.micelium.documented_examples import EXAMPLES, evaluate  # noqa: E402
from app.modules.micelium.schemas import MiceliumSimulationRequest  # noqa: E402
from tests.exemplos_helpers import example_payload  # noqa: E402
from tests.stability_cases import SDS  # noqa: E402

IDS = ["sds_esferica", "ctab_nasal_vermiforme", "dppc_bicamada_hidratacao", "dppc_vesicula_extrusao",
       "aot_inversa_isooctano"]
SDS_C_OVER_CMC = 3.87   # c/CMC do SDS 3 mmol/100 mL medido no motor (relatório WEB_LITE_V1); integração na tarefa 4


def request_of(example_id: str, **kwargs) -> MiceliumSimulationRequest:
    payload = example_payload(example_id, with_id=False, **kwargs)
    return MiceliumSimulationRequest(**payload)


def verdict(example_id: str, c_over_cmc: float | None = None, **kwargs):
    return evaluate(EXAMPLES[example_id], request_of(example_id, **kwargs), c_over_cmc)


def test_catalogo_tem_cinco_exemplos_versionados():
    assert list(EXAMPLES) == IDS
    for example in EXAMPLES.values():
        assert example.example_version == "1.0.0" and example.last_reviewed_at == "2026-11-05"
        assert example.references and example.protocol and example.notes
    assert [e.id for e in EXAMPLES.values() if e.kind == "validated_prediction"] == ["sds_esferica"]
    assert {e.documented_morphology for e in EXAMPLES.values()} == {
        "micela esférica", "micela cilíndrica/wormlike", "bicamada plana/lamelar", "vesícula/bicamada fechada",
        "micela inversa"}


def test_toda_condicao_tem_natureza_e_fonte():
    for example in EXAMPLES.values():
        assert example.conditions
        for condition in example.conditions:
            assert condition.basis in {"experimental", "protocol", "technical"}
            assert condition.source.strip() and condition.label.strip()


@pytest.mark.parametrize("example_id,parameter,bound", [
    ("sds_esferica", "ionic_strength", 0.07),
    ("sds_esferica", "temperature_c", 30.0),
    ("ctab_nasal_vermiforme", "temperature_c", 20.5),
    ("dppc_bicamada_hidratacao", "temperature_c", 100.0),
    ("aot_inversa_isooctano", "w0", 10.5),
    ("aot_inversa_isooctano", "aot_m", 0.101),
    ("aot_inversa_isooctano", "temperature_c", 25.5),
])
def test_limites_tecnicos_nao_se_apresentam_como_experimentais(example_id, parameter, bound):
    matching = [c for c in EXAMPLES[example_id].conditions if c.parameter == parameter and c.maximum == bound]
    assert matching and all(c.basis == "technical" for c in matching)
    assert all("limite técnico" in c.label or "tolerância" in c.label for c in matching)


def test_condicoes_experimentais_citadas_para_o_ponto_documentado():
    aot = {c.parameter: c for c in EXAMPLES["aot_inversa_isooctano"].conditions if c.basis == "experimental"}
    assert "w0" in aot and "10" in aot["w0"].label
    dppc = [c for c in EXAMPLES["dppc_bicamada_hidratacao"].conditions if c.parameter == "temperature_c"]
    assert any(c.basis == "experimental" and c.minimum == 41.0 for c in dppc)
    vesicle = [c for c in EXAMPLES["dppc_vesicula_extrusao"].conditions if c.parameter == "temperature_c"]
    assert any(c.basis == "protocol" and (c.minimum, c.maximum) == (51.0, 61.0) for c in vesicle)


@pytest.mark.parametrize("example_id", IDS)
def test_ponto_de_cada_exemplo_esta_dentro_das_condicoes(example_id):
    result = verdict(example_id, SDS_C_OVER_CMC if example_id == "sds_esferica" else None)
    assert result.within_range, result.reasons
    if example_id == "aot_inversa_isooctano":
        assert result.w0 == pytest.approx(10.0)


@pytest.mark.parametrize("example_id,kwargs,parameter_word", [
    ("sds_esferica", {"environment": {"ionic_strength_mol_l": 0.1}}, "força iônica"),
    ("ctab_nasal_vermiforme", {"amounts": {"nasal": 1.0}}, "razão"),
    ("ctab_nasal_vermiforme", {"environment": {"temperature_k": 298.15}}, "temperatura"),
    ("dppc_bicamada_hidratacao", {"environment": {"temperature_k": 303.15}}, "temperatura"),
    ("dppc_vesicula_extrusao", {"environment": {"temperature_k": 318.15}}, "temperatura"),
    ("aot_inversa_isooctano", {"amounts": {"agua": 200.0}}, "w0"),
    ("aot_inversa_isooctano", {"replace": {"isooctano": "O"}, "environment": {"solvent_name": "água"}}, "solvente"),
])
def test_fora_das_condicoes_por_exemplo(example_id, kwargs, parameter_word):
    result = verdict(example_id, SDS_C_OVER_CMC if example_id == "sds_esferica" else None, **kwargs)
    assert not result.within_range
    assert any(parameter_word in reason for reason in result.reasons), result.reasons


def test_componentes_trocados_saem_do_exemplo():
    result = verdict("ctab_nasal_vermiforme", replace={"ctab": SDS})
    assert not result.within_range and "componentes diferentes do exemplo" in result.reasons


def test_smiles_equivalente_e_aceito():
    result = verdict("ctab_nasal_vermiforme", replace={"nasal": "[Na+].[O-]C(=O)c1ccccc1O"})
    assert result.within_range, result.reasons


def test_w0_calculado_das_quantidades():
    assert verdict("aot_inversa_isooctano").w0 == pytest.approx(10.0)
    missing = verdict("aot_inversa_isooctano", drop=("agua",))
    assert not missing.within_range and "w0 indefinido" in missing.reasons and missing.w0 is None


@pytest.mark.parametrize("app_env", ["development", "production"])
def test_rota_catalogo_lista_cinco_com_formula(app_env):
    client = TestClient(create_app(Settings(database_url="postgresql+psycopg://v:v@127.0.0.1/v", app_env=app_env)))
    response = client.get("/api/v1/micelium/documented-examples")
    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == IDS
    for item in body:
        assert item["conditions"] and item["references"]
        for component in item["components"]:
            assert component["formula"] and component["molar_mass"] > 0
    aot = body[-1]
    water = next(c for c in aot["components"] if c["key"] == "agua")
    assert water["derived_from_w0"] is True and aot["w0"] == 10.0
