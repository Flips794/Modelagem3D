// Exemplos documentados de morfologias: catálogo do backend e montagem da mistura no painel 2D→3D.
// A forma de cada exemplo vem do backend (previsão validada no SDS; demonstração representativa nos demais).
import { API_BASE_URL } from "../../config/apiBaseUrl";

export type DocumentedConditionBasis = "experimental" | "protocol" | "technical";

export type DocumentedExampleComponentDto = {
  key: string;
  name: string;
  smiles: string;
  role: "reagent" | "solvent";
  amount_mmol: number | null;
  formula: string;
  molar_mass: number;
  is_surfactant: boolean | null;
  tail_carbon_count: number | null;
  tail_chain_count: number | null;
  example_role: string | null;
  derived_from_w0: boolean;
};

export type DocumentedExampleConditionDto = {
  parameter: string;
  label: string;
  basis: DocumentedConditionBasis;
  source: string;
  minimum?: number | null;
  maximum?: number | null;
  allowed?: string[] | null;
};

export type DocumentedExampleReferenceDto = { label: string; url: string | null };

export type DocumentedExampleDto = {
  id: string;
  title: string;
  kind: "validated_prediction" | "representative_demo";
  example_version: string;
  last_reviewed_at: string;
  documented_morphology: string;
  components: DocumentedExampleComponentDto[];
  environment: Record<string, number | string>;
  conditions: DocumentedExampleConditionDto[];
  protocol: string;
  references: DocumentedExampleReferenceDto[];
  notes: string[];
  w0: number | null;
  cmc_note?: string | null;
};

export type ExampleMixtureItem = {
  key: string;
  name: string;
  smiles: string;
  formula: string;
  molarMass: string;
  role: "reagent" | "solvent";
  amountMmol: number | null;
  derivedFromW0: boolean;
};

export type LoadedExampleState = {
  id: string;
  w0: number | null;
  aotKey: string | null;
  waterKey: string | null;
};

// Campos do ambiente do backend → chaves do painel (StableEnvironmentSettings).
const ENVIRONMENT_KEYS: Record<string, string> = {
  volume_ml: "volumeMl",
  temperature_k: "temperatureK",
  ionic_strength_mol_l: "ionicStrengthMolL",
  solvent_name: "solventName",
  dielectric_constant: "dielectricConstant",
  solvent_polarity_index: "solventPolarityIndex",
};

export async function fetchDocumentedExamples(signal?: AbortSignal): Promise<DocumentedExampleDto[]> {
  const response = await fetch(`${API_BASE_URL}/micelium/documented-examples`, { signal });
  if (!response.ok) {
    throw new Error(`Falha ao carregar os exemplos documentados (HTTP ${response.status}).`);
  }
  return (await response.json()) as DocumentedExampleDto[];
}

export function deriveCoreWaterMmol(w0: number, aotMmol: number): number {
  return w0 * aotMmol;
}

export function exampleToMixture(example: DocumentedExampleDto): {
  items: ExampleMixtureItem[];
  environment: Record<string, string>;
  state: LoadedExampleState;
} {
  const items = example.components.map((component) => ({
    key: component.key,
    name: component.name,
    smiles: component.smiles,
    formula: component.formula,
    molarMass: component.molar_mass.toFixed(2),
    role: component.role,
    amountMmol: component.amount_mmol,
    derivedFromW0: component.derived_from_w0,
  }));
  const environment: Record<string, string> = {};
  for (const [key, value] of Object.entries(example.environment)) {
    const panelKey = ENVIRONMENT_KEYS[key];
    if (panelKey) environment[panelKey] = String(value);
  }
  const water = example.components.find((component) => component.derived_from_w0) ?? null;
  const aot = water ? example.components.find((component) => component.is_surfactant) ?? null : null;
  return {
    items,
    environment,
    state: { id: example.id, w0: example.w0, aotKey: aot?.key ?? null, waterKey: water?.key ?? null },
  };
}
