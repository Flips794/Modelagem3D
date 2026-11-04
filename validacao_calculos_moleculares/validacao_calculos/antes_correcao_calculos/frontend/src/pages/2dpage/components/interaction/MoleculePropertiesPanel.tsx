import { useEffect, useMemo, useState } from "react";

import type {
  BondVisualStyle,
  InternalAtomModel,
  InternalBondModel,
  InternalMoleculeModel,
  SelectedMoleculeTarget,
} from "../../type/rdkit2d.types";

type InspectorTab = "molecule" | "atoms" | "bonds";

type MoleculePropertiesPanelProps = {
  molecule: InternalMoleculeModel | null;
  selectedTarget: SelectedMoleculeTarget;
  selectedBondStyle: BondVisualStyle;
  showAtomIndices: boolean;
  onToggleAtomIndices: () => void;
  onChangeAtomCharge: (atomId: string, nextCharge: number) => void;
  onToggleRadical: (atomId: string) => void;
  onToggleLonePair: (atomId: string) => void;
  onDeleteAtom: (atomId: string) => void;
  onChangeBondStyle: (bondId: string, style: BondVisualStyle) => void;
  onDeleteBond: (bondId: string) => void;
};

function findSelectedAtom(
  molecule: InternalMoleculeModel,
  selectedTarget: SelectedMoleculeTarget
): InternalAtomModel | null {
  if (!selectedTarget || selectedTarget.kind !== "atom") return null;

  return molecule.atoms.find((atom) => atom.id === selectedTarget.id) ?? null;
}

function findSelectedBond(
  molecule: InternalMoleculeModel,
  selectedTarget: SelectedMoleculeTarget
): InternalBondModel | null {
  if (!selectedTarget || selectedTarget.kind !== "bond") return null;

  return molecule.bonds.find((bond) => bond.id === selectedTarget.id) ?? null;
}

function getAtomDisplayIndex(atom: InternalAtomModel) {
  return atom.rdkit_index + 1;
}

function getTabFromTarget(selectedTarget: SelectedMoleculeTarget): InspectorTab {
  if (selectedTarget?.kind === "atom") return "atoms";
  if (selectedTarget?.kind === "bond") return "bonds";

  return "molecule";
}

function shortId(id: string) {
  if (id.length <= 12) return id;

  return `${id.slice(0, 8)}…${id.slice(-4)}`;
}

export function MoleculePropertiesPanel({
  molecule,
  selectedTarget,
  selectedBondStyle,
  showAtomIndices,
  onToggleAtomIndices,
  onChangeAtomCharge,
  onToggleRadical,
  onToggleLonePair,
  onDeleteAtom,
  onChangeBondStyle,
  onDeleteBond,
}: MoleculePropertiesPanelProps) {
  const [activeTab, setActiveTab] = useState<InspectorTab>(
    getTabFromTarget(selectedTarget)
  );

  useEffect(() => {
    setActiveTab(getTabFromTarget(selectedTarget));
  }, [selectedTarget]);

  const atom = useMemo(() => {
    if (!molecule) return null;

    return findSelectedAtom(molecule, selectedTarget);
  }, [molecule, selectedTarget]);

  const bond = useMemo(() => {
    if (!molecule) return null;

    return findSelectedBond(molecule, selectedTarget);
  }, [molecule, selectedTarget]);

  if (!molecule) {
    return (
      <aside className="molecule-properties-panel">
        <header className="inspector-header">
          <div className="inspector-tabs" role="tablist" aria-label="Inspetor molecular">
            <button className="inspector-tab active" type="button">
              ⌬ Molécula
            </button>

            <button className="inspector-tab" type="button" disabled>
              🔴 Átomos
            </button>

            <button className="inspector-tab" type="button" disabled>
              🔗 Ligações
            </button>
          </div>

          <button
            className={`atom-index-toggle ${showAtomIndices ? "active" : ""}`}
            type="button"
            onClick={onToggleAtomIndices}
            title="Mostrar/ocultar numeração dos átomos no canvas"
          >
            # Numeração: {showAtomIndices ? "ON" : "OFF"}
          </button>
        </header>

        <div className="property-empty">Nenhuma molécula carregada.</div>
      </aside>
    );
  }

  return (
    <aside className="molecule-properties-panel">
      <header className="inspector-header">
        <div className="inspector-tabs" role="tablist" aria-label="Inspetor molecular">
          <button
            className={`inspector-tab ${activeTab === "molecule" ? "active" : ""}`}
            type="button"
            onClick={() => setActiveTab("molecule")}
          >
            ⌬ Molécula
          </button>

          <button
            className={`inspector-tab ${activeTab === "atoms" ? "active" : ""}`}
            type="button"
            onClick={() => setActiveTab("atoms")}
          >
            🔴 Átomos
          </button>

          <button
            className={`inspector-tab ${activeTab === "bonds" ? "active" : ""}`}
            type="button"
            onClick={() => setActiveTab("bonds")}
          >
            🔗 Ligações
          </button>
        </div>

        <button
          className={`atom-index-toggle ${showAtomIndices ? "active" : ""}`}
          type="button"
          onClick={onToggleAtomIndices}
          title="Mostrar/ocultar numeração dos átomos no canvas"
        >
          # Numeração: {showAtomIndices ? "ON" : "OFF"}
        </button>
      </header>

      {activeTab === "molecule" && (
        <div className="property-grid">
          <h4>Molécula</h4>

          <span>SMILES canônico</span>
          <strong>{molecule.metadata.canonical_smiles || "—"}</strong>

          <span>Fórmula</span>
          <strong>{molecule.metadata.formula || "—"}</strong>

          <span>Massa molecular</span>
          <strong>
            {Number.isFinite(molecule.metadata.molecular_weight)
              ? `${molecule.metadata.molecular_weight.toFixed(3)} g/mol`
              : "—"}
          </strong>

          <span>Massa exata</span>
          <strong>
            {Number.isFinite(molecule.metadata.exact_molecular_weight)
              ? molecule.metadata.exact_molecular_weight.toFixed(5)
              : "—"}
          </strong>

          <span>Átomos</span>
          <strong>{molecule.metadata.atom_count}</strong>

          <span>Ligações</span>
          <strong>{molecule.metadata.bond_count}</strong>

          <span>Fonte</span>
          <strong>{molecule.metadata.source}</strong>

          <span>Formato</span>
          <strong>{molecule.metadata.source_format}</strong>

          <span>Versão do modelo</span>
          <strong>{molecule.model_version}</strong>

          <span>Estado</span>
          <strong>
            {molecule.validation_state.is_valid ? "válida" : "com alerta"}
          </strong>
        </div>
      )}

      {activeTab === "atoms" && (
        <>
          {!atom && (
            <div className="property-empty">
              Selecione um átomo no ambiente 2D para ver os dados completos.
            </div>
          )}

          {atom && (
            <div className="property-grid">
              <h4>Átomo selecionado</h4>

              <span>Número visual</span>
              <strong>#{getAtomDisplayIndex(atom)}</strong>

              <span>ID</span>
              <strong>{atom.id}</strong>

              <span>Elemento</span>
              <strong>{atom.element}</strong>

              <span>Número atômico</span>
              <strong>{atom.atomic_number}</strong>

              <span>Índice RDKit</span>
              <strong>{atom.rdkit_index}</strong>

              <span>Carga formal</span>
              <strong>{atom.formal_charge}</strong>

              <span>Radicais</span>
              <strong>{atom.radical_count ?? 0}</strong>

              <span>Pares livres</span>
              <strong>{atom.lone_pair_count ?? 0}</strong>

              <span>Aromático</span>
              <strong>{atom.is_aromatic ? "sim" : "não"}</strong>

              <span>Hibridização</span>
              <strong>{atom.hybridization}</strong>

              <span>Hidrogênios totais</span>
              <strong>{atom.total_hydrogens}</strong>

              <span>Valência total</span>
              <strong>{atom.total_valence ?? "—"}</strong>

              <span>Grau</span>
              <strong>{atom.degree}</strong>

              <span>Posição 2D</span>
              <strong>
                x: {atom.position_2d.x.toFixed(2)} · y:{" "}
                {atom.position_2d.y.toFixed(2)}
              </strong>

              <div className="property-actions">
                <button
                  type="button"
                  onClick={() => onChangeAtomCharge(atom.id, atom.formal_charge - 1)}
                >
                  Carga −
                </button>

                <button
                  type="button"
                  onClick={() => onChangeAtomCharge(atom.id, atom.formal_charge + 1)}
                >
                  Carga +
                </button>

                <button type="button" onClick={() => onToggleRadical(atom.id)}>
                  Radical
                </button>

                <button type="button" onClick={() => onToggleLonePair(atom.id)}>
                  Par livre
                </button>

                <button
                  className="danger"
                  type="button"
                  onClick={() => onDeleteAtom(atom.id)}
                >
                  Deletar átomo
                </button>
              </div>
            </div>
          )}

          <div className="property-list">
            <h4>Lista de átomos</h4>

            {molecule.atoms.length === 0 && (
              <span className="property-muted">Nenhum átomo no ambiente.</span>
            )}

            {molecule.atoms.map((item) => (
              <div className="property-list-row" key={item.id}>
                <strong>#{getAtomDisplayIndex(item)} · {item.element}</strong>
                <span>
                  RDKit {item.rdkit_index} · carga {item.formal_charge} ·{" "}
                  {shortId(item.id)}
                </span>
              </div>
            ))}
          </div>
        </>
      )}

      {activeTab === "bonds" && (
        <>
          {!bond && (
            <div className="property-empty">
              Selecione uma ligação no ambiente 2D para ver os dados completos.
            </div>
          )}

          {bond && (
            <div className="property-grid">
              <h4>Ligação selecionada</h4>

              <span>ID</span>
              <strong>{bond.id}</strong>

              <span>Índice RDKit</span>
              <strong>{bond.rdkit_index}</strong>

              <span>Átomo A</span>
              <strong>
                #{bond.atom_a_rdkit_index + 1} / RDKit {bond.atom_a_rdkit_index}
              </strong>

              <span>Átomo B</span>
              <strong>
                #{bond.atom_b_rdkit_index + 1} / RDKit {bond.atom_b_rdkit_index}
              </strong>

              <span>Ordem</span>
              <strong>{bond.order}</strong>

              <span>Tipo visual</span>
              <strong>{bond.visual_style ?? "auto"}</strong>

              <span>Tipo químico</span>
              <strong>{bond.bond_type}</strong>

              <span>Aromática</span>
              <strong>{bond.is_aromatic ? "sim" : "não"}</strong>

              <span>Estereoquímica</span>
              <strong>{bond.stereo}</strong>

              <span>Direção</span>
              <strong>{bond.direction}</strong>

              <div className="property-actions">
                <button
                  type="button"
                  onClick={() => onChangeBondStyle(bond.id, selectedBondStyle)}
                >
                  Aplicar ligação ativa
                </button>

                <button
                  className="danger"
                  type="button"
                  onClick={() => onDeleteBond(bond.id)}
                >
                  Deletar ligação
                </button>
              </div>
            </div>
          )}

          <div className="property-list">
            <h4>Lista de ligações</h4>

            {molecule.bonds.length === 0 && (
              <span className="property-muted">Nenhuma ligação no ambiente.</span>
            )}

            {molecule.bonds.map((item) => (
              <div className="property-list-row" key={item.id}>
                <strong>
                  #{item.atom_a_rdkit_index + 1} — #{item.atom_b_rdkit_index + 1}
                </strong>
                <span>
                  ordem {item.order} · {item.visual_style ?? item.bond_type} ·{" "}
                  {shortId(item.id)}
                </span>
              </div>
            ))}
          </div>
        </>
      )}

      <footer className="molecule-global-summary">
        <span>Fórmula: {molecule.metadata.formula || "—"}</span>
        <span>
          Massa: {molecule.metadata.molecular_weight.toFixed(3)} g/mol
        </span>
        <span>
          {molecule.metadata.atom_count} átomos ·{" "}
          {molecule.metadata.bond_count} ligações
        </span>
      </footer>
    </aside>
  );
}

export default MoleculePropertiesPanel;
