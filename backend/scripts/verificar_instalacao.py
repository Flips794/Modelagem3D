"""Checks the running local installation without writing molecules to the DB."""

from __future__ import annotations

import argparse
import json
import math
import sys
from urllib.request import Request, urlopen


def check_prediction_response(response: dict, expected_class: str) -> None:
    """Classe correta e CMC honesta: número positivo finito ou ausente com aviso explícito.

    O sistema não inventa CMC fora do domínio validado; ausência sem aviso é falha.
    """
    if response["molecule"]["surfactant_class"] != expected_class:
        raise AssertionError(f"Classe {response['molecule']['surfactant_class']!r}; esperada {expected_class!r}")
    prediction = response["prediction"]
    cmc = prediction.get("predicted_cmc_mmol_l")
    if cmc is None:
        if not any(str(w).strip() for w in prediction.get("warnings") or []):
            raise AssertionError("CMC ausente sem aviso explicando o motivo")
        return
    if not (isinstance(cmc, (int, float)) and math.isfinite(cmc) and cmc > 0):
        raise AssertionError(f"CMC inválida: {cmc!r}")


def run(base_url: str) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    base_url = base_url.rstrip("/")

    def request(path: str, payload: dict | None = None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = Request(
            base_url + path,
            data=data,
            headers={"Content-Type": "application/json", "Origin": "http://localhost:5173"},
        )
        with urlopen(req, timeout=45) as response:
            return json.load(response)

    def check(name: str, operation):
        try:
            operation()
        except Exception as exc:
            results.append({"check": name, "status": "FAIL", "detail": str(exc)})
            print(f"FALHOU: {name}: {exc}")
        else:
            results.append({"check": name, "status": "PASS"})
            print(f"OK: {name}")

    def require(condition, detail="Resposta inesperada"):
        if not condition:
            raise AssertionError(detail)

    check("API", lambda: require(request("/health")["status"] == "ok"))
    check("Banco conectado", lambda: require(request("/health/database")["database"] == "connected"))

    def elements():
        response = request("/reference-data/elements")
        require(response["count"] == 118, "A tabela deve conter 118 elementos")
        require(response["source"] == "database", "A tabela está usando o fallback local")

    check("Tabela periódica no banco", elements)
    check("RDKit disponível", lambda: require(request("/chemistry/parameters/status")["rdkit_available"]))

    for name, smiles, formula in (
        ("Etanol", "CCO", "C2H6O"),
        ("Benzeno", "c1ccccc1", "C6H6"),
        ("Amônio", "[NH4+]", "H4N+"),
        ("Acetato", "CC(=O)[O-]", "C2H3O2-"),
    ):
        def parse(smiles=smiles, formula=formula):
            response = request("/chemistry/rdkit/parse-2d", {"identifier": smiles})
            require(response["success"] and response["formula"] == formula)

        check(f"Desenho 2D: {name}", parse)

        check(f"Importação 2D: {name}", parse)

    def roundtrip():
        parsed = request("/chemistry/rdkit/parse-2d", {"identifier": "CCO"})
        response = request("/chemistry/rdkit/graph-to-smiles", {
            "atoms": parsed["atoms"], "bonds": parsed["bonds"],
        })
        require(response["canonical_smiles"] == "CCO")

    check("Grafo para SMILES", roundtrip)
    check("Otimização 2D", lambda: require(request(
        "/chemistry/rdkit/optimize-2d", {"smiles": "CCO"}
    )["success"]))

    def hydrogens():
        response = request("/chemistry/rdkit/hydrogens-2d", {"smiles": "CCO", "explicit_hs": True})
        require(response["atom_count"] == 9)

    check("Hidrogênios explícitos", hydrogens)
    check("Parâmetros químicos", lambda: require(request(
        "/chemistry/parameters/analyze", {"smiles": "CCO", "generate_3d": False}
    )["success"]))

    for name, smiles, expected in (
        ("SDS", "CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]", "anionic"),
        ("CTAB", "CCCCCCCCCCCCCCCC[N+](C)(C)C.[Br-]", "cationic"),
        ("Éster não iônico", "CCCCCCCC=CCCCCCCCC(=O)OCC(O)CO", "nonionic"),
        ("Betaína", "CCCCCCCCCCCC(=O)NCC[N+](C)(C)CC(=O)[O-]", "zwitterionic"),
    ):
        def predict(smiles=smiles, expected=expected):
            response = request("/micelium-ai/predict", {
                "smiles": smiles, "concentration": 10, "unit": "mmol/L",
            })
            check_prediction_response(response, expected)

        check(f"Rota de previsão: {name}", predict)

    def micelle():
        response = request("/micelium/simulate", {
            "molecules": [
                {"name": "SDS", "smiles": "CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]",
                 "role": "reagent", "count": 8, "is_surfactant": True,
                 "cmc_mmol_l": 8.2, "tail_carbon_count": 12},
                {"name": "Água", "smiles": "O", "role": "solvent", "count": 16},
            ],
            "steps": 3, "max_particles": 500,
        })
        require(bool(response["particles"]) and bool(response["frames"]))

    check("Micelium: partículas e frames", micelle)

    def stream():
        from websockets.sync.client import connect

        url = base_url.replace("https://", "wss://", 1).replace("http://", "ws://", 1)
        with connect(url + "/simulation/stream", open_timeout=10, close_timeout=3) as socket:
            socket.send(json.dumps({
                "type": "start", "stepsPerFrame": 1, "targetHz": 1, "minimize": False,
                "topology": {
                    "id": "installation-water", "title": "Verificação de instalação",
                    "box": {"x": 4, "y": 4, "z": 4},
                    "atoms": [
                        {"index": 0, "element": "O", "moleculeId": "water"},
                        {"index": 1, "element": "H", "moleculeId": "water"},
                        {"index": 2, "element": "H", "moleculeId": "water"},
                    ],
                    "bonds": [
                        {"index": 0, "atomAIndex": 0, "atomBIndex": 1, "moleculeId": "water"},
                        {"index": 1, "atomAIndex": 0, "atomBIndex": 2, "moleculeId": "water"},
                    ],
                    "moleculeCount": 1, "createdAt": "2026-11-04T00:00:00Z",
                },
                "frame": {"frameIndex": 0, "timePs": 0, "coordinates": [
                    [0, 0, 0], [0.0957, 0, 0], [-0.024, 0.093, 0],
                ]},
            }))
            for _ in range(10):
                message = json.loads(socket.recv(timeout=45))
                require(message.get("type") != "error", message.get("message", "Erro OpenMM"))
                if message.get("type") == "frame":
                    frame = message.get("frame", message)
                    coordinates = frame.get("coordinates", [])
                    require(len(coordinates) == 3)
                    require(all(math.isfinite(value) for row in coordinates for value in row))
                    return
            raise AssertionError("OpenMM não entregou um frame")

    check("OpenMM por WebSocket", stream)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000/api/v1")
    args = parser.parse_args()
    results = run(args.url)
    failures = sum(result["status"] != "PASS" for result in results)
    print(f"\n{len(results) - failures}/{len(results)} verificações passaram.")
    print("Estes testes verificam a instalação; não validam a precisão científica dos estimadores.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
