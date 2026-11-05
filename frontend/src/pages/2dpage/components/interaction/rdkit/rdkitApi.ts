import type {
  EditableMoleculeGraph,
  GraphToSmilesResult,
  Hydrogens2DInput,
  InternalMoleculeModel,
  Optimize2DInput,
  RDKitMolecule2D,
} from "../../../type/rdkit2d.types";
import { API_BASE_URL } from "../../../../../config/apiBaseUrl";

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;

    try {
      const data = await response.json();
      detail = data.detail ?? data.message ?? JSON.stringify(data);
    } catch {
      detail = await response.text();
    }

    throw new Error(detail || `Erro na requisição ${path}`);
  }

  return response.json() as Promise<T>;
}

async function postJsonWithFallback<T>(
  paths: string[],
  body: unknown
): Promise<T> {
  const errors: string[] = [];

  for (const path of paths) {
    try {
      return await postJson<T>(path, body);
    } catch (error) {
      errors.push(
        `${path}: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  throw new Error(errors.join(" | "));
}

export async function parseSmilesTo2D(
  identifier: string
): Promise<RDKitMolecule2D> {
  return postJsonWithFallback<RDKitMolecule2D>(
    [
      "/chemistry/rdkit/parse-2d",
      "/chemistry/parse-2d",
      "/rdkit/parse-2d",
      "/chemistry/rdkit_engine/parse-2d",
    ],
    {
      identifier,
      input_type: "SMILES",
      width: 900,
      height: 520,
    }
  );
}

export async function graphToSmiles(
  graph: EditableMoleculeGraph
): Promise<GraphToSmilesResult> {
  return postJsonWithFallback<GraphToSmilesResult>(
    [
      "/chemistry/rdkit/graph-to-smiles",
      "/chemistry/graph-to-smiles",
      "/rdkit/graph-to-smiles",
      "/chemistry/rdkit_engine/graph-to-smiles",
    ],
    graph
  );
}

export async function optimizeMolecule2D({
  internalMolecule,
  graph,
  smiles,
}: Optimize2DInput): Promise<RDKitMolecule2D> {
  return postJsonWithFallback<RDKitMolecule2D>(
    [
      "/chemistry/rdkit/optimize-2d",
      "/chemistry/optimize-2d",
      "/rdkit/optimize-2d",
      "/chemistry/rdkit_engine/optimize-2d",
    ],
    {
      internal_molecule: internalMolecule,
      graph,
      smiles: smiles || internalMolecule.metadata.canonical_smiles || null,
      width: 900,
      height: 520,
    }
  );
}

export async function toggleExplicitHydrogens2D({
  internalMolecule,
  graph,
  smiles,
  explicitHs,
}: Hydrogens2DInput): Promise<RDKitMolecule2D> {
  return postJsonWithFallback<RDKitMolecule2D>(
    [
      "/chemistry/rdkit/hydrogens-2d",
      "/chemistry/hydrogens-2d",
      "/rdkit/hydrogens-2d",
      "/chemistry/rdkit_engine/hydrogens-2d",
    ],
    {
      internal_molecule: internalMolecule,
      graph,
      smiles: smiles || internalMolecule.metadata.canonical_smiles || null,
      explicit_hs: explicitHs,
      width: 900,
      height: 520,
    }
  );
}

export function rdkitMoleculeToEditableGraph(
  molecule: RDKitMolecule2D
): EditableMoleculeGraph {
  if (molecule.internal_molecule) {
    return {
      atoms: molecule.internal_molecule.atoms.map((atom) => ({
        index: atom.rdkit_index,
        symbol: atom.element,
        formal_charge: atom.formal_charge,
        is_aromatic: atom.is_aromatic,
        x: atom.position_2d.x,
        y: atom.position_2d.y,
      })),
      bonds: molecule.internal_molecule.bonds.map((bond) => ({
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
        bond_role: bond.bond_role,
      })),
    };
  }

  return {
    atoms:
      molecule.atoms?.map((atom) => ({
        index: atom.index,
        symbol: atom.symbol,
        formal_charge: atom.formal_charge,
        is_aromatic: atom.is_aromatic,
        x: atom.x,
        y: atom.y,
      })) ?? [],
    bonds:
      molecule.bonds?.map((bond) => ({
        begin_atom_index: bond.begin_atom_index,
        end_atom_index: bond.end_atom_index,
        order:
          bond.visual_style === "single-resonance"
            ? 1
            : bond.visual_style === "double-resonance"
              ? 2
              : bond.order,
        is_aromatic: bond.visual_style === "aromatic" || bond.is_aromatic,
        visual_style: bond.visual_style,
        bond_role: bond.bond_role,
      })) ?? [],
  };
}

export function getCurrentCanonicalSmiles(
  molecule: InternalMoleculeModel | RDKitMolecule2D | null
): string {
  if (!molecule) return "";

  if ("canonical_smiles" in molecule) {
    return molecule.canonical_smiles;
  }

  return molecule.metadata.canonical_smiles;
}


