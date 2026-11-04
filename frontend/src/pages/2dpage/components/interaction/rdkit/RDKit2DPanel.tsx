import { useState } from "react";

import type {
  EditableMoleculeGraph,
  RDKitMolecule2D,
} from "../../../type/rdkit2d.types";

import {
  parseSmilesTo2D,
  rdkitMoleculeToEditableGraph,
} from "./rdkitApi";

type Props = {
  currentSmiles: string;
  onMoleculeLoaded: (
    molecule: RDKitMolecule2D,
    graph: EditableMoleculeGraph
  ) => void;
};

export function RDKit2DPanel({ currentSmiles, onMoleculeLoaded }: Props) {
  const [input, setInput] = useState("C[C@H](O)Cl");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleParse() {
    try {
      setLoading(true);
      setError("");

      const molecule = await parseSmilesTo2D(input);
      const graph = rdkitMoleculeToEditableGraph(molecule);

      onMoleculeLoaded(molecule, graph);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Erro inesperado ao interpretar SMILES."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="rdkit-panel">
      <header className="rdkit-panel-header">
        <div>
          <strong>RDKit 2D</strong>
          <span>Entrada química, validação e geração de molécula 2D.</span>
        </div>
      </header>

      <div className="rdkit-input-row">
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Digite um SMILES. Ex: CCO, c1ccccc1, C[C@H](O)Cl"
        />

        <button type="button" onClick={handleParse} disabled={loading}>
          {loading ? "Lendo..." : "Ler SMILES"}
        </button>
      </div>

      {error && <div className="rdkit-error">{error}</div>}

      <div className="rdkit-current-smiles">
        <span>SMILES atual:</span>
        <code>{currentSmiles || "vazio"}</code>
      </div>
    </section>
  );
}

export default RDKit2DPanel;

