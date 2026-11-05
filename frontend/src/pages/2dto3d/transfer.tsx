import { useEffect, useMemo, useState } from "react";

import type { SavedMolecule } from "../2dpage/type/rdkit2d.types";
import {
  buildMoleculeTransferFrom2D,
  cancelMolecule3DExecution,
  clearMoleculesSentTo3D,
  replaceMoleculesIn3D,
  type MoleculeMixtureRole3D,
  type MoleculeTransferFrom2D,
} from "../3dpage/type/3dpage.types";

import {
  deriveCoreWaterMmol,
  exampleToMixture,
  fetchDocumentedExamples,
  type DocumentedExampleDto,
  type LoadedExampleState,
} from "./documentedExamples";
import "./transfer.css";

type SolutionMolecule = {
  id: string;
  name: string;
  formula: string;
  smiles: string;
  molarMass: string;
  status: SavedMolecule["status"];
};

type SolutionItem = {
  id: string;
  molecule: SolutionMolecule;
  moleculeCount: string;
  role: MoleculeMixtureRole3D;
};

type StableEnvironmentSettings = {
  temperatureK: string;
  pressureAtm: string;
  ph: string;
  ionicStrengthMolL: string;
  solventPolarityIndex: string;
  dielectricConstant: string;
  agitationRpm: string;
  volumeMl: string;
  simulationSpeed: string;
  solventName: string;
};

type Transfer2DTo3DProps = {
  savedMolecules: SavedMolecule[];
  currentSmiles: string;
  currentFormula?: string | null;
  currentMolarMass?: number | string | null;
  currentStatus?: SavedMolecule["status"];
  onSaveCurrentMolecule: () => void;
  onOpenSavedMolecule: (smiles: string) => void | Promise<void>;
  onUpdateConcentration: (id: string, concentration: string) => void;
  onUpdateUnit?: (id: string, unit: SavedMolecule["unit"]) => void;
};

type TransferMessage = {
  type: "success" | "warning" | "error" | "info";
  text: string;
};

const MAX_MOLECULES_PER_COMPOUND = 5000;
const DEFAULT_REAGENT_COUNT = "10";
const DEFAULT_SOLVENT_COUNT = "250";

export const MIXTURE_ENVIRONMENT_STORAGE_KEY =
  "modelagem3d:environment3d:settings";

export const MIXTURE_ENVIRONMENT_EVENT =
  "modelagem3d:environment-updated";

export const MIXTURE_TRANSFER_STATE_STORAGE_KEY =
  "modelagem3d:2dto3d:solution";

export const MIXTURE_TRANSFER_STATE_EVENT =
  "modelagem3d:transfer-state-updated";

const STABLE_ENVIRONMENT: StableEnvironmentSettings = {
  temperatureK: "298.15",
  pressureAtm: "1",
  ph: "7",
  ionicStrengthMolL: "0.01",
  solventPolarityIndex: "1",
  dielectricConstant: "78.5",
  agitationRpm: "0",
  volumeMl: "100",
  simulationSpeed: "1",
  solventName: "water",
};

function createSolutionItemId(molecule: SolutionMolecule, role: MoleculeMixtureRole3D) {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${role}_${molecule.id}_${crypto.randomUUID()}`;
  }

  return `${role}_${molecule.id}_${Date.now()}_${Math.random()
    .toString(16)
    .slice(2)}`;
}

function createMixtureId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `mixture_${crypto.randomUUID()}`;
  }

  return `mixture_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}


function inferSolventNameFromMolecule(molecule: SolutionMolecule | null) {
  if (!molecule) return "water";

  const label = `${molecule.name} ${molecule.formula} ${molecule.smiles}`.toLowerCase();
  const smiles = molecule.smiles.trim();

  if (smiles === "O" || label.includes("água") || label.includes("agua") || label.includes("water") || label.includes("h2o")) {
    return "água";
  }

  if (smiles === "CCO" || smiles === "OCC" || label.includes("etanol") || label.includes("ethanol")) {
    return "etanol";
  }

  if (smiles === "CO" || smiles === "OC" || label.includes("metanol") || label.includes("methanol")) {
    return "metanol";
  }

  if (label.includes("óleo") || label.includes("oleo") || label.includes("oil") || label.includes("hexan") || /^C{5,}$/.test(smiles)) {
    return "meio apolar";
  }

  return molecule.name || molecule.formula || "solvente personalizado";
}

function getSolventVisualCount(environment: StableEnvironmentSettings) {
  const volume = getEnvironmentNumber(environment.volumeMl, 100);
  const speed = clampEnvironmentNumber(environment.simulationSpeed, 1, 0.1, 5);

  // Solvente representa excesso do meio. A contagem é visual e limitada para
  // não explodir o sistema.
  const visual = Math.round(110 + Math.sqrt(Math.max(volume, 1)) * 13 + speed * 8);

  return Math.max(80, Math.min(360, visual));
}


function toSolutionMolecule(molecule: SavedMolecule): SolutionMolecule {
  return {
    id: molecule.id,
    name: molecule.name,
    formula: molecule.formula,
    smiles: molecule.smiles,
    molarMass: molecule.molarMass,
    status: molecule.status,
  };
}


function sanitizeIntegerInput(value: string | number | undefined) {
  const onlyDigits = String(value ?? "").replace(/[^\d]/g, "");
  if (!onlyDigits) return "";
  const parsed = Math.floor(Number(onlyDigits));
  if (!Number.isFinite(parsed)) return "";
  return String(Math.max(0, Math.min(MAX_MOLECULES_PER_COMPOUND, parsed)));
}

function sanitizeDecimalInput(value: string | number | undefined, fallback = "") {
  const normalized = String(value ?? "")
    .replace(",", ".")
    .replace(/[^\d.-]/g, "");

  if (!normalized) return fallback;
  return Number.isFinite(Number(normalized)) ? normalized : fallback;
}

function getEnvironmentNumber(value: string, fallback: number) {
  const parsed = Number(String(value).replace(",", "."));
  return Number.isFinite(parsed) ? parsed : fallback;
}

function clampEnvironmentNumber(
  value: string,
  fallback: number,
  min: number,
  max: number
) {
  const parsed = getEnvironmentNumber(value, fallback);
  return Math.max(min, Math.min(max, parsed));
}

function normalizeEnvironment(environment: StableEnvironmentSettings) {
  return {
    temperature_k: getEnvironmentNumber(environment.temperatureK, 298.15),
    pressure_atm: getEnvironmentNumber(environment.pressureAtm, 1),
    ph: getEnvironmentNumber(environment.ph, 7),
    ionic_strength_mol_l: getEnvironmentNumber(environment.ionicStrengthMolL, 0.01),
    solvent_polarity_index: getEnvironmentNumber(environment.solventPolarityIndex, 1),
    dielectric_constant: getEnvironmentNumber(environment.dielectricConstant, 78.5),
    agitation_rpm: getEnvironmentNumber(environment.agitationRpm, 0),
    volume_ml: getEnvironmentNumber(environment.volumeMl, 100),
    simulation_speed: clampEnvironmentNumber(environment.simulationSpeed, 1, 0.1, 5),
    visual_speed_multiplier: clampEnvironmentNumber(environment.simulationSpeed, 1, 0.1, 5),
    solvent_name: environment.solventName || "water",
    solvent_mode: "excess",
    solvent_description: "Solvente em excesso: não usa quantidade molar no painel.",
  };
}

function getSafeMoleculeCount(value: string | number | undefined) {
  const sanitized = sanitizeIntegerInput(value);
  const parsed = Number(sanitized);
  if (!Number.isFinite(parsed) || parsed <= 0) return 0;
  return Math.max(0, Math.min(MAX_MOLECULES_PER_COMPOUND, Math.floor(parsed)));
}


function getAmountMmol(value: string | number | undefined) {
  const parsed = Number(String(value ?? "").replace(",", "."));

  if (!Number.isFinite(parsed) || parsed <= 0) return 0;

  return Math.max(0, Math.min(100000, parsed));
}

function getVisualRenderCountFromAmount(
  value: string | number | undefined,
  role: MoleculeMixtureRole3D,
  environment: StableEnvironmentSettings = STABLE_ENVIRONMENT
) {
  if (role === "solvent") {
    return getSolventVisualCount(environment);
  }

  const amountMmol = getAmountMmol(value);

  if (amountMmol <= 0) return 0;

  /*
   * A quantidade do painel agora é real em mmol.
   * Para não quebrar o 3D, a quantidade visual cresce de forma sublinear:
   * 0,01 mmol -> poucas moléculas;
   * 1 mmol    -> dezenas de surfactantes visuais;
   * 100 mmol  -> centenas, não milhares explosivos.
   */
  const visual = Math.round(8 + Math.sqrt(amountMmol) * 36);

  return Math.max(1, Math.min(MAX_MOLECULES_PER_COMPOUND, visual));
}

function getRealAmountMmolFromItem(item: SolutionItem) {
  if (item.role === "solvent") return null;

  return getAmountMmol(item.moleculeCount);
}

function getRealConcentrationMmolLFromItem(
  item: SolutionItem,
  environment: StableEnvironmentSettings
) {
  const amountMmol = getRealAmountMmolFromItem(item);

  if (amountMmol === null) return null;

  const volumeL = Math.max(getEnvironmentNumber(environment.volumeMl, 100) / 1000, 1e-12);

  return amountMmol / volumeL;
}

function buildStoredSolutionItems(
  items: SolutionItem[],
  environment: StableEnvironmentSettings,
  documentedExampleId: string | null = null
) {
  const normalized = normalizeEnvironment(environment);

  return items
    .map((item) => {
      const amountMmol = getAmountMmol(item.moleculeCount);
      const renderCount = getVisualRenderCountFromAmount(item.moleculeCount, item.role, environment);
      const realConcentrationMmolL = getRealConcentrationMmolLFromItem(item, environment);

      if (!item.molecule.smiles.trim() || renderCount <= 0) {
        return null;
      }

      if (item.role !== "solvent" && amountMmol <= 0) {
        return null;
      }

      return {
        id: item.id,
        name: item.molecule.name,
        formula: item.molecule.formula,
        smiles: item.molecule.smiles,
        molarMass: item.molecule.molarMass,
        status: item.molecule.status,
        moleculeCount: item.role === "solvent" ? "excesso" : String(amountMmol),
        count: renderCount,
        quantity: item.role === "solvent" ? null : amountMmol,
        concentration: item.role === "solvent" ? renderCount : amountMmol,
        unit: item.role === "solvent" ? "partes" : "mmol",
        transferMetadata: {
          role: item.role,
          roleLabel: item.role === "solvent" ? "Solvente" : "Reagente",
          measurementSystem: item.role === "solvent" ? "ratio" : "amount",
          measurementLabel:
            item.role === "solvent"
              ? "Solvente em excesso do meio"
              : "Quantidade real de reagente",
          measurementUnit: item.role === "solvent" ? "partes" : "mmol",
          solventExcess: item.role === "solvent",
          renderCount,
          realAmountMmol: item.role === "solvent" ? null : amountMmol,
          realConcentrationMmolL,
          environment: normalized,
          documentedExampleId,
        },
      };
    })
    .filter(Boolean);
}

function saveTransferState(
  items: SolutionItem[],
  environment: StableEnvironmentSettings,
  reason: string,
  documentedExampleId: string | null = null
) {
  if (typeof window === "undefined") return;

  const normalized = normalizeEnvironment(environment);
  const updatedAt = new Date().toISOString();

  window.localStorage.setItem(
    MIXTURE_ENVIRONMENT_STORAGE_KEY,
    JSON.stringify({
      ...environment,
      normalized,
      updatedAt,
    })
  );

  window.localStorage.setItem(
    MIXTURE_TRANSFER_STATE_STORAGE_KEY,
    JSON.stringify({
      items: buildStoredSolutionItems(items, environment, documentedExampleId),
      environment: normalized,
      updatedAt,
      reason,
    })
  );

  window.dispatchEvent(
    new CustomEvent(MIXTURE_TRANSFER_STATE_EVENT, {
      detail: {
        reason,
        environment: normalized,
        itemCount: items.length,
        updatedAt,
      },
    })
  );
}

function formatInteger(value: number) {
  return new Intl.NumberFormat("pt-BR").format(value);
}

function formatPercent(value: number) {
  if (!Number.isFinite(value)) return "0%";
  if (value >= 10) return `${value.toFixed(1)}%`;
  return `${value.toFixed(2)}%`;
}

function readStoredEnvironment() {
  try {
    const raw = window.localStorage.getItem(MIXTURE_ENVIRONMENT_STORAGE_KEY);
    if (!raw) return STABLE_ENVIRONMENT;
    const parsed = JSON.parse(raw) as Partial<StableEnvironmentSettings>;
    return { ...STABLE_ENVIRONMENT, ...parsed };
  } catch {
    return STABLE_ENVIRONMENT;
  }
}

function saveEnvironment(environment: StableEnvironmentSettings) {
  const normalized = normalizeEnvironment(environment);
  const updatedAt = new Date().toISOString();

  window.localStorage.setItem(
    MIXTURE_ENVIRONMENT_STORAGE_KEY,
    JSON.stringify({
      ...environment,
      normalized,
      updatedAt,
    })
  );

  window.dispatchEvent(
    new CustomEvent(MIXTURE_ENVIRONMENT_EVENT, {
      detail: normalized,
    })
  );
}

export default function Transfer2DTo3D({
  savedMolecules,
  currentSmiles,
  onSaveCurrentMolecule,
  onOpenSavedMolecule,
}: Transfer2DTo3DProps) {
  const [solutionItems, setSolutionItems] = useState<SolutionItem[]>([]);
  const [environment, setEnvironment] = useState<StableEnvironmentSettings>(() =>
    typeof window === "undefined" ? STABLE_ENVIRONMENT : readStoredEnvironment()
  );
  const [activeEnvironment, setActiveEnvironment] = useState<StableEnvironmentSettings>(() =>
    typeof window === "undefined" ? STABLE_ENVIRONMENT : readStoredEnvironment()
  );
  const [hasUnmixedChanges, setHasUnmixedChanges] = useState(false);
  const [message, setMessage] = useState<TransferMessage | null>(null);
  const [documentedExamples, setDocumentedExamples] = useState<DocumentedExampleDto[] | null>(null);
  const [documentedExamplesError, setDocumentedExamplesError] = useState<string | null>(null);
  const [loadedExample, setLoadedExample] = useState<LoadedExampleState | null>(null);
  const loadedExampleId = loadedExample?.id ?? null;

  useEffect(() => {
    const controller = new AbortController();
    fetchDocumentedExamples(controller.signal)
      .then((examples) => setDocumentedExamples(examples))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setDocumentedExamplesError(error instanceof Error ? error.message : "Falha ao carregar os exemplos documentados.");
      });
    return () => controller.abort();
  }, []);

  const hasCurrentMolecule = currentSmiles.trim().length > 0;
  const normalizedEnvironment = useMemo(() => normalizeEnvironment(environment), [environment]);
  const normalizedActiveEnvironment = useMemo(
    () => normalizeEnvironment(activeEnvironment),
    [activeEnvironment]
  );

  const solventItem = solutionItems.find((item) => item.role === "solvent") ?? null;
  const reagentItems = solutionItems.filter((item) => item.role === "reagent");

  const totalMoleculeCount = useMemo(
    () =>
      solutionItems.reduce(
        (sum, item) => sum + getVisualRenderCountFromAmount(item.moleculeCount, item.role, environment),
        0
      ),
    [solutionItems]
  );

  const totalReagentCount = useMemo(
    () =>
      reagentItems.reduce(
        (sum, item) => sum + getVisualRenderCountFromAmount(item.moleculeCount, item.role, environment),
        0
      ),
    [reagentItems]
  );

  const totalReagentAmountMmol = useMemo(
    () =>
      reagentItems.reduce(
        (sum, item) => sum + getAmountMmol(item.moleculeCount),
        0
      ),
    [reagentItems]
  );

  const selectedSavedMoleculeIds = useMemo(
    () => new Set(solutionItems.map((item) => item.molecule.id)),
    [solutionItems]
  );

  const environmentModeLabel = useMemo(() => {
    const draftSerialized = JSON.stringify(normalizedEnvironment);
    const activeSerialized = JSON.stringify(normalizedActiveEnvironment);
    const stable =
      Math.abs(normalizedEnvironment.temperature_k - 298.15) < 0.01 &&
      Math.abs(normalizedEnvironment.pressure_atm - 1) < 0.01 &&
      Math.abs(normalizedEnvironment.ph - 7) < 0.01 &&
      Math.abs(normalizedEnvironment.ionic_strength_mol_l - 0.01) < 0.0001;

    if (draftSerialized !== activeSerialized) {
      return "Ambiente pendente — clique em Aplicar";
    }

    return stable ? "Ambiente estável padrão aplicado" : "Ambiente ajustado aplicado";
  }, [normalizedEnvironment, normalizedActiveEnvironment]);

  function markSolutionDirty() {
    setHasUnmixedChanges(true);
  }

  function exampleItemId(example: LoadedExampleState, key: string) {
    return `exemplo:${example.id}:${key}`;
  }

  // Exemplo AOT: a água do núcleo é derivada de w0 × AOT sempre que o AOT ou o w0 mudam.
  function withDerivedWater(items: SolutionItem[], example: LoadedExampleState | null): SolutionItem[] {
    if (!example || example.w0 === null || !example.aotKey || !example.waterKey) return items;
    const aot = items.find((item) => item.id === exampleItemId(example, example.aotKey as string));
    if (!aot) return items;
    const waterMmol = deriveCoreWaterMmol(example.w0, getAmountMmol(aot.moleculeCount));
    return items.map((item) =>
      item.id === exampleItemId(example, example.waterKey as string)
        ? { ...item, moleculeCount: String(Number(waterMmol.toFixed(4))) }
        : item
    );
  }

  function isDerivedWater(item: SolutionItem) {
    return Boolean(loadedExample?.waterKey && item.id === exampleItemId(loadedExample, loadedExample.waterKey));
  }

  function commitSolutionItems(nextItems: SolutionItem[], reason: string) {
    const derived = withDerivedWater(nextItems, loadedExample);
    setSolutionItems(derived);
    saveTransferState(derived, environment, reason, loadedExampleId);
    markSolutionDirty();
  }

  function loadDocumentedExample(example: DocumentedExampleDto) {
    const { items, environment: exampleEnvironment, state } = exampleToMixture(example);
    const nextItems: SolutionItem[] = items.map((item) => ({
      id: exampleItemId(state, item.key),
      molecule: {
        id: exampleItemId(state, item.key),
        name: item.name,
        formula: item.formula,
        smiles: item.smiles,
        molarMass: item.molarMass,
        status: "Otimizada",
      },
      role: item.role,
      moleculeCount: item.role === "solvent" ? DEFAULT_SOLVENT_COUNT : String(item.amountMmol ?? 0),
    }));
    const nextEnvironment = { ...environment, ...exampleEnvironment } as StableEnvironmentSettings;
    setEnvironment(nextEnvironment);
    setLoadedExample(state);
    setSolutionItems(nextItems);
    saveTransferState(nextItems, nextEnvironment, "solution:example-loaded", state.id);
    markSolutionDirty();
    setMessage({
      type: "info",
      text: `Exemplo carregado: ${example.title}. Confira o meio e clique em Misturar no 3D.`,
    });
  }

  function updateExampleW0(value: string) {
    if (!loadedExample) return;
    const w0 = Number(sanitizeDecimalInput(value, String(loadedExample.w0 ?? "")));
    if (!Number.isFinite(w0) || w0 < 0) return;
    const nextExample = { ...loadedExample, w0 };
    setLoadedExample(nextExample);
    const derived = withDerivedWater(solutionItems, nextExample);
    setSolutionItems(derived);
    saveTransferState(derived, environment, "solution:example-w0", nextExample.id);
    markSolutionDirty();
  }

  function unlinkDocumentedExample() {
    setLoadedExample(null);
    saveTransferState(solutionItems, environment, "solution:example-unlinked", null);
    markSolutionDirty();
    setMessage({
      type: "info",
      text: "Exemplo desvinculado. A mistura continua aqui e será tratada pelo cálculo normal.",
    });
  }

  function updateEnvironmentField(key: keyof StableEnvironmentSettings, value: string) {
    const nextValue =
      key === "solventName"
        ? value
        : sanitizeDecimalInput(value, environment[key]);

    if (nextValue === environment[key]) {
      return;
    }

    setEnvironment({
      ...environment,
      [key]: nextValue,
    });
    markSolutionDirty();
  }

  function resetEnvironment() {
    setEnvironment(STABLE_ENVIRONMENT);
    setActiveEnvironment(STABLE_ENVIRONMENT);
    saveEnvironment(STABLE_ENVIRONMENT);
    saveTransferState(solutionItems, STABLE_ENVIRONMENT, "environment:reset");

    if (reagentItems.length > 0 && totalReagentCount > 0) {
      const mixtureId = createMixtureId();
      replaceMoleculesIn3D(buildTransferPayloads(mixtureId, STABLE_ENVIRONMENT), mixtureId);
      setHasUnmixedChanges(false);
    } else {
      markSolutionDirty();
    }

    setMessage({
      type: "info",
      text: "Ambiente restaurado para 298,15 K, 1 atm, pH 7, água polar e baixa força iônica.",
    });
  }

  function addMoleculeToSolution(savedMolecule: SavedMolecule, role: MoleculeMixtureRole3D) {
    const molecule = toSolutionMolecule(savedMolecule);

    if (role === "solvent") {
      const nextItems: SolutionItem[] = [
        ...solutionItems.filter((item) => item.role !== "solvent"),
        {
          id: createSolutionItemId(molecule, "solvent"),
          molecule,
          role: "solvent",
          moleculeCount: DEFAULT_SOLVENT_COUNT,
        },
      ];

      const nextEnvironment = {
        ...environment,
        solventName: inferSolventNameFromMolecule(molecule),
      };

      setEnvironment(nextEnvironment);
      saveEnvironment(nextEnvironment);
      commitSolutionItems(nextItems, "solution:solvent-updated");

      setMessage({
        type: "info",
        text: `${molecule.name} definida como solvente em excesso. pH, dielétrica, volume e velocidade não foram alterados automaticamente.`,
      });
      return;
    }

    const alreadySelected = solutionItems.some(
      (item) => item.role === "reagent" && item.molecule.id === molecule.id
    );

    if (alreadySelected) {
      setMessage({
        type: "warning",
        text: `${molecule.name} já está como reagente. Altere a quantidade na área de preparo.`,
      });
      return;
    }

    const nextItems: SolutionItem[] = [
      ...solutionItems,
      {
        id: createSolutionItemId(molecule, "reagent"),
        molecule,
        role: "reagent",
        moleculeCount: DEFAULT_REAGENT_COUNT,
      },
    ];

    commitSolutionItems(nextItems, "solution:reagent-added");

    setMessage({
      type: "info",
      text: `${molecule.name} adicionada como reagente. Defina quantidade, ambiente e clique em Misturar.`,
    });
  }


  function updateSolutionMoleculeCount(id: string, value: string) {
    const nextItems = solutionItems.map((item) => {
      if (item.id !== id) return item;

      const sanitized =
        item.role === "solvent"
          ? sanitizeIntegerInput(value)
          : sanitizeDecimalInput(value, item.moleculeCount);

      return { ...item, moleculeCount: sanitized };
    });

    commitSolutionItems(nextItems, "solution:count-updated");
  }

  function incrementMoleculeCount(id: string, delta: number) {
    const nextItems = solutionItems.map((item) => {
      if (item.id !== id) return item;

      const currentValue =
        item.role === "solvent"
          ? getSafeMoleculeCount(item.moleculeCount)
          : getAmountMmol(item.moleculeCount);

      const nextValue = Math.max(
        0,
        Math.min(MAX_MOLECULES_PER_COMPOUND, currentValue + delta)
      );

      return {
        ...item,
        moleculeCount:
          item.role === "solvent"
            ? String(Math.floor(nextValue))
            : String(Number(nextValue.toFixed(4))),
      };
    });

    commitSolutionItems(nextItems, "solution:count-step");
  }

  function removeSolutionItem(id: string) {
    const nextItems = solutionItems.filter((item) => item.id !== id);

    commitSolutionItems(nextItems, "solution:item-removed");

    setMessage({
      type: "info",
      text: "Composto removido da solução. Clique em Misturar para atualizar o 3D.",
    });
  }

  function clearSolution() {
    setLoadedExample(null);
    setSolutionItems([]);
    saveTransferState([], environment, "solution:cleared");
    markSolutionDirty();
    setMessage({
      type: "info",
      text: "Solução limpa. Clique em Misturar apenas se quiser substituir o sistema 3D.",
    });
  }

  function cancel3DExecution() {
    cancelMolecule3DExecution("cancelado-pelo-painel-de-transferencia");
    setMessage({
      type: "warning",
      text: "Execução 3D cancelada. A solução em preparo foi mantida e a cena anterior não será apagada.",
    });
  }

  function clear3DEnvironment() {
    clearMoleculesSentTo3D("limpeza-pelo-painel-de-transferencia");
    setHasUnmixedChanges(true);
    setMessage({
      type: "info",
      text: "Ambiente 3D apagado. A solução em preparo continua aqui para você ajustar e misturar novamente.",
    });
  }

  function buildTransferPayloads(
    mixtureId: string,
    sourceEnvironment: StableEnvironmentSettings
  ): MoleculeTransferFrom2D[] {
    const normalized = normalizeEnvironment(sourceEnvironment);

    return solutionItems
      .map((item) => {
        const molecule = item.molecule;
        const amountMmol = getAmountMmol(item.moleculeCount);
        const renderCount = getVisualRenderCountFromAmount(item.moleculeCount, item.role, environment);
        const realConcentrationMmolL = getRealConcentrationMmolLFromItem(item, sourceEnvironment);

        if (!molecule.smiles.trim() || amountMmol <= 0 || renderCount <= 0) return null;

        return buildMoleculeTransferFrom2D({
          id: molecule.id,
          name: molecule.name,
          formula: molecule.formula,
          smiles: molecule.smiles,
          molarMass: molecule.molarMass,
          status: molecule.status,
          concentration: item.role === "solvent" ? undefined : amountMmol,
          unit: item.role === "solvent" ? "partes" : "mmol",
          transferMetadata: {
            measurementSystem: item.role === "solvent" ? "ratio" : "amount",
            measurementLabel:
              item.role === "solvent"
                ? "Solvente em excesso do meio"
                : "Quantidade real de reagente",
            measurementUnit: item.role === "solvent" ? "partes" : "mmol",
            solventExcess: item.role === "solvent",
            mixtureId,
            mixedAt: new Date().toISOString(),
            renderCount,
            realAmountMmol: item.role === "solvent" ? null : amountMmol,
            realConcentrationMmolL,
            role: item.role,
            roleLabel: item.role === "solvent" ? "Solvente" : "Reagente",
            environment: normalized,
            documentedExampleId: loadedExampleId,
          },
        });
      })
      .filter((payload): payload is MoleculeTransferFrom2D => payload !== null);
  }

  function applyEnvironmentChanges() {
    setActiveEnvironment(environment);
    saveEnvironment(environment);
    saveTransferState(solutionItems, environment, "environment:applied", loadedExampleId);

    if (reagentItems.length > 0 && totalReagentCount > 0) {
      const mixtureId = createMixtureId();
      const payloads = buildTransferPayloads(mixtureId, environment);
      replaceMoleculesIn3D(payloads, mixtureId);
      setHasUnmixedChanges(false);
      setMessage({
        type: "success",
        text:
          "Ambiente aplicado. O motor 3D recalculará a solução sem alterar a topologia química das moléculas.",
      });
      return;
    }

    markSolutionDirty();
    setMessage({
      type: "info",
      text: "Ambiente aplicado. Adicione reagentes e clique em Misturar para montar o 3D.",
    });
  }

  function mixSolutionTo3D() {
    if (reagentItems.length === 0) {
      setMessage({ type: "warning", text: "Selecione pelo menos um reagente. O solvente é opcional." });
      return;
    }

    if (totalReagentAmountMmol <= 0) {
      setMessage({ type: "warning", text: "A quantidade total de reagentes precisa ser maior que zero mmol." });
      return;
    }

    const mixtureId = createMixtureId();
    const mixedAt = new Date().toISOString();
    saveEnvironment(environment);
    saveTransferState(solutionItems, environment, "solution:mixed-to-3d", loadedExampleId);

    const payloads: MoleculeTransferFrom2D[] = solutionItems
      .map((item) => {
        const molecule = item.molecule;
        const amountMmol = getAmountMmol(item.moleculeCount);
        const renderCount = getVisualRenderCountFromAmount(item.moleculeCount, item.role, environment);
        const realConcentrationMmolL = getRealConcentrationMmolLFromItem(item, environment);

        if (!molecule.smiles.trim() || renderCount <= 0) return null;
        if (item.role !== "solvent" && amountMmol <= 0) return null;

        return buildMoleculeTransferFrom2D({
          id: molecule.id,
          name: molecule.name,
          formula: molecule.formula,
          smiles: molecule.smiles,
          molarMass: molecule.molarMass,
          status: molecule.status,
          concentration: item.role === "solvent" ? undefined : amountMmol,
          unit: item.role === "solvent" ? "partes" : "mmol",
          transferMetadata: {
            measurementSystem: item.role === "solvent" ? "ratio" : "amount",
            measurementLabel:
              item.role === "solvent"
                ? "Solvente em excesso do meio"
                : "Quantidade real de reagente",
            measurementUnit: item.role === "solvent" ? "partes" : "mmol",
            solventExcess: item.role === "solvent",
            mixtureId,
            mixedAt,
            renderCount,
            realAmountMmol: item.role === "solvent" ? null : amountMmol,
            realConcentrationMmolL,
            role: item.role,
            roleLabel: item.role === "solvent" ? "Solvente" : "Reagente",
            environment: normalizedEnvironment,
            documentedExampleId: loadedExampleId,
          },
        });
      })
      .filter((item): item is MoleculeTransferFrom2D => Boolean(item));

    if (payloads.length === 0) {
      setMessage({ type: "error", text: "Nenhuma molécula válida foi gerada para o ambiente 3D." });
      return;
    }

    replaceMoleculesIn3D(payloads, mixtureId);
    setHasUnmixedChanges(false);

    window.dispatchEvent(
      new CustomEvent("modelagem3d:mix-solution", {
        detail: {
          mixtureId,
          environment: normalizedEnvironment,
          moleculeCount: totalMoleculeCount,
          reagentCount: totalReagentCount,
          solvent: solventItem?.molecule ?? null,
        },
      })
    );

    setMessage({
      type: "success",
      text: `${formatInteger(totalReagentCount)} reagente(s)${
        solventItem ? ` em solvente em excesso (${inferSolventNameFromMolecule(solventItem.molecule)})` : ""
      } enviados ao 3D com ${environmentModeLabel.toLowerCase()}.`,
    });
  }

  function renderSolutionCard(item: SolutionItem) {
    const molecule = item.molecule;
    const amountMmol = getAmountMmol(item.moleculeCount);
    const renderCount = getVisualRenderCountFromAmount(item.moleculeCount, item.role, environment);
    const realConcentrationMmolL = getRealConcentrationMmolLFromItem(item, environment);
    const fraction = totalMoleculeCount > 0 ? (renderCount / totalMoleculeCount) * 100 : 0;
    const derivedWater = isDerivedWater(item);

    return (
      <article key={item.id} className={`solution-item-card role-${item.role}`}>
        <div className="solution-item-formula">
          <span>{molecule.formula}</span>
        </div>

        <div className="solution-item-info">
          <strong>{molecule.name}</strong>
          <code>{molecule.smiles}</code>
          <small>{molecule.molarMass} g/mol · {item.role === "solvent" ? "solvente" : "reagente"}</small>
        </div>

        <label className="solution-item-count">
          <span>{item.role === "solvent" ? "Solvente em excesso" : "Quantidade do reagente"}</span>

          {item.role === "solvent" ? (
            <div className="solution-solvent-excess-box">
              <strong>Excesso do meio</strong>
              <small>sem mol/mmol · render ≈ {formatInteger(renderCount)} partículas visuais</small>
            </div>
          ) : (
            <div>
              <button type="button" onClick={() => incrementMoleculeCount(item.id, -1)} disabled={derivedWater}>−</button>
              <input
                type="number"
                min={0}
                max={MAX_MOLECULES_PER_COMPOUND}
                step={0.1}
                value={item.moleculeCount}
                onChange={(event) => updateSolutionMoleculeCount(item.id, event.target.value)}
                inputMode="decimal"
                disabled={derivedWater}
              />
              <button type="button" onClick={() => incrementMoleculeCount(item.id, 1)} disabled={derivedWater}>+</button>
            </div>
          )}

          <small>
            {item.role === "solvent"
              ? "A quantidade molar não é editada porque o solvente é tratado como componente majoritário."
              : `${amountMmol.toLocaleString("pt-BR")} mmol · ${realConcentrationMmolL?.toFixed(3) ?? "—"} mmol/L · render ≈ ${formatInteger(renderCount)}${
                  derivedWater ? ` · derivada de w0 = ${loadedExample?.w0?.toLocaleString("pt-BR") ?? "—"} × AOT` : ""
                }`}
          </small>
        </label>

        <div className="solution-item-fraction">
          <span>proporção visual</span>
          <strong>{formatPercent(fraction)}</strong>
        </div>

        <button type="button" className="solution-remove-button" onClick={() => removeSolutionItem(item.id)}>
          Remover
        </button>
      </article>
    );
  }

  return (
    <section className="solution-transfer-shell" aria-label="Soluções 2D para 3D">
      <header className="solution-transfer-header">
        <div>
          <strong>Soluções 2D → 3D</strong>
          <span>
            Solvente opcional, reagentes salvos, quantidade real em mmol e escala visual proporcional e ambiente físico-químico.
          </span>
        </div>

        <div className="solution-header-actions">
          <button className="solution-save-current" type="button" onClick={onSaveCurrentMolecule} disabled={!hasCurrentMolecule}>
            Salvar atual
          </button>

          <button className={hasUnmixedChanges ? "solution-mix-button pending" : "solution-mix-button"} type="button" onClick={mixSolutionTo3D} disabled={reagentItems.length === 0}>
            {hasUnmixedChanges ? "Misturar alterações" : "Misturar"}
          </button>
        </div>
      </header>

      <div className="solution-transfer-layout">
        <aside className="saved-library-panel">
          <div className="solution-panel-title">
            <strong>Moléculas salvas</strong>
            <span>Escolha como solvente ou como reagente</span>
          </div>

          <div className="saved-library-list">
            {savedMolecules.length === 0 && (
              <div className="solution-empty-state compact">
                <strong>Nada salvo</strong>
                <span>Use “Salvar atual”.</span>
              </div>
            )}

            {savedMolecules.map((molecule) => {
              const selected = selectedSavedMoleculeIds.has(molecule.id);

              return (
                <article key={molecule.id} className="saved-library-card">
                  <button type="button" className="saved-library-main" onClick={() => addMoleculeToSolution(molecule, "reagent")} title="Adicionar como reagente">
                    <span className="saved-library-formula">{molecule.formula}</span>
                    <span className="saved-library-info">
                      <strong>{molecule.name}</strong>
                      <small>{molecule.molarMass} g/mol</small>
                    </span>
                  </button>

                  <div className="saved-library-actions three-actions">
                    <button type="button" onClick={() => void onOpenSavedMolecule(molecule.smiles)}>Abrir 2D</button>
                    <button type="button" className={selected ? "selected" : ""} onClick={() => addMoleculeToSolution(molecule, "reagent")}>+ reagente</button>
                    <button type="button" className="solvent-action" onClick={() => addMoleculeToSolution(molecule, "solvent")}>usar solvente</button>
                  </div>
                </article>
              );
            })}
          </div>

          <div className="solution-panel-title">
            <strong>Exemplos documentados</strong>
            <span>Morfologias com condições de referências experimentais. Carregar substitui a solução e o meio.</span>
          </div>

          <div className="saved-library-list">
            {documentedExamplesError && (
              <div className="solution-empty-state compact">
                <strong>Exemplos indisponíveis</strong>
                <span>{documentedExamplesError}</span>
              </div>
            )}
            {!documentedExamplesError && documentedExamples === null && (
              <div className="solution-empty-state compact">
                <strong>Carregando exemplos…</strong>
                <span>Catálogo do servidor.</span>
              </div>
            )}
            {documentedExamples !== null && documentedExamples.length === 0 && (
              <div className="solution-empty-state compact">
                <strong>Nenhum exemplo</strong>
                <span>O servidor não devolveu exemplos documentados.</span>
              </div>
            )}
            {documentedExamples?.map((example) => {
              const reagents = example.components.filter((component) => component.role === "reagent");
              const point = reagents
                .map((component) => `${component.name} ${component.amount_mmol ?? "—"} mmol`)
                .join(" + ");
              return (
                <article key={example.id} className="saved-library-card">
                  <button type="button" className="saved-library-main" onClick={() => loadDocumentedExample(example)} title="Carregar exemplo">
                    <span className="saved-library-formula">{reagents[0]?.formula ?? "—"}</span>
                    <span className="saved-library-info">
                      <strong>{example.title}</strong>
                      <small>{example.kind === "validated_prediction" ? "Previsão validada" : "Demonstração representativa"} · v{example.example_version}</small>
                      <small>{point} · {example.environment.temperature_k} K{example.w0 !== null ? ` · w0 = ${example.w0}` : ""}</small>
                    </span>
                  </button>

                  <div className="saved-library-actions single-action">
                    <button type="button" className={loadedExampleId === example.id ? "selected" : ""} onClick={() => loadDocumentedExample(example)}>
                      Carregar exemplo
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        </aside>

        <section className="solution-lab-panel">
          <div className="solution-count-summary">
            <div>
              <strong>Laboratório de mistura</strong>
              <span>O solvente é opcional. Reagentes são obrigatórios. Nada muda antes de Misturar.</span>
            </div>
            <aside>
              <span>Total</span>
              <strong>{formatInteger(totalMoleculeCount)}</strong>
              <small>{totalReagentAmountMmol.toLocaleString("pt-BR")} mmol · render ≈ {formatInteger(totalReagentCount)} reagente(s){solventItem ? " + solvente" : ""}</small>
              {hasUnmixedChanges && <em>alterações pendentes</em>}
            </aside>
          </div>

          {message && <div className={`solution-message solution-message-${message.type}`}>{message.text}</div>}

          <div className="solution-selected-panel">
            <div className="solution-panel-title">
              <strong>Solução em preparo</strong>
              <span>Defina solvente, reagentes e quantidades. Clique em Misturar para recalcular.</span>
            </div>

            {loadedExample && (
              <section className="mixture-role-section">
                <header>
                  <strong>Exemplo documentado</strong>
                  <span>
                    {(() => {
                      const example = documentedExamples?.find((item) => item.id === loadedExample.id);
                      const kind = example?.kind === "validated_prediction" ? "Previsão validada" : "Demonstração representativa";
                      return `${example?.title ?? loadedExample.id} · ${kind}`;
                    })()}
                  </span>
                </header>
                <small>A forma no 3D vem da referência enquanto a mistura estiver dentro das condições documentadas; fora delas, o cálculo normal com aviso.</small>
                {loadedExample.w0 !== null && (
                  <label className="solution-item-count">
                    <span>w0 = [H₂O]/[AOT]</span>
                    <input type="number" step="0.5" min="0" value={loadedExample.w0} onChange={(event) => updateExampleW0(event.target.value)} inputMode="decimal" />
                    <small>parâmetro principal · água do núcleo = w0 × AOT</small>
                  </label>
                )}
                <div className="solution-footer-actions">
                  <button type="button" onClick={unlinkDocumentedExample}>
                    Desvincular exemplo
                  </button>
                </div>
              </section>
            )}

            <section className="mixture-role-section">
              <header>
                <strong>Solvente opcional</strong>
                <span>{solventItem ? solventItem.molecule.name : "sem solvente definido"}</span>
              </header>
              {solventItem ? renderSolutionCard(solventItem) : (
                <div className="solution-empty-state compact">
                  <strong>Sem solvente</strong>
                  <span>O sistema usará apenas o ambiente físico-químico padrão/ajustado.</span>
                </div>
              )}
            </section>

            <section className="mixture-role-section">
              <header>
                <strong>Reagentes</strong>
                <span>{reagentItems.length} espécie(s)</span>
              </header>

              <div className="solution-selected-list">
                {reagentItems.length === 0 && (
                  <div className="solution-empty-state">
                    <strong>Nenhum reagente selecionado</strong>
                    <span>Use “+ reagente” nas moléculas salvas.</span>
                  </div>
                )}
                {reagentItems.map(renderSolutionCard)}
              </div>
            </section>

            <div className="solution-footer-actions">
              <button type="button" onClick={cancel3DExecution}>
                Cancelar execução 3D
              </button>
              <button type="button" onClick={clear3DEnvironment}>
                Apagar ambiente 3D
              </button>
              <button type="button" onClick={clearSolution} disabled={solutionItems.length === 0}>
                Limpar solução
              </button>
              <button type="button" className={hasUnmixedChanges ? "solution-mix-button pending" : "solution-mix-button"} onClick={mixSolutionTo3D} disabled={reagentItems.length === 0}>
                {hasUnmixedChanges ? "Misturar alterações no 3D" : "Misturar no 3D"}
              </button>
            </div>
          </div>
        </section>

      </div>

      <section className="solution-environment-panel solution-environment-panel-near-3d">
        <div className="solution-panel-title">
          <strong>Ambiente físico-químico aplicado ao 3D</strong>
          <span>Use depois de preparar solvente/reagentes. Estes valores influenciam o empacotamento, a dinâmica e a leitura da solução 3D.</span>
        </div>

        <div className="environment-grid">
          <label>
            <span>Solvente do meio</span>
            <input type="text" value={environment.solventName || inferSolventNameFromMolecule(solventItem?.molecule ?? null)} onChange={(e) => updateEnvironmentField("solventName", e.target.value)} />
            <small>excesso · não usa mol/mmol</small>
          </label>
          <label><span>Temperatura</span><input type="number" step="0.1" value={environment.temperatureK} onChange={(e) => updateEnvironmentField("temperatureK", e.target.value)} /><small>K</small></label>
          <label><span>Pressão</span><input type="number" step="0.01" value={environment.pressureAtm} onChange={(e) => updateEnvironmentField("pressureAtm", e.target.value)} /><small>atm</small></label>
          <label><span>pH</span><input type="number" step="0.1" min="0" max="14" value={environment.ph} onChange={(e) => updateEnvironmentField("ph", e.target.value)} /><small>0–14</small></label>
          <label><span>Força iônica</span><input type="number" step="0.001" min="0" value={environment.ionicStrengthMolL} onChange={(e) => updateEnvironmentField("ionicStrengthMolL", e.target.value)} /><small>mol/L</small></label>
          <label><span>Polaridade</span><input type="number" step="0.01" min="0" max="1" value={environment.solventPolarityIndex} onChange={(e) => updateEnvironmentField("solventPolarityIndex", e.target.value)} /><small>0 apolar · 1 polar</small></label>
          <label><span>Constante dielétrica</span><input type="number" step="0.1" min="1" value={environment.dielectricConstant} onChange={(e) => updateEnvironmentField("dielectricConstant", e.target.value)} /><small>água ≈ 78,5</small></label>
          <label><span>Agitação</span><input type="number" step="10" min="0" value={environment.agitationRpm} onChange={(e) => updateEnvironmentField("agitationRpm", e.target.value)} /><small>rpm</small></label>
          <label><span>Volume</span><input type="number" step="1" min="1" value={environment.volumeMl} onChange={(e) => updateEnvironmentField("volumeMl", e.target.value)} /><small>mL</small></label>
          <label><span>Velocidade 3D</span><input type="number" step="0.1" min="0.1" max="5" value={environment.simulationSpeed} onChange={(e) => updateEnvironmentField("simulationSpeed", e.target.value)} /><small>0,1× lento · 5× rápido</small></label>
        </div>

        <div className="environment-footer">
          <span>{environmentModeLabel}</span>
          <div className="environment-footer-actions">
            <button type="button" onClick={applyEnvironmentChanges}>Aplicar ambiente</button>
            <button type="button" onClick={resetEnvironment}>Restaurar ambiente estável</button>
          </div>
        </div>
      </section>
    </section>
  );
}


