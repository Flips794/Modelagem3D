"""Ajudantes dos testes dos exemplos documentados.

`screen_request` monta o pedido como a tela 3D monta hoje (frontend: getVisualRenderCountFromAmount,
getSolventVisualCount e buildMiceliumRequest), para os testes exercitarem o mesmo caminho do navegador.
"""
from __future__ import annotations

import math

MAX_VISUAL_MOLECULES = 240
MAX_PARTICLES = 900

DEFAULT_ENVIRONMENT = {
    "temperature_k": 298.15, "pressure_atm": 1.0, "ph": 7.0, "ionic_strength_mol_l": 0.01,
    "solvent_polarity_index": 1.0, "dielectric_constant": 78.5, "agitation_rpm": 0.0, "volume_ml": 100.0,
    "simulation_speed": 1.0, "visual_speed_multiplier": 1.0, "solvent_name": "água", "solvent_mode": "excess",
    "stable_preset": True,
}


def reagent_visual_count(amount_mmol: float) -> int:
    return max(1, min(5000, round(8 + math.sqrt(amount_mmol) * 36)))


def solvent_visual_count(volume_ml: float, speed: float = 1.0) -> int:
    return max(80, min(360, round(110 + math.sqrt(max(volume_ml, 1.0)) * 13 + speed * 8)))


def screen_request(components: list[dict], environment: dict | None = None,
                   documented_example_id: str | None = None) -> dict:
    """`components`: dicts com name, smiles, role ("reagent"|"solvent"), mmol (reagentes) e campos extras opcionais."""
    env = {**DEFAULT_ENVIRONMENT, **(environment or {})}
    volume_l = env["volume_ml"] / 1000.0
    molecules = []
    for component in components:
        extra = {k: v for k, v in component.items() if k not in {"name", "smiles", "role", "mmol"}}
        if component.get("role") == "solvent":
            count = solvent_visual_count(env["volume_ml"], env["simulation_speed"])
            molecules.append({"id": component["name"], "name": component["name"], "smiles": component["smiles"],
                              "role": "solvent", "count": count, "real_amount_mmol": None,
                              "real_concentration_mmol_l": None, "solvent_excess": True, "cmc_mmol_l": None,
                              "is_surfactant": False, "tail_carbon_count": None, **extra})
        else:
            mmol = float(component["mmol"])
            molecules.append({"id": component["name"], "name": component["name"], "smiles": component["smiles"],
                              "role": "reagent", "count": reagent_visual_count(mmol), "real_amount_mmol": mmol,
                              "real_amount_unit": "mmol", "real_concentration_mmol_l": mmol / volume_l,
                              "cmc_mmol_l": None, "is_surfactant": None, "tail_carbon_count": None, **extra})
    requested = sum(m["count"] for m in molecules)
    scale = MAX_VISUAL_MOLECULES / requested if requested > MAX_VISUAL_MOLECULES else 1.0
    for molecule in molecules:
        molecule["count"] = max(1, math.floor(molecule["count"] * scale))
        molecule["visual_count"] = molecule["count"]
        molecule["visual_scale_factor"] = scale
    visual = sum(m["count"] for m in molecules)
    steps = 120 if visual > 220 else 160 if visual > 120 else 220
    payload = {"molecules": molecules, "environment": env, "max_particles": MAX_PARTICLES, "steps": steps,
               "dt": 0.016, "seed": 13}
    if documented_example_id is not None:
        payload["documented_example_id"] = documented_example_id
    return payload


def _round(values, digits: int = 6):
    return [round(float(v), digits) for v in values]


def baseline_signature(response_json: dict) -> dict:
    """Resumo determinístico da resposta: partículas, último quadro e análise (sem notas)."""
    analysis = {k: v for k, v in response_json["analysis"].items()
                if k not in {"morphology_source", "documented_example"}}
    last = response_json["frames"][-1]
    return {
        "particles": [[p["id"], p["kind"], *_round(p["position"])] for p in response_json["particles"]],
        "bonds": [[b["particle_a"], b["particle_b"]] for b in response_json["bonds"]],
        "frame_count": len(response_json["frames"]),
        "last_frame": [_round(c) for c in last["coordinates"]],
        "analysis": analysis,
    }
