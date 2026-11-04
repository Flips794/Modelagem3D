from __future__ import annotations

from typing import Any

from app.modules.chemistry.rdkit_engine.internal_model.mapper import (
    rdkit_molecule_to_internal_model,
)
from app.modules.chemistry.rdkit_engine.shared.rdkit_provider import RDKitProvider
from app.modules.chemistry.rdkit_engine.shared.svg_drawer import draw_molecule_svg


class Parse2DService:
    def __init__(self):
        self.rdkit = RDKitProvider()

    def execute(
        self,
        identifier: str,
        input_type: str = "SMILES",
        width: int = 900,
        height: int = 520,
    ) -> dict[str, Any]:
        molecule = self._molecule_from_identifier(identifier, input_type)

        self._validate_elements_with_rdkit(molecule)
        self._prepare_2d_molecule(molecule)

        conformer = molecule.GetConformer()

        canonical_smiles = self.rdkit.Chem.MolToSmiles(
            molecule,
            canonical=True,
            isomericSmiles=True,
        )
        formula = self.rdkit.rdMolDescriptors.CalcMolFormula(molecule)
        molecular_weight = float(self.rdkit.Descriptors.MolWt(molecule))
        exact_molecular_weight = float(self.rdkit.Descriptors.ExactMolWt(molecule))
        svg = draw_molecule_svg(self.rdkit, molecule, width, height)

        atoms = self._build_atoms(molecule, conformer)
        bonds = self._build_bonds(molecule)

        internal_molecule = rdkit_molecule_to_internal_model(
            molecule,
            original_input=identifier,
            source_format=input_type if input_type != "Auto" else "SMILES",
            canonical_smiles=canonical_smiles,
            formula=formula,
            molecular_weight=molecular_weight,
            exact_molecular_weight=exact_molecular_weight,
            svg=svg,
        )

        internal_molecule = self._enrich_internal_molecule(
            internal_molecule=internal_molecule,
            bonds_payload=bonds,
        )

        return {
            "success": True,
            "input_type": input_type if input_type != "Auto" else "SMILES",
            "original_input": identifier,
            "canonical_smiles": canonical_smiles,
            "formula": formula,
            "molecular_weight": molecular_weight,
            "exact_molecular_weight": exact_molecular_weight,
            "atom_count": molecule.GetNumAtoms(),
            "bond_count": molecule.GetNumBonds(),
            "svg": svg,
            "atoms": atoms,
            "bonds": bonds,
            "internal_molecule": internal_molecule,
        }

    def _molecule_from_identifier(self, identifier: str, input_type: str):
        clean_identifier = identifier.strip()

        if not clean_identifier:
            raise ValueError("Entrada química vazia.")

        normalized_type = input_type

        if normalized_type == "Auto":
            normalized_type = self._detect_input_type(clean_identifier)

        if normalized_type == "InChIKey":
            raise ValueError(
                "InChIKey não contém informação estrutural suficiente para gerar uma molécula 2D. Use SMILES ou InChI."
            )

        if normalized_type == "InChI":
            mol_from_inchi = getattr(self.rdkit.Chem, "MolFromInchi", None)

            if mol_from_inchi is None:
                raise RuntimeError(
                    "Esta instalação do RDKit não possui suporte a InChI habilitado."
                )

            molecule = mol_from_inchi(clean_identifier)
        else:
            molecule = self.rdkit.Chem.MolFromSmiles(clean_identifier)

        if molecule is None:
            raise ValueError("Entrada química inválida ou não reconhecida pelo RDKit.")

        try:
            self.rdkit.Chem.SanitizeMol(molecule)
        except Exception as error:
            raise ValueError(f"RDKit não conseguiu sanitizar a molécula: {error}") from error

        return molecule

    def _detect_input_type(self, identifier: str) -> str:
        if identifier.startswith("InChI="):
            return "InChI"

        # InChIKey tem formato rígido, mas não reconstrói estrutura.
        if len(identifier) == 27 and identifier.count("-") == 2:
            return "InChIKey"

        return "SMILES"

    def _validate_elements_with_rdkit(self, molecule) -> None:
        periodic_table = self.rdkit.Chem.GetPeriodicTable()

        for atom in molecule.GetAtoms():
            symbol = atom.GetSymbol()
            atomic_number = periodic_table.GetAtomicNumber(symbol)

            if atomic_number <= 0:
                raise ValueError(
                    f"Elemento químico inválido ou não reconhecido pelo RDKit: {symbol}"
                )

    def _prepare_2d_molecule(self, molecule) -> None:
        self.rdkit.Chem.AssignStereochemistry(
            molecule,
            cleanIt=True,
            force=True,
        )

        self.rdkit.rdDepictor.Compute2DCoords(
            molecule,
            canonOrient=True,
            clearConfs=True,
        )

        try:
            self.rdkit.Chem.WedgeMolBonds(
                molecule,
                molecule.GetConformer(),
            )
        except Exception:
            # Moléculas sem estereoquímica explícita não precisam de cunha.
            pass

    def _build_atoms(self, molecule, conformer) -> list[dict[str, Any]]:
        atoms: list[dict[str, Any]] = []

        for atom in molecule.GetAtoms():
            position = conformer.GetAtomPosition(atom.GetIdx())

            atoms.append(
                {
                    "index": atom.GetIdx(),
                    "symbol": atom.GetSymbol(),
                    "atomic_number": atom.GetAtomicNum(),
                    "formal_charge": atom.GetFormalCharge(),
                    "is_aromatic": atom.GetIsAromatic(),
                    "chiral_tag": str(atom.GetChiralTag()),
                    "hybridization": str(atom.GetHybridization()),
                    "total_hydrogens": atom.GetTotalNumHs(includeNeighbors=True),
                    "implicit_hydrogens": atom.GetNumImplicitHs(),
                    "explicit_hydrogens": atom.GetNumExplicitHs(),
                    "x": float(position.x),
                    "y": float(position.y),
                }
            )

        return atoms

    def _build_bonds(self, molecule) -> list[dict[str, Any]]:
        bonds: list[dict[str, Any]] = []

        for bond in molecule.GetBonds():
            visual_style = self._visual_style_from_bond(bond)
            bond_role = self._bond_role_from_visual_style(visual_style)

            bonds.append(
                {
                    "index": bond.GetIdx(),
                    "begin_atom_index": bond.GetBeginAtomIdx(),
                    "end_atom_index": bond.GetEndAtomIdx(),
                    "bond_type": str(bond.GetBondType()),
                    "order": self._bond_order_from_rdkit(bond, visual_style),
                    "is_aromatic": bond.GetIsAromatic() or visual_style == "aromatic",
                    "is_conjugated": bond.GetIsConjugated()
                    or bond_role in {"resonance", "aromatic"},
                    "stereo": str(bond.GetStereo()),
                    "direction": str(bond.GetBondDir()),
                    "stereo_visual": self._stereo_visual_from_style(visual_style),
                    "visual_style": visual_style,
                    "bond_role": bond_role,
                }
            )

        return bonds

    def _bond_order_from_rdkit(self, bond, visual_style: str | None = None) -> float:
        if visual_style == "aromatic" or bond.GetIsAromatic():
            return 1.5

        if bond.GetBondType() == self.rdkit.Chem.BondType.DOUBLE:
            return 2

        if bond.GetBondType() == self.rdkit.Chem.BondType.TRIPLE:
            return 3

        return 1

    def _visual_style_from_bond(self, bond) -> str:
        direction = str(bond.GetBondDir())

        if direction == "BEGINWEDGE":
            return "wedge-filled"

        if direction == "BEGINDASH":
            return "wedge-dashed"

        if bond.GetBondType() == self.rdkit.Chem.BondType.DATIVE:
            return "dashed"

        if bond.GetIsAromatic() or bond.GetBondType() == self.rdkit.Chem.BondType.AROMATIC:
            return "aromatic"

        if bond.GetBondType() == self.rdkit.Chem.BondType.DOUBLE:
            return "double"

        if bond.GetBondType() == self.rdkit.Chem.BondType.TRIPLE:
            return "triple"

        return "single"

    def _bond_role_from_visual_style(self, visual_style: str | None) -> str:
        if visual_style in {"wedge-filled", "wedge-dashed"}:
            return "stereo"

        if visual_style == "dashed":
            return "coordination"

        if visual_style in {"single-resonance", "double-resonance"}:
            return "resonance"

        if visual_style == "aromatic":
            return "aromatic"

        return "covalent"

    def _stereo_visual_from_style(self, visual_style: str | None) -> str:
        if visual_style == "wedge-filled":
            return "wedge"

        if visual_style == "wedge-dashed":
            return "dash"

        return "none"

    def _enrich_internal_molecule(
        self,
        internal_molecule,
        bonds_payload: list[dict[str, Any]],
    ):
        """
        Mantém compatibilidade com o mapper interno atual.

        Se o InternalMoleculeModel já aceitar os campos novos, eles serão
        adicionados nas ligações. Se for um modelo Pydantic mais rígido, fazemos
        model_dump(), enriquecemos o dicionário e retornamos dict compatível com
        o response_model.
        """
        if hasattr(internal_molecule, "model_dump"):
            internal_data = internal_molecule.model_dump()
        elif hasattr(internal_molecule, "dict"):
            internal_data = internal_molecule.dict()
        else:
            internal_data = internal_molecule

        if not isinstance(internal_data, dict):
            return internal_molecule

        bonds_by_index = {bond["index"]: bond for bond in bonds_payload}
        internal_bonds = internal_data.get("bonds", [])

        for bond in internal_bonds:
            rdkit_index = bond.get("rdkit_index")

            if rdkit_index not in bonds_by_index:
                continue

            payload_bond = bonds_by_index[rdkit_index]

            bond["is_conjugated"] = payload_bond.get("is_conjugated", False)
            bond["stereo_visual"] = payload_bond.get("stereo_visual", "none")
            bond["visual_style"] = payload_bond.get("visual_style")
            bond["bond_role"] = payload_bond.get("bond_role")

        return internal_data


def parse_2d(payload: Any) -> dict[str, Any]:
    service = Parse2DService()

    return service.execute(
        identifier=payload.identifier,
        input_type=getattr(payload, "input_type", "SMILES"),
        width=payload.width,
        height=payload.height,
    )


