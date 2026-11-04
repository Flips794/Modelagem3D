export type Molecule3DUnit =
  | "mol/L"
  | "mmol/L"
  | "µmol/L"
  | "g/L"
  | "mg/L"
  | "mol"
  | "mmol"
  | "µmol"
  | "g"
  | "mg"
  | "L"
  | "mL"
  | "% m/m"
  | "% mol"
  | "partes";

export type MoleculeTransferMeasurementSystem =
  | "concentration"
  | "amount"
  | "mass"
  | "volume"
  | "massPercent"
  | "molarPercent"
  | "ratio"
  | "moleculeCount";

export type MoleculeMixtureRole3D = "reagent" | "solvent";

export type MoleculeTransferEnvironment3D = {
  temperature_k: number;
  pressure_atm: number;
  ph: number;
  ionic_strength_mol_l: number;
  solvent_polarity_index: number;
  dielectric_constant: number;
  agitation_rpm: number;
  volume_ml: number;

  /**
   * Velocidade visual/computacional.
   * Não altera CMC real nem química real.
   */
  simulation_speed?: number;
  visual_speed_multiplier?: number;

  micelle_visualization_mode?: "auto" | "off" | "force" | string;
  interaction_visualization?: boolean;
  formation_visualization?: "emergent" | "diagnostic" | string;
};

export type MoleculeTransferMetadata = {
  measurementSystem?: MoleculeTransferMeasurementSystem;
  measurementLabel?: string;
  measurementUnit?: Molecule3DUnit;
  mixtureId?: string;
  mixedAt?: string;
  renderCount?: number;
  role?: MoleculeMixtureRole3D;
  roleLabel?: string;
  environment?: MoleculeTransferEnvironment3D;
  realAmountMmol?: number | null;
  realConcentrationMmolL?: number | null;
  solventExcess?: boolean | null;
};

export type Molecule3DAtom = {
  index: number;
  element: string;
  x: number;
  y: number;
  z: number;
  charge?: number | null;
  hybridization?: string | null;
  mass?: number | null;
};

export type Molecule3DBond = {
  index: number;
  atomAIndex: number;
  atomBIndex: number;
  order: number;
  isAromatic?: boolean;
  isConjugated?: boolean;
};

export type Molecule3DItem = {
  id: string;
  source2DId?: string | null;
  name: string;
  smiles: string;
  formula: string;
  concentration: number;
  unit: Molecule3DUnit;
  atoms: Molecule3DAtom[];
  bonds: Molecule3DBond[];
  source: "backend-rdkit" | "frontend-fallback" | "backend-simulation";
  transferMetadata?: MoleculeTransferMetadata;
  metadata?: {
    molecularWeight?: number | null;
    logp?: number | null;
    tpsa?: number | null;
    isSurfactant?: boolean | null;
    micellarBehavior?: string | null;
    surfactantClass?: string | null;
    cmcMmolL?: number | null;
    hlb?: number | null;
    effectiveHlb?: number | null;
    tailCarbonCount?: number | null;
    realAmountMmol?: number | null;
    realConcentrationMmolL?: number | null;
  };
};

export type MoleculeTransferFrom2D = {
  transferId?: string;
  id?: string;
  name?: string;
  smiles: string;
  formula?: string;
  molarMass?: string;
  status?: string;
  concentration?: string | number;
  unit?: Molecule3DUnit;
  transferMetadata?: MoleculeTransferMetadata;
};

export type SolutionTransferEventDetail = {
  mode: "replace" | "clear" | "cancel";
  molecules?: MoleculeTransferFrom2D[];
  mixtureId?: string;
  createdAt?: string;
  reason?: string;
  revision?: number;
};

export type Molecules3DStoragePayload = {
  mode: "replace";
  molecules: MoleculeTransferFrom2D[];
  mixtureId: string;
  createdAt: string;
  revision: number;
};

export type SimulationSettings3D = {
  dynamicMode: boolean;
  showInteractionField: boolean;
  showReactionAura: boolean;
  agitation: number;
  temperature: number;
  solventPolarity: number;
  ph: number;
  ionicStrength: number;
  pressure: number;
};

export type SendableMolecule2D = {
  id?: string;
  name?: string;
  formula?: string;
  smiles?: string;
  canonical_smiles?: string;
  molarMass?: string;
  molecularWeight?: number | string | null;
  status?: string;
  concentration?: string | number;
  unit?: Molecule3DUnit;
  transferMetadata?: MoleculeTransferMetadata;
  metadata?: {
    canonical_smiles?: string;
    formula?: string;
    molecular_weight?: number;
  };
};

export type SimulationBox3D = {
  x: number;
  y: number;
  z: number;
  center?: {
    x: number;
    y: number;
    z: number;
  };
};

export type SimulationAtom3D = {
  index: number;
  element: string;
  moleculeId: string;
  moleculeName?: string;
  residueName?: string;
  isSolvent?: boolean;
  radius?: number;
  color?: string;
  charge?: number | null;
  hybridization?: string | null;
  mass?: number | null;

  /**
   * Usado pelo Micelium para diferenciar bead de cabeça, cauda, solvente e soluto.
   */
  particleKind?: MiceliumParticleKind | string;
};

export type SimulationBond3D = {
  index: number;
  atomAIndex: number;
  atomBIndex: number;
  order: number;
  moleculeId: string;
  drawAcrossPbc?: boolean;
};

export type MiceliumCluster3D = {
  id: string;
  particle_ids: string[];
  surfactant_count: number;
  center: number[];
  radius: number;
  core_radius: number;
  stability_score: number;
  aggregation_number: number;
  morphology: string;
  phase?: string | null;
};

export type MiceliumAnalysis3D = {
  total_particles: number;
  molecule_count: number;
  surfactant_count: number;
  solvent_count: number;
  solute_count: number;
  c_over_cmc_proxy?: number | null;
  real_concentration_mmol_l?: number | null;
  real_amount_mmol?: number | null;
  critical_amount_mmol?: number | null;
  missing_amount_mmol?: number | null;
  excess_amount_mmol?: number | null;
  visual_scale_factor?: number | null;
  micelle_probability: number;
  average_cluster_size: number;
  cluster_count: number;
  largest_cluster_size: number;
  mean_head_distance?: number | null;
  stability_score: number;
  dominant_morphology?: string | null;
  predicted_morphology?: string | null;
  morphology_distribution?: Record<string, number>;
  formation_phase?: string | null;
  micellized_fraction?: number | null;
  free_monomer_fraction?: number | null;
  orientation_score?: number | null;
  hydrophobic_core_score?: number | null;
  hydrophobic_exposure?: number | null;
  warnings: string[];
};

export type SimulationTopology3D = {
  id: string;
  title: string;
  box: SimulationBox3D;
  atoms: SimulationAtom3D[];
  bonds: SimulationBond3D[];
  moleculeCount: number;
  createdAt: string;

  source?: "rdkit-openmm" | "micelium";
  clusters?: MiceliumCluster3D[];
  analysis?: MiceliumAnalysis3D | null;
};

export type SimulationFrame3D = {
  frameIndex: number;
  timePs: number;
  coordinates: Array<[number, number, number]>;
  box?: SimulationBox3D;
  hiddenBonds?: number[];
};

export type SimulationStartMessage3D = {
  type: "start";
  topology: SimulationTopology3D;
  frame: SimulationFrame3D;
  stepsPerFrame?: number;
  targetHz?: number;
  temperatureK?: number;
  frictionPerPs?: number;
  timestepFs?: number;
  minimize?: boolean;
  minimizeMaxIterations?: number;
  geodesicPaddingNm?: number;
};

export type SimulationStreamMessage3D =
  | {
      type: "topology";
      topology: SimulationTopology3D;
    }
  | {
      type: "frame";
      frame: SimulationFrame3D;
    }
  | {
      type: "status";
      message: string;
    }
  | {
      type: "error";
      message: string;
    };

export type MiceliumParticleKind =
  | "head"
  | "tail"
  | "counterion"
  | "solvent"
  | "solute"
  | "atomistic";

export type MiceliumEnvironment3D = {
  temperature_k: number;
  pressure_atm: number;
  ph: number;
  ionic_strength_mol_l: number;
  solvent_polarity_index: number;
  dielectric_constant: number;
  agitation_rpm: number;
  volume_ml: number;
  visual_speed_multiplier?: number;
  simulation_speed?: number | null;
  solvent_name?: string;
  solvent_mode?: string;
  solvent_description?: string | null;
  stable_preset?: boolean;
};

export type MiceliumMoleculeInput3D = {
  id?: string | null;
  name?: string | null;
  smiles: string;
  formula?: string | null;
  role: MoleculeMixtureRole3D;
  count: number;
  is_surfactant?: boolean | null;
  surfactant_class?: string | null;
  logp?: number | null;
  tpsa?: number | null;
  cmc_mmol_l?: number | null;
  hlb?: number | null;
  effective_hlb?: number | null;
  tail_carbon_count?: number | null;
  head_area_a2?: number | null;
  tail_volume_a3?: number | null;
  packing_parameter?: number | null;
  micellar_behavior?: string | null;
  visual_count?: number | null;
  visual_scale_factor?: number | null;
  real_amount_mmol?: number | null;
  real_amount_unit?: string | null;
  real_concentration_mmol_l?: number | null;
  solvent_excess?: boolean | null;
};

export type MiceliumSimulationRequest3D = {
  molecules: MiceliumMoleculeInput3D[];
  environment: MiceliumEnvironment3D;
  max_particles?: number;
  steps?: number;
  dt?: number;
  seed?: number;
};

export type MiceliumParticle3D = {
  id: string;
  molecule_id: string;
  molecule_name: string;
  role: MoleculeMixtureRole3D;
  kind: MiceliumParticleKind;
  bead_index: number;
  position: number[];
  velocity: number[];
  charge: number;
  radius: number;
  mass: number;
  polarity: number;
  hydrophobicity: number;
  color: string;
};

export type MiceliumBond3D = {
  id: string;
  particle_a: string;
  particle_b: string;
  stiffness: number;
  length: number;
};

export type MiceliumFrame3D = {
  frame_index: number;
  time_ps: number;
  coordinates: number[][];
};

export type MiceliumSimulationResponse3D = {
  engine: string;
  engine_version: string;
  representation: string;
  environment: MiceliumEnvironment3D;
  particles: MiceliumParticle3D[];
  bonds: MiceliumBond3D[];
  frames: MiceliumFrame3D[];
  clusters: MiceliumCluster3D[];
  analysis: MiceliumAnalysis3D;
  notes: string[];
};

export const MOLECULES_3D_STORAGE_KEY =
  "modelagem3d:environment3d:molecules";

export const MOLECULES_3D_TRANSFER_EVENT =
  "modelagem3d:add-molecule-to-3d";

export const MIXTURE_ENVIRONMENT_STORAGE_KEY =
  "modelagem3d:environment3d:settings";

export const MIXTURE_ENVIRONMENT_EVENT =
  "modelagem3d:environment-updated";

const VALID_MOLECULE_3D_UNITS: Molecule3DUnit[] = [
  "mol/L",
  "mmol/L",
  "µmol/L",
  "g/L",
  "mg/L",
  "mol",
  "mmol",
  "µmol",
  "g",
  "mg",
  "L",
  "mL",
  "% m/m",
  "% mol",
  "partes",
];

function normalizeUnitText(unit: unknown): string {
  const value = String(unit ?? "").trim();

  if (!value) return "";

  return value
    .replaceAll("µ", "µ")
    .replaceAll("µ", "µ")
    .replace(/^umol\b/i, "µmol")
    .replace(/^u mol\b/i, "µmol");
}

function isMolecule3DUnit(unit: unknown): unit is Molecule3DUnit {
  const normalized = normalizeUnitText(unit);

  return VALID_MOLECULE_3D_UNITS.includes(normalized as Molecule3DUnit);
}

function createTransferId(molecule: SendableMolecule2D) {
  const base =
    molecule.id ??
    molecule.smiles ??
    molecule.canonical_smiles ??
    molecule.metadata?.canonical_smiles ??
    "mol2d";

  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${base}_${crypto.randomUUID()}`;
  }

  return `${base}_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function normalizeUnit(unit: unknown): Molecule3DUnit {
  const normalized = normalizeUnitText(unit);

  if (isMolecule3DUnit(normalized)) {
    return normalized as Molecule3DUnit;
  }

  return "partes";
}



function resolveSmiles(molecule: SendableMolecule2D) {
  return (
    molecule.smiles?.trim() ||
    molecule.canonical_smiles?.trim() ||
    molecule.metadata?.canonical_smiles?.trim() ||
    ""
  );
}

function resolveFormula(molecule: SendableMolecule2D) {
  return molecule.formula?.trim() || molecule.metadata?.formula?.trim() || "";
}

function resolveMolarMass(molecule: SendableMolecule2D) {
  if (molecule.molarMass?.trim()) return molecule.molarMass.trim();

  const molecularWeight =
    molecule.molecularWeight ?? molecule.metadata?.molecular_weight ?? null;

  if (typeof molecularWeight === "number" && Number.isFinite(molecularWeight)) {
    return molecularWeight.toFixed(3);
  }

  if (typeof molecularWeight === "string" && molecularWeight.trim()) {
    return molecularWeight.trim();
  }

  return "";
}

function resolveName(molecule: SendableMolecule2D) {
  return molecule.name?.trim() || resolveFormula(molecule) || "Molécula 2D";
}

function normalizeRenderCount(value: unknown) {
  const parsed = Number(value);

  if (!Number.isFinite(parsed)) return undefined;

  return Math.max(1, Math.floor(parsed));
}

export function buildMoleculeTransferFrom2D(
  molecule: SendableMolecule2D
): MoleculeTransferFrom2D {
  const smiles = resolveSmiles(molecule);

  if (!smiles) {
    throw new Error(
      "A molécula não possui SMILES/canonical_smiles para envio ao 3D."
    );
  }

  const renderCount = normalizeRenderCount(
    molecule.transferMetadata?.renderCount
  );

  return {
    transferId: createTransferId(molecule),
    id: molecule.id,
    name: resolveName(molecule),
    smiles,
    formula: resolveFormula(molecule),
    molarMass: resolveMolarMass(molecule),
    status: molecule.status ?? "Aguardando",
    concentration: molecule.concentration ?? 1,
    unit: normalizeUnit(molecule.unit),
    transferMetadata: {
      ...molecule.transferMetadata,
      ...(renderCount ? { renderCount } : {}),
    },
  };
}

function createTransferRevision() {
  return Date.now();
}

function createMixtureIdForStorage() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `mixture_${crypto.randomUUID()}`;
  }

  return `mixture_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function writeMolecules3DStorage(
  molecules: MoleculeTransferFrom2D[],
  mixtureId = createMixtureIdForStorage()
): Molecules3DStoragePayload {
  const now = new Date().toISOString();
  const payload: Molecules3DStoragePayload = {
    mode: "replace",
    molecules,
    mixtureId,
    createdAt: now,
    revision: createTransferRevision(),
  };

  window.localStorage.setItem(MOLECULES_3D_STORAGE_KEY, JSON.stringify(payload));

  return payload;
}

export function sendMoleculeTo3D(molecule: SendableMolecule2D) {
  const payload = buildMoleculeTransferFrom2D(molecule);
  const mixtureId = createMixtureIdForStorage();
  const stored = writeMolecules3DStorage([payload], mixtureId);

  const detail: SolutionTransferEventDetail = {
    mode: "replace",
    molecules: [payload],
    mixtureId: stored.mixtureId,
    createdAt: stored.createdAt,
    revision: stored.revision,
    reason: "send-single-molecule-replace",
  };

  window.dispatchEvent(
    new CustomEvent<SolutionTransferEventDetail>(MOLECULES_3D_TRANSFER_EVENT, {
      detail,
    })
  );

  return payload;
}

export function replaceMoleculesIn3D(
  molecules: MoleculeTransferFrom2D[],
  mixtureId?: string
) {
  const safeMolecules = molecules.filter((molecule) => molecule.smiles?.trim());
  const stored = writeMolecules3DStorage(
    safeMolecules,
    mixtureId || createMixtureIdForStorage()
  );

  const detail: SolutionTransferEventDetail = {
    mode: "replace",
    molecules: safeMolecules,
    mixtureId: stored.mixtureId,
    createdAt: stored.createdAt,
    revision: stored.revision,
    reason: "replace-solution",
  };

  window.dispatchEvent(
    new CustomEvent<SolutionTransferEventDetail>(MOLECULES_3D_TRANSFER_EVENT, {
      detail,
    })
  );

  return detail;
}

export function clearMoleculesSentTo3D(reason = "transfer-panel-clear") {
  window.localStorage.removeItem(MOLECULES_3D_STORAGE_KEY);

  const detail: SolutionTransferEventDetail = {
    mode: "clear",
    molecules: [],
    createdAt: new Date().toISOString(),
    reason,
    revision: createTransferRevision(),
  };

  window.dispatchEvent(
    new CustomEvent<SolutionTransferEventDetail>(MOLECULES_3D_TRANSFER_EVENT, {
      detail,
    })
  );

  return detail;
}

export function cancelMolecule3DExecution(reason = "transfer-panel-cancel") {
  const detail: SolutionTransferEventDetail = {
    mode: "cancel",
    molecules: [],
    createdAt: new Date().toISOString(),
    reason,
    revision: createTransferRevision(),
  };

  window.dispatchEvent(
    new CustomEvent<SolutionTransferEventDetail>(MOLECULES_3D_TRANSFER_EVENT, {
      detail,
    })
  );

  return detail;
}


