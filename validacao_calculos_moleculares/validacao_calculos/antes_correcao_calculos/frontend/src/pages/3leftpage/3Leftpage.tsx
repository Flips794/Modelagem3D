import { useCallback, useEffect, useMemo, useState } from "react";

import { ParameterMetric } from "./components/ParameterMetric";

import "./3Leftpage.css";

type DynamicRecord = Record<string, unknown>;

type StoredMoleculeLike = {
  id?: string;
  transferId?: string;
  name?: string;
  smiles?: string;
  canonical_smiles?: string;
  formula?: string;
  concentration?: number | string;
  count?: number | string;
  quantity?: number | string;
  moleculeCount?: number | string;
  copies?: number | string;
  unit?: string;
  role?: "reagent" | "solvent";
  molecule?: {
    id?: string;
    name?: string;
    formula?: string;
    smiles?: string;
    canonical_smiles?: string;
    molarMass?: string | number;
    status?: string;
  };
  metadata?: DynamicRecord;
  transferMetadata?: {
    role?: "reagent" | "solvent";
    roleLabel?: string;
    environment?: DynamicEnvironmentPayload;
    renderCount?: number;
  };
};

type BackendParameterResponse = {
  success?: boolean;
  molecule?: DynamicRecord;
  molecule_parameters?: DynamicRecord;
  parameters?: DynamicRecord;
  warnings?: unknown;
  limitations?: unknown;
  libraries?: unknown;
};

type DynamicEnvironmentPayload = {
  temperature_k: number;
  pressure_atm: number;
  ph: number;
  ionic_strength_mol_l: number;
  solvent_polarity_index: number;
  dielectric_constant: number;
  agitation_rpm: number;
  volume_ml: number;
};

type MoleculeSetItem = {
  id: string;
  name: string;
  smiles: string;
  formula: string;
  count: number;
  role: "reagent" | "solvent";
  metadata: DynamicRecord;
  backend: DynamicRecord;
};

const ENVIRONMENT_STORAGE_KEY = "modelagem3d:environment3d:settings";
const TRANSFER_STATE_STORAGE_KEY = "modelagem3d:2dto3d:solution";
const TRANSFER_STATE_EVENT = "modelagem3d:transfer-state-updated";

const STABLE_ENVIRONMENT: DynamicEnvironmentPayload = {
  temperature_k: 298.15,
  pressure_atm: 1,
  ph: 7,
  ionic_strength_mol_l: 0.01,
  solvent_polarity_index: 1,
  dielectric_constant: 78.5,
  agitation_rpm: 0,
  volume_ml: 100,
};

const MIXTURE_STORAGE_KEYS = [
  "modelagem3d:environment3d:molecules",
  "modelagem3d:environment3d:last-mixture",
  TRANSFER_STATE_STORAGE_KEY,
  "modelagem3d:2dto3d:mixer",
  "modelagem3d:solution:molecules",
];

const REFRESH_EVENTS = [
  TRANSFER_STATE_EVENT,
  "modelagem3d:mixture-updated",
  "modelagem3d:mix-solution",
  "modelagem3d:environment-updated",
];

function getApiBaseUrl() {
  return String(
    import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api/v1"
  ).replace(/\/$/, "");
}

function asRecord(value: unknown): DynamicRecord {
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  return value as DynamicRecord;
}

function normalizeValue(value: unknown): unknown {
  if (value === null || value === undefined || value === "") return null;
  if (typeof value !== "object") return value;
  const record = asRecord(value);
  if ("available" in record && record.available === false) return null;
  if ("value" in record) return normalizeValue(record.value);
  if ("valor" in record) return normalizeValue(record.valor);
  return value;
}

function formatValue(value: unknown, suffix = ""): string {
  const normalized = normalizeValue(value);
  if (normalized === null || normalized === undefined || normalized === "") return "—";
  if (typeof normalized === "boolean") return normalized ? "sim" : "não";
  if (typeof normalized === "number") {
    const fixed =
      Math.abs(normalized) >= 100 ? normalized.toFixed(2) : normalized.toFixed(5);
    return `${String(Number(fixed))}${suffix}`;
  }
  if (Array.isArray(normalized)) {
    return normalized.length ? normalized.map((item) => formatValue(item)).join(", ") : "—";
  }
  if (typeof normalized === "object") {
    try {
      return JSON.stringify(normalized);
    } catch {
      return "—";
    }
  }
  return `${String(normalized)}${suffix}`;
}

function toNumber(value: unknown) {
  const normalized = normalizeValue(value);
  if (typeof normalized === "number" && Number.isFinite(normalized)) return normalized;
  if (typeof normalized === "string" && normalized.trim()) {
    const parsed = Number(normalized.replace(",", "."));
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function getFirstValue(records: DynamicRecord[], keys: string[]) {
  for (const record of records) {
    for (const key of keys) {
      const value = record[key];
      if (normalizeValue(value) !== null) return value;
    }
  }
  return null;
}

function getStoredEnvironment(): DynamicEnvironmentPayload {
  try {
    const raw = window.localStorage.getItem(ENVIRONMENT_STORAGE_KEY);
    if (!raw) return STABLE_ENVIRONMENT;

    const parsed = JSON.parse(raw);

    if (parsed?.normalized) {
      return { ...STABLE_ENVIRONMENT, ...parsed.normalized };
    }

    return {
      temperature_k: Number(parsed.temperatureK ?? STABLE_ENVIRONMENT.temperature_k),
      pressure_atm: Number(parsed.pressureAtm ?? STABLE_ENVIRONMENT.pressure_atm),
      ph: Number(parsed.ph ?? STABLE_ENVIRONMENT.ph),
      ionic_strength_mol_l: Number(parsed.ionicStrengthMolL ?? STABLE_ENVIRONMENT.ionic_strength_mol_l),
      solvent_polarity_index: Number(parsed.solventPolarityIndex ?? STABLE_ENVIRONMENT.solvent_polarity_index),
      dielectric_constant: Number(parsed.dielectricConstant ?? STABLE_ENVIRONMENT.dielectric_constant),
      agitation_rpm: Number(parsed.agitationRpm ?? STABLE_ENVIRONMENT.agitation_rpm),
      volume_ml: Number(parsed.volumeMl ?? STABLE_ENVIRONMENT.volume_ml),
    };
  } catch {
    return STABLE_ENVIRONMENT;
  }
}

function isStableEnvironment(environment: DynamicEnvironmentPayload) {
  return (
    Math.abs(environment.temperature_k - 298.15) < 0.01 &&
    Math.abs(environment.pressure_atm - 1) < 0.01 &&
    Math.abs(environment.ph - 7) < 0.01 &&
    Math.abs(environment.ionic_strength_mol_l - 0.01) < 0.0001
  );
}

function getSmiles(item: StoredMoleculeLike) {
  return String(
    item.smiles ??
      item.canonical_smiles ??
      item.molecule?.smiles ??
      item.molecule?.canonical_smiles ??
      item.metadata?.canonical_smiles ??
      item.metadata?.smiles ??
      ""
  ).trim();
}

function getCount(item: StoredMoleculeLike) {
  const raw =
    item.transferMetadata?.renderCount ??
    item.count ??
    item.quantity ??
    item.moleculeCount ??
    item.copies ??
    item.concentration ??
    1;

  const parsed = typeof raw === "number" ? raw : Number(String(raw).replace(",", "."));
  if (!Number.isFinite(parsed) || parsed <= 0) return 1;
  return Math.max(1, Math.round(parsed));
}

function getRole(item: StoredMoleculeLike): "reagent" | "solvent" {
  return item.role === "solvent" || item.transferMetadata?.role === "solvent"
    ? "solvent"
    : "reagent";
}

function extractItemsFromPayload(payload: unknown): StoredMoleculeLike[] {
  if (Array.isArray(payload)) {
    return payload.filter((item) => typeof item === "object") as StoredMoleculeLike[];
  }

  const record = asRecord(payload);
  const candidates = [
    record.molecules,
    record.items,
    record.solutionItems,
    record.solution,
    record.selectedMolecules,
    record.labMolecules,
    record.transfers,
  ];

  for (const candidate of candidates) {
    if (Array.isArray(candidate)) {
      return candidate.filter((item) => typeof item === "object") as StoredMoleculeLike[];
    }
  }

  return [];
}

function collectStoredMolecules(): StoredMoleculeLike[] {
  const collected: StoredMoleculeLike[] = [];

  MIXTURE_STORAGE_KEYS.forEach((key) => {
    try {
      const raw = window.localStorage.getItem(key);
      if (!raw) return;
      collected.push(...extractItemsFromPayload(JSON.parse(raw)));
    } catch {
      // Ignora chaves antigas/corrompidas.
    }
  });

  return collected;
}

async function fetchBackendParameters(smiles: string, environment: DynamicEnvironmentPayload) {
  if (!smiles) return {};

  const response = await fetch(`${getApiBaseUrl()}/chemistry/parameters/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ smiles, generate_3d: false, environment }),
  });

  if (!response.ok) return {};
  const json = (await response.json()) as BackendParameterResponse;
  return asRecord(json.molecule ?? json.molecule_parameters ?? json.parameters);
}

function dominantText(items: MoleculeSetItem[], keys: string[]) {
  const counter = new Map<string, number>();
  items.forEach((item) => {
    const value = getFirstValue([item.metadata, item.backend], keys);
    const text = formatValue(value);
    if (text === "—") return;
    counter.set(text, (counter.get(text) ?? 0) + item.count);
  });
  const ranked = Array.from(counter.entries()).sort((a, b) => b[1] - a[1]);
  return ranked[0]?.[0] ?? "—";
}

function weightedAverage(items: MoleculeSetItem[], keys: string[], suffix = "") {
  let weightedSum = 0;
  let weightTotal = 0;

  items.forEach((item) => {
    const value = getFirstValue([item.metadata, item.backend], keys);
    const number = toNumber(value);
    if (number === null) return;
    weightedSum += number * item.count;
    weightTotal += item.count;
  });

  if (weightTotal <= 0) return "—";
  return formatValue(weightedSum / weightTotal, suffix);
}

function weightedRawValue(items: MoleculeSetItem[], keys: string[], suffix = "") {
  if (items.length === 1) {
    const value = getFirstValue([items[0].metadata, items[0].backend], keys);
    return formatValue(value, suffix);
  }
  return weightedAverage(items, keys, suffix);
}

function getFirstNumberByKeys(records: DynamicRecord[], keys: string[]) {
  for (const record of records) {
    for (const key of keys) {
      const number = toNumber(record[key]);
      if (number !== null) {
        return { key, value: number };
      }
    }
  }

  return null;
}

function getCmcMmolLForItem(item: MoleculeSetItem) {
  const found = getFirstNumberByKeys(
    [item.metadata, item.backend],
    [
      "cmc_corrigida_mmol_l",
      "cmc_ambiente_estimada",
      "cmc_klevens_mmol_l",
      "cmc_estimada",
      "cmc",
      "cmc_corrigida_mol_l",
      "cmc_klevens_mol_l",
    ]
  );

  if (!found || found.value <= 0) return null;

  if (found.key.endsWith("_mol_l")) {
    return found.value * 1000;
  }

  return found.value;
}

function clintCmcMixMmolL(items: MoleculeSetItem[]) {
  const surfactants = items
    .map((item) => ({
      item,
      cmcMmolL: getCmcMmolLForItem(item),
    }))
    .filter((entry): entry is { item: MoleculeSetItem; cmcMmolL: number } =>
      entry.cmcMmolL !== null && Number.isFinite(entry.cmcMmolL) && entry.cmcMmolL > 0
    );

  const total = surfactants.reduce((sum, entry) => sum + entry.item.count, 0);

  if (total <= 0 || surfactants.length === 0) return "—";

  const denominator = surfactants.reduce((sum, entry) => {
    const alpha = entry.item.count / total;
    return sum + alpha / entry.cmcMmolL;
  }, 0);

  if (denominator <= 0) return "—";

  return `${formatValue(1 / denominator)} mmol/L`;
}

function clintCmcMixNote(items: MoleculeSetItem[]) {
  const usable = items.filter((item) => getCmcMmolLForItem(item) !== null);

  if (usable.length <= 1) {
    return "CMC do surfactante/reagente calculada por Klevens + correção ambiental.";
  }

  return "CMC da mistura calculada pelo modelo ideal de Clint: 1/CMCmix = Σ(alpha_i/CMCi).";
}


function buildItemFromStored(item: StoredMoleculeLike, backend: DynamicRecord): MoleculeSetItem | null {
  const smiles = getSmiles(item);
  if (!smiles) return null;

  const molecule = asRecord(item.molecule);

  const metadata = {
    ...asRecord(item.metadata),
    ...asRecord(item.transferMetadata),
  };

  return {
    id: String(item.id ?? item.transferId ?? molecule.id ?? smiles),
    name: String(
      item.name ??
        molecule.name ??
        metadata.common_name ??
        metadata.formula ??
        smiles
    ),
    smiles,
    formula: String(item.formula ?? molecule.formula ?? metadata.formula ?? "—"),
    count: getCount(item),
    role: getRole(item),
    metadata,
    backend,
  };
}

export function ThreeLeftPage() {
  const [items, setItems] = useState<MoleculeSetItem[]>([]);
  const [environment, setEnvironment] = useState<DynamicEnvironmentPayload>(STABLE_ENVIRONMENT);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("Aguardando mistura ou molécula atual.");

  const reagentItems = useMemo(() => items.filter((item) => item.role === "reagent"), [items]);
  const solventItems = useMemo(() => items.filter((item) => item.role === "solvent"), [items]);
  const activeItems = reagentItems.length > 0 ? reagentItems : items;

  const cmcMixMmolL = useMemo(
    () => clintCmcMixMmolL(activeItems),
    [activeItems]
  );

  const cmcMixNote = useMemo(
    () => clintCmcMixNote(activeItems),
    [activeItems]
  );

  const totalCount = useMemo(
    () => items.reduce((sum, item) => sum + item.count, 0),
    [items]
  );

  const reagentCount = useMemo(
    () => reagentItems.reduce((sum, item) => sum + item.count, 0),
    [reagentItems]
  );

  const solventCount = useMemo(
    () => solventItems.reduce((sum, item) => sum + item.count, 0),
    [solventItems]
  );

  const environmentLabel = useMemo(
    () => `${environment.temperature_k} K · ${environment.pressure_atm} atm · pH ${environment.ph}`,
    [environment]
  );

  const solventLabel = useMemo(
    () => solventItems.length > 0 ? solventItems.map((item) => item.name).join(", ") : "sem solvente",
    [solventItems]
  );

  const loadData = useCallback(async () => {
    const activeEnvironment = getStoredEnvironment();
    setEnvironment(activeEnvironment);

    const storedItems = collectStoredMolecules();
    const uniqueItems = new Map<string, StoredMoleculeLike>();

    storedItems.forEach((item) => {
      const smiles = getSmiles(item);
      if (!smiles) return;

      const key = `${getRole(item)}:${smiles}:${item.name ?? ""}`;
      const current = uniqueItems.get(key);

      if (current) {
        uniqueItems.set(key, {
          ...current,
          count: getCount(current) + getCount(item),
          concentration: getCount(current) + getCount(item),
          metadata: {
            ...asRecord(item.metadata),
            ...asRecord(current.metadata),
          },
        });
      } else {
        uniqueItems.set(key, item);
      }
    });

    const nextStored = Array.from(uniqueItems.values());

    if (nextStored.length === 0) {
      setItems([]);
      setStatus("Nenhuma molécula disponível para análise do conjunto.");
      return;
    }

    setLoading(true);

    try {
      const nextItems = await Promise.all(
        nextStored.map(async (item) => {
          const backend = await fetchBackendParameters(getSmiles(item), activeEnvironment);
          return buildItemFromStored(item, backend);
        })
      );

      setItems(nextItems.filter((item): item is MoleculeSetItem => Boolean(item)));
      setStatus(
        isStableEnvironment(activeEnvironment)
          ? "Parâmetros carregados em ambiente estável padrão."
          : "Parâmetros recalculados com ambiente ajustado pelo usuário."
      );
    } catch {
      setStatus("Não foi possível consultar todos os parâmetros do backend.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();

    const handleRefresh = () => void loadData();

    REFRESH_EVENTS.forEach((eventName) => {
      window.addEventListener(eventName, handleRefresh);
    });

    window.addEventListener("storage", handleRefresh);

    return () => {
      REFRESH_EVENTS.forEach((eventName) => {
        window.removeEventListener(eventName, handleRefresh);
      });
      window.removeEventListener("storage", handleRefresh);
    };
  }, [loadData]);

  return (
    <aside className="three-left-page" aria-label="Parâmetros do conjunto molecular">
      <header className="three-left-header">
        <div>
          <span>Segunda coluna</span>
          <strong>Mistura / solução</strong>
        </div>

        <button
          type="button"
          onClick={() => void loadData()}
          disabled={loading}
          aria-busy={loading}
          title={loading ? "Atualizando dados da mistura..." : "Atualizar dados da mistura"}
        >
          Atualizar
        </button>
      </header>

      <section className="three-left-system-card">
        <div className="three-left-system-title">
          <span>{isStableEnvironment(environment) ? "Ambiente estável" : "Ambiente ajustado"}</span>
          <strong>{environmentLabel}</strong>
        </div>

        <div className="three-left-mini-grid">
          <div className="three-left-mini-stat"><span>Total de moléculas</span><strong>{totalCount}</strong></div>
          <div className="three-left-mini-stat"><span>Reagentes</span><strong>{reagentCount}</strong></div>
          <div className="three-left-mini-stat"><span>Solvente</span><strong>{solventCount > 0 ? solventCount : "opcional"}</strong></div>
          <div className="three-left-mini-stat"><span>Molécula solvente</span><strong>{solventLabel}</strong></div>
          <div className="three-left-mini-stat"><span>Força iônica</span><strong>{environment.ionic_strength_mol_l} mol/L</strong></div>
          <div className="three-left-mini-stat"><span>Agitação</span><strong>{environment.agitation_rpm} rpm</strong></div>
        </div>
      </section>

      <section className="three-left-section">
        <div className="three-left-section-title">
          <span>Parâmetros dinâmicos e físico-químicos da mistura</span>
          <small>média ponderada pelos reagentes; solvente separado como meio</small>
        </div>

        <ParameterMetric label="LogP" value={weightedRawValue(activeItems, ["logp", "LogP"])} />
        <ParameterMetric label="LogD" value={weightedRawValue(activeItems, ["logd", "LogD", "coeficiente_distribuicao_ph"])} />
        <ParameterMetric label="pKa" value={weightedRawValue(activeItems, ["pka", "pKa"])} />
        <ParameterMetric label="LogS" value={weightedRawValue(activeItems, ["logs", "log_s", "LogS", "solubilidade_aquosa"])} />
        <ParameterMetric label="TPSA" value={weightedRawValue(activeItems, ["tpsa", "TPSA"], " Å²")} />
        <ParameterMetric label="SASA total" value={weightedRawValue(activeItems, ["sasa_total", "sasa", "superficie_acessivel_solvente"], " Å²")} />
        <ParameterMetric label="Raio de giração" value={weightedRawValue(activeItems, ["raio_de_giracao", "raio_giracao", "radius_of_gyration"], " Å")} />
        <ParameterMetric label="NPR1" value={weightedRawValue(activeItems, ["npr1", "NPR1"])} />
        <ParameterMetric label="NPR2" value={weightedRawValue(activeItems, ["npr2", "NPR2"])} />
        <ParameterMetric label="Volume de Van der Waals" value={weightedRawValue(activeItems, ["volume_vdw_total", "volume_vdw", "vdw_volume", "volume_van_der_waals"], " Å³")} />
        <ParameterMetric label="Energia conformacional / estérica" value={weightedRawValue(activeItems, ["energia_conformacional", "energia_esterica", "conformational_energy"], " kcal/mol")} />
        <ParameterMetric label="Energia livre de Gibbs de solvatação" value={weightedRawValue(activeItems, ["energia_livre_gibbs_solvacao", "gibbs_solvation_energy"], " kcal/mol")} />
        <ParameterMetric label="Calor de formação" value={weightedRawValue(activeItems, ["calor_de_formacao", "heat_of_formation", "entalpia_formacao"])} />
        <ParameterMetric label="Refratividade molar" value={weightedRawValue(activeItems, ["refratividade_molar", "molar_refractivity"])} />
        <ParameterMetric label="Densidade" value={weightedRawValue(activeItems, ["densidade", "density"], " g/cm³")} />
        <ParameterMetric label="Ponto de fusão" value={weightedRawValue(activeItems, ["ponto_fusao", "melting_point"], " °C")} />
        <ParameterMetric label="Ponto de ebulição" value={weightedRawValue(activeItems, ["ponto_ebulicao", "boiling_point"], " °C")} />
        <ParameterMetric label="Pressão de vapor" value={weightedRawValue(activeItems, ["pressao_vapor", "vapor_pressure"], " atm")} />
        <ParameterMetric label="Tensão superficial" value={weightedRawValue(activeItems, ["tensao_superficial", "surface_tension"], " mN/m")} />
        <ParameterMetric label="Viscosidade" value={weightedRawValue(activeItems, ["viscosidade", "viscosity"], " cP")} />
      </section>

      <section className="three-left-section">
        <div className="three-left-section-title">
          <span>Surfactante, micela e agregação na mistura</span>
          <small>parâmetros de comportamento do sistema</small>
        </div>

        <ParameterMetric label="Classe surfactante" value={dominantText(activeItems, ["classe_surfactante", "surfactant_class"])} emphasis />
        <ParameterMetric label="Comportamento micelar" value={dominantText(activeItems, ["comportamento_micelar_previsto", "comportamento_micelar", "micellar_behavior"])} emphasis />
        <ParameterMetric label="Índice anfifílico" value={weightedRawValue(activeItems, ["indice_anfifilico", "amphiphilic_index"])} />
        <ParameterMetric label="Comprimento da cauda" value={weightedRawValue(activeItems, ["comprimento_cauda", "tail_length"], " carbonos")} />
        <ParameterMetric label="Volume da cauda" value={weightedRawValue(activeItems, ["volume_cauda", "tail_volume"], " Å³")} />
        <ParameterMetric label="Área da cabeça micelar" value={weightedRawValue(activeItems, ["area_cabeca_micela", "head_area", "micellar_head_area"], " Å²")} />
        <ParameterMetric label="HLB" value={weightedRawValue(activeItems, ["hlb_estimado", "hlb", "HLB"])} />
        <ParameterMetric label="CMC" value={cmcMixMmolL} note={cmcMixNote} />
        <ParameterMetric label="XCMC" value={weightedRawValue(activeItems, ["x_cmc", "XCMC"])} />
        <ParameterMetric label="ΔG° micelização" value={weightedRawValue(activeItems, ["delta_g_micelizacao", "delta_g_micellization"], " kJ/mol")} />
        <ParameterMetric label="HLD" value={weightedRawValue(activeItems, ["hld", "HLD"])} />
        <ParameterMetric label="NAC" value={weightedRawValue(activeItems, ["nac", "NAC"], " 1/Å")} />
        <ParameterMetric label="Parâmetro de empacotamento" value={weightedRawValue(activeItems, ["parametro_empacotamento", "packing_parameter"])} />
        <ParameterMetric label="QED" value={weightedRawValue(activeItems, ["qed", "QED"])} />
        <ParameterMetric label="Qualidade/Confiança da CMC" value={dominantText(activeItems, ["confianca_cmc"])} />
        <ParameterMetric label="Perfil de calibração" value={dominantText(activeItems, ["perfil_calibracao_literatura"])} />
        <ParameterMetric label="Identificação MIRIAM-2.1" value={dominantText(activeItems, ["miriam2_identity"])} />
        <ParameterMetric label="Validação física MIRIAM-2.1" value={dominantText(activeItems, ["miriam2_physical_validation"])} />
      </section>

      <section className="three-left-section">
        <div className="three-left-section-title">
          <span>Índices de grafo e biblioteca</span>
          <small>calculados via RDKit quando disponível</small>
        </div>

        <ParameterMetric label="Índice de Wiener" value={weightedRawValue(activeItems, ["indice_wiener", "wiener_index"])} />
        <ParameterMetric label="Índice de Randic" value={weightedRawValue(activeItems, ["indice_randic", "randic_index"])} />
      </section>

      <section className="three-left-section three-left-warnings">
        <div className="three-left-section-title">
          <span>Leitura dos dados</span>
          <small>dados da mistura, não da molécula isolada</small>
        </div>

        <p className="three-left-empty-warning">{status}</p>

        <p className="three-left-warning is-info">
          Esta coluna representa a manipulação de soluções: solvente opcional,
          reagentes, quantidades e ambiente. Os valores são atualizados depois
          do botão Misturar.
        </p>
      </section>
    </aside>
  );
}

export default ThreeLeftPage;
