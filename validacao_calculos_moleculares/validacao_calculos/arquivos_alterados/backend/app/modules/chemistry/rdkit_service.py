class RDKitService:
    def __init__(self):
        try:
            from rdkit import Chem
            from rdkit.Chem import Descriptors, Crippen, Lipinski, QED, rdDepictor, rdMolDescriptors
            from rdkit.Chem.Draw import rdMolDraw2D
            from rdkit.Geometry import Point3D
        except ImportError as error:
            raise RuntimeError(
                "RDKit não está instalado neste ambiente. "
                "Instale com: python -m pip install rdkit"
            ) from error

        self.Chem = Chem
        self.Descriptors = Descriptors
        self.Crippen = Crippen
        self.Lipinski = Lipinski
        self.QED = QED
        self.rdDepictor = rdDepictor
        self.rdMolDescriptors = rdMolDescriptors
        self.rdMolDraw2D = rdMolDraw2D
        self.Point3D = Point3D

    def parse_smiles_2d(self, smiles: str, width: int = 640, height: int = 420) -> dict:
        molecule = self.Chem.MolFromSmiles(smiles)

        if molecule is None:
            raise ValueError("SMILES inválido ou não reconhecido pelo RDKit.")

        return self._molecule_to_payload(
            molecule=molecule,
            original_input=smiles,
            input_type="SMILES",
            width=width,
            height=height,
        )

    def graph_to_smiles(self, atoms: list, bonds: list) -> dict:
        if not atoms:
            return {
                "success": True,
                "canonical_smiles": "",
                "formula": None,
                "molecular_weight": None,
                "exact_molecular_weight": None,
                "atom_count": 0,
                "atom_count_total": 0,
                "heavy_atom_count": 0,
                "bond_count": 0,
                "bond_count_total": 0,
                "heavy_bond_count": 0,
            }

        rw_molecule = self.Chem.RWMol()
        index_map: dict[int, int] = {}

        for atom_data in sorted(atoms, key=lambda item: item.index):
            atom = self.Chem.Atom(atom_data.symbol)
            atom.SetFormalCharge(atom_data.formal_charge)

            if atom_data.is_aromatic:
                atom.SetIsAromatic(True)

            rdkit_index = rw_molecule.AddAtom(atom)
            index_map[atom_data.index] = rdkit_index

        for bond_data in bonds:
            begin = index_map.get(bond_data.begin_atom_index)
            end = index_map.get(bond_data.end_atom_index)

            if begin is None or end is None:
                raise ValueError("Ligação aponta para átomo inexistente.")

            bond_type = self._bond_order_to_rdkit_bond_type(
                order=bond_data.order,
                is_aromatic=bond_data.is_aromatic,
            )

            rw_molecule.AddBond(begin, end, bond_type)

            if bond_data.is_aromatic:
                rw_molecule.GetAtomWithIdx(begin).SetIsAromatic(True)
                rw_molecule.GetAtomWithIdx(end).SetIsAromatic(True)

        molecule = rw_molecule.GetMol()

        has_any_coordinate = any(
            atom_data.x is not None and atom_data.y is not None
            for atom_data in atoms
        )

        if has_any_coordinate:
            conformer = self.Chem.Conformer(len(atoms))

            for atom_data in atoms:
                rdkit_index = index_map[atom_data.index]
                x = atom_data.x if atom_data.x is not None else 0.0
                y = atom_data.y if atom_data.y is not None else 0.0
                conformer.SetAtomPosition(
                    rdkit_index,
                    self.Point3D(float(x), float(y), 0.0),
                )

            molecule.AddConformer(conformer)

        try:
            self.Chem.SanitizeMol(molecule)
        except Exception as error:
            raise ValueError(f"Grafo químico inválido para gerar SMILES: {error}") from error

        canonical_smiles = self.Chem.MolToSmiles(
            molecule,
            canonical=True,
            isomericSmiles=True,
        )

        molecule_h = self.Chem.AddHs(molecule)
        formula = self.rdMolDescriptors.CalcMolFormula(molecule_h)
        molecular_weight = float(self.Descriptors.MolWt(molecule))
        exact_molecular_weight = float(self.Descriptors.ExactMolWt(molecule))

        return {
            "success": True,
            "canonical_smiles": canonical_smiles,
            "formula": formula,
            "molecular_weight": molecular_weight,
            "exact_molecular_weight": exact_molecular_weight,

            # Compatibilidade antiga + correção com H.
            "atom_count": molecule_h.GetNumAtoms(),
            "bond_count": molecule_h.GetNumBonds(),

            # Campos explícitos novos.
            "atom_count_total": molecule_h.GetNumAtoms(),
            "bond_count_total": molecule_h.GetNumBonds(),
            "heavy_atom_count": molecule.GetNumHeavyAtoms(),
            "heavy_bond_count": molecule.GetNumBonds(),
        }

    def optimize_2d(
        self,
        internal_molecule: dict | None = None,
        graph: dict | None = None,
        smiles: str | None = None,
        width: int = 900,
        height: int = 520,
    ) -> dict:
        from app.modules.chemistry.rdkit_engine.optimize_2d.schemas import (
            Optimize2DRequest,
        )
        from app.modules.chemistry.rdkit_engine.optimize_2d.service import optimize_2d

        return optimize_2d(
            Optimize2DRequest(
                internal_molecule=internal_molecule,
                graph=graph,
                smiles=smiles,
                width=width,
                height=height,
            )
        )

    def _safe(self, callback, default=None):
        try:
            return callback()
        except Exception:
            return default

    def _wiener_index(self, molecule):
        matrix = self.Chem.GetDistanceMatrix(molecule)
        total = 0.0

        for i in range(molecule.GetNumAtoms()):
            for j in range(i + 1, molecule.GetNumAtoms()):
                total += float(matrix[i, j])

        return total

    def _randic_index(self, molecule):
        total = 0.0

        for bond in molecule.GetBonds():
            degree_a = max(bond.GetBeginAtom().GetDegree(), 1)
            degree_b = max(bond.GetEndAtom().GetDegree(), 1)
            total += 1.0 / ((degree_a * degree_b) ** 0.5)

        return total

    def _inchi_payload(self, molecule):
        try:
            inchi = self.Chem.MolToInchi(molecule)
            inchikey = self.Chem.MolToInchiKey(molecule)
            return inchi, inchikey
        except Exception:
            return None, None

    def _molecule_to_payload(
        self,
        molecule,
        original_input: str,
        input_type: str,
        width: int,
        height: int,
    ) -> dict:
        self.Chem.SanitizeMol(molecule)
        self.Chem.AssignStereochemistry(molecule, cleanIt=True, force=True)

        if molecule.GetNumConformers() == 0:
            self.rdDepictor.Compute2DCoords(molecule)

        conformer = molecule.GetConformer()

        try:
            self.Chem.WedgeMolBonds(molecule, conformer)
        except Exception:
            pass

        molecule_h = self.Chem.AddHs(molecule)

        canonical_smiles = self.Chem.MolToSmiles(
            molecule,
            canonical=True,
            isomericSmiles=True,
        )

        canonical_smiles_no_isomeric = self.Chem.MolToSmiles(
            molecule,
            canonical=True,
            isomericSmiles=False,
        )

        formula = self.rdMolDescriptors.CalcMolFormula(molecule_h)
        molecular_weight = float(self.Descriptors.MolWt(molecule))
        exact_molecular_weight = float(self.Descriptors.ExactMolWt(molecule))
        inchi, inchikey = self._inchi_payload(molecule)

        from app.modules.chemistry.parameters.validated_calculations import profile
        active = profile(molecule).active
        rotatable_bonds = self._safe(
            lambda: int(self.rdMolDescriptors.CalcNumRotatableBonds(active)),
            0,
        )
        ring_count = self._safe(
            lambda: int(self.rdMolDescriptors.CalcNumRings(active)),
            0,
        )
        aromatic_ring_count = self._safe(
            lambda: int(self.rdMolDescriptors.CalcNumAromaticRings(active)),
            0,
        )
        fraction_csp3 = self._safe(
            lambda: float(self.rdMolDescriptors.CalcFractionCSP3(active)),
            0.0,
        )
        hbd = self._safe(lambda: int(self.rdMolDescriptors.CalcNumHBD(active)), 0)
        hba = self._safe(lambda: int(self.rdMolDescriptors.CalcNumHBA(active)), 0)
        formal_charge = int(sum(atom.GetFormalCharge() for atom in molecule.GetAtoms()))
        bertz_complexity = self._safe(lambda: float(self.Descriptors.BertzCT(active)))
        wiener_index = self._safe(lambda: float(self._wiener_index(active)))
        randic_index = self._safe(lambda: float(self._randic_index(active)))
        logp = self._safe(lambda: float(self.Crippen.MolLogP(active)))
        tpsa = self._safe(lambda: float(self.rdMolDescriptors.CalcTPSA(active)))
        qed = self._safe(lambda: float(self.QED.qed(active)))
        molar_refractivity = self._safe(lambda: float(self.Crippen.MolMR(active)))

        svg = self._draw_svg(molecule, width, height)

        atoms = []
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
                    "total_hydrogens": atom.GetTotalNumHs(),
                    "implicit_hydrogens": atom.GetNumImplicitHs(),
                    "explicit_hydrogens": atom.GetNumExplicitHs(),
                    "x": float(position.x),
                    "y": float(position.y),
                }
            )

        bonds = []
        for bond in molecule.GetBonds():
            bonds.append(
                {
                    "index": bond.GetIdx(),
                    "begin_atom_index": bond.GetBeginAtomIdx(),
                    "end_atom_index": bond.GetEndAtomIdx(),
                    "bond_type": str(bond.GetBondType()),
                    "order": float(bond.GetBondTypeAsDouble()),
                    "is_aromatic": bond.GetIsAromatic(),
                    "is_conjugated": bond.GetIsConjugated(),
                    "stereo": str(bond.GetStereo()),
                    "direction": str(bond.GetBondDir()),
                }
            )

        return {
            "success": True,
            "input_type": input_type,
            "original_input": original_input,
            "canonical_smiles": canonical_smiles,
            "canonical_smiles_no_isomeric": canonical_smiles_no_isomeric,
            "isomeric_smiles": canonical_smiles,
            "smiles_canonico": canonical_smiles_no_isomeric,
            "smiles_isomerico": canonical_smiles,
            "inchi": inchi,
            "inchikey": inchikey,
            "formula": formula,
            "molecular_weight": molecular_weight,
            "exact_molecular_weight": exact_molecular_weight,

            # Compatibilidade antiga, agora corrigida com H.
            "atom_count": molecule_h.GetNumAtoms(),
            "bond_count": molecule_h.GetNumBonds(),

            # Campos explícitos para a primeira tabela.
            "atom_count_total": molecule_h.GetNumAtoms(),
            "bond_count_total": molecule_h.GetNumBonds(),
            "heavy_atom_count": molecule.GetNumHeavyAtoms(),
            "heavy_bond_count": molecule.GetNumBonds(),
            "rotatable_bonds": rotatable_bonds,
            "ring_count": ring_count,
            "aromatic_ring_count": aromatic_ring_count,
            "fraction_csp3": fraction_csp3,
            "hbd": hbd,
            "hba": hba,
            "formal_charge": formal_charge,
            "bertz_complexity": bertz_complexity,
            "wiener_index": wiener_index,
            "randic_index": randic_index,
            "active_component_smiles": self.Chem.MolToSmiles(active),
            "descriptor_scope": "active fragment; formula/mass/counts refer to full input",
            "logp": logp,
            "tpsa": tpsa,
            "qed": qed,
            "molar_refractivity": molar_refractivity,

            # Também em português, porque algumas telas usam estes nomes.
            "total_atomos": molecule_h.GetNumAtoms(),
            "total_ligacoes": molecule_h.GetNumBonds(),
            "total_atomos_pesados": molecule.GetNumHeavyAtoms(),
            "total_ligacoes_pesadas": molecule.GetNumBonds(),
            "rotatable_bonds": rotatable_bonds,
            "total_aneis": ring_count,
            "aneis_aromaticos": aromatic_ring_count,
            "fracao_csp3": fraction_csp3,
            "complexidade_bertz": bertz_complexity,
            "indice_wiener": wiener_index,
            "indice_randic": randic_index,
            "carga_formal_total": formal_charge,

            "svg": svg,
            "atoms": atoms,
            "bonds": bonds,
        }

    def _draw_svg(self, molecule, width: int, height: int) -> str:
        prepared = self.rdMolDraw2D.PrepareMolForDrawing(
            molecule,
            kekulize=True,
            addChiralHs=True,
            wedgeBonds=True,
        )

        drawer = self.rdMolDraw2D.MolDraw2DSVG(width, height)
        drawer.DrawMolecule(prepared)
        drawer.FinishDrawing()

        svg = drawer.GetDrawingText()
        return svg.replace("svg:", "")

    def _bond_order_to_rdkit_bond_type(self, order: float, is_aromatic: bool):
        if is_aromatic or order == 1.5:
            return self.Chem.BondType.AROMATIC

        if order == 1:
            return self.Chem.BondType.SINGLE

        if order == 2:
            return self.Chem.BondType.DOUBLE

        if order == 3:
            return self.Chem.BondType.TRIPLE

        raise ValueError(f"Ordem de ligação não suportada: {order}")
