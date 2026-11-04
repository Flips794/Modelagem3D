from __future__ import annotations

from app.modules.micelium.engine import MiceliumEngine
from app.modules.micelium.schemas import (
    MiceliumEnvironment,
    MiceliumMoleculeInput,
    MiceliumSimulationRequest,
)


def base_environment(**updates) -> MiceliumEnvironment:
    data = {
        "temperature_k": 298.15,
        "pressure_atm": 1.0,
        "ph": 7.0,
        "ionic_strength_mol_l": 0.01,
        "solvent_polarity_index": 1.0,
        "dielectric_constant": 78.5,
        "agitation_rpm": 250.0,
        "volume_ml": 100.0,
        "visual_speed_multiplier": 1.0,
        "simulation_speed": 1.0,
        "solvent_name": "water",
    }
    data.update(updates)
    return MiceliumEnvironment(**data)


def solvent_water(count: int = 140) -> MiceliumMoleculeInput:
    return MiceliumMoleculeInput(
        id="water",
        name="Água em excesso",
        smiles="O",
        role="solvent",
        count=count,
        visual_count=count,
        solvent_excess=True,
    )


def solvent_ethanol(count: int = 140) -> MiceliumMoleculeInput:
    return MiceliumMoleculeInput(
        id="ethanol",
        name="Etanol em excesso",
        smiles="CCO",
        role="solvent",
        count=count,
        visual_count=count,
        solvent_excess=True,
    )


def solvent_oil(count: int = 110) -> MiceliumMoleculeInput:
    return MiceliumMoleculeInput(
        id="oil",
        name="Meio apolar",
        smiles="CCCCCC",
        role="solvent",
        count=count,
        visual_count=count,
        solvent_excess=True,
    )


def surfactant(
    *,
    id: str,
    name: str,
    smiles: str,
    surfactant_class: str,
    tail_carbon_count: int,
    cmc_mmol_l: float,
    concentration_mmol_l: float,
    count: int,
    cpp: float,
    hlb: float = 20.0,
    effective_hlb: float = 20.0,
) -> MiceliumMoleculeInput:
    return MiceliumMoleculeInput(
        id=id,
        name=name,
        smiles=smiles,
        role="reagent",
        count=count,
        visual_count=count,
        real_concentration_mmol_l=concentration_mmol_l,
        cmc_mmol_l=cmc_mmol_l,
        is_surfactant=True,
        surfactant_class=surfactant_class,
        tail_carbon_count=tail_carbon_count,
        cpp=cpp,
        hlb=hlb,
        effective_hlb=effective_hlb,
    )


def run_case(
    name: str,
    request: MiceliumSimulationRequest,
    expected_fragment: str,
    min_fraction: float = 0.0,
    max_fraction: float = 1.0,
) -> None:
    engine = MiceliumEngine()
    response = engine.run(request)

    morphology = (response.analysis.dominant_morphology or "").lower()
    frame_count = len(response.frames)
    particle_count = len(response.particles)
    fraction = float(response.analysis.micellized_fraction or 0.0)

    assert frame_count >= 72, (name, "poucos frames", frame_count)
    assert particle_count > 0, (name, "sem partículas")
    assert expected_fragment.lower() in morphology, (name, morphology, expected_fragment)
    assert min_fraction <= fraction <= max_fraction, (name, fraction, min_fraction, max_fraction)

    first = response.frames[0].coordinates
    middle = response.frames[len(response.frames) // 2].coordinates
    last = response.frames[-1].coordinates

    movement_a = sum(
        abs(first[i][0] - middle[i][0]) + abs(first[i][1] - middle[i][1]) + abs(first[i][2] - middle[i][2])
        for i in range(min(len(first), len(middle), 80))
    )
    movement_b = sum(
        abs(middle[i][0] - last[i][0]) + abs(middle[i][1] - last[i][1]) + abs(middle[i][2] - last[i][2])
        for i in range(min(len(middle), len(last), 80))
    )

    assert movement_a > 0.4, (name, "sem movimento inicial suficiente", movement_a)
    assert movement_b > 0.12, (name, "sem reorganização final suficiente", movement_b)

    print(
        f"OK - {name}: morphology={response.analysis.dominant_morphology}; "
        f"fraction={fraction:.2f}; frames={frame_count}; particles={particle_count}; "
        f"C/CMC={response.analysis.c_over_cmc_proxy}"
    )


def main() -> None:
    # Abaixo da CMC: não deve formar micela estável.
    run_case(
        "SDS abaixo da CMC",
        MiceliumSimulationRequest(
            molecules=[
                surfactant(
                    id="sds-low",
                    name="SDS",
                    smiles="CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]",
                    surfactant_class="anionic",
                    tail_carbon_count=12,
                    cmc_mmol_l=8.2,
                    concentration_mmol_l=4.0,
                    count=70,
                    cpp=0.24,
                    hlb=40.0,
                    effective_hlb=40.0,
                ),
                solvent_water(),
            ],
            environment=base_environment(solvent_name="água"),
            steps=180,
            seed=111,
        ),
        "abaixo",
        min_fraction=0.0,
        max_fraction=0.08,
    )

    # Esférica/circular: SDS em água bem acima da CMC.
    run_case(
        "SDS micela esférica",
        MiceliumSimulationRequest(
            molecules=[
                surfactant(
                    id="sds-sphere",
                    name="SDS",
                    smiles="CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]",
                    surfactant_class="anionic",
                    tail_carbon_count=12,
                    cmc_mmol_l=8.2,
                    concentration_mmol_l=30.0,
                    count=90,
                    cpp=0.24,
                    hlb=40.0,
                    effective_hlb=40.0,
                ),
                solvent_water(),
            ],
            environment=base_environment(solvent_name="água"),
            steps=180,
            seed=222,
        ),
        "esférica",
        min_fraction=0.35,
        max_fraction=0.94,
    )

    # Cilíndrica/wormlike: CTAB acima da CMC com CPP intermediário.
    run_case(
        "CTAB micela cilíndrica",
        MiceliumSimulationRequest(
            molecules=[
                surfactant(
                    id="ctab-cylinder",
                    name="CTAB",
                    smiles="CCCCCCCCCCCCCCCC[N+](C)(C)C.[Br-]",
                    surfactant_class="cationic",
                    tail_carbon_count=16,
                    cmc_mmol_l=0.92,
                    concentration_mmol_l=5.0,
                    count=110,
                    cpp=0.42,
                    hlb=22.0,
                    effective_hlb=26.0,
                ),
                solvent_water(),
            ],
            environment=base_environment(solvent_name="água", ionic_strength_mol_l=0.08),
            steps=200,
            seed=333,
        ),
        "cilíndrica",
        min_fraction=0.45,
        max_fraction=0.94,
    )

    # Bicamada plana/lamelar: DDAB ou fosfolipídio simplificado com CPP alto.
    run_case(
        "DDAB bicamada plana",
        MiceliumSimulationRequest(
            molecules=[
                surfactant(
                    id="ddab-lamellar",
                    name="DDAB",
                    smiles="CCCCCCCCCCCC[N+](C)(CCCCCCCCCCCC)C.[Br-]",
                    surfactant_class="cationic",
                    tail_carbon_count=12,
                    cmc_mmol_l=1.5,
                    concentration_mmol_l=8.0,
                    count=130,
                    cpp=0.88,
                    hlb=16.0,
                    effective_hlb=18.0,
                ),
                solvent_water(),
            ],
            environment=base_environment(solvent_name="água", ionic_strength_mol_l=0.12),
            steps=220,
            seed=444,
        ),
        "bicamada plana",
        min_fraction=0.55,
        max_fraction=0.94,
    )

    # Vesícula/bicamada fechada: dupla cauda e alta concentração.
    run_case(
        "DDAB vesícula",
        MiceliumSimulationRequest(
            molecules=[
                surfactant(
                    id="ddab-vesicle",
                    name="DDAB",
                    smiles="CCCCCCCCCCCC[N+](C)(CCCCCCCCCCCC)C.[Br-]",
                    surfactant_class="cationic",
                    tail_carbon_count=12,
                    cmc_mmol_l=1.5,
                    concentration_mmol_l=12.0,
                    count=150,
                    cpp=0.92,
                    hlb=16.0,
                    effective_hlb=18.0,
                ),
                solvent_water(),
            ],
            environment=base_environment(solvent_name="água", ionic_strength_mol_l=0.16),
            steps=240,
            seed=555,
        ),
        "vesícula",
        min_fraction=0.60,
        max_fraction=0.94,
    )

    # Micela inversa: AOT em meio apolar.
    run_case(
        "AOT micela inversa",
        MiceliumSimulationRequest(
            molecules=[
                surfactant(
                    id="aot-inverse",
                    name="AOT",
                    smiles="CCCCC(C)CCCOC(=O)C(CS(=O)(=O)[O-])OC(=O)CC(C)CCCC.[Na+]",
                    surfactant_class="anionic",
                    tail_carbon_count=8,
                    cmc_mmol_l=2.5,
                    concentration_mmol_l=10.0,
                    count=120,
                    cpp=1.10,
                    hlb=10.0,
                    effective_hlb=12.0,
                ),
                solvent_oil(),
            ],
            environment=base_environment(
                solvent_name="óleo/apolar",
                solvent_polarity_index=0.15,
                dielectric_constant=7.0,
                ionic_strength_mol_l=0.0,
            ),
            steps=220,
            seed=666,
        ),
        "inversa",
        min_fraction=0.20,
        max_fraction=0.94,
    )

    # Água versus etanol: SDS deve agregar pior em etanol.
    run_case(
        "SDS em etanol: agregação mais fraca",
        MiceliumSimulationRequest(
            molecules=[
                surfactant(
                    id="sds-ethanol",
                    name="SDS",
                    smiles="CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]",
                    surfactant_class="anionic",
                    tail_carbon_count=12,
                    cmc_mmol_l=8.2,
                    concentration_mmol_l=30.0,
                    count=85,
                    cpp=0.24,
                    hlb=40.0,
                    effective_hlb=40.0,
                ),
                solvent_ethanol(),
            ],
            environment=base_environment(
                solvent_name="etanol",
                solvent_polarity_index=0.62,
                dielectric_constant=24.3,
            ),
            steps=180,
            seed=777,
        ),
        "pré-agregados",
        min_fraction=0.0,
        max_fraction=0.35,
    )


if __name__ == "__main__":
    main()

