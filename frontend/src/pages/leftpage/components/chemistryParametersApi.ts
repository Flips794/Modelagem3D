import type { InternalMoleculeModel } from "../../2dpage/type/rdkit2d.types";
import type { ChemistryParametersResponse } from "./chemistryParameters.types";

const API_BASE_URL = String(
  import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api/v1"
).replace(/\/$/, "");

/**
 * Ambiente padrão da molécula individual.
 *
 * Ele NÃO representa uma mistura real. É uma referência estável para estimar
 * propriedades da molécula pura no painel esquerdo:
 * - 298.15 K = 25 °C
 * - 1 atm
 * - pH 7
 * - força iônica baixa: 0.01 mol/L
 * - solvente polar idealizado, equivalente a água como referência
 * - constante dielétrica da água a 25 °C: aproximadamente 78.5
 * - sem agitação: 0 rpm
 * - volume de referência: 100 mL
 *
 * A solução real com solvente/reagentes/quantidade é manipulada na 3LeftPage.
 */
const STABLE_ISOLATED_ENVIRONMENT = {
  temperature_k: 298.15,
  pressure_atm: 1,
  ph: 7,
  ionic_strength_mol_l: 0.01,
  solvent_polarity_index: 1,
  dielectric_constant: 78.5,
  agitation_rpm: 0,
  volume_ml: 100,
};


type SafeLibraryStatus = {
  name: string;
  installed: boolean;
  purpose: string;
  import_error?: string | null;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function normalizeLibraryStatus(input: unknown): Record<string, SafeLibraryStatus> {
  const raw = isRecord(input) && "value" in input ? input.value : input;

  if (!isRecord(raw)) {
    return {};
  }

  const normalized: Record<string, SafeLibraryStatus> = {};

  Object.entries(raw).forEach(([key, value]) => {
    if (value === null || value === undefined) {
      normalized[key] = {
        name: key,
        installed: false,
        purpose: "Status indisponível.",
        import_error: null,
      };
      return;
    }

    if (typeof value === "boolean") {
      normalized[key] = {
        name: key,
        installed: value,
        purpose: "Status booleano recebido do backend.",
        import_error: null,
      };
      return;
    }

    if (isRecord(value)) {
      const installedSource = value.installed ?? value.ok ?? value.available ?? false;
      const nameSource = value.name ?? value.source ?? key;
      const purposeSource = value.purpose ?? value.note ?? "Biblioteca/recurso informado pelo backend.";
      const errorSource = value.import_error ?? value.error ?? null;

      normalized[key] = {
        name: String(nameSource),
        installed: Boolean(installedSource),
        purpose: String(purposeSource),
        import_error: errorSource === null || errorSource === undefined ? null : String(errorSource),
      };
      return;
    }

    normalized[key] = {
      name: key,
      installed: Boolean(value),
      purpose: "Status convertido automaticamente para evitar quebra visual.",
      import_error: null,
    };
  });

  return normalized;
}

function normalizeChemistryParametersResponse(
  data: ChemistryParametersResponse
): ChemistryParametersResponse {
  const molecule = data.molecule as typeof data.molecule & {
    biblioteca_status?: unknown;
  };

  molecule.biblioteca_status = normalizeLibraryStatus(molecule.biblioteca_status) as never;

  return data;
}


function shouldGenerate3D(_molecule: InternalMoleculeModel) {
  // v36: painel individual sempre rápido; 3D pesado fica no ambiente 3D/Micelium.
  return false;
}

function getCanonicalSmiles(molecule: InternalMoleculeModel) {
  return (
    molecule.metadata?.canonical_smiles ||
    (molecule.metadata as Record<string, unknown>)?.smiles_canonico ||
    ""
  ).toString();
}

export type AnalyzeOptions = {
  /** Geometria 3D (ETKDG + MMFF94) só sob demanda, nunca automática. */
  generate3d?: boolean;
};

export async function analyzeChemistryParameters(
  molecule: InternalMoleculeModel,
  signal?: AbortSignal,
  options: AnalyzeOptions = {}
): Promise<ChemistryParametersResponse> {
  const canonicalSmiles = getCanonicalSmiles(molecule);

  if (!canonicalSmiles) {
    throw new Error("Molécula atual não possui SMILES canônico para análise.");
  }

  const response = await fetch(`${API_BASE_URL}/chemistry/parameters/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    signal,
    body: JSON.stringify({
      smiles: canonicalSmiles,
      internal_molecule: molecule,
      generate_3d: options.generate3d ?? shouldGenerate3D(molecule),
      deep_analysis: false,
      environment: STABLE_ISOLATED_ENVIRONMENT,
    }),
  });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;

    try {
      const data = await response.json();
      detail = data.detail ?? JSON.stringify(data);
    } catch {
      detail = await response.text();
    }

    throw new Error(detail || "Erro ao calcular parâmetros químicos.");
  }

  const data = await response.json() as ChemistryParametersResponse;
  return normalizeChemistryParametersResponse(data);
}


