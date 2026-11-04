"""Regressões das coordenadas CG; rótulos de morfologia não bastam."""
from __future__ import annotations

import numpy as np
import pytest

from app.modules.micelium.ai_bridge import enrich_molecules_with_ai
from app.modules.micelium.analyzer import geometry_evidence_for_cluster
from app.modules.micelium.engine import (
    MiceliumEngine, _MICELIUM_SESSION_STATE, apply_autonomous_pairwise_forces,
    build_initial_state, calculate_micellization_metrics, choose_formation_plan,
    infer_solvent_profile,
    request_session_key,
)
from app.modules.micelium.mapping import build_particle_template, infer_charge_from_smiles, max_consecutive_carbon_run
from app.modules.micelium.organization import constrain_bond_lengths
from app.modules.micelium.schemas import MiceliumEnvironment, MiceliumMoleculeInput, MiceliumSimulationRequest


def surfactant(**updates):
    data = dict(id="surfactant", name="SDS", smiles="CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]",
                count=48, real_concentration_mmol_l=30, cmc_mmol_l=8.2,
                is_surfactant=True, surfactant_class="anionic", tail_carbon_count=12,
                hlb=40, effective_hlb=40, packing_parameter=0.24)
    return MiceliumMoleculeInput(**(data | updates))


def request_for(molecule=None, solvent_smiles="O", **env):
    solvent = MiceliumMoleculeInput(id="solvent", name="solvent", smiles=solvent_smiles, role="solvent", count=12)
    return MiceliumSimulationRequest(molecules=[molecule or surfactant(), solvent], environment=MiceliumEnvironment(**env), steps=180)


def plan_for(request):
    profile = infer_solvent_profile(request)
    metrics = calculate_micellization_metrics(request.molecules, request.environment.volume_ml, profile)
    return choose_formation_plan(request, sum(m.count for m in request.molecules if m.role != "solvent"), metrics, profile)


@pytest.fixture(autouse=True)
def independent_sessions():
    _MICELIUM_SESSION_STATE.clear()
    yield
    _MICELIUM_SESSION_STATE.clear()


@pytest.mark.parametrize("smiles,expected", [("CCCCCCCCCCCCO", 12), ("OCCCCCC=CCCCCC", 12), ("CCO", 2)])
def test_tail_length_uses_graph_including_unsaturation(smiles, expected):
    assert max_consecutive_carbon_run(smiles) == expected


def test_equivalent_smiles_keep_nonionic_identity():
    result, _notes = enrich_molecules_with_ai([MiceliumMoleculeInput(smiles="OCCCCCC=CCCCCC")], MiceliumEnvironment())
    assert result[0].is_surfactant is True
    assert result[0].tail_carbon_count == 12
    assert build_particle_template(result[0]).representation == "coarse-grained-surfactant"


def test_neutral_hydrocarbon_and_zwitterion_do_not_gain_head_charge():
    assert infer_charge_from_smiles("CCCCCCCCCCCC") == 0
    assert infer_charge_from_smiles("CCCCCCCCCCCC[N+](C)(C)CC(=O)[O-]") == 0
    assert infer_charge_from_smiles("CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]") == -1


@pytest.mark.parametrize("smiles,name,polarity", [("O", "water", 1.0), ("CCCCCC", "hexane", 0.08), ("CCO", "ethanol", 0.62), ("CO", "metanol", 0.78)])
def test_implicit_and_explicit_solvent_profiles_agree(smiles, name, polarity):
    explicit = infer_solvent_profile(request_for(solvent_smiles=smiles))
    implicit = infer_solvent_profile(MiceliumSimulationRequest(molecules=[surfactant()], environment=MiceliumEnvironment(solvent_name=name)))
    assert explicit.polarity == pytest.approx(polarity)
    assert implicit.polarity == pytest.approx(polarity)
    assert implicit.dielectric == pytest.approx(explicit.dielectric)


def test_neutral_long_chain_alcohol_is_not_misidentified_as_alkane_solvent():
    profile = infer_solvent_profile(request_for(solvent_smiles="CCCCCCCCCCCCO"))
    assert profile.name != "meio apolar"


def test_ideal_mixture_cmc_uses_real_concentrations_and_excludes_solute():
    a = surfactant(id="a", cmc_mmol_l=10, real_concentration_mmol_l=6, count=8)
    b = surfactant(id="b", cmc_mmol_l=20, real_concentration_mmol_l=12, count=500)
    solute = MiceliumMoleculeInput(smiles="CCO", is_surfactant=False, cmc_mmol_l=0.001, real_concentration_mmol_l=100)
    metrics = calculate_micellization_metrics([a, b, solute], 100)
    assert metrics.c_over_cmc == pytest.approx(1.2)
    assert metrics.real_concentration_mmol_l == 18
    assert metrics.critical_amount_mmol == pytest.approx(1.5)


def test_bond_constraint_handles_coincident_beads():
    positions = [[0., 0., 0.], [0., 0., 0.], [1.6, .4, .2]]
    constrain_bond_lengths(positions, [(0, 1, .46, 2), (1, 2, .46, 2)], iterations=24)
    assert np.linalg.norm(np.array(positions[0]) - positions[1]) == pytest.approx(.46, abs=1e-5)


def test_component_order_cannot_swap_cached_coordinates():
    req = request_for()
    reverse = req.model_copy(update={"molecules": list(reversed(req.molecules))})
    assert request_session_key(req) != request_session_key(reverse)


def test_repeated_components_have_distinct_molecular_topologies():
    molecule = surfactant(count=2)
    req = MiceliumSimulationRequest(molecules=[molecule, molecule])
    particles, _b, _x, _v, _box, _rep = build_initial_state(req)
    assert len({p.molecule_id for p in particles}) == 4


def test_pair_forces_do_not_repel_covalently_adjacent_beads():
    req = request_for(surfactant(count=1))
    template = build_particle_template(req.molecules[0])
    positions = [p.position[:] for p in template.particles]
    velocities = [[0., 0., 0.] for _ in positions]
    apply_autonomous_pairwise_forces(positions=positions, velocities=velocities, particles=template.particles, request=req, plan=plan_for(req))
    assert np.max(np.abs(velocities)) == 0


@pytest.mark.parametrize("morphology", ["micela esférica", "micela cilíndrica/wormlike", "bicamada plana/lamelar", "micela inversa"])
def test_random_aggregate_is_not_accepted_as_the_predicted_shape(morphology):
    rng = np.random.default_rng(19)
    ids = [str(i) for i in range(24)]
    tails = {mid: rng.normal(size=3) for mid in ids}
    heads = {mid: rng.normal(size=3) for mid in ids}
    orientation, segregation, shape_ok = geometry_evidence_for_cluster(ids, tails, heads, morphology)
    assert not (orientation >= .62 and segregation >= .70 and shape_ok)


@pytest.mark.parametrize("name,cpp,sc,count,concentration,cmc,solvent,fragment", [
    ("sphere", .24, "anionic", 48, 30, 8.2, "O", "esférica"),
    ("cylinder", .40, "cationic", 48, 30, 8.2, "O", "cilíndrica"),
    ("bilayer", .65, "nonionic", 64, 18, 1., "O", "bicamada"),
    ("inverse", .60, "nonionic", 48, 9, 1., "CCCCCC", "inversa"),
])
def test_coordinates_organize_without_stretching_bonds(name, cpp, sc, count, concentration, cmc, solvent, fragment):
    smiles = "CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]" if sc == "anionic" else "CCCCCCCCCCCC[N+](C)(C)C.[Br-]" if sc == "cationic" else "CCCCCCCCCCCCOCCO"
    req = request_for(surfactant(id=name, name=name, smiles=smiles, packing_parameter=cpp, surfactant_class=sc, count=count, real_concentration_mmol_l=concentration, cmc_mmol_l=cmc), solvent)
    engine = MiceliumEngine()
    first = engine.run(req)
    second = engine.run(req)
    assert fragment in second.analysis.predicted_morphology
    organized = [c for c in second.clusters if fragment in c.morphology]
    assert organized, [(c.surfactant_count, c.morphology) for c in second.clusters]
    assert second.analysis.orientation_score > .62
    assert second.analysis.hydrophobic_core_score >= .70
    # Continuidade, sem reabrir a mesma mistura nas posições de dispersão.
    assert np.mean(np.linalg.norm(np.array(second.frames[0].coordinates) - first.frames[-1].coordinates, axis=1)) < .25
    index = {p.id: i for i, p in enumerate(second.particles)}
    for frame in second.frames[::20] + second.frames[-1:]:
        xyz = np.array(frame.coordinates)
        assert np.all(np.isfinite(xyz))
        ratios = [np.linalg.norm(xyz[index[b.particle_a]] - xyz[index[b.particle_b]]) / b.length for b in second.bonds]
        assert np.max(np.abs(np.array(ratios) - 1.0)) < .015


def test_below_cmc_stays_dispersed_without_center_collapse():
    req = request_for(surfactant(count=24, real_concentration_mmol_l=1))
    _p, _b, initial, _v, _box, _rep = build_initial_state(req)
    response = MiceliumEngine().run(req)
    assert response.analysis.c_over_cmc_proxy < 1
    assert response.analysis.micellized_fraction == 0
    xyz = np.array(response.frames[-1].coordinates)
    initial = np.array(initial)
    rg_initial = np.mean(np.linalg.norm(initial - initial.mean(axis=0), axis=1))
    rg_final = np.mean(np.linalg.norm(xyz - xyz.mean(axis=0), axis=1))
    assert rg_final > .80 * rg_initial
