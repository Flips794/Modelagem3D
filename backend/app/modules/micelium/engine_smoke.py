from app.modules.micelium.schemas import (
    MiceliumEnvironment,
    MiceliumMoleculeInput,
    MiceliumSimulationRequest,
)
from app.modules.micelium.service import run_micelium_simulation


def test_micelium_engine_runs_surfactant_water_system():
    payload = MiceliumSimulationRequest(
        molecules=[
            MiceliumMoleculeInput(
                name="SDS",
                smiles="CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]",
                role="reagent",
                count=24,
                is_surfactant=True,
                cmc_mmol_l=8.2,
                tail_carbon_count=12,
            ),
            MiceliumMoleculeInput(
                name="Water",
                smiles="O",
                role="solvent",
                count=80,
            ),
        ],
        environment=MiceliumEnvironment(
            temperature_k=298.15,
            pressure_atm=1,
            ph=7,
            ionic_strength_mol_l=0.01,
            solvent_polarity_index=1,
            dielectric_constant=78.5,
            agitation_rpm=0,
            volume_ml=100,
        ),
        steps=6,
        max_particles=1000,
    )

    result = run_micelium_simulation(payload)

    assert result.particles
    assert result.frames
    assert result.analysis.total_particles == len(result.particles)
    assert result.analysis.surfactant_count > 0


