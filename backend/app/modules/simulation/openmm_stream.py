from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# Exemplo isolado. Adapte imports/topologia para o seu módulo real.
# pip install openmm
from openmm import LangevinIntegrator, Platform, unit
from openmm.app import ForceField, Modeller, PDBFile, Simulation

router = APIRouter(prefix="/simulation", tags=["Simulation 3D Stream"])


def build_topology_message(simulation: Simulation) -> dict[str, Any]:
    topology = simulation.topology

    atoms = []
    atom_index_map: dict[Any, int] = {}

    for index, atom in enumerate(topology.atoms()):
        atom_index_map[atom] = index

        atoms.append(
            {
                "index": index,
                "element": atom.element.symbol if atom.element else atom.name[0],
                "moleculeId": f"chain_{atom.residue.chain.id}_res_{atom.residue.index}",
                "moleculeName": atom.residue.name,
                "residueName": atom.residue.name,
                "isSolvent": atom.residue.name.upper() in {"HOH", "WAT", "SOL", "H2O"},
                "charge": None,
                "hybridization": None,
            }
        )

    bonds = []
    for bond_index, bond in enumerate(topology.bonds()):
        bonds.append(
            {
                "index": bond_index,
                "atomAIndex": atom_index_map[bond[0]],
                "atomBIndex": atom_index_map[bond[1]],
                "order": 1,
                "moleculeId": f"chain_{bond[0].residue.chain.id}_res_{bond[0].residue.index}",
                "drawAcrossPbc": False,
            }
        )

    # O exemplo usa caixa cúbica; em produção, pegue isso do sistema OpenMM.
    box_nm = 8.0

    return {
        "type": "topology",
        "topology": {
            "id": "openmm-live-topology",
            "title": "OpenMM live simulation",
            "box": {
                "x": box_nm,
                "y": box_nm,
                "z": box_nm,
                "center": {"x": 0.0, "y": 0.0, "z": 0.0},
            },
            "atoms": atoms,
            "bonds": bonds,
            "moleculeCount": len({atom["moleculeId"] for atom in atoms}),
            "createdAt": "server-runtime",
        },
    }


def positions_to_frame_message(
    simulation: Simulation,
    frame_index: int,
    time_ps: float,
) -> dict[str, Any]:
    state = simulation.context.getState(getPositions=True, enforcePeriodicBox=True)
    positions = state.getPositions(asNumpy=True).value_in_unit(unit.nanometer)

    coordinates = [
        [float(position[0]), float(position[1]), float(position[2])]
        for position in positions
    ]

    return {
        "type": "frame",
        "frame": {
            "frameIndex": frame_index,
            "timePs": time_ps,
            "coordinates": coordinates,
            "box": {
                "x": 8.0,
                "y": 8.0,
                "z": 8.0,
                "center": {"x": 0.0, "y": 0.0, "z": 0.0},
            },
            "hiddenBonds": [],
        },
    }


def create_demo_simulation_from_pdb(pdb_path: str) -> Simulation:
    pdb = PDBFile(pdb_path)

    forcefield = ForceField("amber14-all.xml", "amber14/tip3pfb.xml")
    modeller = Modeller(pdb.topology, pdb.positions)

    system = forcefield.createSystem(
        modeller.topology,
        nonbondedMethod=None,
        constraints=None,
    )

    integrator = LangevinIntegrator(
        300 * unit.kelvin,
        1.0 / unit.picosecond,
        0.002 * unit.picoseconds,
    )

    platform = Platform.getPlatformByName("CPU")

    simulation = Simulation(modeller.topology, system, integrator, platform)
    simulation.context.setPositions(modeller.positions)

    return simulation


@router.websocket("/ws/openmm")
async def openmm_stream(websocket: WebSocket):
    await websocket.accept()

    try:
        # Troque pelo caminho/gerador real da solução montada no seu backend.
        simulation = create_demo_simulation_from_pdb("input.pdb")

        await websocket.send_json(build_topology_message(simulation))

        frame_index = 0
        steps_per_frame = 5
        target_hz = 20
        sleep_seconds = 1 / target_hz

        while True:
            simulation.step(steps_per_frame)

            time_ps = frame_index * steps_per_frame * 0.002

            await websocket.send_json(
                positions_to_frame_message(
                    simulation=simulation,
                    frame_index=frame_index,
                    time_ps=time_ps,
                )
            )

            frame_index += 1
            await asyncio.sleep(sleep_seconds)

    except WebSocketDisconnect:
        return
    except Exception as exc:
        await websocket.send_json(
            {
                "type": "error",
                "message": str(exc),
            }
        )
        await websocket.close()


