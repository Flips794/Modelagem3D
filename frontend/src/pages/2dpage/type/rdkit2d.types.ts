export type ImportFormat = "SMILES" | "InChI" | "InChIKey" | "Auto";

export type Position2D = {
  x: number;
  y: number;
};

export type CanvasViewport = {
  zoom: number;
  panX: number;
  panY: number;
};

export type Viewport2D = CanvasViewport;

export type BondOrder = 1 | 2 | 3 | 1.5;

export type BondVisualStyle =
  | "single"
  | "double"
  | "triple"
  | "wedge-filled"
  | "wedge-dashed"
  | "dashed"
  | "single-resonance"
  | "double-resonance"
  | "aromatic";

export type BondRole =
  | "covalent"
  | "stereo"
  | "coordination"
  | "resonance"
  | "aromatic";

export type EditorToolState = {
  moveAtomToolActive: boolean;
  panToolActive: boolean;
  atomToolActive: boolean;
  bondToolActive: boolean;
  atomBondToolActive: boolean;
  radicalToolActive: boolean;
  lonePairToolActive: boolean;
  chargeToolActive: boolean;
  deleteToolActive: boolean;
};

export type InternalAtomModel = {
  id: string;
  rdkit_index: number;
  element: string;
  atomic_number: number;
  formal_charge: number;
  is_aromatic: boolean;
  chiral_tag: string;
  hybridization: string;
  total_hydrogens: number;
  implicit_hydrogens: number;
  explicit_hydrogens: number;
  total_valence: number | null;
  degree: number;
  position_2d: Position2D;
  radical_count?: number;
  lone_pair_count?: number;
};

export type InternalBondModel = {
  id: string;
  rdkit_index: number;
  atom_a_id: string;
  atom_b_id: string;
  atom_a_rdkit_index: number;
  atom_b_rdkit_index: number;
  order: number;
  bond_type: string;
  is_aromatic: boolean;
  is_conjugated?: boolean;
  stereo: string;
  direction: string;
  stereo_visual: "none" | "wedge" | "dash" | "unknown";
  visual_style?: BondVisualStyle;
  bond_role?: BondRole;
};

export type InternalMoleculeMetadata = {
  source: string;
  source_format: string;
  original_input: string;
  canonical_smiles: string;
  formula: string;
  molecular_weight: number;
  exact_molecular_weight: number;
  atom_count: number;
  bond_count: number;
};

export type InternalMoleculeModel = {
  id: string;
  model_version: string;
  metadata: InternalMoleculeMetadata;
  atoms: InternalAtomModel[];
  bonds: InternalBondModel[];
  svg: string | null;
  validation_state: {
    is_valid: boolean;
    warnings: string[];
    errors: string[];
  };
};

export type RDKitAtom2D = {
  index: number;
  symbol: string;
  atomic_number: number;
  formal_charge: number;
  is_aromatic: boolean;
  chiral_tag: string;
  hybridization: string;
  total_hydrogens: number;
  implicit_hydrogens: number;
  explicit_hydrogens: number;
  x: number;
  y: number;
};

export type RDKitBond2D = {
  index: number;
  begin_atom_index: number;
  end_atom_index: number;
  bond_type: string;
  order: number;
  is_aromatic: boolean;
  is_conjugated?: boolean;
  stereo: string;
  direction: string;
  visual_style?: BondVisualStyle;
  bond_role?: BondRole;
};

export type RDKitMolecule2D = {
  success: boolean;
  input_type: string;
  original_input: string;
  canonical_smiles: string;
  formula: string;
  molecular_weight: number;
  exact_molecular_weight: number;
  atom_count: number;
  bond_count: number;
  svg: string;
  atoms?: RDKitAtom2D[];
  bonds?: RDKitBond2D[];
  internal_molecule: InternalMoleculeModel;
};

export type EditableAtom2D = {
  index: number;
  symbol: string;
  formal_charge: number;
  is_aromatic: boolean;
  x: number;
  y: number;
};

export type EditableBond2D = {
  begin_atom_index: number;
  end_atom_index: number;
  order: number;
  is_aromatic: boolean;
  visual_style?: BondVisualStyle;
  bond_role?: BondRole;
};

export type EditableMoleculeGraph = {
  atoms: EditableAtom2D[];
  bonds: EditableBond2D[];
};

export type GraphToSmilesResult = {
  success: boolean;
  canonical_smiles: string;
  formula: string | null;
  molecular_weight: number | null;
  atom_count: number;
  bond_count: number;
  internal_molecule: InternalMoleculeModel | null;
};

export type Optimize2DInput = {
  internalMolecule: InternalMoleculeModel;
  graph: EditableMoleculeGraph;
  smiles?: string;
};

export type Hydrogens2DInput = {
  internalMolecule: InternalMoleculeModel;
  graph: EditableMoleculeGraph;
  smiles?: string;
  explicitHs: boolean;
};

export type PeriodicElement = {
  id: string;
  atomicNumber: number;
  symbol: string;
  name: string;
  atomicMass: number | null;
  category: string | null;
  period: number | null;
  group: number | null;
  block: string | null;
  colorHex: string | null;
  covalentRadiusPm?: number | null;
  vdwRadiusPm?: number | null;
};

export type SelectedMoleculeTarget =
  | {
      kind: "atom";
      id: string;
    }
  | {
      kind: "bond";
      id: string;
    }
  | null;

export type MinimapMoleculeAtom = {
  id: string;
  x: number;
  y: number;
};

export type MinimapMoleculeBond = {
  id: string;
  atomAId: string;
  atomBId: string;
};

export type SavedMolecule = {
  id: string;
  name: string;
  formula: string;
  smiles: string;
  molarMass: string;
  status: "Otimizada" | "Aguardando" | "Aviso";
  concentration: string;
  unit: "mol/L" | "mmol/L" | "µmol/L" | "g/L" | "mg/L";
};


