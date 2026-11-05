"""Medidas geométricas por tendência para os testes dos exemplos documentados (sem coordenadas rígidas)."""
from __future__ import annotations

from collections import defaultdict

import numpy as np


def run_chunks(client, payload: dict, chunks: int = 3) -> dict:
    """Roda trechos seguidos como a tela 3D (o estado continua entre trechos); devolve o último."""
    from app.modules.micelium.engine import _MICELIUM_SESSION_STATE

    _MICELIUM_SESSION_STATE.clear()
    body = None
    for _ in range(chunks):
        response = client.post("/api/v1/micelium/simulate", json=payload)
        assert response.status_code == 200, response.text
        body = response.json()
    return body


def last_frame(body: dict) -> np.ndarray:
    return np.asarray(body["frames"][-1]["coordinates"], dtype=float)


def largest_cluster(body: dict) -> list[int]:
    index_of = {p["id"]: i for i, p in enumerate(body["particles"])}
    clusters = sorted(body["clusters"], key=lambda c: c["surfactant_count"], reverse=True)
    assert clusters, "nenhum agregado detectado"
    return [index_of[pid] for pid in clusters[0]["particle_ids"] if pid in index_of]


def clusters_indices(body: dict) -> list[list[int]]:
    index_of = {p["id"]: i for i, p in enumerate(body["particles"])}
    return [[index_of[pid] for pid in c["particle_ids"] if pid in index_of] for c in body["clusters"]]


def surfactants(body: dict, indices: list[int]) -> list[dict]:
    """Por molécula surfactante do agregado: índices da cabeça e das caudas (por cadeia)."""
    particles = body["particles"]
    groups: dict[str, dict] = defaultdict(lambda: {"head": [], "tail": [], "chains": defaultdict(list)})
    for i in indices:
        p = particles[i]
        if p["kind"] == "head":
            groups[p["molecule_id"]]["head"].append(i)
        elif p["kind"] == "tail":
            groups[p["molecule_id"]]["tail"].append(i)
            groups[p["molecule_id"]]["chains"][p.get("chain_index", 0)].append(i)
    return [g for g in groups.values() if g["head"] and g["tail"]]


def principal_axes(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    centered = points - points.mean(axis=0)
    values, vectors = np.linalg.eigh(centered.T @ centered / max(len(points), 1))
    return values, vectors           # crescente: vectors[:, -1] = maior eixo


def radial_from_axis(points: np.ndarray, center: np.ndarray, axis: np.ndarray) -> np.ndarray:
    rel = points - center
    return np.linalg.norm(rel - np.outer(rel @ axis, axis), axis=1)


def fraction(flags) -> float:
    flags = list(flags)
    return sum(bool(f) for f in flags) / max(len(flags), 1)


def role_groups(body: dict, role: str) -> dict[str, list[int]]:
    groups: dict[str, list[int]] = defaultdict(list)
    for i, p in enumerate(body["particles"]):
        if p.get("example_role") == role:
            groups[p["molecule_id"]].append(i)
    return groups
