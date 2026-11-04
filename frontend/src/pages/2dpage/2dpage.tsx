import { useEffect, useMemo, useState } from "react";

import Minimap from "./components/interaction/minimap/minimap";
import Molecule2DViewer from "./components/interaction/Molecule2DViewer";
import ToolsBar from "./components/interaction/toolsbar/toolsbar";

import {
  PeriodicTable,
  type PeriodicElement,
} from "./components/periodictable/periodictable";

import {
  graphToSmiles,
  optimizeMolecule2D,
  parseSmilesTo2D,
  rdkitMoleculeToEditableGraph,
  toggleExplicitHydrogens2D,
} from "./components/interaction/rdkit/rdkitApi";

import Transfer2DTo3D from "../2dto3d/transfer";

import type {
  BondOrder,
  BondRole,
  BondVisualStyle,
  CanvasViewport,
  EditableMoleculeGraph,
  EditorToolState,
  ImportFormat,
  InternalAtomModel,
  InternalBondModel,
  InternalMoleculeModel,
  Position2D,
  RDKitMolecule2D,
  SavedMolecule,
  SelectedMoleculeTarget,
} from "./type/rdkit2d.types";

import "./2dpage.css";

const LEFTPAGE_STATE_EVENT = "molecular-editor:leftpage-state";
const LEFTPAGE_COMMAND_EVENT = "molecular-editor:leftpage-command";
const LEFTPAGE_STORAGE_KEY = "molecular-editor:leftpage-state";

const initialQuickElements = ["P", "N", "O", "K"];

const allElementSymbols = new Set<string>([
  "H",
  "He",
  "Li",
  "Be",
  "B",
  "C",
  "N",
  "O",
  "F",
  "Ne",
  "Na",
  "Mg",
  "Al",
  "Si",
  "P",
  "S",
  "Cl",
  "Ar",
  "K",
  "Ca",
  "Sc",
  "Ti",
  "V",
  "Cr",
  "Mn",
  "Fe",
  "Co",
  "Ni",
  "Cu",
  "Zn",
  "Ga",
  "Ge",
  "As",
  "Se",
  "Br",
  "Kr",
  "Rb",
  "Sr",
  "Y",
  "Zr",
  "Nb",
  "Mo",
  "Tc",
  "Ru",
  "Rh",
  "Pd",
  "Ag",
  "Cd",
  "In",
  "Sn",
  "Sb",
  "Te",
  "I",
  "Xe",
  "Cs",
  "Ba",
  "La",
  "Ce",
  "Pr",
  "Nd",
  "Pm",
  "Sm",
  "Eu",
  "Gd",
  "Tb",
  "Dy",
  "Ho",
  "Er",
  "Tm",
  "Yb",
  "Lu",
  "Hf",
  "Ta",
  "W",
  "Re",
  "Os",
  "Ir",
  "Pt",
  "Au",
  "Hg",
  "Tl",
  "Pb",
  "Bi",
  "Po",
  "At",
  "Rn",
  "Fr",
  "Ra",
  "Ac",
  "Th",
  "Pa",
  "U",
  "Np",
  "Pu",
  "Am",
  "Cm",
  "Bk",
  "Cf",
  "Es",
  "Fm",
  "Md",
  "No",
  "Lr",
  "Rf",
  "Db",
  "Sg",
  "Bh",
  "Hs",
  "Mt",
  "Ds",
  "Rg",
  "Cn",
  "Nh",
  "Fl",
  "Mc",
  "Lv",
  "Ts",
  "Og",
]);

const atomicNumberBySymbol: Record<string, number> = {
  H: 1,
  He: 2,
  Li: 3,
  Be: 4,
  B: 5,
  C: 6,
  N: 7,
  O: 8,
  F: 9,
  Ne: 10,
  Na: 11,
  Mg: 12,
  Al: 13,
  Si: 14,
  P: 15,
  S: 16,
  Cl: 17,
  Ar: 18,
  K: 19,
  Ca: 20,
  Sc: 21,
  Ti: 22,
  V: 23,
  Cr: 24,
  Mn: 25,
  Fe: 26,
  Co: 27,
  Ni: 28,
  Cu: 29,
  Zn: 30,
  Ga: 31,
  Ge: 32,
  As: 33,
  Se: 34,
  Br: 35,
  Kr: 36,
  Rb: 37,
  Sr: 38,
  Y: 39,
  Zr: 40,
  Nb: 41,
  Mo: 42,
  Tc: 43,
  Ru: 44,
  Rh: 45,
  Pd: 46,
  Ag: 47,
  Cd: 48,
  In: 49,
  Sn: 50,
  Sb: 51,
  Te: 52,
  I: 53,
  Xe: 54,
  Cs: 55,
  Ba: 56,
  La: 57,
  Ce: 58,
  Pr: 59,
  Nd: 60,
  Pm: 61,
  Sm: 62,
  Eu: 63,
  Gd: 64,
  Tb: 65,
  Dy: 66,
  Ho: 67,
  Er: 68,
  Tm: 69,
  Yb: 70,
  Lu: 71,
  Hf: 72,
  Ta: 73,
  W: 74,
  Re: 75,
  Os: 76,
  Ir: 77,
  Pt: 78,
  Au: 79,
  Hg: 80,
  Tl: 81,
  Pb: 82,
  Bi: 83,
  Po: 84,
  At: 85,
  Rn: 86,
  Fr: 87,
  Ra: 88,
  Ac: 89,
  Th: 90,
  Pa: 91,
  U: 92,
  Np: 93,
  Pu: 94,
  Am: 95,
  Cm: 96,
  Bk: 97,
  Cf: 98,
  Es: 99,
  Fm: 100,
  Md: 101,
  No: 102,
  Lr: 103,
  Rf: 104,
  Db: 105,
  Sg: 106,
  Bh: 107,
  Hs: 108,
  Mt: 109,
  Ds: 110,
  Rg: 111,
  Cn: 112,
  Nh: 113,
  Fl: 114,
  Mc: 115,
  Lv: 116,
  Ts: 117,
  Og: 118,
};

type ElementCatalogItem = {
  atomicNumber: number;
  name?: string;
  atomicMass?: number | null;
};

const initialElementCatalog: Record<string, ElementCatalogItem> = {
  H: { atomicNumber: 1, name: "Hidrogênio" },
  He: { atomicNumber: 2, name: "Hélio" },
  Li: { atomicNumber: 3, name: "Lítio" },
  Be: { atomicNumber: 4, name: "Berílio" },
  B: { atomicNumber: 5, name: "Boro" },
  C: { atomicNumber: 6, name: "Carbono" },
  N: { atomicNumber: 7, name: "Nitrogênio" },
  O: { atomicNumber: 8, name: "Oxigênio" },
  F: { atomicNumber: 9, name: "Flúor" },
  Ne: { atomicNumber: 10, name: "Neônio" },
  Na: { atomicNumber: 11, name: "Sódio" },
  Mg: { atomicNumber: 12, name: "Magnésio" },
  Al: { atomicNumber: 13, name: "Alumínio" },
  Si: { atomicNumber: 14, name: "Silício" },
  P: { atomicNumber: 15, name: "Fósforo" },
  S: { atomicNumber: 16, name: "Enxofre" },
  Cl: { atomicNumber: 17, name: "Cloro" },
  Ar: { atomicNumber: 18, name: "Argônio" },
  K: { atomicNumber: 19, name: "Potássio" },
  Ca: { atomicNumber: 20, name: "Cálcio" },
  Sc: { atomicNumber: 21, name: "Escândio" },
  Ti: { atomicNumber: 22, name: "Titânio" },
  V: { atomicNumber: 23, name: "Vanádio" },
  Cr: { atomicNumber: 24, name: "Cromo" },
  Mn: { atomicNumber: 25, name: "Manganês" },
  Fe: { atomicNumber: 26, name: "Ferro" },
  Co: { atomicNumber: 27, name: "Cobalto" },
  Ni: { atomicNumber: 28, name: "Níquel" },
  Cu: { atomicNumber: 29, name: "Cobre" },
  Zn: { atomicNumber: 30, name: "Zinco" },
  Ga: { atomicNumber: 31, name: "Gálio" },
  Ge: { atomicNumber: 32, name: "Germânio" },
  As: { atomicNumber: 33, name: "Arsênio" },
  Se: { atomicNumber: 34, name: "Selênio" },
  Br: { atomicNumber: 35, name: "Bromo" },
  Kr: { atomicNumber: 36, name: "Criptônio" },
  Rb: { atomicNumber: 37, name: "Rubídio" },
  Sr: { atomicNumber: 38, name: "Estrôncio" },
  Y: { atomicNumber: 39, name: "Ítrio" },
  Zr: { atomicNumber: 40, name: "Zircônio" },
  Nb: { atomicNumber: 41, name: "Nióbio" },
  Mo: { atomicNumber: 42, name: "Molibdênio" },
  Tc: { atomicNumber: 43, name: "Tecnécio" },
  Ru: { atomicNumber: 44, name: "Rutênio" },
  Rh: { atomicNumber: 45, name: "Ródio" },
  Pd: { atomicNumber: 46, name: "Paládio" },
  Ag: { atomicNumber: 47, name: "Prata" },
  Cd: { atomicNumber: 48, name: "Cádmio" },
  In: { atomicNumber: 49, name: "Índio" },
  Sn: { atomicNumber: 50, name: "Estanho" },
  Sb: { atomicNumber: 51, name: "Antimônio" },
  Te: { atomicNumber: 52, name: "Telúrio" },
  I: { atomicNumber: 53, name: "Iodo" },
  Xe: { atomicNumber: 54, name: "Xenônio" },
  Cs: { atomicNumber: 55, name: "Césio" },
  Ba: { atomicNumber: 56, name: "Bário" },
  La: { atomicNumber: 57, name: "Lantânio" },
  Ce: { atomicNumber: 58, name: "Cério" },
  Pr: { atomicNumber: 59, name: "Praseodímio" },
  Nd: { atomicNumber: 60, name: "Neodímio" },
  Pm: { atomicNumber: 61, name: "Promécio" },
  Sm: { atomicNumber: 62, name: "Samário" },
  Eu: { atomicNumber: 63, name: "Európio" },
  Gd: { atomicNumber: 64, name: "Gadolínio" },
  Tb: { atomicNumber: 65, name: "Térbio" },
  Dy: { atomicNumber: 66, name: "Disprósio" },
  Ho: { atomicNumber: 67, name: "Hólmio" },
  Er: { atomicNumber: 68, name: "Érbio" },
  Tm: { atomicNumber: 69, name: "Túlio" },
  Yb: { atomicNumber: 70, name: "Itérbio" },
  Lu: { atomicNumber: 71, name: "Lutécio" },
  Hf: { atomicNumber: 72, name: "Háfnio" },
  Ta: { atomicNumber: 73, name: "Tântalo" },
  W: { atomicNumber: 74, name: "Tungstênio" },
  Re: { atomicNumber: 75, name: "Rênio" },
  Os: { atomicNumber: 76, name: "Ósmio" },
  Ir: { atomicNumber: 77, name: "Irídio" },
  Pt: { atomicNumber: 78, name: "Platina" },
  Au: { atomicNumber: 79, name: "Ouro" },
  Hg: { atomicNumber: 80, name: "Mercúrio" },
  Tl: { atomicNumber: 81, name: "Tálio" },
  Pb: { atomicNumber: 82, name: "Chumbo" },
  Bi: { atomicNumber: 83, name: "Bismuto" },
  Po: { atomicNumber: 84, name: "Polônio" },
  At: { atomicNumber: 85, name: "Astato" },
  Rn: { atomicNumber: 86, name: "Radônio" },
  Fr: { atomicNumber: 87, name: "Frâncio" },
  Ra: { atomicNumber: 88, name: "Rádio" },
  Ac: { atomicNumber: 89, name: "Actínio" },
  Th: { atomicNumber: 90, name: "Tório" },
  Pa: { atomicNumber: 91, name: "Protactínio" },
  U: { atomicNumber: 92, name: "Urânio" },
  Np: { atomicNumber: 93, name: "Neptúnio" },
  Pu: { atomicNumber: 94, name: "Plutônio" },
  Am: { atomicNumber: 95, name: "Amerício" },
  Cm: { atomicNumber: 96, name: "Cúrio" },
  Bk: { atomicNumber: 97, name: "Berquélio" },
  Cf: { atomicNumber: 98, name: "Califórnio" },
  Es: { atomicNumber: 99, name: "Einstênio" },
  Fm: { atomicNumber: 100, name: "Férmio" },
  Md: { atomicNumber: 101, name: "Mendelévio" },
  No: { atomicNumber: 102, name: "Nobélio" },
  Lr: { atomicNumber: 103, name: "Laurêncio" },
  Rf: { atomicNumber: 104, name: "Rutherfórdio" },
  Db: { atomicNumber: 105, name: "Dúbnio" },
  Sg: { atomicNumber: 106, name: "Seabórgio" },
  Bh: { atomicNumber: 107, name: "Bóhrio" },
  Hs: { atomicNumber: 108, name: "Hássio" },
  Mt: { atomicNumber: 109, name: "Meitnério" },
  Ds: { atomicNumber: 110, name: "Darmstádio" },
  Rg: { atomicNumber: 111, name: "Roentgênio" },
  Cn: { atomicNumber: 112, name: "Copernício" },
  Nh: { atomicNumber: 113, name: "Nihônio" },
  Fl: { atomicNumber: 114, name: "Fleróvio" },
  Mc: { atomicNumber: 115, name: "Moscóvio" },
  Lv: { atomicNumber: 116, name: "Livermório" },
  Ts: { atomicNumber: 117, name: "Tenessino" },
  Og: { atomicNumber: 118, name: "Oganessônio" },
};

const emptyGraph: EditableMoleculeGraph = {
  atoms: [],
  bonds: [],
};

const initialViewport: CanvasViewport = {
  zoom: 1,
  panX: 0,
  panY: 0,
};

function createId(prefix: string) {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}_${crypto.randomUUID()}`;
  }

  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function normalizeElementSymbol(symbol: string) {
  const trimmed = symbol.trim();

  if (!trimmed) return "";
  if (trimmed.length === 1) return trimmed.toUpperCase();

  return `${trimmed.charAt(0).toUpperCase()}${trimmed.slice(1).toLowerCase()}`;
}

function isKnownElementSymbol(symbol: string) {
  return allElementSymbols.has(normalizeElementSymbol(symbol));
}

function getBondOrderFromStyle(style: BondVisualStyle): BondOrder {
  if (style === "double" || style === "double-resonance") return 2;
  if (style === "triple") return 3;
  if (style === "aromatic") return 1.5;

  // Cunhas, coordenação tracejada e ressonância simples continuam como
  // ligação simples no grafo base. O significado fica em visual_style/bond_role.
  return 1;
}

function getBondRoleFromStyle(style: BondVisualStyle): BondRole {
  if (style === "wedge-filled" || style === "wedge-dashed") return "stereo";
  if (style === "dashed") return "coordination";
  if (style === "single-resonance" || style === "double-resonance") {
    return "resonance";
  }
  if (style === "aromatic") return "aromatic";

  return "covalent";
}

function getBondTypeFromStyle(style: BondVisualStyle) {
  if (style === "dashed") return "DATIVE";
  if (style === "double" || style === "double-resonance") return "DOUBLE";
  if (style === "triple") return "TRIPLE";
  if (style === "aromatic") return "AROMATIC";

  return "SINGLE";
}

function isConjugatedLikeStyle(style: BondVisualStyle) {
  return (
    style === "single-resonance" ||
    style === "double-resonance" ||
    style === "aromatic"
  );
}

function getStereoVisualFromStyle(
  style: BondVisualStyle
): "none" | "wedge" | "dash" | "unknown" {
  if (style === "wedge-filled") return "wedge";
  if (style === "wedge-dashed") return "dash";

  return "none";
}

function getBondDirectionFromStyle(style: BondVisualStyle) {
  if (style === "wedge-filled") return "BEGINWEDGE";
  if (style === "wedge-dashed") return "BEGINDASH";

  return "NONE";
}

type AtomBondEnvironment = {
  bondCount: number;
  bondOrderSum: number;
  hasDoubleBond: boolean;
  hasTripleBond: boolean;
  hasAromaticOrResonance: boolean;
  coordinationBondCount: number;
};

type AtomChemistryEstimate = {
  formalCharge: number;
  lonePairCount: number;
  hybridization: string;
  warnings: string[];
  errors: string[];
};

function isHalogen(element: string) {
  return element === "F" || element === "Cl" || element === "Br" || element === "I";
}

function roundBondOrder(value: number) {
  return Math.round(value * 10) / 10;
}

function normalizeNullableNumber(value: unknown): number | null {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }

  if (typeof value === "string") {
    const trimmed = value.trim();

    if (!trimmed || trimmed === "—" || trimmed.toLowerCase() === "null") {
      return null;
    }

    const parsed = Number(trimmed.replace(",", "."));

    return Number.isFinite(parsed) ? parsed : null;
  }

  return null;
}

function getBondOrderForElectronCounting(bond: InternalBondModel) {
  if (bond.visual_style === "double-resonance") return 2;
  if (bond.visual_style === "single-resonance") return 1;
  if (bond.visual_style === "aromatic") return 1.5;
  if (bond.visual_style === "dashed") return 1;

  if (bond.order === 1.5) return 1.5;
  if (bond.order === 2) return 2;
  if (bond.order === 3) return 3;

  return 1;
}

function getAtomBondEnvironment(
  molecule: InternalMoleculeModel,
  atomId: string
): AtomBondEnvironment {
  let bondCount = 0;
  let bondOrderSum = 0;
  let hasDoubleBond = false;
  let hasTripleBond = false;
  let hasAromaticOrResonance = false;
  let coordinationBondCount = 0;

  molecule.bonds.forEach((bond) => {
    if (bond.atom_a_id !== atomId && bond.atom_b_id !== atomId) return;

    const order = getBondOrderForElectronCounting(bond);

    bondCount += 1;
    bondOrderSum += order;

    if (order === 2) hasDoubleBond = true;
    if (order === 3) hasTripleBond = true;

    if (
      bond.visual_style === "aromatic" ||
      bond.visual_style === "single-resonance" ||
      bond.visual_style === "double-resonance" ||
      bond.is_aromatic ||
      bond.is_conjugated
    ) {
      hasAromaticOrResonance = true;
    }

    if (bond.visual_style === "dashed" || bond.bond_role === "coordination") {
      coordinationBondCount += 1;
    }
  });

  return {
    bondCount,
    bondOrderSum: roundBondOrder(bondOrderSum),
    hasDoubleBond,
    hasTripleBond,
    hasAromaticOrResonance,
    coordinationBondCount,
  };
}

function estimateHybridization(
  element: string,
  environment: AtomBondEnvironment,
  lonePairCount: number
) {
  if (element === "H") return "S";
  if (environment.hasTripleBond) return "SP";

  if (environment.hasDoubleBond || environment.hasAromaticOrResonance) {
    return "SP2";
  }

  const stericNumber = environment.bondCount + lonePairCount;

  if (stericNumber <= 0) {
    if (element === "O" || element === "N" || element === "S" || element === "P") {
      return "SP3";
    }

    return "UNSPECIFIED";
  }

  if (stericNumber <= 2) return "SP";
  if (stericNumber === 3) return "SP2";
  if (stericNumber === 4) return "SP3";
  if (stericNumber === 5) return "SP3D";
  if (stericNumber >= 6) return "SP3D2";

  return "UNSPECIFIED";
}

function estimateAtomChemistry(
  atom: InternalAtomModel,
  environment: AtomBondEnvironment
): AtomChemistryEstimate {
  const element = atom.element;
  const order = roundBondOrder(environment.bondOrderSum);
  const warnings: string[] = [];
  const errors: string[] = [];

  let formalCharge = 0;
  let lonePairCount = 0;

  if (element === "H") {
    formalCharge = 0;
    lonePairCount = 0;

    if (order > 1) {
      errors.push(`Hidrogênio ${atom.rdkit_index + 1} não pode ter mais de 1 ligação.`);
    }
  } else if (element === "C") {
    formalCharge = 0;
    lonePairCount = 0;

    if (order > 4) {
      errors.push(
        `Carbono ${atom.rdkit_index + 1} está com valência ${order}. Carbono pentavalente não é uma estrutura orgânica comum; remova uma ligação antes de otimizar.`
      );
    }

    if (order < 4 && atom.formal_charge !== 0) {
      warnings.push(
        `Carbono ${atom.rdkit_index + 1} manteve carga automática 0. Use carga manual se quiser carbocátion, carbânion ou carbene.`
      );
    }
  } else if (element === "B") {
    if (order > 4) {
      errors.push(`Boro ${atom.rdkit_index + 1} excede valência comum 4.`);
    }

    formalCharge = order >= 4 ? -1 : 0;
    lonePairCount = 0;
  } else if (element === "N") {
    if (order > 4) {
      errors.push(`Nitrogênio ${atom.rdkit_index + 1} excede valência comum 4.`);
    }

    if (order >= 4) {
      formalCharge = 1;
      lonePairCount = 0;
    } else {
      // N com 1, 2 ou 3 ligações normalmente pode ser completado por H implícito.
      // Portanto, não force -2/-1 automaticamente.
      formalCharge = 0;
      lonePairCount = 1;
    }
  } else if (element === "O") {
    if (order > 3) {
      errors.push(`Oxigênio ${atom.rdkit_index + 1} excede valência comum 3.`);
    }

    if (order >= 3) {
      formalCharge = 1;
      lonePairCount = 1;
    } else {
      // O com 0 ou 1 ligação pode ter H implícito; O com 2 ligações é neutro.
      formalCharge = 0;
      lonePairCount = 2;
    }
  } else if (isHalogen(element)) {
    if (order > 2) {
      errors.push(`${element} ${atom.rdkit_index + 1} excede valência comum 2.`);
    }

    if (order >= 2) {
      formalCharge = 1;
      lonePairCount = 2;
    } else {
      formalCharge = 0;
      lonePairCount = 3;
    }
  } else if (element === "P") {
    if (order > 5) {
      errors.push(`Fósforo ${atom.rdkit_index + 1} excede valência comum 5.`);
    }

    if (order >= 5) {
      formalCharge = 0;
      lonePairCount = 0;
    } else if (order >= 4) {
      formalCharge = 1;
      lonePairCount = 0;
    } else {
      formalCharge = 0;
      lonePairCount = 1;
    }
  } else if (element === "S") {
    if (order > 6) {
      errors.push(`Enxofre ${atom.rdkit_index + 1} excede valência comum 6.`);
    }

    if (order >= 6) {
      formalCharge = 0;
      lonePairCount = 0;
    } else if (order >= 4) {
      formalCharge = 0;
      lonePairCount = 1;
    } else if (order >= 3) {
      formalCharge = 1;
      lonePairCount = 1;
    } else {
      formalCharge = 0;
      lonePairCount = 2;
    }
  } else {
    // Metais, gases nobres e elementos menos comuns:
    // não inventar pares livres nem carga automaticamente.
    formalCharge = atom.formal_charge;
    lonePairCount = 0;
    warnings.push(
      `${element} ${atom.rdkit_index + 1}: carga formal preservada; regras automáticas completas ainda não foram definidas para este elemento.`
    );
  }

  const hybridization = estimateHybridization(element, environment, lonePairCount);

  return {
    formalCharge,
    lonePairCount,
    hybridization,
    warnings,
    errors,
  };
}

function validateMoleculeForRdkit(molecule: InternalMoleculeModel) {
  const errors: string[] = [];

  molecule.atoms.forEach((atom) => {
    const environment = getAtomBondEnvironment(molecule, atom.id);
    const order = environment.bondOrderSum;

    if (atom.element === "H" && order > 1) {
      errors.push(`Hidrogênio ${atom.rdkit_index + 1} tem ${order} ligações.`);
    }

    if (atom.element === "C" && order > 4) {
      errors.push(
        `Carbono ${atom.rdkit_index + 1} tem valência ${order}. Isso não é corrigível apenas com carga formal.`
      );
    }

    if (atom.element === "N" && order === 4 && atom.formal_charge !== 1) {
      errors.push(
        `Nitrogênio ${atom.rdkit_index + 1} com 4 ligações precisa de carga +1. Use ⚖ Cargas/pares.`
      );
    }

    if (atom.element === "O" && order === 3 && atom.formal_charge !== 1) {
      errors.push(
        `Oxigênio ${atom.rdkit_index + 1} com 3 ligações precisa de carga +1. Use ⚖ Cargas/pares.`
      );
    }

    if (atom.element === "B" && order === 4 && atom.formal_charge !== -1) {
      errors.push(
        `Boro ${atom.rdkit_index + 1} com 4 ligações normalmente precisa de carga -1. Use ⚖ Cargas/pares.`
      );
    }
  });

  return errors;
}

function applyFormalChargeDistributionToMolecule(
  molecule: InternalMoleculeModel
): InternalMoleculeModel {
  const warnings: string[] = [];
  const errors: string[] = [];

  const atoms = molecule.atoms.map((atom) => {
    const environment = getAtomBondEnvironment(molecule, atom.id);
    const estimate = estimateAtomChemistry(atom, environment);

    warnings.push(...estimate.warnings);
    errors.push(...estimate.errors);

    return {
      ...atom,
      formal_charge: estimate.formalCharge,
      lone_pair_count: estimate.lonePairCount,
      hybridization: estimate.hybridization,
    };
  });

  return {
    ...molecule,
    atoms,
    validation_state: {
      is_valid: errors.length === 0,
      warnings,
      errors,
    },
  };
}

function getBondMetadataKey(atomAIndex: number, atomBIndex: number) {
  return [atomAIndex, atomBIndex].sort((a, b) => a - b).join("-");
}

function mergeEditorChemistryAfterRdkit(
  previous: InternalMoleculeModel,
  next: InternalMoleculeModel
): InternalMoleculeModel {
  const previousBondByPair = new Map<string, InternalBondModel>();
  const previousAtomByIndex = new Map<number, InternalAtomModel>();

  previous.atoms.forEach((atom) => {
    previousAtomByIndex.set(atom.rdkit_index, atom);
  });

  previous.bonds.forEach((bond) => {
    previousBondByPair.set(
      getBondMetadataKey(bond.atom_a_rdkit_index, bond.atom_b_rdkit_index),
      bond
    );
  });

  return {
    ...next,
    atoms: next.atoms.map((atom) => {
      const previousAtom = previousAtomByIndex.get(atom.rdkit_index);

      if (!previousAtom) return atom;

      return {
        ...atom,
        formal_charge: previousAtom.formal_charge,
        lone_pair_count: previousAtom.lone_pair_count ?? atom.lone_pair_count ?? 0,
        radical_count: previousAtom.radical_count ?? atom.radical_count ?? 0,
      };
    }),
    bonds: next.bonds.map((bond) => {
      const previousBond = previousBondByPair.get(
        getBondMetadataKey(bond.atom_a_rdkit_index, bond.atom_b_rdkit_index)
      );

      if (!previousBond) return bond;

      const visualStyle = previousBond.visual_style;
      const bondRole =
        previousBond.bond_role ??
        (visualStyle ? getBondRoleFromStyle(visualStyle) : bond.bond_role);

      if (!visualStyle) {
        return {
          ...bond,
          bond_role: bondRole,
        };
      }

      return {
        ...bond,
        order: getBondOrderFromStyle(visualStyle),
        bond_type: getBondTypeFromStyle(visualStyle),
        is_aromatic: visualStyle === "aromatic",
        is_conjugated:
          isConjugatedLikeStyle(visualStyle) || bond.is_conjugated,
        stereo_visual: getStereoVisualFromStyle(visualStyle),
        direction: getBondDirectionFromStyle(visualStyle),
        visual_style: visualStyle,
        bond_role: bondRole,
      };
    }),
  };
}

function getFormulaFromAtoms(atoms: InternalAtomModel[]) {
  if (atoms.length === 0) return "";

  const counts = atoms.reduce<Record<string, number>>((acc, atom) => {
    acc[atom.element] = (acc[atom.element] ?? 0) + 1;
    return acc;
  }, {});

  return Object.entries(counts)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([element, count]) => `${element}${count > 1 ? count : ""}`)
    .join("");
}

function createEmptyInternalMolecule(): InternalMoleculeModel {
  return {
    id: createId("local_mol"),
    model_version: "internal-molecule-v1",
    metadata: {
      source: "FrontendEditor2D",
      source_format: "INTERNAL_2D_EDITOR",
      original_input: "",
      canonical_smiles: "",
      formula: "",
      molecular_weight: 0,
      exact_molecular_weight: 0,
      atom_count: 0,
      bond_count: 0,
    },
    atoms: [],
    bonds: [],
    svg: null,
    validation_state: {
      is_valid: true,
      warnings: [],
      errors: [],
    },
  };
}

function sanitizeInternalMolecule(molecule: InternalMoleculeModel): InternalMoleculeModel {
  return {
    ...molecule,
    atoms: molecule.atoms.map((atom) => ({
      ...atom,
      radical_count: atom.radical_count ?? 0,
      lone_pair_count: atom.lone_pair_count ?? 0,
    })),
    bonds: molecule.bonds.map((bond) => ({
      ...bond,
      visual_style: bond.visual_style ?? undefined,
      bond_role:
        bond.bond_role ??
        (bond.visual_style ? getBondRoleFromStyle(bond.visual_style) : undefined),
    })),
  };
}

function refreshInternalMetadata(
  molecule: InternalMoleculeModel,
  canonicalSmiles: string
): InternalMoleculeModel {
  const formula = getFormulaFromAtoms(molecule.atoms);

  return {
    ...molecule,
    metadata: {
      ...molecule.metadata,
      canonical_smiles: canonicalSmiles,
      formula,
      atom_count: molecule.atoms.length,
      bond_count: molecule.bonds.length,
    },
  };
}

function createLocalRDKitWrapper(
  internalMolecule: InternalMoleculeModel,
  currentSmiles: string
): RDKitMolecule2D {
  const refreshed = refreshInternalMetadata(internalMolecule, currentSmiles);

  return {
    success: true,
    input_type: "INTERNAL_2D_EDITOR",
    original_input: refreshed.metadata.original_input,
    canonical_smiles: currentSmiles,
    formula: refreshed.metadata.formula,
    molecular_weight: refreshed.metadata.molecular_weight,
    exact_molecular_weight: refreshed.metadata.exact_molecular_weight,
    atom_count: refreshed.atoms.length,
    bond_count: refreshed.bonds.length,
    svg: refreshed.svg ?? "",
    internal_molecule: refreshed,
  };
}

function internalMoleculeToGraph(
  molecule: InternalMoleculeModel | null
): EditableMoleculeGraph {
  if (!molecule) return emptyGraph;

  return {
    atoms: molecule.atoms.map((atom) => ({
      index: atom.rdkit_index,
      symbol: atom.element,
      formal_charge: atom.formal_charge,
      is_aromatic: atom.is_aromatic,
      x: atom.position_2d.x,
      y: atom.position_2d.y,
    })),
    bonds: molecule.bonds.map((bond) => ({
      begin_atom_index: bond.atom_a_rdkit_index,
      end_atom_index: bond.atom_b_rdkit_index,
      order:
        bond.visual_style === "single-resonance"
          ? 1
          : bond.visual_style === "double-resonance"
            ? 2
            : bond.order,
      is_aromatic: bond.visual_style === "aromatic" || bond.is_aromatic,
      visual_style: bond.visual_style,
      bond_role:
        bond.bond_role ??
        (bond.visual_style ? getBondRoleFromStyle(bond.visual_style) : undefined),
    })),
  };
}

function getNextAtomIndex(molecule: InternalMoleculeModel) {
  if (molecule.atoms.length === 0) return 0;

  return Math.max(...molecule.atoms.map((atom) => atom.rdkit_index)) + 1;
}

function getNextBondIndex(molecule: InternalMoleculeModel) {
  if (molecule.bonds.length === 0) return 0;

  return Math.max(...molecule.bonds.map((bond) => bond.rdkit_index)) + 1;
}

function createInternalAtom(
  molecule: InternalMoleculeModel,
  symbol: string,
  atomicNumber: number,
  position: Position2D,
  formalCharge: number
): InternalAtomModel {
  const nextIndex = getNextAtomIndex(molecule);

  return {
    id: createId("a"),
    rdkit_index: nextIndex,
    element: symbol,
    atomic_number: atomicNumber,
    formal_charge: formalCharge,
    is_aromatic: false,
    chiral_tag: "CHI_UNSPECIFIED",
    hybridization: "UNSPECIFIED",
    total_hydrogens: 0,
    implicit_hydrogens: 0,
    explicit_hydrogens: 0,
    total_valence: null,
    degree: 0,
    position_2d: position,
    radical_count: 0,
    lone_pair_count: 0,
  };
}

function createInternalBond(
  molecule: InternalMoleculeModel,
  atomA: InternalAtomModel,
  atomB: InternalAtomModel,
  style: BondVisualStyle
): InternalBondModel {
  const order = getBondOrderFromStyle(style);

  return {
    id: createId("b"),
    rdkit_index: getNextBondIndex(molecule),
    atom_a_id: atomA.id,
    atom_b_id: atomB.id,
    atom_a_rdkit_index: atomA.rdkit_index,
    atom_b_rdkit_index: atomB.rdkit_index,
    order,
    bond_type: getBondTypeFromStyle(style),
    is_aromatic: style === "aromatic",
    is_conjugated: isConjugatedLikeStyle(style),
    stereo: "STEREONONE",
    direction: getBondDirectionFromStyle(style),
    stereo_visual: getStereoVisualFromStyle(style),
    visual_style: style,
    bond_role: getBondRoleFromStyle(style),
  };
}

function recalculateAtomDegrees(
  molecule: InternalMoleculeModel
): InternalMoleculeModel {
  const degreeByAtomId = new Map<string, number>();

  molecule.atoms.forEach((atom) => {
    degreeByAtomId.set(atom.id, 0);
  });

  molecule.bonds.forEach((bond) => {
    degreeByAtomId.set(
      bond.atom_a_id,
      (degreeByAtomId.get(bond.atom_a_id) ?? 0) + 1
    );

    degreeByAtomId.set(
      bond.atom_b_id,
      (degreeByAtomId.get(bond.atom_b_id) ?? 0) + 1
    );
  });

  return {
    ...molecule,
    atoms: molecule.atoms.map((atom) => ({
      ...atom,
      degree: degreeByAtomId.get(atom.id) ?? 0,
    })),
  };
}


function hasAnyActiveTool(tools: EditorToolState) {
  return (
    tools.panToolActive ||
    tools.atomToolActive ||
    tools.bondToolActive ||
    tools.atomBondToolActive ||
    tools.radicalToolActive ||
    tools.lonePairToolActive ||
    tools.chargeToolActive ||
    tools.deleteToolActive
  );
}

export function Page2D() {
  const [format, setFormat] = useState<ImportFormat>("SMILES");
  const [importValue, setImportValue] = useState("O");

  const [selectedElement, setSelectedElement] = useState("O");
  const [quickElements, setQuickElements] = useState<string[]>(
    initialQuickElements
  );
  const [elementCatalog, setElementCatalog] =
    useState<Record<string, ElementCatalogItem>>(initialElementCatalog);

  const [showPeriodicTable, setShowPeriodicTable] = useState(false);
  const [viewport, setViewport] = useState<CanvasViewport>(initialViewport);

  const [molecule, setMolecule] = useState<RDKitMolecule2D | null>(
    createLocalRDKitWrapper(createEmptyInternalMolecule(), "")
  );
  const [graph, setGraph] = useState<EditableMoleculeGraph>(emptyGraph);
  const [currentSmiles, setCurrentSmiles] = useState("");
  const [syncError, setSyncError] = useState("");
  const [loadingImport, setLoadingImport] = useState(false);
  const [optimizing2D, setOptimizing2D] = useState(false);
  const [showExplicitHs, setShowExplicitHs] = useState(false);

  const [selectedBondOrder, setSelectedBondOrder] = useState<BondOrder>(1);
  const [selectedBondStyle, setSelectedBondStyle] =
    useState<BondVisualStyle>("single");
  const [defaultFormalCharge, setDefaultFormalCharge] = useState(0);
  const [selectedTarget, setSelectedTarget] =
    useState<SelectedMoleculeTarget>(null);

  const [showAtomIndices, setShowAtomIndices] = useState(false);

  const [moveAtomToolActive, setMoveAtomToolActive] = useState(true);
  const [panToolActive, setPanToolActive] = useState(false);
  const [atomToolActive, setAtomToolActive] = useState(false);
  const [bondToolActive, setBondToolActive] = useState(false);
  const [atomBondToolActive, setAtomBondToolActive] = useState(false);
  const [radicalToolActive, setRadicalToolActive] = useState(false);
  const [lonePairToolActive, setLonePairToolActive] = useState(false);
  const [chargeToolActive, setChargeToolActive] = useState(false);
  const [deleteToolActive, setDeleteToolActive] = useState(false);
  const [pendingBondAtomId, setPendingBondAtomId] = useState<string | null>(
    null
  );

  const [savedMolecules, setSavedMolecules] = useState<SavedMolecule[]>([
    {
      id: "oxygen-demo",
      name: "Oxigênio",
      formula: "H2O",
      smiles: "O",
      molarMass: "18.015",
      status: "Otimizada",
      concentration: "1",
      unit: "mmol/L",
    },
    {
      id: "potassium-demo",
      name: "Potássio",
      formula: "K+",
      smiles: "[K+]",
      molarMass: "39.098",
      status: "Aguardando",
      concentration: "1",
      unit: "mmol/L",
    },
  ]);

  const tools = useMemo<EditorToolState>(
    () => ({
      moveAtomToolActive,
      panToolActive,
      atomToolActive,
      bondToolActive,
      atomBondToolActive,
      radicalToolActive,
      lonePairToolActive,
      chargeToolActive,
      deleteToolActive,
    }),
    [
      atomToolActive,
      atomBondToolActive,
      bondToolActive,
      chargeToolActive,
      deleteToolActive,
      lonePairToolActive,
      moveAtomToolActive,
      panToolActive,
      radicalToolActive,
    ]
  );

  const placeholder = useMemo(() => {
    if (format === "SMILES") {
      return "Ex: O, N, P, [K+], CCO, benzene etc.";
    }

    if (format === "InChI") return "Nesta fase inicial, use SMILES.";
    if (format === "InChIKey") return "Nesta fase inicial, use SMILES.";

    return "Use SMILES";
  }, [format]);

  const internalMolecule = useMemo(
    () =>
      molecule?.internal_molecule
        ? sanitizeInternalMolecule(molecule.internal_molecule)
        : null,
    [molecule]
  );

  const selectedBondId =
    selectedTarget?.kind === "bond" ? selectedTarget.id : null;


  useEffect(() => {
    const leftPageState = {
      molecule: internalMolecule,
      selectedTarget,
      selectedBondStyle,
      showAtomIndices,
    };

    try {
      window.localStorage.setItem(
        LEFTPAGE_STORAGE_KEY,
        JSON.stringify(leftPageState)
      );
    } catch {
      // LocalStorage pode estar indisponível em alguns contextos.
    }

    window.dispatchEvent(
      new CustomEvent(LEFTPAGE_STATE_EVENT, {
        detail: leftPageState,
      })
    );
  }, [internalMolecule, selectedTarget, selectedBondStyle, showAtomIndices]);

  useEffect(() => {
    if (graph.atoms.length === 0) {
      setCurrentSmiles("");
      return;
    }

    const timeout = window.setTimeout(async () => {
      try {
        setSyncError("");

        const result = await graphToSmiles(graph);
        setCurrentSmiles(result.canonical_smiles);
      } catch (error) {
        setSyncError(
          error instanceof Error
            ? error.message
            : "Não foi possível atualizar o SMILES. A estrutura visual continua preservada."
        );
      }
    }, 350);

    return () => window.clearTimeout(timeout);
  }, [graph]);

  function setExclusiveTool(tool: keyof EditorToolState) {
    const currentlyActive = tools[tool];

    setMoveAtomToolActive(tool === "moveAtomToolActive" ? !currentlyActive : false);
    setPanToolActive(tool === "panToolActive" ? !currentlyActive : false);
    setAtomToolActive(tool === "atomToolActive" ? !currentlyActive : false);
    setBondToolActive(tool === "bondToolActive" ? !currentlyActive : false);
    setAtomBondToolActive(tool === "atomBondToolActive" ? !currentlyActive : false);
    setRadicalToolActive(tool === "radicalToolActive" ? !currentlyActive : false);
    setLonePairToolActive(tool === "lonePairToolActive" ? !currentlyActive : false);
    setChargeToolActive(tool === "chargeToolActive" ? !currentlyActive : false);
    setDeleteToolActive(tool === "deleteToolActive" ? !currentlyActive : false);
    setPendingBondAtomId(null);

    if (currentlyActive) {
      setMoveAtomToolActive(true);
    }
  }

  function getAtomicNumberForSymbol(symbol: string) {
    const normalizedSymbol = normalizeElementSymbol(symbol);

    return (
      elementCatalog[normalizedSymbol]?.atomicNumber ??
      atomicNumberBySymbol[normalizedSymbol] ??
      0
    );
  }

  function commitInternalMolecule(nextMolecule: InternalMoleculeModel) {
    const normalized = recalculateAtomDegrees(
      refreshInternalMetadata(nextMolecule, currentSmiles)
    );

    setMolecule(createLocalRDKitWrapper(normalized, currentSmiles));
    setGraph(internalMoleculeToGraph(normalized));
  }

  function updateInternalMolecule(
    updater: (previous: InternalMoleculeModel) => InternalMoleculeModel
  ) {
    const previous = internalMolecule ?? createEmptyInternalMolecule();
    const next = updater(previous);

    commitInternalMolecule(next);
  }

  function handlePeriodicElementSelect(
    symbol: string,
    element: PeriodicElement
  ) {
    const normalizedSymbol = normalizeElementSymbol(symbol);

    if (!normalizedSymbol) return;

    if (!isKnownElementSymbol(normalizedSymbol)) {
      setSyncError(`Elemento químico inválido ou não reconhecido: ${normalizedSymbol}.`);
      return;
    }

    const atomicMass = normalizeNullableNumber(element.atomicMass);

    setElementCatalog((current): Record<string, ElementCatalogItem> => ({
      ...current,
      [normalizedSymbol]: {
        atomicNumber:
          element.atomicNumber || atomicNumberBySymbol[normalizedSymbol] || 0,
        name: element.name,
        atomicMass,
      },
    }));

    setSelectedElement(normalizedSymbol);
    setSyncError("");

    setQuickElements((current) => {
      if (current.includes(normalizedSymbol)) return current;
      return [...current, normalizedSymbol];
    });
  }

  async function handleGenerate2D() {
    try {
      setLoadingImport(true);
      setSyncError("");

      if (format !== "SMILES" && format !== "Auto") {
        throw new Error("Nesta fase inicial, use SMILES.");
      }

      const loadedMolecule = await parseSmilesTo2D(importValue);
      const loadedGraph = rdkitMoleculeToEditableGraph(loadedMolecule);

      setMolecule({
        ...loadedMolecule,
        internal_molecule: sanitizeInternalMolecule(loadedMolecule.internal_molecule),
      });
      setGraph(loadedGraph);
      setCurrentSmiles(loadedMolecule.canonical_smiles);
      setImportValue(loadedMolecule.canonical_smiles);
      setSelectedTarget(null);
      setPendingBondAtomId(null);
      setShowExplicitHs(false);
    } catch (error) {
      setSyncError(
        error instanceof Error ? error.message : "Erro ao gerar molécula 2D."
      );
    } finally {
      setLoadingImport(false);
    }
  }

  function addAtomAtPosition(position: Position2D) {
    const symbol = normalizeElementSymbol(selectedElement);

    if (!symbol) {
      setSyncError("Selecione um elemento na tabela periódica ou na barra de átomos antes de adicionar.");
      return;
    }

    if (!isKnownElementSymbol(symbol)) {
      setSyncError(`Elemento químico inválido ou não reconhecido: ${symbol}.`);
      return;
    }

    setSyncError("");

    updateInternalMolecule((previous) => {
      const atom = createInternalAtom(
        previous,
        symbol,
        getAtomicNumberForSymbol(symbol),
        position,
        defaultFormalCharge
      );

      return {
        ...previous,
        atoms: [...previous.atoms, atom],
      };
    });
  }

  function moveAtom(atomId: string, position: Position2D) {
    updateInternalMolecule((previous) => ({
      ...previous,
      atoms: previous.atoms.map((atom) =>
        atom.id === atomId
          ? {
              ...atom,
              position_2d: position,
            }
          : atom
      ),
    }));
  }

  function createBond(atomAId: string, atomBId: string) {
    if (atomAId === atomBId) {
      setPendingBondAtomId(null);
      return;
    }

    updateInternalMolecule((previous) => {
      const existingBond = previous.bonds.find(
        (bond) =>
          (bond.atom_a_id === atomAId && bond.atom_b_id === atomBId) ||
          (bond.atom_a_id === atomBId && bond.atom_b_id === atomAId)
      );

      /*
        Se já existe ligação entre os dois átomos, a ferramenta de ligação
        selecionada substitui a ligação atual em vez de ignorar a ação.
        Exemplo:
        C-C + ferramenta dupla ativa -> C=C
        C=C + ferramenta tripla ativa -> C≡C
        cunha/tracejada/ressonância também substituem o estilo visual.
      */
      if (existingBond) {
        const order = getBondOrderFromStyle(selectedBondStyle);

        return {
          ...previous,
          bonds: previous.bonds.map((bond) =>
            bond.id === existingBond.id
              ? {
                  ...bond,
                  order,
                  bond_type: getBondTypeFromStyle(selectedBondStyle),
                  is_aromatic: selectedBondStyle === "aromatic",
                  is_conjugated: isConjugatedLikeStyle(selectedBondStyle),
                  stereo_visual: getStereoVisualFromStyle(selectedBondStyle),
                  direction: getBondDirectionFromStyle(selectedBondStyle),
                  visual_style: selectedBondStyle,
                  bond_role: getBondRoleFromStyle(selectedBondStyle),
                }
              : bond
          ),
        };
      }

      const atomA = previous.atoms.find((atom) => atom.id === atomAId);
      const atomB = previous.atoms.find((atom) => atom.id === atomBId);

      if (!atomA || !atomB) return previous;

      const bond = createInternalBond(previous, atomA, atomB, selectedBondStyle);

      return {
        ...previous,
        bonds: [...previous.bonds, bond],
      };
    });

    setPendingBondAtomId(null);
  }

  function extendAtomWithBond(originAtomId: string, position: Position2D) {
    const symbol = normalizeElementSymbol(selectedElement);

    if (!symbol) {
      setSyncError("Selecione um elemento antes de arrastar para criar um novo átomo ligado.");
      return;
    }

    if (!isKnownElementSymbol(symbol)) {
      setSyncError(`Elemento químico inválido ou não reconhecido: ${symbol}.`);
      return;
    }

    updateInternalMolecule((previous) => {
      const originAtom = previous.atoms.find((atom) => atom.id === originAtomId);

      if (!originAtom) return previous;

      const newAtom = createInternalAtom(
        previous,
        symbol,
        getAtomicNumberForSymbol(symbol),
        position,
        defaultFormalCharge
      );

      const interimMolecule = {
        ...previous,
        atoms: [...previous.atoms, newAtom],
      };

      const newBond = createInternalBond(
        interimMolecule,
        originAtom,
        newAtom,
        selectedBondStyle
      );

      return {
        ...interimMolecule,
        bonds: [...interimMolecule.bonds, newBond],
      };
    });
  }

  function deleteAtom(atomId: string) {
    updateInternalMolecule((previous) => ({
      ...previous,
      atoms: previous.atoms.filter((atom) => atom.id !== atomId),
      bonds: previous.bonds.filter(
        (bond) => bond.atom_a_id !== atomId && bond.atom_b_id !== atomId
      ),
    }));

    setSelectedTarget(null);
    setPendingBondAtomId((current) => (current === atomId ? null : current));
  }

  function deleteBond(bondId: string) {
    updateInternalMolecule((previous) => ({
      ...previous,
      bonds: previous.bonds.filter((bond) => bond.id !== bondId),
    }));

    setSelectedTarget(null);
  }

  function clearCanvas() {
    setMolecule(createLocalRDKitWrapper(createEmptyInternalMolecule(), ""));
    setGraph(emptyGraph);
    setCurrentSmiles("");
    setImportValue("");
    setSelectedTarget(null);
    setPendingBondAtomId(null);
    setViewport(initialViewport);
    setShowExplicitHs(false);
  }

  function clearSelectedElementsBar() {
    setQuickElements([]);
    setSelectedElement("");
    setSyncError("");
  }

  function changeAtomCharge(atomId: string, nextCharge: number) {
    updateInternalMolecule((previous) => ({
      ...previous,
      atoms: previous.atoms.map((atom) =>
        atom.id === atomId
          ? {
              ...atom,
              formal_charge: nextCharge,
            }
          : atom
      ),
    }));
  }

  function toggleRadical(atomId: string) {
    updateInternalMolecule((previous) => ({
      ...previous,
      atoms: previous.atoms.map((atom) =>
        atom.id === atomId
          ? {
              ...atom,
              radical_count: atom.radical_count && atom.radical_count > 0 ? 0 : 1,
            }
          : atom
      ),
    }));
  }

  function clearRadical(atomId: string) {
    updateInternalMolecule((previous) => ({
      ...previous,
      atoms: previous.atoms.map((atom) =>
        atom.id === atomId
          ? {
              ...atom,
              radical_count: 0,
            }
          : atom
      ),
    }));
  }

  function toggleLonePair(atomId: string) {
    updateInternalMolecule((previous) => ({
      ...previous,
      atoms: previous.atoms.map((atom) =>
        atom.id === atomId
          ? {
              ...atom,
              lone_pair_count:
                atom.lone_pair_count && atom.lone_pair_count > 0 ? 0 : 1,
            }
          : atom
      ),
    }));
  }

  function clearLonePair(atomId: string) {
    updateInternalMolecule((previous) => ({
      ...previous,
      atoms: previous.atoms.map((atom) =>
        atom.id === atomId
          ? {
              ...atom,
              lone_pair_count: 0,
            }
          : atom
      ),
    }));
  }

  function changeBondStyle(bondId: string, style: BondVisualStyle) {
    const order = getBondOrderFromStyle(style);

    updateInternalMolecule((previous) => ({
      ...previous,
      bonds: previous.bonds.map((bond) =>
        bond.id === bondId
          ? {
              ...bond,
              order,
              bond_type: getBondTypeFromStyle(style),
              is_aromatic: style === "aromatic",
              is_conjugated: isConjugatedLikeStyle(style),
              stereo_visual: getStereoVisualFromStyle(style),
              direction: getBondDirectionFromStyle(style),
              visual_style: style,
              bond_role: getBondRoleFromStyle(style),
            }
          : bond
      ),
    }));
  }

  function handleSelectAtom(atomId: string) {
    setSelectedTarget({
      kind: "atom",
      id: atomId,
    });

    if (!bondToolActive) return;

    if (!pendingBondAtomId) {
      setPendingBondAtomId(atomId);
      return;
    }

    createBond(pendingBondAtomId, atomId);
  }

  function handleSelectBond(bondId: string) {
    setSelectedTarget({
      kind: "bond",
      id: bondId,
    });

    setPendingBondAtomId(null);

    /*
      Com a ferramenta de ligação ativa, clicar diretamente em uma ligação
      existente substitui sua ordem/estilo pela ligação selecionada na toolbar.
      Se a ferramenta de ligação não estiver ativa, o clique apenas seleciona
      a ligação para inspeção no painel de propriedades.
    */
    if (bondToolActive) {
      changeBondStyle(bondId, selectedBondStyle);
    }
  }

  function handleBondToolChange(style: BondVisualStyle, order: BondOrder) {
    setSelectedBondStyle(style);
    setSelectedBondOrder(order);
  }

  function applyBondStyleToSelected() {
    if (!selectedBondId) return;

    changeBondStyle(selectedBondId, selectedBondStyle);
  }

  async function applyAutomaticFormalChargesAndLonePairs() {
    if (!internalMolecule) return;

    const preparedMolecule = recalculateAtomDegrees(
      applyFormalChargeDistributionToMolecule(internalMolecule)
    );

    const localGraph = internalMoleculeToGraph(preparedMolecule);
    const validationErrors = validateMoleculeForRdkit(preparedMolecule);

    setMolecule(createLocalRDKitWrapper(preparedMolecule, currentSmiles));
    setGraph(localGraph);

    if (preparedMolecule.validation_state.errors.length > 0 || validationErrors.length > 0) {
      setSyncError(
        [
          ...preparedMolecule.validation_state.errors,
          ...validationErrors,
        ]
          .filter(Boolean)
          .join(" | ")
      );
      return;
    }

    setSyncError("");

    try {
      const result = await graphToSmiles(localGraph);

      const refreshed = refreshInternalMetadata(
        preparedMolecule,
        result.canonical_smiles
      );

      setMolecule(createLocalRDKitWrapper(refreshed, result.canonical_smiles));
      setGraph(internalMoleculeToGraph(refreshed));
      setCurrentSmiles(result.canonical_smiles);
      setImportValue(result.canonical_smiles);
    } catch (error) {
      setSyncError(
        error instanceof Error
          ? error.message
          : "As cargas formais foram aplicadas, mas o RDKit não validou o grafo."
      );
    }
  }

  async function optimizeCurrentStructure() {
    if (!internalMolecule || optimizing2D) return;

        const validationErrors = validateMoleculeForRdkit(internalMolecule);

    if (validationErrors.length > 0) {
      setSyncError(validationErrors.join(" | "));
      return;
    }

try {
      setOptimizing2D(true);
      setSyncError("");

      const optimizedMolecule = await optimizeMolecule2D({
        internalMolecule,
        graph: internalMoleculeToGraph(internalMolecule),
        smiles: currentSmiles,
      });

      const optimizedInternal = sanitizeInternalMolecule(
        mergeEditorChemistryAfterRdkit(
          internalMolecule,
          optimizedMolecule.internal_molecule
        )
      );

      const mergedMolecule = {
        ...optimizedMolecule,
        internal_molecule: optimizedInternal,
      };

      setMolecule(mergedMolecule);

      setGraph(rdkitMoleculeToEditableGraph(mergedMolecule));
      setCurrentSmiles(optimizedMolecule.canonical_smiles);
      setImportValue(optimizedMolecule.canonical_smiles);
      setSelectedTarget(null);
      setPendingBondAtomId(null);
      setViewport(initialViewport);
    } catch (error) {
      setSyncError(
        error instanceof Error
          ? error.message
          : "Erro ao otimizar geometria 2D com RDKit."
      );
    } finally {
      setOptimizing2D(false);
    }
  }

  async function toggleHydrogens() {
    if (!internalMolecule || optimizing2D) return;

    const nextShowExplicitHs = !showExplicitHs;

    try {
      setOptimizing2D(true);
      setSyncError("");

      const updatedMolecule = await toggleExplicitHydrogens2D({
        internalMolecule,
        graph: internalMoleculeToGraph(internalMolecule),
        smiles: currentSmiles,
        explicitHs: nextShowExplicitHs,
      });

      const updatedInternal = sanitizeInternalMolecule(
        mergeEditorChemistryAfterRdkit(
          internalMolecule,
          updatedMolecule.internal_molecule
        )
      );

      const mergedMolecule = {
        ...updatedMolecule,
        internal_molecule: updatedInternal,
      };

      setMolecule(mergedMolecule);

      setGraph(rdkitMoleculeToEditableGraph(mergedMolecule));
      setCurrentSmiles(updatedMolecule.canonical_smiles);
      setImportValue(updatedMolecule.canonical_smiles);
      setSelectedTarget(null);
      setPendingBondAtomId(null);
      setViewport(initialViewport);
      setShowExplicitHs(nextShowExplicitHs);
    } catch (error) {
      setSyncError(
        error instanceof Error
          ? error.message
          : "Erro ao alternar hidrogênios explícitos com RDKit."
      );
    } finally {
      setOptimizing2D(false);
    }
  }

  async function analyzeCurrentSmiles() {
    if (!currentSmiles) return;

    try {
      setSyncError("");

      const loadedMolecule = await parseSmilesTo2D(currentSmiles);
      const loadedGraph = rdkitMoleculeToEditableGraph(loadedMolecule);

      setMolecule({
        ...loadedMolecule,
        internal_molecule: sanitizeInternalMolecule(loadedMolecule.internal_molecule),
      });
      setGraph(loadedGraph);
      setCurrentSmiles(loadedMolecule.canonical_smiles);
      setImportValue(loadedMolecule.canonical_smiles);
      setSelectedTarget(null);
      setPendingBondAtomId(null);
      setShowExplicitHs(false);
    } catch (error) {
      setSyncError(
        error instanceof Error ? error.message : "Erro ao analisar estrutura."
      );
    }
  }

  function updateConcentration(id: string, concentration: string) {
    setSavedMolecules((current) =>
      current.map((moleculeItem) =>
        moleculeItem.id === id
          ? {
              ...moleculeItem,
              concentration,
            }
          : moleculeItem
      )
    );
  }

  function updateUnit(id: string, unit: SavedMolecule["unit"]) {
    setSavedMolecules((current) =>
      current.map((moleculeItem) =>
        moleculeItem.id === id
          ? {
              ...moleculeItem,
              unit,
            }
          : moleculeItem
      )
    );
  }

  async function loadFastMolecule(smiles: string) {
    try {
      setLoadingImport(true);
      setSyncError("");

      const loadedMolecule = await parseSmilesTo2D(smiles);
      const loadedGraph = rdkitMoleculeToEditableGraph(loadedMolecule);

      setMolecule({
        ...loadedMolecule,
        internal_molecule: sanitizeInternalMolecule(loadedMolecule.internal_molecule),
      });
      setGraph(loadedGraph);
      setCurrentSmiles(loadedMolecule.canonical_smiles);
      setImportValue(loadedMolecule.canonical_smiles);
      setSelectedTarget(null);
      setPendingBondAtomId(null);
      setViewport(initialViewport);
      setShowExplicitHs(false);
    } catch (error) {
      setSyncError(
        error instanceof Error
          ? error.message
          : "Erro ao carregar molécula rápida via SMILES."
      );
    } finally {
      setLoadingImport(false);
    }
  }

  async function openSavedMolecule(smiles: string) {
    try {
      setSyncError("");

      const loadedMolecule = await parseSmilesTo2D(smiles);
      const loadedGraph = rdkitMoleculeToEditableGraph(loadedMolecule);

      setMolecule({
        ...loadedMolecule,
        internal_molecule: sanitizeInternalMolecule(loadedMolecule.internal_molecule),
      });
      setGraph(loadedGraph);
      setCurrentSmiles(loadedMolecule.canonical_smiles);
      setImportValue(loadedMolecule.canonical_smiles);
      setSelectedTarget(null);
      setPendingBondAtomId(null);
      setShowExplicitHs(false);
    } catch (error) {
      setSyncError(
        error instanceof Error ? error.message : "Erro ao abrir molécula."
      );
    }
  }

  function saveCurrentMolecule() {
    if (!currentSmiles) return;

    const nextMolecule: SavedMolecule = {
      id: createId("saved"),
      name: molecule?.formula ? `Molécula ${molecule.formula}` : "Molécula 2D",
      formula: molecule?.formula ?? "—",
      smiles: currentSmiles,
      molarMass: molecule?.molecular_weight
        ? molecule.molecular_weight.toFixed(3)
        : "—",
      status: syncError ? "Aviso" : "Otimizada",
      concentration: "1",
      unit: "mmol/L",
    };

    setSavedMolecules((current) => [nextMolecule, ...current]);
  }

  function zoomViewportAtCenter(nextZoom: number) {
    const viewCenter = {
      x: 900 / 2,
      y: 520 / 2,
    };

    setViewport((current) => {
      const baseCenterBeforeZoom = {
        x: (viewCenter.x - current.panX) / current.zoom,
        y: (viewCenter.y - current.panY) / current.zoom,
      };

      return {
        zoom: nextZoom,
        panX: viewCenter.x - baseCenterBeforeZoom.x * nextZoom,
        panY: viewCenter.y - baseCenterBeforeZoom.y * nextZoom,
      };
    });
  }

  function zoomIn() {
    zoomViewportAtCenter(
      Math.min(3, Number((viewport.zoom * 1.12).toFixed(3)))
    );
  }

  function zoomOut() {
    zoomViewportAtCenter(
      Math.max(0.45, Number((viewport.zoom / 1.12).toFixed(3)))
    );
  }

  function resetViewport() {
    setViewport(initialViewport);
  }

  const canvasSubtitle = currentSmiles
    ? `SMILES atual: ${currentSmiles}`
    : "Use a barra de ferramentas para adicionar átomos, ligações, radicais, pares livres e cargas.";


  useEffect(() => {
    const handleLeftPageCommand = (event: Event) => {
      const command = (event as CustomEvent).detail as
        | {
            type: "toggleAtomIndices";
          }
        | {
            type: "changeAtomCharge";
            atomId: string;
            charge: number;
          }
        | {
            type: "toggleRadical";
            atomId: string;
          }
        | {
            type: "toggleLonePair";
            atomId: string;
          }
        | {
            type: "deleteAtom";
            atomId: string;
          }
        | {
            type: "changeBondStyle";
            bondId: string;
            style: BondVisualStyle;
          }
        | {
            type: "deleteBond";
            bondId: string;
          };

      if (!command || typeof command !== "object") return;

      if (command.type === "toggleAtomIndices") {
        setShowAtomIndices((current) => !current);
        return;
      }

      if (command.type === "changeAtomCharge") {
        changeAtomCharge(command.atomId, command.charge);
        return;
      }

      if (command.type === "toggleRadical") {
        toggleRadical(command.atomId);
        return;
      }

      if (command.type === "toggleLonePair") {
        toggleLonePair(command.atomId);
        return;
      }

      if (command.type === "deleteAtom") {
        deleteAtom(command.atomId);
        return;
      }

      if (command.type === "changeBondStyle") {
        changeBondStyle(command.bondId, command.style);
        return;
      }

      if (command.type === "deleteBond") {
        deleteBond(command.bondId);
      }
    };

    window.addEventListener(LEFTPAGE_COMMAND_EVENT, handleLeftPageCommand);

    return () => {
      window.removeEventListener(LEFTPAGE_COMMAND_EVENT, handleLeftPageCommand);
    };
  });

  const anyActiveTool = hasAnyActiveTool(tools);

  return (
    <div className="page-2d-container">
      <div className="import-bar">
        <div className="import-title">
          <strong>Editor molecular 2D</strong>
          <span>SMILES / RDKit / edição visual do InternalMoleculeModel</span>
        </div>

        <select
          className="import-select"
          value={format}
          onChange={(event) => setFormat(event.target.value as ImportFormat)}
        >
          <option>SMILES</option>
          <option>InChI</option>
          <option>InChIKey</option>
          <option>Auto</option>
        </select>

        <input
          type="text"
          placeholder={placeholder}
          className="import-input"
          value={importValue}
          onChange={(event) => setImportValue(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              void handleGenerate2D();
            }
          }}
        />

        <button
          className="btn-generate"
          type="button"
          onClick={() => void handleGenerate2D()}
          disabled={loadingImport}
        >
          {loadingImport ? "Gerando..." : "Gerar 2D"}
        </button>

        <button
          className="btn-secondary"
          type="button"
          onClick={() => void analyzeCurrentSmiles()}
        >
          Analisar
        </button>
      </div>

      <div className="toolbar-area">
        <ToolsBar
          quickElements={quickElements}
          selectedElement={selectedElement}
          showPeriodicTable={showPeriodicTable}
          defaultFormalCharge={defaultFormalCharge}
          moveAtomToolActive={moveAtomToolActive}
          panToolActive={panToolActive}
          atomToolActive={atomToolActive}
          atomBondToolActive={atomBondToolActive}
          radicalToolActive={radicalToolActive}
          lonePairToolActive={lonePairToolActive}
          chargeToolActive={chargeToolActive}
          bondToolActive={bondToolActive}
          deleteToolActive={deleteToolActive}
          selectedBondOrder={selectedBondOrder}
          selectedBondStyle={selectedBondStyle}
          selectedBondId={selectedBondId}
          pendingBondAtomId={pendingBondAtomId}
          showExplicitHs={showExplicitHs}
          onSelectElement={(element) => {
            const normalizedElement = normalizeElementSymbol(element);

            if (!isKnownElementSymbol(normalizedElement)) {
              setSyncError(`Elemento químico inválido ou não reconhecido: ${normalizedElement}.`);
              return;
            }

            setSelectedElement(normalizedElement);
            setSyncError("");
          }}
          onOpenPeriodicTable={() => setShowPeriodicTable(true)}
          onActivateMoveTool={() => setExclusiveTool("moveAtomToolActive")}
          onActivatePanTool={() => setExclusiveTool("panToolActive")}
          onToggleAtomTool={() => setExclusiveTool("atomToolActive")}
          onToggleAtomBondTool={() => setExclusiveTool("atomBondToolActive")}
          onToggleRadicalTool={() => setExclusiveTool("radicalToolActive")}
          onToggleLonePairTool={() => setExclusiveTool("lonePairToolActive")}
          onToggleChargeTool={() => setExclusiveTool("chargeToolActive")}
          onChangeFormalCharge={setDefaultFormalCharge}
          onToggleBondTool={() => setExclusiveTool("bondToolActive")}
          onToggleDeleteTool={() => setExclusiveTool("deleteToolActive")}
          onChangeBondTool={handleBondToolChange}
          onApplyBondStyleToSelected={applyBondStyleToSelected}
          onApplyFormalChemistry={() => void applyAutomaticFormalChargesAndLonePairs()}
          onClearCanvas={clearCanvas}
          onOptimizeStructure={() => void optimizeCurrentStructure()}
          onToggleHydrogens={() => void toggleHydrogens()}
          onLoadFastMolecule={(smiles) => void loadFastMolecule(smiles)}
        />

        <PeriodicTable
          isOpen={showPeriodicTable}
          selectedSymbols={quickElements}
          onSelectElement={handlePeriodicElementSelect}
          onClose={() => setShowPeriodicTable(false)}
          onClearSelectedElements={clearSelectedElementsBar}
        />
      </div>

      <section className="canvas-panel">
        <div className="canvas-wrapper">
          <Minimap
            molecule={internalMolecule}
            viewport={viewport}
            onViewportChange={setViewport}
            onResetViewport={resetViewport}
          />

          <div className="zoom-controls">
            <button onClick={zoomOut} type="button">
              −
            </button>

            <button onClick={zoomIn} type="button">
              +
            </button>

            <button onClick={resetViewport} type="button">
              Centralizar
            </button>
          </div>

          <div className="canvas-content">
            <div className="molecule-canvas-stage">
              <div className="molecule-canvas-info">
                <span className="selected-element-pill">
                  Elemento selecionado: {selectedElement || "nenhum"}
                  {anyActiveTool ? "" : " · modo neutro"}
                </span>

                <h2>Ambiente molecular 2D</h2>

                <p>{canvasSubtitle}</p>

                {syncError && (
                  <div className="rdkit-compact-error">{syncError}</div>
                )}
              </div>

              <div className="molecule-canvas-body">
                <Molecule2DViewer
                  molecule={internalMolecule}
                  selectedTarget={selectedTarget}
                  viewport={viewport}
                  tools={tools}
                  selectedElement={selectedElement}
                  showAtomIndices={showAtomIndices}
                  selectedBondOrder={selectedBondOrder}
                  defaultFormalCharge={defaultFormalCharge}
                  pendingBondAtomId={pendingBondAtomId}
                  onCanvasAddAtom={addAtomAtPosition}
                  onMoveAtom={moveAtom}
                  onViewportChange={setViewport}
                  onSelectAtom={handleSelectAtom}
                  onSelectBond={handleSelectBond}
                  onExtendAtomWithBond={extendAtomWithBond}
                  onToggleRadical={toggleRadical}
                  onClearRadical={clearRadical}
                  onToggleLonePair={toggleLonePair}
                  onClearLonePair={clearLonePair}
                  onSetAtomCharge={changeAtomCharge}
                  onDeleteAtom={deleteAtom}
                  onDeleteBond={deleteBond}
                />
              </div>

              {optimizing2D && (
                <div className="optimization-processing-overlay">
                  <div className="optimization-card">
                    <strong>Otimizando geometria 2D com RDKit</strong>
                    <span>
                      Validando valências, recalculando coordenadas e preparando
                      camadas de renderização.
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

      </section>

      <Transfer2DTo3D
        savedMolecules={savedMolecules}
        currentSmiles={currentSmiles}
        currentFormula={
          molecule?.formula ??
          internalMolecule?.metadata.formula ??
          ""
        }
        currentMolarMass={
          molecule?.molecular_weight ??
          internalMolecule?.metadata.molecular_weight ??
          null
        }
        currentStatus={syncError ? "Aviso" : currentSmiles ? "Otimizada" : "Aguardando"}
        onSaveCurrentMolecule={saveCurrentMolecule}
        onOpenSavedMolecule={(smiles) => void openSavedMolecule(smiles)}
        onUpdateConcentration={updateConcentration}
        onUpdateUnit={updateUnit}
      />
    </div>
  );
}

export default Page2D;


