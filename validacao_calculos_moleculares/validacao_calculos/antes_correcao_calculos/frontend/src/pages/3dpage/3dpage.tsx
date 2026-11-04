import { useEffect, useMemo, useRef, useState } from "react";

import SimulationViewer3D from "./components/render/SimulationViewer3D";

import type {
  MiceliumEnvironment3D,
  MiceliumMoleculeInput3D,
  MiceliumSimulationRequest3D,
  MiceliumSimulationResponse3D,
  MoleculeTransferFrom2D,
  Molecules3DStoragePayload,
  SimulationAtom3D,
  SimulationBond3D,
  SimulationBox3D,
  SimulationFrame3D,
  SimulationTopology3D,
  SolutionTransferEventDetail,
} from "./type/3dpage.types";

import {
  MOLECULES_3D_STORAGE_KEY,
  MOLECULES_3D_TRANSFER_EVENT,
} from "./type/3dpage.types";

import "./3dpage.css";

type BuildSimulationResult = {
  topology: SimulationTopology3D;
  frames: SimulationFrame3D[];
  transfers: MoleculeTransferFrom2D[];
  totalRenderedMolecules: number;
  micelium: MiceliumSimulationResponse3D;
};

type BackendElement = {
  id?: string | number;
  atomic_number?: number | string;
  atomicNumber?: number | string;
  number?: number | string;
  symbol?: string;
  name?: string;
  name_pt?: string;
  atomic_mass?: number | string | null;
  atomicMass?: number | string | null;
  mass?: number | string | null;
  category?: string | null;
  element_category?: string | null;
  period?: number | string | null;
  group?: number | string | null;
  group_number?: number | string | null;
  block?: string | null;
  color_hex?: string | null;
  colorHex?: string | null;
  color?: string | null;
};

type ElementColorMap = Record<string, string>;

const API_BASE_URL = String(
  import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api/v1"
).replace(/\/$/, "");

const MICELIUM_SIMULATE_ENDPOINT = `${API_BASE_URL}/micelium/simulate`;

const ELEMENT_COLOR_ENDPOINTS = [
  "/reference-data/elements",
  "/chemical-parameters/elements",
];

const FALLBACK_ELEMENT_COLORS: ElementColorMap = {
  H: "#FFFFFF",
  C: "#9099A5",
  N: "#3050F8",
  O: "#FF0D0D",
  F: "#90E050",
  P: "#FF8000",
  S: "#FFFF30",
  Cl: "#1FF01F",
  Br: "#A62929",
  I: "#940094",
  Na: "#AB5CF2",
  K: "#8F40D4",
  Ca: "#3DFF00",
  Fe: "#E06633",
  Cu: "#C88033",
  Zn: "#7D80B0",
};

function normalizeHexColor(value: unknown): string | null {
  if (typeof value !== "string") return null;

  const trimmed = value.trim();

  if (/^#[0-9a-fA-F]{6}$/.test(trimmed)) {
    return trimmed.toUpperCase();
  }

  if (/^[0-9a-fA-F]{6}$/.test(trimmed)) {
    return `#${trimmed.toUpperCase()}`;
  }

  return null;
}

function normalizeSymbol(value: unknown) {
  const symbol = String(value ?? "").trim();

  if (!symbol) return "";
  if (symbol.length === 1) return symbol.toUpperCase();

  return `${symbol[0].toUpperCase()}${symbol.slice(1).toLowerCase()}`;
}

function extractElementItems(data: unknown): BackendElement[] {
  if (Array.isArray(data)) return data as BackendElement[];

  if (!data || typeof data !== "object") return [];

  const wrapped = data as {
    items?: BackendElement[];
    elements?: BackendElement[];
    data?: BackendElement[];
    results?: BackendElement[];
  };

  return wrapped.items ?? wrapped.elements ?? wrapped.data ?? wrapped.results ?? [];
}

async function loadElementColorMap(): Promise<ElementColorMap> {
  const errors: string[] = [];

  for (const path of ELEMENT_COLOR_ENDPOINTS) {
    try {
      const response = await fetch(`${API_BASE_URL}${path}`);

      if (!response.ok) {
        errors.push(`${path}: HTTP ${response.status}`);
        continue;
      }

      const data = await response.json();
      const items = extractElementItems(data);
      const colors: ElementColorMap = {};

      items.forEach((item) => {
        const symbol = normalizeSymbol(item.symbol);
        const color = item.colorHex ?? item.color_hex ?? item.color;

        const normalizedColor = normalizeHexColor(color);

        if (!symbol || !normalizedColor) return;

        colors[symbol] = normalizedColor;
      });

      if (Object.keys(colors).length > 0) {
        return colors;
      }

      errors.push(`${path}: resposta sem color_hex válido`);
    } catch (error) {
      errors.push(`${path}: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  console.warn(
    "Não foi possível carregar elements.color_hex do backend. Usando fallback visual.",
    errors
  );

  return FALLBACK_ELEMENT_COLORS;
}

function getElementColorFromMap(element: string, elementColorMap: ElementColorMap) {
  const normalized = normalizeSymbol(element);

  return (
    normalizeHexColor(elementColorMap[normalized]) ??
    normalizeHexColor(FALLBACK_ELEMENT_COLORS[normalized]) ??
    "#CBD5E1"
  );
}

function applyElementColorsToTopology(
  topology: SimulationTopology3D,
  elementColorMap: ElementColorMap
): SimulationTopology3D {
  return {
    ...topology,
    atoms: topology.atoms.map((atom) => ({
      ...atom,
      color:
        normalizeHexColor(atom.color) ??
        getElementColorFromMap(atom.element, elementColorMap),
    })),
  };
}

function asNumber(value: unknown, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function normalizeUnitText(value: unknown) {
  return String(value ?? "")
    .trim()
    .replaceAll("µ", "µ")
    .replaceAll("µ", "µ")
    .replace(/^umol\b/i, "µmol")
    .replace(/^u mol\b/i, "µmol");
}

function asOptionalNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function getMolarMass(transfer: MoleculeTransferFrom2D): number | null {
  const parsed = asOptionalNumber(transfer.molarMass);

  return parsed && parsed > 0 ? parsed : null;
}

function inferKnownCmcMmolL(transfer: MoleculeTransferFrom2D): number | null {
  const label = `${transfer.name ?? ""} ${transfer.formula ?? ""} ${transfer.smiles ?? ""}`.toLowerCase();

  if (/\bsds\b|sodium dodecyl sulfate|dodecyl sulfate|lauril sulfato/.test(label)) {
    return 8.2;
  }

  if (/\bctab\b|cetyltrimethylammonium|cetrimonium bromide/.test(label)) {
    return 0.92;
  }

  if (/\bdtab\b/.test(label)) {
    return 15.0;
  }

  if (/\bctac\b|cetrimonium chloride/.test(label)) {
    return 1.3;
  }

  if (/tween\s*80|polysorbate\s*80/.test(label)) {
    return 0.012;
  }

  return null;
}

function resolveRealQuantity(
  transfer: MoleculeTransferFrom2D,
  environment: MiceliumEnvironment3D
): {
  realAmountMmol: number | null;
  realConcentrationMmolL: number | null;
  realAmountUnit: string | null;
} {
  const value = asOptionalNumber(transfer.concentration);
  const unit = normalizeUnitText(transfer.unit);
  const volumeL = Math.max(environment.volume_ml / 1000, 1e-12);
  const molarMass = getMolarMass(transfer);
  const metadataAmountMmol = asOptionalNumber(
    transfer.transferMetadata?.realAmountMmol
  );
  const metadataConcentrationMmolL = asOptionalNumber(
    transfer.transferMetadata?.realConcentrationMmolL
  );

  if (metadataAmountMmol !== null && metadataAmountMmol >= 0) {
    return {
      realAmountMmol: metadataAmountMmol,
      realConcentrationMmolL:
        metadataConcentrationMmolL !== null
          ? metadataConcentrationMmolL
          : metadataAmountMmol / volumeL,
      realAmountUnit: "mmol",
    };
  }

  if (value === null || value < 0) {
    return {
      realAmountMmol: null,
      realConcentrationMmolL: null,
      realAmountUnit: null,
    };
  }

  if (unit === "mol/L") {
    const concentration = value * 1000;

    return {
      realAmountMmol: concentration * volumeL,
      realConcentrationMmolL: concentration,
      realAmountUnit: unit,
    };
  }

  if (unit === "mmol/L") {
    return {
      realAmountMmol: value * volumeL,
      realConcentrationMmolL: value,
      realAmountUnit: unit,
    };
  }

  if (unit === "µmol/L") {
    const concentration = value / 1000;

    return {
      realAmountMmol: concentration * volumeL,
      realConcentrationMmolL: concentration,
      realAmountUnit: unit,
    };
  }

  if (unit === "mol") {
    const amount = value * 1000;

    return {
      realAmountMmol: amount,
      realConcentrationMmolL: amount / volumeL,
      realAmountUnit: unit,
    };
  }

  if (unit === "mmol") {
    return {
      realAmountMmol: value,
      realConcentrationMmolL: value / volumeL,
      realAmountUnit: unit,
    };
  }

  if (unit === "µmol") {
    const amount = value / 1000;

    return {
      realAmountMmol: amount,
      realConcentrationMmolL: amount / volumeL,
      realAmountUnit: unit,
    };
  }

  if (unit === "g/L" && molarMass) {
    const concentration = (value / molarMass) * 1000;

    return {
      realAmountMmol: concentration * volumeL,
      realConcentrationMmolL: concentration,
      realAmountUnit: unit,
    };
  }

  if (unit === "mg/L" && molarMass) {
    const concentration = value / molarMass;

    return {
      realAmountMmol: concentration * volumeL,
      realConcentrationMmolL: concentration,
      realAmountUnit: unit,
    };
  }

  if (unit === "g" && molarMass) {
    const amount = (value / molarMass) * 1000;

    return {
      realAmountMmol: amount,
      realConcentrationMmolL: amount / volumeL,
      realAmountUnit: unit,
    };
  }

  if (unit === "mg" && molarMass) {
    const amount = value / molarMass;

    return {
      realAmountMmol: amount,
      realConcentrationMmolL: amount / volumeL,
      realAmountUnit: unit,
    };
  }

  return {
    realAmountMmol: null,
    realConcentrationMmolL: null,
    realAmountUnit: unit || null,
  };
}


function clampNumber(value: number, min: number, max: number) {
  if (!Number.isFinite(value)) return min;
  return Math.max(min, Math.min(max, value));
}

function getRenderCount(transfer: MoleculeTransferFrom2D) {
  const fromMetadata = Number(transfer.transferMetadata?.renderCount);
  const fromConcentration = Number(transfer.concentration);

  const raw = Number.isFinite(fromMetadata) ? fromMetadata : fromConcentration;

  if (!Number.isFinite(raw)) return 1;

  return Math.max(1, Math.floor(raw));
}

function isSolutionControlEvent(value: unknown): value is SolutionTransferEventDetail {
  return Boolean(
    value &&
      typeof value === "object" &&
      ["replace", "clear", "cancel"].includes(String((value as SolutionTransferEventDetail).mode))
  );
}

function isSolutionReplaceEvent(value: unknown): value is SolutionTransferEventDetail {
  return Boolean(
    isSolutionControlEvent(value) &&
      (value as SolutionTransferEventDetail).mode === "replace" &&
      Array.isArray((value as SolutionTransferEventDetail).molecules)
  );
}

function isSolutionClearEvent(value: unknown): value is SolutionTransferEventDetail {
  return Boolean(
    isSolutionControlEvent(value) &&
      (value as SolutionTransferEventDetail).mode === "clear"
  );
}

function isSolutionCancelEvent(value: unknown): value is SolutionTransferEventDetail {
  return Boolean(
    isSolutionControlEvent(value) &&
      (value as SolutionTransferEventDetail).mode === "cancel"
  );
}

function normalizeTransfers(input: unknown): MoleculeTransferFrom2D[] {
  if (!input) return [];

  if (isSolutionReplaceEvent(input)) {
    return (input.molecules ?? []).filter((item) => item.smiles?.trim());
  }

  if (
    typeof input === "object" &&
    (input as Molecules3DStoragePayload).mode === "replace" &&
    Array.isArray((input as Molecules3DStoragePayload).molecules)
  ) {
    return ((input as Molecules3DStoragePayload).molecules ?? []).filter((item) =>
      item.smiles?.trim()
    );
  }

  if (Array.isArray(input)) {
    return input.filter(
      (item): item is MoleculeTransferFrom2D =>
        Boolean(item && typeof item === "object" && item.smiles?.trim())
    );
  }

  if (typeof input === "object" && (input as MoleculeTransferFrom2D).smiles?.trim()) {
    return [input as MoleculeTransferFrom2D];
  }

  return [];
}

function readStoredTransferPayload(): SolutionTransferEventDetail | null {
  try {
    const raw = window.localStorage.getItem(MOLECULES_3D_STORAGE_KEY);

    if (!raw) return null;

    const parsed = JSON.parse(raw);

    if (
      parsed &&
      typeof parsed === "object" &&
      parsed.mode === "replace" &&
      Array.isArray(parsed.molecules)
    ) {
      return {
        mode: "replace",
        molecules: normalizeTransfers(parsed),
        mixtureId: parsed.mixtureId,
        createdAt: parsed.createdAt,
        revision: parsed.revision,
        reason: "storage-wrapper",
      };
    }

    const molecules = normalizeTransfers(parsed);

    if (molecules.length === 0) return null;

    return {
      mode: "replace",
      molecules,
      mixtureId: `legacy_${Date.now()}`,
      createdAt: new Date().toISOString(),
      revision: Date.now(),
      reason: "legacy-storage-array",
    };
  } catch {
    return null;
  }
}



function looksLikeSolvent(transfer: MoleculeTransferFrom2D) {
  const formula = transfer.formula?.replace(/\s/g, "").toUpperCase();
  const name = transfer.name?.toUpperCase();
  const smiles = transfer.smiles.trim();

  return (
    formula === "H2O" ||
    name === "ÁGUA" ||
    name === "AGUA" ||
    name === "WATER" ||
    smiles === "O"
  );
}

function getMaxConsecutiveCarbonRun(smiles: string): number {
  const matches = smiles.match(/C{4,}/g);

  if (!matches) return 0;

  return matches.reduce<number>((max, item: string) => {
    return Math.max(max, item.length);
  }, 0);
}

function inferSurfactantFromStructure(transfer: MoleculeTransferFrom2D) {
  if (transfer.transferMetadata?.role === "solvent") return false;

  const smiles = transfer.smiles;
  const carbonRun = getMaxConsecutiveCarbonRun(smiles);
  const hasPolarOrChargedHead =
    /\[N\+\]|\[O-\]|\[Na\+\]|\[K\+\]|\[Br-\]|\[Cl-\]|S\(=O\)|P\(=O\)|N\(/.test(
      smiles
    );
  const hasEtherOrAlcoholHead = /OCC|COC|CO$|OH|\(O\)/.test(smiles);

  return carbonRun >= 8 && (hasPolarOrChargedHead || hasEtherOrAlcoholHead);
}

function readEnvironmentFromTransfers(
  transfers: MoleculeTransferFrom2D[]
): MiceliumEnvironment3D {
  const environment = transfers.find((transfer) => transfer.transferMetadata?.environment)
    ?.transferMetadata?.environment as Record<string, unknown> | undefined;

  const simulationSpeed = clampNumber(
    asNumber(
      environment?.simulation_speed ??
        environment?.visual_speed_multiplier ??
        1,
      1
    ),
    0.1,
    5
  );

  const solventName = String(environment?.solvent_name ?? "water");

  return {
    temperature_k: Math.max(1, asNumber(environment?.temperature_k, 298.15)),
    pressure_atm: Math.max(0.001, asNumber(environment?.pressure_atm, 1)),
    ph: clampNumber(asNumber(environment?.ph, 7), 0, 14),
    ionic_strength_mol_l: Math.max(
      0,
      asNumber(environment?.ionic_strength_mol_l, 0.01)
    ),
    solvent_polarity_index: clampNumber(
      asNumber(environment?.solvent_polarity_index, 1),
      0,
      1
    ),
    dielectric_constant: Math.max(
      1,
      asNumber(environment?.dielectric_constant, 78.5)
    ),
    agitation_rpm: Math.max(0, asNumber(environment?.agitation_rpm, 0)),
    volume_ml: Math.max(0.000001, asNumber(environment?.volume_ml, 100)),
    simulation_speed: simulationSpeed,
    visual_speed_multiplier: simulationSpeed,
    solvent_name: solventName,
    solvent_mode: String(environment?.solvent_mode ?? "excess"),
    solvent_description:
      typeof environment?.solvent_description === "string"
        ? environment.solvent_description
        : null,
    stable_preset: true,
  };
}

function buildMiceliumMolecules(
  transfers: MoleculeTransferFrom2D[],
  environment: MiceliumEnvironment3D
): MiceliumMoleculeInput3D[] {
  return transfers
    .map((transfer) => {
      const count = getRenderCount(transfer);
      const role: MiceliumMoleculeInput3D["role"] =
        transfer.transferMetadata?.role === "solvent" || looksLikeSolvent(transfer)
          ? "solvent"
          : "reagent";

      const isSurfactant =
        role !== "solvent" && inferSurfactantFromStructure(transfer);
      const quantity =
        role === "solvent"
          ? {
              realAmountMmol: null,
              realConcentrationMmolL: null,
              realAmountUnit: null,
            }
          : resolveRealQuantity(transfer, environment);

      return {
        id: transfer.transferId ?? transfer.id ?? transfer.smiles,
        name: transfer.name ?? transfer.formula ?? "Molécula",
        smiles: transfer.smiles,
        formula: transfer.formula ?? null,
        role,
        count,
        visual_count: count,
        visual_scale_factor: 1,
        real_amount_mmol: quantity.realAmountMmol,
        real_amount_unit: quantity.realAmountUnit,
        real_concentration_mmol_l: quantity.realConcentrationMmolL,
        solvent_excess:
          role === "solvent"
            ? Boolean(transfer.transferMetadata?.solventExcess ?? true)
            : null,
        cmc_mmol_l: isSurfactant ? inferKnownCmcMmolL(transfer) : null,
        // Uma heurística textual negativa não pode bloquear a classificação
        // química do backend (caudas insaturadas/ramificadas, por exemplo).
        is_surfactant: role === "solvent" ? false : isSurfactant ? true : null,
        tail_carbon_count: null,
      };
    })
    .filter((item) => item.smiles.trim() && item.count > 0);
}

function createTransferSimulationSignature(
  transfers: MoleculeTransferFrom2D[],
  eventContext?: Pick<SolutionTransferEventDetail, "mixtureId" | "revision" | "createdAt">
) {
  const normalized = transfers
    .map((transfer) => {
      const environment = transfer.transferMetadata?.environment ?? {};

      return {
        id: transfer.transferId ?? transfer.id ?? null,
        smiles: transfer.smiles,
        formula: transfer.formula ?? null,
        role: transfer.transferMetadata?.role ?? null,
        renderCount: transfer.transferMetadata?.renderCount ?? null,
        concentration: transfer.concentration ?? null,
        unit: transfer.unit ?? null,
        environment,
      };
    })
    .sort((a, b) => {
      const keyA = `${a.role ?? ""}|${a.smiles}|${a.id ?? ""}`;
      const keyB = `${b.role ?? ""}|${b.smiles}|${b.id ?? ""}`;
      return keyA.localeCompare(keyB);
    });

  return JSON.stringify({
    mixtureId: eventContext?.mixtureId ?? null,
    revision: eventContext?.revision ?? null,
    createdAt: eventContext?.createdAt ?? null,
    molecules: normalized,
  });
}

export function buildMiceliumRequest(
  transfers: MoleculeTransferFrom2D[],
  seed = 13
): MiceliumSimulationRequest3D {
  const environment = readEnvironmentFromTransfers(transfers);
  const rawMolecules = buildMiceliumMolecules(transfers, environment);

  const MAX_VISUAL_MOLECULES = 240;
  const MAX_PARTICLES = 900;

  const requestedMolecules = rawMolecules.reduce(
    (sum, molecule) => sum + molecule.count,
    0
  );

  const scale =
    requestedMolecules > MAX_VISUAL_MOLECULES
      ? MAX_VISUAL_MOLECULES / requestedMolecules
      : 1;

  const molecules = rawMolecules
    .map((molecule) => {
      const visualCount = Math.max(1, Math.floor(molecule.count * scale));

      return {
        ...molecule,
        count: visualCount,
        visual_count: visualCount,
        visual_scale_factor: scale,
      };
    })
    .filter((molecule) => molecule.smiles.trim() && molecule.count > 0);

  const visualMolecules = molecules.reduce(
    (sum, molecule) => sum + molecule.count,
    0
  );

  // v28: chunk físico-químico leve.
  // A continuidade deve vir de chunks menores, não de um cálculo único pesado.
  const steps =
    visualMolecules > 220
      ? 120
      : visualMolecules > 120
        ? 160
        : 220;

  return {
    molecules,
    environment,
    max_particles: MAX_PARTICLES,
    steps,
    dt: 0.016,
    seed,
  };
}

async function simulateMicelium(
  transfers: MoleculeTransferFrom2D[],
  signal?: AbortSignal,
  seed = 13
): Promise<MiceliumSimulationResponse3D> {
  const payload = buildMiceliumRequest(transfers, seed);

  const response = await fetch(MICELIUM_SIMULATE_ENDPOINT, {
    method: "POST",
    signal,
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;

    try {
      const data = await response.json();
      detail = data.detail ?? JSON.stringify(data);
    } catch {
      detail = await response.text();
    }

    throw new Error(detail || "Erro ao executar motor Micelium.");
  }

  return response.json() as Promise<MiceliumSimulationResponse3D>;
}

function particleKindToElement(kind: string) {
  if (kind === "head") return "N";
  if (kind === "tail") return "C";
  if (kind === "solvent") return "O";
  if (kind === "counterion") return "Na";
  if (kind === "solute") return "C";
  return "C";
}

function particleKindToResidue(kind: string, role: string) {
  if (kind === "solvent" || role === "solvent") return "SOL";
  if (kind === "head" || kind === "tail") return "SURF";
  if (kind === "counterion") return "ION";
  return "LIG";
}

function sanitizeCoordinate(value: number[] | undefined): [number, number, number] {
  return [
    asNumber(value?.[0], 0),
    asNumber(value?.[1], 0),
    asNumber(value?.[2], 0),
  ];
}

function computeBoxFromCoordinates(
  coordinates: Array<[number, number, number]>,
  fallbackSide = 18
): SimulationBox3D {
  if (coordinates.length === 0) {
    return {
      x: fallbackSide,
      y: fallbackSide,
      z: fallbackSide,
      center: { x: 0, y: 0, z: 0 },
    };
  }

  const maxExtent = coordinates.reduce((max, coordinate) => {
    return Math.max(
      max,
      Math.abs(coordinate[0]),
      Math.abs(coordinate[1]),
      Math.abs(coordinate[2])
    );
  }, 0);

  const side = Math.max(fallbackSide, maxExtent * 2 + 8);

  return {
    x: side,
    y: side,
    z: side,
    center: {
      x: 0,
      y: 0,
      z: 0,
    },
  };
}

function convertMiceliumToSimulation(
  micelium: MiceliumSimulationResponse3D,
  transfers: MoleculeTransferFrom2D[],
  elementColorMap: ElementColorMap
): BuildSimulationResult {
  const particleIndex = new Map<string, number>();

  const atoms: SimulationAtom3D[] = micelium.particles.map((particle, index) => {
    particleIndex.set(particle.id, index);

    const element = particleKindToElement(particle.kind);
    const residueName = particleKindToResidue(particle.kind, particle.role);

    return {
      index,
      element,
      color:
        normalizeHexColor(particle.color) ??
        getElementColorFromMap(element, elementColorMap),
      moleculeId: particle.molecule_id,
      moleculeName: particle.molecule_name,
      residueName,
      isSolvent: particle.kind === "solvent" || particle.role === "solvent",
      radius: particle.radius,
      charge: particle.charge,
      mass: particle.mass,
      hybridization: null,
      particleKind: particle.kind,
    };
  });

  const bonds: SimulationBond3D[] = micelium.bonds
    .map((bond, index): SimulationBond3D | null => {
      const atomAIndex = particleIndex.get(bond.particle_a);
      const atomBIndex = particleIndex.get(bond.particle_b);

      if (atomAIndex === undefined || atomBIndex === undefined) return null;

      return {
        index,
        atomAIndex,
        atomBIndex,
        order: 1,
        moleculeId: micelium.particles[atomAIndex]?.molecule_id ?? "micelium",
        drawAcrossPbc: false,
      };
    })
    .filter((bond): bond is SimulationBond3D => bond !== null);

  const initialCoordinates =
    micelium.frames[0]?.coordinates.map(sanitizeCoordinate) ??
    micelium.particles.map((particle) => sanitizeCoordinate(particle.position));

  const box = computeBoxFromCoordinates(
    initialCoordinates,
    Math.max(18, Math.cbrt(Math.max(atoms.length, 1)) * 4.5)
  );

  const frames: SimulationFrame3D[] =
    micelium.frames.length > 0
      ? micelium.frames.map((frame) => ({
          frameIndex: frame.frame_index,
          timePs: frame.time_ps,
          coordinates: frame.coordinates.map(sanitizeCoordinate),
          box,
        }))
      : [
          {
            frameIndex: 0,
            timePs: 0,
            coordinates: initialCoordinates,
            box,
          },
        ];

  const totalRenderedMolecules =
    micelium.analysis?.molecule_count ??
    transfers.reduce((sum, transfer) => sum + getRenderCount(transfer), 0);

  const micelleProbability = micelium.analysis?.micelle_probability ?? 0;
  const dominantMorphology =
    micelium.analysis?.dominant_morphology ??
    micelium.clusters[0]?.morphology ??
    null;
  const hasMicelle = micelleProbability >= 0.35 || micelium.clusters.length > 0;

  const topology: SimulationTopology3D = {
    id: transfers[0]?.transferMetadata?.mixtureId ?? `micelium_${Date.now()}`,
    title: hasMicelle
      ? `${totalRenderedMolecules} molécula(s) · Micelium · ${dominantMorphology ?? "micela/agregado provável"}`
      : `${totalRenderedMolecules} molécula(s) · Micelium Engine`,
    box,
    atoms,
    bonds,
    moleculeCount: totalRenderedMolecules,
    createdAt: new Date().toISOString(),
    source: "micelium",
    clusters: micelium.clusters,
    analysis: micelium.analysis,
  };

  return {
    topology,
    frames,
    transfers,
    totalRenderedMolecules,
    micelium,
  };
}







type WebGLAvailability = "checking" | "available" | "unavailable";

function canCreateWebGLContext() {
  if (typeof document === "undefined") return false;

  try {
    const canvas = document.createElement("canvas");
    const attributes: WebGLContextAttributes = {
      antialias: true,
      alpha: false,
      failIfMajorPerformanceCaveat: false,
    };

    const webgl2Context = canvas.getContext(
      "webgl2",
      attributes
    ) as WebGL2RenderingContext | null;

    const webglContext = canvas.getContext(
      "webgl",
      attributes
    ) as WebGLRenderingContext | null;

    const experimentalContext = canvas.getContext(
      "experimental-webgl",
      attributes
    ) as WebGLRenderingContext | null;

    const available = Boolean(webgl2Context ?? webglContext ?? experimentalContext);

    canvas.width = 1;
    canvas.height = 1;

    return available;
  } catch {
    return false;
  }
}

function WebGLUnavailablePanel() {
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        minHeight: 420,
        display: "grid",
        placeItems: "center",
        padding: 24,
        borderRadius: 22,
        background:
          "radial-gradient(circle at center, rgba(239, 68, 68, 0.12), transparent 42%), #020617",
        color: "#e5e7eb",
      }}
    >
      <div
        style={{
          maxWidth: 560,
          display: "grid",
          gap: 12,
          border: "1px solid rgba(248, 113, 113, 0.28)",
          borderRadius: 18,
          padding: 20,
          background: "rgba(15, 23, 42, 0.92)",
          textAlign: "center",
        }}
      >
        <strong
          style={{
            color: "#fecaca",
            fontSize: "1rem",
            fontWeight: 950,
          }}
        >
          WebGL indisponível neste navegador
        </strong>

        <span
          style={{
            color: "#cbd5e1",
            fontSize: "0.82rem",
            lineHeight: 1.5,
          }}
        >
          O backend está funcionando, mas o navegador não conseguiu criar o contexto
          WebGL usado pelo Three.js. Ative a aceleração de hardware, atualize o
          driver de vídeo ou teste em outro navegador.
        </span>

        <small
          style={{
            color: "#94a3b8",
            fontSize: "0.72rem",
            lineHeight: 1.45,
          }}
        >
          Verifique em chrome://gpu se WebGL e WebGL2 aparecem como Hardware
          accelerated. Depois reinicie o navegador e faça Ctrl + F5.
        </small>
      </div>
    </div>
  );
}

function WebGLCheckingPanel() {
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        minHeight: 420,
        display: "grid",
        placeItems: "center",
        padding: 24,
        borderRadius: 22,
        background: "#020617",
        color: "#94a3b8",
        fontSize: "0.82rem",
      }}
    >
      Verificando suporte WebGL...
    </div>
  );
}

export function Page3D() {
  const [topology, setTopology] = useState<SimulationTopology3D | null>(null);
  const [frame, setFrame] = useState<SimulationFrame3D | null>(null);
  const [miceliumFrames, setMiceliumFrames] = useState<SimulationFrame3D[]>([]);
  const [currentTransfers, setCurrentTransfers] = useState<MoleculeTransferFrom2D[]>([]);
  const [selectedMoleculeId, setSelectedMoleculeId] = useState<string | null>(null);
  const [showSolvent, setShowSolvent] = useState(true);
  const [message, setMessage] = useState("");
  const [isLoadingSolution, setIsLoadingSolution] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isPlaybackPausedByUser, setIsPlaybackPausedByUser] = useState(false);
  const [totalRenderedMolecules, setTotalRenderedMolecules] = useState(0);
  const [playbackIntervalMs, setPlaybackIntervalMs] = useState(90);
  const [webglAvailability, setWebglAvailability] =
    useState<WebGLAvailability>("checking");

  const lastBuildIdRef = useRef(0);
  const lastSimulationSignatureRef = useRef("");
  const elementColorMapRef = useRef<ElementColorMap>({});
  const activeRequestControllerRef = useRef<AbortController | null>(null);
  const requestTimeoutRef = useRef<number | null>(null);
  const activeSimulationSignatureRef = useRef("");
  const playbackFrameIndexRef = useRef(0);
  const playbackContinuationStepRef = useRef(0);
  const userPausedPlaybackRef = useRef(false);
  const playbackTimerRef = useRef<number | null>(null);
  const playbackRunningRef = useRef(false);
  const latestFrameRef = useRef<SimulationFrame3D | null>(null);
  const latestPlaybackDataRef = useRef<{
    frames: SimulationFrame3D[];
    topology: SimulationTopology3D | null;
    intervalMs: number;
  }>({
    frames: [],
    topology: null,
    intervalMs: 90,
  });
  const currentTransfersRef = useRef<MoleculeTransferFrom2D[]>([]);
  const autoContinueChunkRef = useRef(false);

  const selectedLabel = useMemo(() => {
    if (!selectedMoleculeId) return "—";

    const match = topology?.atoms.find((atom) => atom.moleculeId === selectedMoleculeId);

    return match?.moleculeName ?? selectedMoleculeId;
  }, [selectedMoleculeId, topology]);

  const miceliumAnalysis = topology?.analysis ?? null;
  const clusterCount = topology?.clusters?.length ?? 0;
  const currentEnvironment = currentTransfers[0]?.transferMetadata?.environment as
    | Record<string, unknown>
    | undefined;

  useEffect(() => {
    const available = canCreateWebGLContext();

    setWebglAvailability(available ? "available" : "unavailable");

    if (!available) {
      setMessage(
        "WebGL indisponível no navegador. Ative a aceleração de hardware ou teste outro navegador."
      );
    }
  }, []);

  function stopPlaybackTimer() {
    playbackRunningRef.current = false;

    if (playbackTimerRef.current !== null) {
      window.clearTimeout(playbackTimerRef.current);
      playbackTimerRef.current = null;
    }
  }

  function scheduleNextPlaybackTick() {
    if (!playbackRunningRef.current) return;

    if (playbackTimerRef.current !== null) {
      window.clearTimeout(playbackTimerRef.current);
    }

    playbackTimerRef.current = window.setTimeout(
      playbackTick,
      latestPlaybackDataRef.current.intervalMs
    );
  }

  function playbackTick() {
    if (!playbackRunningRef.current) return;

    const {
      frames,
    } = latestPlaybackDataRef.current;

    let nextFrame: SimulationFrame3D | null = null;

    if (frames.length > 0) {
      const nextIndex = playbackFrameIndexRef.current + 1;

      if (nextIndex < frames.length) {
        playbackFrameIndexRef.current = nextIndex;
        playbackContinuationStepRef.current = 0;
        nextFrame = frames[nextIndex];
      } else {
        // Fim do chunk calculado pelo backend.
        // v29: não inventa microdinâmica no frontend; solicita novo chunk calculado.
        stopPlaybackTimer();
        setIsPlaying(false);

        if (
          !userPausedPlaybackRef.current &&
          currentTransfersRef.current.length > 0 &&
          !autoContinueChunkRef.current
        ) {
          autoContinueChunkRef.current = true;
          setMessage("Chunk físico-químico finalizado. Continuando do último estado calculado...");
          void replaceSolution(currentTransfersRef.current, {
            mixtureId: `auto_chunk_${Date.now()}`,
            revision: Date.now(),
            createdAt: new Date().toISOString(),
            reason: "auto-continuation",
          } as Pick<SolutionTransferEventDetail, "mixtureId" | "revision" | "createdAt" | "reason">);
          return;
        }

        setIsPlaybackPausedByUser(false);
        setMessage("Cálculo físico-químico finalizado. Cena mantida no último frame calculado.");
        return;
      }
    }

    if (nextFrame) {
      latestFrameRef.current = nextFrame;
      setFrame(nextFrame);
    }

    // Continua apenas enquanto ainda houver frames calculados a reproduzir.
    scheduleNextPlaybackTick();
  }

  function startPlaybackTimer() {
    if (playbackRunningRef.current) {
      setIsPlaying(true);
      return;
    }

    if (
      latestPlaybackDataRef.current.frames.length === 0 &&
      latestFrameRef.current === null
    ) {
      setIsPlaying(false);
      return;
    }

    playbackRunningRef.current = true;
    setIsPlaying(true);
    scheduleNextPlaybackTick();
  }

  function pausePlaybackTimer() {
    stopPlaybackTimer();
    setIsPlaying(false);
  }

  useEffect(() => {
    latestPlaybackDataRef.current = {
      frames: miceliumFrames,
      topology,
      intervalMs: playbackIntervalMs,
    };
  }, [miceliumFrames, topology, playbackIntervalMs]);

  useEffect(() => {
    latestFrameRef.current = frame;
  }, [frame]);

  useEffect(() => {
    currentTransfersRef.current = currentTransfers;
  }, [currentTransfers]);

  useEffect(() => {
    if (miceliumFrames.length === 0) {
      playbackFrameIndexRef.current = 0;
      playbackContinuationStepRef.current = 0;
      latestFrameRef.current = frame;
      pausePlaybackTimer();
      return;
    }

    playbackFrameIndexRef.current = 0;
    playbackContinuationStepRef.current = 0;
    latestFrameRef.current = miceliumFrames[0];
    setFrame(miceliumFrames[0]);

    if (!userPausedPlaybackRef.current) {
      setIsPlaybackPausedByUser(false);
      window.setTimeout(() => {
        latestPlaybackDataRef.current = {
          frames: miceliumFrames,
          topology,
          intervalMs: playbackIntervalMs,
        };
        startPlaybackTimer();
      }, 0);
    } else {
      pausePlaybackTimer();
    }
  }, [miceliumFrames]);

  useEffect(() => {
    latestPlaybackDataRef.current.intervalMs = playbackIntervalMs;

    if (playbackRunningRef.current) {
      scheduleNextPlaybackTick();
    }
  }, [playbackIntervalMs]);



  function toggle3DPlayback() {
    const frames = latestPlaybackDataRef.current.frames;

    if (frames.length === 0 && latestFrameRef.current === null && !frame) {
      setMessage("Nenhuma simulação 3D carregada para pausar ou retomar.");
      return;
    }

    if (playbackRunningRef.current) {
      userPausedPlaybackRef.current = true;
      autoContinueChunkRef.current = false;
      setIsPlaybackPausedByUser(true);
      pausePlaybackTimer();
      setMessage("Reprodução 3D pausada.");
      return;
    }

    userPausedPlaybackRef.current = false;
    autoContinueChunkRef.current = false;
    setIsPlaybackPausedByUser(false);

    if (frames.length === 0 && frame) {
      latestFrameRef.current = frame;
      latestPlaybackDataRef.current = {
        frames: [frame],
        topology,
        intervalMs: playbackIntervalMs,
      };
      playbackFrameIndexRef.current = 0;
      playbackContinuationStepRef.current = 0;
    }

    startPlaybackTimer();
    setMessage("Reprodução 3D retomada.");
  }


  function clearRequestTimeout() {
    if (requestTimeoutRef.current !== null) {
      window.clearTimeout(requestTimeoutRef.current);
      requestTimeoutRef.current = null;
    }
  }

  function abortActiveRequest() {
    clearRequestTimeout();

    if (activeRequestControllerRef.current) {
      activeRequestControllerRef.current.abort();
      activeRequestControllerRef.current = null;
    }

    activeSimulationSignatureRef.current = "";
  }

  function cancelActiveSimulation(messageText: string) {
    abortActiveRequest();
    lastBuildIdRef.current += 1;

    setIsLoadingSolution(false);
    pausePlaybackTimer();
    setMessage(messageText);
  }

  function clear3DEnvironment(messageText: string) {
    abortActiveRequest();
    lastBuildIdRef.current += 1;
    lastSimulationSignatureRef.current = "";

    window.localStorage.removeItem(MOLECULES_3D_STORAGE_KEY);

    setIsLoadingSolution(false);
    userPausedPlaybackRef.current = false;
    setIsPlaybackPausedByUser(false);
    pausePlaybackTimer();
    latestFrameRef.current = null;
    setTopology(null);
    setFrame(null);
    setMiceliumFrames([]);
    setCurrentTransfers([]);
    setTotalRenderedMolecules(0);
    setSelectedMoleculeId(null);
    setMessage(messageText);
  }

  async function replaceSolution(
    transfers: MoleculeTransferFrom2D[],
    eventContext?: Pick<SolutionTransferEventDetail, "mixtureId" | "revision" | "createdAt" | "reason">
  ) {
    const validTransfers = transfers.filter((transfer) => transfer.smiles?.trim());

    if (validTransfers.length === 0) {
      setMessage("Nenhuma molécula válida foi enviada ao ambiente 3D.");
      return;
    }

    const signature = createTransferSimulationSignature(validTransfers, eventContext);

    userPausedPlaybackRef.current = false;
    setIsPlaybackPausedByUser(false);

    if (signature === activeSimulationSignatureRef.current && activeRequestControllerRef.current) {
      setMessage("Essa mistura já está sendo processada pelo Micelium Engine.");
      return;
    }

    if (signature === lastSimulationSignatureRef.current && topology) {
      setMessage("Essa mistura já está renderizada no ambiente 3D.");
      return;
    }

    if (
      activeRequestControllerRef.current &&
      activeSimulationSignatureRef.current &&
      activeSimulationSignatureRef.current !== signature
    ) {
      abortActiveRequest();
    }

    const buildId = lastBuildIdRef.current + 1;
    lastBuildIdRef.current = buildId;

    const controller = new AbortController();
    activeRequestControllerRef.current = controller;
    activeSimulationSignatureRef.current = signature;

    requestTimeoutRef.current = window.setTimeout(() => {
      if (lastBuildIdRef.current === buildId) {
        controller.abort();
        setIsLoadingSolution(false);
        setMessage(
          "Tempo limite do 3D atingido antes da resposta do backend. A cena anterior foi preservada. Tente reduzir a quantidade visual ou usar chunk menor."
        );
      }
    }, 600000);

    setIsLoadingSolution(true);
    setMessage("Enviando mistura ao Micelium Engine...");

    try {
      const elementColorMap = await loadElementColorMap();
      elementColorMapRef.current = elementColorMap;

      if (lastBuildIdRef.current !== buildId) return;

      setMessage("Chamando /micelium/simulate para formar a micela...");
      console.info("[Micelium3D] Chamando /micelium/simulate", {
        transferCount: validTransfers.length,
        mixtureId: eventContext?.mixtureId,
        revision: eventContext?.revision,
        molecules: validTransfers.map((item) => ({
          name: item.name,
          smiles: item.smiles,
          role: item.transferMetadata?.role,
        })),
      });

      const micelium = await simulateMicelium(validTransfers, controller.signal, 13);

      if (!micelium || typeof micelium !== "object") {
        throw new Error("Resposta vazia ou inválida do Micelium Engine.");
      }

      if (!Array.isArray(micelium.particles)) {
        throw new Error("Resposta do Micelium sem lista de partículas.");
      }

      if (!Array.isArray(micelium.frames)) {
        throw new Error("Resposta do Micelium sem frames.");
      }

      if (!Array.isArray(micelium.bonds)) {
        micelium.bonds = [];
      }

      if (!Array.isArray(micelium.clusters)) {
        micelium.clusters = [];
      }

      if (!micelium.analysis || typeof micelium.analysis !== "object") {
        micelium.analysis = {
          total_particles: micelium.particles.length,
          molecule_count: validTransfers.length,
          surfactant_count: 0,
          solvent_count: 0,
          solute_count: 0,
          micelle_probability: 0,
          average_cluster_size: 0,
          cluster_count: 0,
          largest_cluster_size: 0,
          stability_score: 0,
          warnings: ["Análise ausente na resposta; fallback seguro aplicado."],
        };
      }

      if (!Array.isArray(micelium.analysis.warnings)) {
        micelium.analysis.warnings = [];
      }

      if (lastBuildIdRef.current !== buildId) return;

      clearRequestTimeout();
      activeRequestControllerRef.current = null;
      activeSimulationSignatureRef.current = "";
      lastSimulationSignatureRef.current = signature;

      const result = convertMiceliumToSimulation(
        micelium,
        validTransfers,
        elementColorMap
      );

      const simulationSpeed = readEnvironmentFromTransfers(validTransfers).simulation_speed ?? 1;
      const intervalMs = Math.max(55, Math.min(900, 260 / simulationSpeed));

      setPlaybackIntervalMs(intervalMs);
      setTopology(applyElementColorsToTopology(result.topology, elementColorMap));
      setFrame(result.frames[0] ?? null);
      setMiceliumFrames(result.frames);
      setCurrentTransfers(result.transfers);
      setTotalRenderedMolecules(result.totalRenderedMolecules);
      setSelectedMoleculeId(null);

      const miceliumWarnings = Array.isArray(result.micelium.analysis?.warnings)
        ? result.micelium.analysis.warnings
        : [];

      const warningText =
        miceliumWarnings.length > 0
          ? ` Aviso: ${miceliumWarnings[0]}`
          : "";

      autoContinueChunkRef.current = false;

      setMessage(
        `${result.totalRenderedMolecules} molécula(s) processadas pelo Micelium. ` +
          `${result.topology.atoms.length} partícula(s), ${result.frames.length} frame(s).${warningText}`
      );
    } catch (error) {
      if (lastBuildIdRef.current !== buildId) return;

      activeSimulationSignatureRef.current = "";
      autoContinueChunkRef.current = false;

      const isAbort =
        error instanceof DOMException
          ? error.name === "AbortError"
          : error instanceof Error && error.name === "AbortError";

      if (!isAbort && !topology) {
        setMiceliumFrames([]);
        setFrame(null);
      }

      console.error("[Modelagem3D] Falha controlada no ambiente 3D:", error);

      setMessage(
        isAbort
          ? "Execução 3D cancelada. A cena anterior foi preservada."
          : error instanceof Error
            ? `Falha ao executar Micelium Engine: ${error.message}`
            : "Falha ao executar Micelium Engine."
      );
    } finally {
      if (lastBuildIdRef.current === buildId) {
        clearRequestTimeout();
        activeRequestControllerRef.current = null;
        activeSimulationSignatureRef.current = "";
        setIsLoadingSolution(false);
      }
    }
  }

  useEffect(() => {
    const storedPayload = readStoredTransferPayload();

    if (storedPayload?.molecules && storedPayload.molecules.length > 0) {
      void replaceSolution(storedPayload.molecules, storedPayload);
    }

    const handleTransfer = (event: Event) => {
      const detail = (event as CustomEvent).detail;

      if (isSolutionCancelEvent(detail)) {
        cancelActiveSimulation("Execução 3D cancelada pelo painel de transferência. A cena anterior foi preservada.");
        return;
      }

      if (isSolutionClearEvent(detail)) {
        clear3DEnvironment("Ambiente 3D apagado pelo painel de transferência.");
        return;
      }

      if (isSolutionReplaceEvent(detail)) {
        void replaceSolution(detail.molecules ?? [], detail);
        return;
      }

      const transfers = normalizeTransfers(detail);

      if (transfers.length > 0) {
        void replaceSolution(transfers, {
          mixtureId: `event_${Date.now()}`,
          revision: Date.now(),
          createdAt: new Date().toISOString(),
          reason: "raw-transfer-event",
        });
      }
    };

    const handleStorage = (event: StorageEvent) => {
      if (event.key !== MOLECULES_3D_STORAGE_KEY) return;

      const stored = readStoredTransferPayload();

      if (stored?.molecules && stored.molecules.length > 0) {
        void replaceSolution(stored.molecules, stored);
        return;
      }

      setMessage("LocalStorage do 3D está vazio. Cena atual preservada.");
    };

    window.addEventListener(MOLECULES_3D_TRANSFER_EVENT, handleTransfer);
    window.addEventListener("storage", handleStorage);

    return () => {
      stopPlaybackTimer();
      window.removeEventListener(MOLECULES_3D_TRANSFER_EVENT, handleTransfer);
      window.removeEventListener("storage", handleStorage);
      abortActiveRequest();
    };
  }, []);

  return (
    <main className="page-3d-container">
      <section className="page-3d-header">
        <div>
          <strong>Ambiente 3D molecular</strong>
          <span>
            A mistura agora é calculada no backend pelo Micelium Engine e o
            Three.js apenas renderiza partículas, frames, clusters e interações.
          </span>
        </div>

        <div className="page-3d-header-actions">
          <button
            type="button"
            className="page-3d-solvent-toggle"
            onClick={() => setShowSolvent((current) => !current)}
          >
            {showSolvent ? "Ocultar solvente" : "Mostrar solvente"}
          </button>

          <button
            type="button"
            className="page-3d-solvent-toggle"
            onClick={toggle3DPlayback}
            disabled={miceliumFrames.length === 0 && !frame}
          >
            {isPlaying ? "Pausar 3D" : isPlaybackPausedByUser ? "Retomar 3D" : "Reproduzir 3D"}
          </button>

          <button
            type="button"
            className="page-3d-solvent-toggle"
            onClick={() => cancelActiveSimulation("Execução 3D cancelada manualmente. A cena anterior foi preservada.")}
            disabled={!isLoadingSolution}
          >
            Cancelar execução
          </button>

          <button
            type="button"
            className="page-3d-solvent-toggle"
            onClick={() => clear3DEnvironment("Ambiente 3D limpo manualmente.")}
            disabled={!topology && !isLoadingSolution}
          >
            Limpar 3D
          </button>
        </div>
      </section>

      <section className="page-3d-main-field">
        {message && <div className="page-3d-message-bar">{message}</div>}

        <div className="page-3d-render-field">
          {webglAvailability === "checking" && <WebGLCheckingPanel />}

          {webglAvailability === "unavailable" && <WebGLUnavailablePanel />}

          {webglAvailability === "available" && (
            <SimulationViewer3D
              topology={topology}
              frame={frame}
              showSolvent={showSolvent}
              selectedMoleculeId={selectedMoleculeId}
              onSelectMolecule={setSelectedMoleculeId}
              onStatus={setMessage}
            />
          )}

          {isLoadingSolution && (
            <div className="page-3d-loading-overlay">
              <strong>Executando Micelium Engine...</strong>
              <span>Gerando frames da formação micelar. Você pode cancelar se ficar pesado.</span>
              <button
                type="button"
                onClick={() => cancelActiveSimulation("Execução 3D cancelada manualmente. A cena anterior foi preservada.")}
              >
                Cancelar execução
              </button>
            </div>
          )}
        </div>

        <div className="page-3d-bottom-inspector">
          <section className="bottom-inspector-card selected-card">
            <strong>Solução carregada</strong>

            {currentTransfers.length === 0 && (
              <span className="empty-inspector">
                Nenhuma solução misturada. Use o botão Misturar no painel 2D.
              </span>
            )}

            {currentTransfers.length > 0 && (
              <div className="inline-inspector-grid">
                <span>Compostos</span>
                <strong>{currentTransfers.length}</strong>

                <span>Moléculas representadas</span>
                <strong>{totalRenderedMolecules}</strong>

                <span>Partículas</span>
                <strong>{topology?.atoms.length ?? 0}</strong>

                <span>Ligações CG</span>
                <strong>{topology?.bonds.length ?? 0}</strong>

                <span>Frames Micelium</span>
                <strong>{miceliumFrames.length}</strong>

                <span>Clusters</span>
                <strong>{clusterCount}</strong>

                <span>Probabilidade micelar</span>
                <strong>
                  {miceliumAnalysis
                    ? `${(miceliumAnalysis.micelle_probability * 100).toFixed(1)}%`
                    : "—"}
                </strong>

                <span>Morfologia dominante</span>
                <strong>{miceliumAnalysis?.dominant_morphology ?? topology?.clusters?.[0]?.morphology ?? "—"}</strong>

                <span>Tendência prevista</span>
                <strong>{miceliumAnalysis?.predicted_morphology ?? "—"}</strong>

                <span>Fase visual</span>
                <strong>{miceliumAnalysis?.formation_phase ?? "—"}</strong>

                <span>Fração organizada na amostra 3D</span>
                <strong>
                  {miceliumAnalysis?.micellized_fraction !== undefined && miceliumAnalysis?.micellized_fraction !== null
                    ? `${(miceliumAnalysis.micellized_fraction * 100).toFixed(1)}%`
                    : "—"}
                </strong>

                <span>C/CMC</span>
                <strong>
                  {miceliumAnalysis?.c_over_cmc_proxy !== undefined && miceliumAnalysis?.c_over_cmc_proxy !== null
                    ? miceliumAnalysis.c_over_cmc_proxy.toFixed(2)
                    : "—"}
                </strong>

                <span>Quantidade real</span>
                <strong>
                  {miceliumAnalysis?.real_amount_mmol !== undefined && miceliumAnalysis?.real_amount_mmol !== null
                    ? `${miceliumAnalysis.real_amount_mmol.toFixed(4)} mmol`
                    : "—"}
                </strong>

                <span>Solvente/meio</span>
                <strong>{String(currentEnvironment?.solvent_name ?? "—")}</strong>

                <span>pH</span>
                <strong>{currentEnvironment?.ph !== undefined ? String(currentEnvironment.ph) : "—"}</strong>

                <span>Constante dielétrica</span>
                <strong>{currentEnvironment?.dielectric_constant !== undefined ? String(currentEnvironment.dielectric_constant) : "—"}</strong>

                <span>Volume</span>
                <strong>{currentEnvironment?.volume_ml !== undefined ? `${String(currentEnvironment.volume_ml)} mL` : "—"}</strong>

                <span>Velocidade visual</span>
                <strong>{currentEnvironment?.visual_speed_multiplier !== undefined ? `${String(currentEnvironment.visual_speed_multiplier)}×` : "—"}</strong>

                <span>Caixa</span>
                <strong>
                  {topology
                    ? `${topology.box.x.toFixed(1)} × ${topology.box.y.toFixed(
                        1
                      )} × ${topology.box.z.toFixed(1)} nm`
                    : "—"}
                </strong>

                <span>Selecionada</span>
                <strong>{selectedLabel}</strong>

                <span>Playback</span>
                <strong>{isPlaying ? "ativo" : "parado"}</strong>
              </div>
            )}
          </section>

          <section className="bottom-inspector-card scope-card">
            <strong>Regra aplicada</strong>
            <span>
              O painel 2D define quantidade real em mmol para reagentes. Solvente entra como excesso do meio,
              sem mol/mmol. pH, dielétrica, polaridade, volume e velocidade alteram o motor dinâmico sem mudar
              a topologia química das moléculas.
            </span>
          </section>
        </div>
      </section>
    </main>
  );
}

export default Page3D;
