from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from functools import lru_cache

try:
    from rdkit import Chem
except ImportError:  # O motor também aceita o fallback textual sem RDKit.
    Chem = None

from app.modules.micelium.schemas import (
    MiceliumBond,
    MiceliumMoleculeInput,
    MiceliumParticle,
)


def stable_id(*parts: object) -> str:
    raw = "|".join(str(part) for part in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


@lru_cache(maxsize=256)
def max_consecutive_carbon_run(smiles: str) -> int:
    if Chem is not None:
        mol = Chem.MolFromSmiles(smiles or "")
        if mol is not None:
            carbon_ids = {atom.GetIdx() for atom in mol.GetAtoms() if atom.GetAtomicNum() == 6 and not atom.GetIsAromatic()}
            graph = {i: [n.GetIdx() for n in mol.GetAtomWithIdx(i).GetNeighbors() if n.GetIdx() in carbon_ids] for i in carbon_ids}
            longest = 0
            visits = 0
            def walk(index, visited):
                nonlocal longest, visits
                visits += 1
                longest = max(longest, len(visited))
                # Limite do modelo CG e de custo para grafos cíclicos densos.
                if longest >= 32 or visits >= 10000:
                    return
                for neighbor in graph[index]:
                    if neighbor not in visited:
                        walk(neighbor, visited | {neighbor})
            for index in graph:
                if longest >= 32 or visits >= 10000:
                    break
                walk(index, {index})
            return longest
    matches = re.findall(r"C{4,}", smiles or "")
    if not matches:
        return 0
    return max(len(item) for item in matches)


def infer_ionic_like(smiles: str) -> bool:
    return bool(
        re.search(
            r"\[[^\]]*[+-][^\]]*\]|\[Na\+\]|\[K\+\]|\[Br-\]|\[Cl-\]|\[Ca\+2\]",
            smiles or "",
        )
    )


def infer_surfactant_like(molecule: MiceliumMoleculeInput) -> bool:
    if molecule.is_surfactant is not None:
        return molecule.is_surfactant

    smiles = molecule.smiles or ""
    tail = molecule.tail_carbon_count or max_consecutive_carbon_run(smiles)
    # A cabeça pertence ao mesmo componente da cauda; um contraíon isolado
    # não transforma um alcano em surfactante.
    active = max(smiles.split("."), key=lambda part: part.count("C"), default="")
    has_head = bool(re.search(r"[ONSP]", active))

    return molecule.role != "solvent" and tail >= 8 and has_head


def infer_charge_from_smiles(smiles: str) -> float:
    if Chem is not None:
        mol = Chem.MolFromSmiles(smiles or "")
        if mol is not None:
            fragments = Chem.GetMolFrags(mol, asMols=True)
            active = max(fragments, key=lambda part: part.GetNumHeavyAtoms(), default=mol)
            return float(sum(atom.GetFormalCharge() for atom in active.GetAtoms()))
    if "[N+]" in smiles or "[NH+]" in smiles:
        return 1.0
    if "[O-]" in smiles or "S(=O)(=O)[O-]" in smiles:
        return -1.0
    return 0.0


def solvent_profile_from_molecule(molecule: MiceliumMoleculeInput) -> dict[str, float | str]:
    """
    Perfil visual/CG do solvente em excesso.

    A molécula não é transformada quimicamente. O perfil só define como as
    partículas de solvente interagem no ambiente 3D.
    """
    label = f"{molecule.name or ''} {molecule.formula or ''} {molecule.smiles or ''}".lower()
    smiles = molecule.smiles.strip()

    if smiles == "O" or "h2o" in label or "água" in label or "agua" in label or "water" in label:
        return {
            "label": "água",
            "polarity": 1.0,
            "hydrophobicity": 0.0,
            "charge": 0.0,
            "radius": 0.24,
            "mass": 1.0,
            "color": "#60a5fa",
        }

    if smiles in {"CCO", "OCC"} or "etanol" in label or "ethanol" in label:
        return {
            "label": "etanol",
            "polarity": 0.62,
            "hydrophobicity": 0.28,
            "charge": 0.0,
            "radius": 0.28,
            "mass": 1.15,
            "color": "#93c5fd",
        }

    if smiles in {"CO", "OC"} or "metanol" in label or "methanol" in label:
        return {
            "label": "metanol",
            "polarity": 0.78,
            "hydrophobicity": 0.12,
            "charge": 0.0,
            "radius": 0.26,
            "mass": 1.05,
            "color": "#7dd3fc",
        }

    if "hexan" in label or "óleo" in label or "oleo" in label or "oil" in label or re.search(r"^C{5,}$", smiles):
        return {
            "label": "meio apolar",
            "polarity": 0.08,
            "hydrophobicity": 0.92,
            "charge": 0.0,
            "radius": 0.34,
            "mass": 1.35,
            "color": "#fbbf24",
        }

    hydrophobicity = min(0.90, max(0.05, (max_consecutive_carbon_run(smiles) - 1) / 8.0))
    polarity = max(0.10, min(0.90, 1.0 - hydrophobicity * 0.75))

    return {
        "label": molecule.name or molecule.formula or "solvente definido pelo usuário",
        "polarity": polarity,
        "hydrophobicity": hydrophobicity,
        "charge": 0.0,
        "radius": 0.28 + 0.08 * hydrophobicity,
        "mass": 1.0 + 0.40 * hydrophobicity,
        "color": "#38bdf8" if polarity >= 0.55 else "#f59e0b",
    }


def choose_representation(molecule: MiceliumMoleculeInput) -> str:
    """
    Regra simples:
    - solventes: bead solvente;
    - surfactantes: coarse-grained cabeça + cauda;
    - moléculas comuns: solute/atomistic simplificado.

    O atomístico real pode ser acoplado depois ao RDKit/OpenMM.
    """
    if molecule.role == "solvent":
        return "solvent-bead"

    if infer_surfactant_like(molecule):
        return "coarse-grained-surfactant"

    return "solute-bead"


@dataclass(slots=True)
class MoleculeParticleTemplate:
    particles: list[MiceliumParticle]
    bonds: list[MiceliumBond]
    representation: str


def _particle(
    *,
    particle_id: str,
    molecule_id: str,
    molecule_name: str,
    role: str,
    kind: str,
    bead_index: int,
    x: float,
    charge: float,
    radius: float,
    mass: float,
    polarity: float,
    hydrophobicity: float,
    color: str,
) -> MiceliumParticle:
    return MiceliumParticle(
        id=particle_id,
        molecule_id=molecule_id,
        molecule_name=molecule_name,
        role=role,  # type: ignore[arg-type]
        kind=kind,  # type: ignore[arg-type]
        bead_index=bead_index,
        position=[x, 0.0, 0.0],
        velocity=[0.0, 0.0, 0.0],
        charge=charge,
        radius=radius,
        mass=mass,
        polarity=polarity,
        hydrophobicity=hydrophobicity,
        color=color,
    )


def build_particle_template(molecule: MiceliumMoleculeInput) -> MoleculeParticleTemplate:
    representation = choose_representation(molecule)
    molecule_id = molecule.id or stable_id(molecule.name, molecule.smiles)
    molecule_name = molecule.name or molecule.formula or molecule.smiles[:24]

    if representation == "solvent-bead":
        particle_id = f"{molecule_id}:solvent:0"
        profile = solvent_profile_from_molecule(molecule)

        return MoleculeParticleTemplate(
            representation=representation,
            particles=[
                _particle(
                    particle_id=particle_id,
                    molecule_id=molecule_id,
                    molecule_name=str(profile["label"]),
                    role="solvent",
                    kind="solvent",
                    bead_index=0,
                    x=0.0,
                    charge=float(profile["charge"]),
                    radius=float(profile["radius"]),
                    mass=float(profile["mass"]),
                    polarity=float(profile["polarity"]),
                    hydrophobicity=float(profile["hydrophobicity"]),
                    color=str(profile["color"]),
                )
            ],
            bonds=[],
        )

    if representation == "coarse-grained-surfactant":
        tail_carbons = molecule.tail_carbon_count or max_consecutive_carbon_run(
            molecule.smiles
        )
        tail_beads = max(2, min(8, math.ceil(max(tail_carbons, 8) / 4)))
        charge = infer_charge_from_smiles(molecule.smiles)
        if molecule.surfactant_class and "cation" in molecule.surfactant_class.lower():
            charge = 1.0
        elif molecule.surfactant_class and "anion" in molecule.surfactant_class.lower():
            charge = -1.0

        particles: list[MiceliumParticle] = []
        bonds: list[MiceliumBond] = []

        # Cauda: do núcleo para a cabeça.
        for i in range(tail_beads):
            particle_id = f"{molecule_id}:tail:{i}"
            particles.append(
                _particle(
                    particle_id=particle_id,
                    molecule_id=molecule_id,
                    molecule_name=molecule_name,
                    role=molecule.role,
                    kind="tail",
                    bead_index=i,
                    x=i * 0.46,
                    charge=0.0,
                    radius=0.31,
                    mass=1.2,
                    polarity=0.04,
                    hydrophobicity=1.0,
                    color="#f59e0b",
                )
            )

            if i > 0:
                bonds.append(
                    MiceliumBond(
                        id=f"{molecule_id}:tailbond:{i-1}:{i}",
                        particle_a=f"{molecule_id}:tail:{i-1}",
                        particle_b=f"{molecule_id}:tail:{i}",
                        length=0.46,
                        stiffness=2.0,
                    )
                )

        head_id = f"{molecule_id}:head:0"
        particles.append(
            _particle(
                particle_id=head_id,
                molecule_id=molecule_id,
                molecule_name=molecule_name,
                role=molecule.role,
                kind="head",
                bead_index=tail_beads,
                x=tail_beads * 0.46,
                charge=charge,
                radius=max(0.30, min(0.60, 0.36 * math.sqrt((molecule.head_area_a2 or 60.0) / 60.0))),
                mass=1.4,
                polarity=1.0,
                hydrophobicity=0.05,
                color="#22d3ee" if charge == 0 else ("#38bdf8" if charge < 0 else "#f472b6"),
            )
        )
        bonds.append(
            MiceliumBond(
                id=f"{molecule_id}:headbond:{tail_beads-1}:head",
                particle_a=f"{molecule_id}:tail:{tail_beads-1}",
                particle_b=head_id,
                length=0.48,
                stiffness=2.4,
            )
        )

        return MoleculeParticleTemplate(
            representation=representation,
            particles=particles,
            bonds=bonds,
        )

    particle_id = f"{molecule_id}:solute:0"
    logp = molecule.logp or 0.0
    hydrophobicity = max(0.0, min(1.0, (logp + 1.0) / 5.0))
    polarity = max(0.0, min(1.0, (molecule.tpsa or 0.0) / 120.0))

    return MoleculeParticleTemplate(
        representation=representation,
        particles=[
            _particle(
                particle_id=particle_id,
                molecule_id=molecule_id,
                molecule_name=molecule_name,
                role=molecule.role,
                kind="solute",
                bead_index=0,
                x=0.0,
                charge=infer_charge_from_smiles(molecule.smiles),
                radius=0.34,
                mass=1.2,
                polarity=polarity,
                hydrophobicity=hydrophobicity,
                color="#a78bfa",
            )
        ],
        bonds=[],
    )


