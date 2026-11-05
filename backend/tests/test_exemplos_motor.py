"""Exemplos documentados, tarefa 4: exemplo no pedido, plano de formação, origem da forma e avisos."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://validation:validation@127.0.0.1/validation")

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.modules.micelium.documented_examples import EXAMPLES  # noqa: E402
from app.modules.micelium.engine import (  # noqa: E402
    _MICELIUM_SESSION_STATE,
    infer_solvent_profile,
    request_session_key,
)
from app.modules.micelium.schemas import MiceliumSimulationRequest  # noqa: E402
from tests.exemplos_helpers import example_payload, screen_request  # noqa: E402

SIM = "/api/v1/micelium/simulate"
client = TestClient(create_app(Settings(database_url="postgresql+psycopg://v:v@127.0.0.1/v", app_env="development")))


def simulate(payload: dict) -> dict:
    _MICELIUM_SESSION_STATE.clear()
    response = client.post(SIM, json=payload)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize("example_id", list(EXAMPLES))
def test_cada_exemplo_dentro_das_condicoes_tem_forma_e_origem(example_id):
    analysis = simulate(example_payload(example_id))["analysis"]
    example = EXAMPLES[example_id]
    assert analysis["predicted_morphology"] == example.documented_morphology
    expected_source = "calculated" if example.kind == "validated_prediction" else "documented_example"
    assert analysis["morphology_source"] == expected_source
    report = analysis["documented_example"]
    assert report["id"] == example_id and report["within_range"] is True and report["out_of_range_reasons"] == []
    assert report["example_version"] == "1.0.0" and report["references"] and report["conditions"]
    assert all(c["basis"] in {"experimental", "protocol", "technical"} for c in report["conditions"])
    if example.kind == "representative_demo":
        assert analysis["predicted_regime"] == "demonstração representativa (protocolo documentado)"
        assert example_id in analysis["morphology_basis"]
    else:
        assert analysis["predicted_regime"] != "demonstração representativa (protocolo documentado)"
        assert not any("diverge" in w for w in analysis["warnings"])
    if example_id == "aot_inversa_isooctano":
        assert report["w0"] == pytest.approx(10.0)


@pytest.mark.parametrize("example_id,kwargs", [
    ("sds_esferica", {"environment": {"ionic_strength_mol_l": 0.1}}),
    ("ctab_nasal_vermiforme", {"amounts": {"nasal": 1.0}}),
    ("ctab_nasal_vermiforme", {"environment": {"temperature_k": 298.15}}),
    ("dppc_bicamada_hidratacao", {"environment": {"temperature_k": 303.15}}),
    ("dppc_vesicula_extrusao", {"environment": {"temperature_k": 318.15}}),
    ("aot_inversa_isooctano", {"amounts": {"agua": 200.0}}),
])
def test_fora_das_condicoes_volta_ao_calculo_com_aviso(example_id, kwargs):
    body = simulate(example_payload(example_id, **kwargs))
    analysis = body["analysis"]
    assert analysis["morphology_source"] == "calculated"
    assert analysis["documented_example"]["within_range"] is False
    assert analysis["documented_example"]["out_of_range_reasons"]
    assert any(w.startswith("fora das condições documentadas") for w in analysis["warnings"])
    assert analysis["predicted_regime"] != "demonstração representativa (protocolo documentado)"
    assert all(p.get("example_role") is None for p in body["particles"])


def test_aot_com_w0_20_em_isooctano_nao_quebra():
    analysis = simulate(example_payload("aot_inversa_isooctano", amounts={"agua": 200.0}))["analysis"]
    assert analysis["predicted_morphology"] == "monômeros/pré-agregados"


def test_id_desconhecido_da_422():
    payload = example_payload("sds_esferica")
    payload["documented_example_id"] = "ddab_vesicula"
    assert client.post(SIM, json=payload).status_code == 422


def test_chave_de_sessao_distingue_exemplos():
    bilayer = MiceliumSimulationRequest(**example_payload("dppc_bicamada_hidratacao"))
    vesicle = MiceliumSimulationRequest(**example_payload("dppc_vesicula_extrusao"))
    assert request_session_key(bilayer) != request_session_key(vesicle)


@pytest.mark.parametrize("name,smiles", [("Isooctano", "CC(C)CC(C)(C)C"), ("isooctane", "CC(C)CC(C)(C)C"),
                                         ("2,2,4-trimetilpentano", "CC(C)CC(C)(C)C")])
def test_isooctano_e_meio_apolar(name, smiles):
    request = MiceliumSimulationRequest(**screen_request(
        [{"name": "AOT", "smiles": EXAMPLES["aot_inversa_isooctano"].components[0].smiles, "mmol": 1.0},
         {"name": name, "smiles": smiles, "role": "solvent"}]))
    assert infer_solvent_profile(request).polarity < 0.35


@pytest.mark.parametrize("name,smiles,polarity", [("água", "O", 1.0), ("etanol", "CCO", 0.62), ("hexano", "CCCCCC", 0.08)])
def test_outros_solventes_mantem_o_perfil(name, smiles, polarity):
    request = MiceliumSimulationRequest(**screen_request(
        [{"name": "SDS", "smiles": EXAMPLES["sds_esferica"].components[0].smiles, "mmol": 1.0},
         {"name": name, "smiles": smiles, "role": "solvent"}]))
    assert infer_solvent_profile(request).polarity == pytest.approx(polarity)


def test_salicilato_tem_duas_contas_no_exemplo():
    body = simulate(example_payload("ctab_nasal_vermiforme"))
    salicylate = [p for p in body["particles"] if p["molecule_name"] == "Salicilato de sódio"]
    by_molecule: dict[str, list[dict]] = {}
    for particle in salicylate:
        by_molecule.setdefault(particle["molecule_id"], []).append(particle)
    assert by_molecule and all(len(beads) == 2 for beads in by_molecule.values())
    beads = sorted(next(iter(by_molecule.values())), key=lambda p: p["bead_index"])
    assert [p["kind"] for p in beads] == ["solute", "solute"]
    assert [p["charge"] for p in beads] == [0.0, -1.0]
    assert all(p["example_role"] == "interfacial_aromatic_anion" for p in beads)
    plain = simulate(example_payload("ctab_nasal_vermiforme", with_id=False))
    plain_sal = [p for p in plain["particles"] if p["molecule_name"] == "Salicilato de sódio"]
    assert plain_sal and len({p["molecule_id"] for p in plain_sal}) == len(plain_sal)   # uma conta por molécula


@pytest.mark.parametrize("example_id,name,beads", [("dppc_vesicula_extrusao", "DPPC", 9),
                                                   ("aot_inversa_isooctano", "AOT", 5)])
def test_dppc_e_aot_com_duas_caudas_no_exemplo(example_id, name, beads):
    body = simulate(example_payload(example_id))
    counts: dict[str, int] = {}
    chains: dict[str, set[int]] = {}
    for particle in body["particles"]:
        if particle["molecule_name"] == name:
            counts[particle["molecule_id"]] = counts.get(particle["molecule_id"], 0) + 1
            if particle["kind"] == "tail":
                chains.setdefault(particle["molecule_id"], set()).add(particle["chain_index"])
    assert counts and set(counts.values()) == {beads}
    assert all(found == {0, 1} for found in chains.values())


def test_agua_do_nucleo_marcada_so_no_aot_dentro_das_condicoes():
    body = simulate(example_payload("aot_inversa_isooctano"))
    water = [p for p in body["particles"] if p.get("example_role") == "core_water"]
    assert water and all(p["kind"] == "solute" for p in water)


@pytest.mark.parametrize("example_id", list(EXAMPLES))
def test_validacao_nao_atribui_demonstracao_ao_calculo(example_id):
    analysis = simulate(example_payload(example_id))["analysis"]
    status = analysis["validation_status"]
    if EXAMPLES[example_id].kind == "representative_demo":
        assert status.startswith("demonstração representativa") and "CPP" not in status
    else:
        assert "concorda com a referência" in status and "não validado" not in status


def test_nota_de_cmc_do_exemplo():
    expected = {"dppc_bicamada_hidratacao": "não usada neste exemplo (base: Tm e protocolo)",
                "dppc_vesicula_extrusao": "não usada neste exemplo (base: Tm e protocolo)",
                "aot_inversa_isooctano": "não se aplica (meio apolar)"}
    for example_id, note in expected.items():
        assert simulate(example_payload(example_id))["analysis"]["documented_example"]["cmc_note"] == note
    assert simulate(example_payload("sds_esferica"))["analysis"]["documented_example"]["cmc_note"] is None
