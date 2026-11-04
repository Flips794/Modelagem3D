from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from app.modules.simulation.schemas import (
    SimulationAtom3D,
    SimulationBond3D,
    SimulationBox3D,
    SimulationFrame3D,
    SimulationTopology3D,
)

ATOMIC_MASS_DA: dict[str, float] = {
    "H": 1.008,
    "C": 12.011,
    "N": 14.007,
    "O": 15.999,
    "F": 18.998,
    "P": 30.974,
    "S": 32.06,
    "Cl": 35.45,
    "Br": 79.904,
    "I": 126.904,
    "Na": 22.990,
    "K": 39.098,
    "Ca": 40.078,
    "Fe": 55.845,
    "Cu": 63.546,
    "Zn": 65.38,
}

# Parâmetros genéricos e conservadores para protótipo visual.
# Para produção, substitua por GAFF/OpenFF/CHARMM/AMBER conforme a molécula.
LJ_PARAMETERS: dict[str, tuple[float, float]] = {
    # sigma_nm, epsilon_kj_mol
    "H": (0.120, 0.030),
    "C": (0.340, 0.276),
    "N": (0.325, 0.711),
    "O": (0.296, 0.878),
    "F": (0.310, 0.255),
    "P": (0.374, 0.836),
    "S": (0.356, 1.046),
    "Cl": (0.440, 0.418),
    "Br": (0.470, 0.418),
    "I": (0.520, 0.418),
    "Na": (0.258, 0.130),
    "K": (0.330, 0.193),
}


@dataclass(slots=True)
class RunnerSettings:
    temperature_k: float = 298.15
    friction_per_ps: float = 1.0
    timestep_fs: float = 2.0
    steps_per_frame: int = 100
    minimize: bool = True
    minimize_max_iterations: int = 250


def _import_openmm():
    try:
        import openmm
        from openmm import unit
    except ImportError as exc:
        raise RuntimeError(
            "OpenMM não está instalado neste ambiente. Instale com: pip install openmm"
        ) from exc

    return openmm, unit


def _mass_for_atom(atom: SimulationAtom3D) -> float:
    if atom.mass is not None and atom.mass > 0:
        return float(atom.mass)

    return ATOMIC_MASS_DA.get(atom.element, 12.011)


def _lj_for_atom(atom: SimulationAtom3D) -> tuple[float, float]:
    return LJ_PARAMETERS.get(atom.element, (0.340, 0.250))


def _charge_for_atom(atom: SimulationAtom3D) -> float:
    if atom.charge is None:
        return 0.0

    return float(atom.charge)


def _coordinates_to_numpy(frame: SimulationFrame3D) -> np.ndarray:
    coordinates = np.asarray(frame.coordinates, dtype=float)

    if coordinates.ndim != 2 or coordinates.shape[1] != 3:
        raise ValueError("frame.coordinates precisa ter shape (N, 3).")

    return coordinates


def _box_to_dict(box: SimulationBox3D) -> dict[str, Any]:
    return {
        "x": box.x,
        "y": box.y,
        "z": box.z,
        "center": {
            "x": box.center.x,
            "y": box.center.y,
            "z": box.center.z,
        },
    }


class OpenMMRealtimeRunner:
    """
    Runner OpenMM para streaming.

    Este runner é propositalmente genérico para não travar sua arquitetura:
    - Usa massas por elemento.
    - Usa NonbondedForce genérica.
    - Usa HarmonicBondForce para manter conectividade.
    - Minimiza energia antes de transmitir.
    - Produção: substituir parâmetros genéricos por force field real.
    """

    def __init__(
        self,
        topology: SimulationTopology3D,
        initial_frame: SimulationFrame3D,
        settings: RunnerSettings | None = None,
    ):
        self.openmm, self.unit = _import_openmm()
        self.topology = topology
        self.initial_frame = initial_frame
        self.settings = settings or RunnerSettings()

        self.frame_index = 0
        self.time_ps = float(initial_frame.timePs)

        self.system = self.openmm.System()
        self.integrator = None
        self.context = None

        self._build_system()

    def _build_system(self) -> None:
        coordinates = _coordinates_to_numpy(self.initial_frame)

        if len(self.topology.atoms) != coordinates.shape[0]:
            raise ValueError(
                "topology.atoms e frame.coordinates precisam ter o mesmo tamanho."
            )

        for atom in self.topology.atoms:
            self.system.addParticle(_mass_for_atom(atom) * self.unit.dalton)

        nonbonded = self.openmm.NonbondedForce()
        nonbonded.setNonbondedMethod(self.openmm.NonbondedForce.NoCutoff)

        for atom in self.topology.atoms:
            sigma_nm, epsilon_kj_mol = _lj_for_atom(atom)

            nonbonded.addParticle(
                _charge_for_atom(atom) * self.unit.elementary_charge,
                sigma_nm * self.unit.nanometer,
                epsilon_kj_mol * self.unit.kilojoule_per_mole,
            )

        self.system.addForce(nonbonded)

        bonds = self.openmm.HarmonicBondForce()

        for bond in self.topology.bonds:
            atom_a = int(bond.atomAIndex)
            atom_b = int(bond.atomBIndex)

            if atom_a >= coordinates.shape[0] or atom_b >= coordinates.shape[0]:
                continue

            length_nm = float(np.linalg.norm(coordinates[atom_a] - coordinates[atom_b]))
            length_nm = max(length_nm, 0.05)

            # k alto o suficiente para manter conectividade, mas ainda visualmente flexível.
            k = 900.0

            bonds.addBond(
                atom_a,
                atom_b,
                length_nm * self.unit.nanometer,
                k * self.unit.kilojoule_per_mole / (self.unit.nanometer**2),
            )

        self.system.addForce(bonds)

        self.integrator = self.openmm.LangevinIntegrator(
            self.settings.temperature_k * self.unit.kelvin,
            self.settings.friction_per_ps / self.unit.picosecond,
            self.settings.timestep_fs * self.unit.femtosecond,
        )

        self.context = self.openmm.Context(self.system, self.integrator)

        self.context.setPositions(coordinates * self.unit.nanometer)

        if self.settings.minimize and self.settings.minimize_max_iterations > 0:
            self.openmm.LocalEnergyMinimizer.minimize(
                self.context,
                maxIterations=int(self.settings.minimize_max_iterations),
            )

    def topology_message(self) -> dict[str, Any]:
        return {
            "type": "topology",
            "topology": self.topology.model_dump(),
        }

    def step(self) -> dict[str, Any]:
        if self.integrator is None or self.context is None:
            raise RuntimeError("Runner OpenMM não inicializado.")

        self.integrator.step(int(self.settings.steps_per_frame))

        state = self.context.getState(
            getPositions=True,
            enforcePeriodicBox=False,
        )

        positions = state.getPositions(asNumpy=True).value_in_unit(
            self.unit.nanometer
        )

        coordinates = [
            (float(position[0]), float(position[1]), float(position[2]))
            for position in positions
        ]

        self.frame_index += 1
        self.time_ps += (
            self.settings.steps_per_frame * self.settings.timestep_fs * 0.001
        )

        return {
            "type": "frame",
            "frame": {
                "frameIndex": self.frame_index,
                "timePs": self.time_ps,
                "coordinates": coordinates,
                "box": _box_to_dict(self.topology.box),
                "hiddenBonds": [],
            },
        }


