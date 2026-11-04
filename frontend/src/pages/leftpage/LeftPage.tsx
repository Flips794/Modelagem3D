import { useEffect, useMemo, useState } from "react";

import type {
  BondVisualStyle,
  InternalAtomModel,
  InternalBondModel,
  InternalMoleculeModel,
  SelectedMoleculeTarget,
} from "../2dpage/type/rdkit2d.types";

import ChemistryParametersPanel from "./components/ChemistryParametersPanel";

import "./Leftpage.css";

const LEFTPAGE_STATE_EVENT = "molecular-editor:leftpage-state";
const LEFTPAGE_COMMAND_EVENT = "molecular-editor:leftpage-command";
const LEFTPAGE_STORAGE_KEY = "molecular-editor:leftpage-state";

type LeftPageTab = "molecule" | "atoms" | "bonds";

type LeftPageSyncedState = {
  molecule: InternalMoleculeModel | null;
  selectedTarget: SelectedMoleculeTarget;
  selectedBondStyle: BondVisualStyle;
  showAtomIndices: boolean;
};

type LeftPageCommand =
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

type LeftPageProps = {
  molecule?: InternalMoleculeModel | null;
  selectedTarget?: SelectedMoleculeTarget;
  selectedBondStyle?: BondVisualStyle;
  showAtomIndices?: boolean;
  onToggleAtomIndices?: () => void;
  onChangeAtomCharge?: (atomId: string, charge: number) => void;
  onToggleRadical?: (atomId: string) => void;
  onToggleLonePair?: (atomId: string) => void;
  onDeleteAtom?: (atomId: string) => void;
  onChangeBondStyle?: (bondId: string, style: BondVisualStyle) => void;
  onDeleteBond?: (bondId: string) => void;
};

const emptyState: LeftPageSyncedState = {
  molecule: null,
  selectedTarget: null,
  selectedBondStyle: "single",
  showAtomIndices: false,
};

const bondStyleOptions: Array<{
  value: BondVisualStyle;
  label: string;
}> = [
  { value: "single", label: "Simples" },
  { value: "double", label: "Dupla" },
  { value: "triple", label: "Tripla" },
  { value: "wedge-filled", label: "Cunha cheia" },
  { value: "wedge-dashed", label: "Cunha aberta" },
  { value: "dashed", label: "Coordenação" },
  { value: "single-resonance", label: "Ressonância simples" },
  { value: "double-resonance", label: "Ressonância dupla" },
  { value: "aromatic", label: "Aromática" },
];

function readStoredState(): LeftPageSyncedState {
  try {
    const rawState = window.localStorage.getItem(LEFTPAGE_STORAGE_KEY);

    if (!rawState) return emptyState;

    const parsedState = JSON.parse(rawState) as Partial<LeftPageSyncedState>;

    return {
      molecule: parsedState.molecule ?? null,
      selectedTarget: parsedState.selectedTarget ?? null,
      selectedBondStyle: parsedState.selectedBondStyle ?? "single",
      showAtomIndices: parsedState.showAtomIndices ?? false,
    };
  } catch {
    return emptyState;
  }
}

function emitLeftPageCommand(command: LeftPageCommand) {
  window.dispatchEvent(
    new CustomEvent(LEFTPAGE_COMMAND_EVENT, {
      detail: command,
    })
  );
}

function getSelectedAtom(
  molecule: InternalMoleculeModel | null,
  selectedTarget: SelectedMoleculeTarget
) {
  if (!molecule || selectedTarget?.kind !== "atom") return null;

  return molecule.atoms.find((atom) => atom.id === selectedTarget.id) ?? null;
}

function getSelectedBond(
  molecule: InternalMoleculeModel | null,
  selectedTarget: SelectedMoleculeTarget
) {
  if (!molecule || selectedTarget?.kind !== "bond") return null;

  return molecule.bonds.find((bond) => bond.id === selectedTarget.id) ?? null;
}

function getAtomLabel(atom: InternalAtomModel) {
  return `${atom.element}${atom.rdkit_index + 1}`;
}

function getBondLabel(bond: InternalBondModel, molecule: InternalMoleculeModel) {
  const atomA = molecule.atoms.find((atom) => atom.id === bond.atom_a_id);
  const atomB = molecule.atoms.find((atom) => atom.id === bond.atom_b_id);

  return `${atomA ? getAtomLabel(atomA) : "A"} — ${
    atomB ? getAtomLabel(atomB) : "B"
  }`;
}

function AtomDetails({
  atom,
  onChangeAtomCharge,
  onToggleRadical,
  onToggleLonePair,
  onDeleteAtom,
}: {
  atom: InternalAtomModel | null;
  onChangeAtomCharge: (atomId: string, charge: number) => void;
  onToggleRadical: (atomId: string) => void;
  onToggleLonePair: (atomId: string) => void;
  onDeleteAtom: (atomId: string) => void;
}) {
  if (!atom) {
    return (
      <div className="leftpage-empty">
        Selecione um átomo no ambiente 2D para ver e editar propriedades.
      </div>
    );
  }

  return (
    <div className="leftpage-detail-card">
      <header>
        <strong>{getAtomLabel(atom)}</strong>
        <span>Índice RDKit: {atom.rdkit_index}</span>
      </header>

      <div className="leftpage-data-grid compact">
        <span>Elemento</span>
        <strong>{atom.element}</strong>

        <span>Número atômico</span>
        <strong>{atom.atomic_number}</strong>

        <span>Carga formal</span>
        <strong>{atom.formal_charge}</strong>

        <span>Hibridização</span>
        <strong>{atom.hybridization || "—"}</strong>

        <span>Aromático</span>
        <strong>{atom.is_aromatic ? "sim" : "não"}</strong>

        <span>H totais</span>
        <strong>{atom.total_hydrogens}</strong>

        <span>H implícitos</span>
        <strong>{atom.implicit_hydrogens}</strong>

        <span>H explícitos</span>
        <strong>{atom.explicit_hydrogens}</strong>

        <span>Pares livres</span>
        <strong>{atom.lone_pair_count ?? 0}</strong>

        <span>Radicais</span>
        <strong>{atom.radical_count ?? 0}</strong>
      </div>

      <div className="leftpage-action-row">
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
      </div>

      <div className="leftpage-action-row">
        <button type="button" onClick={() => onToggleRadical(atom.id)}>
          Radical
        </button>

        <button type="button" onClick={() => onToggleLonePair(atom.id)}>
          Par livre
        </button>
      </div>

      <button
        className="leftpage-danger-button"
        type="button"
        onClick={() => onDeleteAtom(atom.id)}
      >
        Apagar átomo
      </button>
    </div>
  );
}

function BondDetails({
  bond,
  molecule,
  selectedBondStyle,
  onChangeBondStyle,
  onDeleteBond,
}: {
  bond: InternalBondModel | null;
  molecule: InternalMoleculeModel | null;
  selectedBondStyle: BondVisualStyle;
  onChangeBondStyle: (bondId: string, style: BondVisualStyle) => void;
  onDeleteBond: (bondId: string) => void;
}) {
  if (!bond || !molecule) {
    return (
      <div className="leftpage-empty">
        Selecione uma ligação no ambiente 2D para ver e editar propriedades.
      </div>
    );
  }

  return (
    <div className="leftpage-detail-card">
      <header>
        <strong>{getBondLabel(bond, molecule)}</strong>
        <span>Índice RDKit: {bond.rdkit_index}</span>
      </header>

      <div className="leftpage-data-grid compact">
        <span>Ordem</span>
        <strong>{bond.order}</strong>

        <span>Tipo</span>
        <strong>{bond.bond_type}</strong>

        <span>Estilo visual</span>
        <strong>{bond.visual_style || "—"}</strong>

        <span>Papel químico</span>
        <strong>{bond.bond_role || "—"}</strong>

        <span>Aromática</span>
        <strong>{bond.is_aromatic ? "sim" : "não"}</strong>

        <span>Conjugada</span>
        <strong>{bond.is_conjugated ? "sim" : "não"}</strong>

        <span>Estereo</span>
        <strong>{bond.stereo_visual}</strong>

        <span>Direção</span>
        <strong>{bond.direction}</strong>
      </div>

      <label className="leftpage-field">
        <span>Trocar estilo</span>
        <select
          value={bond.visual_style ?? selectedBondStyle}
          onChange={(event) =>
            onChangeBondStyle(bond.id, event.target.value as BondVisualStyle)
          }
        >
          {bondStyleOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>

      <button
        className="leftpage-danger-button"
        type="button"
        onClick={() => onDeleteBond(bond.id)}
      >
        Apagar ligação
      </button>
    </div>
  );
}

function AtomList({ molecule }: { molecule: InternalMoleculeModel | null }) {
  if (!molecule || molecule.atoms.length === 0) {
    return <div className="leftpage-empty">Nenhum átomo no ambiente 2D.</div>;
  }

  return (
    <div className="leftpage-list">
      {molecule.atoms.map((atom) => (
        <article key={atom.id} className="leftpage-list-row">
          <strong>{getAtomLabel(atom)}</strong>
          <span>
            carga {atom.formal_charge} · H {atom.total_hydrogens} · pares{" "}
            {atom.lone_pair_count ?? 0}
          </span>
        </article>
      ))}
    </div>
  );
}

function BondList({ molecule }: { molecule: InternalMoleculeModel | null }) {
  if (!molecule || molecule.bonds.length === 0) {
    return <div className="leftpage-empty">Nenhuma ligação no ambiente 2D.</div>;
  }

  return (
    <div className="leftpage-list">
      {molecule.bonds.map((bond) => (
        <article key={bond.id} className="leftpage-list-row">
          <strong>{getBondLabel(bond, molecule)}</strong>
          <span>
            ordem {bond.order} · {bond.visual_style || bond.bond_type}
          </span>
        </article>
      ))}
    </div>
  );
}

export function LeftPage({
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
}: LeftPageProps = {}) {
  const [activeTab, setActiveTab] = useState<LeftPageTab>("molecule");
  const [syncedState, setSyncedState] = useState<LeftPageSyncedState>(() =>
    typeof window === "undefined" ? emptyState : readStoredState()
  );

  useEffect(() => {
    const handleLeftPageState = (event: Event) => {
      const nextState = (event as CustomEvent).detail as Partial<LeftPageSyncedState>;

      setSyncedState({
        molecule: nextState.molecule ?? null,
        selectedTarget: nextState.selectedTarget ?? null,
        selectedBondStyle: nextState.selectedBondStyle ?? "single",
        showAtomIndices: nextState.showAtomIndices ?? false,
      });
    };

    window.addEventListener(LEFTPAGE_STATE_EVENT, handleLeftPageState);

    setSyncedState(readStoredState());

    return () => {
      window.removeEventListener(LEFTPAGE_STATE_EVENT, handleLeftPageState);
    };
  }, []);

  const effectiveMolecule =
    molecule !== undefined ? molecule : syncedState.molecule;
  const effectiveSelectedTarget =
    selectedTarget !== undefined ? selectedTarget : syncedState.selectedTarget;
  const effectiveSelectedBondStyle =
    selectedBondStyle !== undefined
      ? selectedBondStyle
      : syncedState.selectedBondStyle;
  const effectiveShowAtomIndices =
    showAtomIndices !== undefined
      ? showAtomIndices
      : syncedState.showAtomIndices;

  const handleToggleAtomIndices =
    onToggleAtomIndices ??
    (() => emitLeftPageCommand({ type: "toggleAtomIndices" }));

  const handleChangeAtomCharge =
    onChangeAtomCharge ??
    ((atomId: string, charge: number) =>
      emitLeftPageCommand({ type: "changeAtomCharge", atomId, charge }));

  const handleToggleRadical =
    onToggleRadical ??
    ((atomId: string) => emitLeftPageCommand({ type: "toggleRadical", atomId }));

  const handleToggleLonePair =
    onToggleLonePair ??
    ((atomId: string) =>
      emitLeftPageCommand({ type: "toggleLonePair", atomId }));

  const handleDeleteAtom =
    onDeleteAtom ??
    ((atomId: string) => emitLeftPageCommand({ type: "deleteAtom", atomId }));

  const handleChangeBondStyle =
    onChangeBondStyle ??
    ((bondId: string, style: BondVisualStyle) =>
      emitLeftPageCommand({ type: "changeBondStyle", bondId, style }));

  const handleDeleteBond =
    onDeleteBond ??
    ((bondId: string) => emitLeftPageCommand({ type: "deleteBond", bondId }));

  const selectedAtom = useMemo(
    () => getSelectedAtom(effectiveMolecule, effectiveSelectedTarget),
    [effectiveMolecule, effectiveSelectedTarget]
  );

  const selectedBond = useMemo(
    () => getSelectedBond(effectiveMolecule, effectiveSelectedTarget),
    [effectiveMolecule, effectiveSelectedTarget]
  );

  return (
    <aside className="leftpage-panel">
      <header className="leftpage-tabs">
        <button
          className={activeTab === "molecule" ? "active" : ""}
          type="button"
          onClick={() => setActiveTab("molecule")}
        >
          ⌬ Molécula
        </button>

        <button
          className={activeTab === "atoms" ? "active" : ""}
          type="button"
          onClick={() => setActiveTab("atoms")}
        >
          🔴 Átomos
        </button>

        <button
          className={activeTab === "bonds" ? "active" : ""}
          type="button"
          onClick={() => setActiveTab("bonds")}
        >
          🔗 Ligações
        </button>

        <button
          className={`leftpage-index-toggle ${
            effectiveShowAtomIndices ? "active" : ""
          }`}
          type="button"
          onClick={handleToggleAtomIndices}
          title="Mostrar/ocultar numeração azul dos átomos no ambiente 2D"
        >
          # Numeração: {effectiveShowAtomIndices ? "ON" : "OFF"}
        </button>
      </header>

      <div className="leftpage-body">
        {activeTab === "molecule" && (
          <>
            <h3>Molécula individual</h3>

            <ChemistryParametersPanel
              molecule={effectiveMolecule}
              selectedTarget={effectiveSelectedTarget}
              mode="molecule"
            />

            {effectiveMolecule?.validation_state?.warnings?.length ? (
              <div className="leftpage-warning-box">
                {effectiveMolecule.validation_state.warnings.map((warning) => (
                  <span key={warning}>{warning}</span>
                ))}
              </div>
            ) : null}

            {effectiveMolecule?.validation_state?.errors?.length ? (
              <div className="leftpage-error-box">
                {effectiveMolecule.validation_state.errors.map((error) => (
                  <span key={error}>{error}</span>
                ))}
              </div>
            ) : null}
          </>
        )}

        {activeTab === "atoms" && (
          <>
            <h3>Átomos</h3>
            <AtomDetails
              atom={selectedAtom}
              onChangeAtomCharge={handleChangeAtomCharge}
              onToggleRadical={handleToggleRadical}
              onToggleLonePair={handleToggleLonePair}
              onDeleteAtom={handleDeleteAtom}
            />

            <ChemistryParametersPanel
              molecule={effectiveMolecule}
              selectedTarget={effectiveSelectedTarget}
              mode="atom"
            />

            <AtomList molecule={effectiveMolecule} />
          </>
        )}

        {activeTab === "bonds" && (
          <>
            <h3>Ligações</h3>
            <BondDetails
              bond={selectedBond}
              molecule={effectiveMolecule}
              selectedBondStyle={effectiveSelectedBondStyle}
              onChangeBondStyle={handleChangeBondStyle}
              onDeleteBond={handleDeleteBond}
            />

            <ChemistryParametersPanel
              molecule={effectiveMolecule}
              selectedTarget={effectiveSelectedTarget}
              mode="bond"
            />

            <BondList molecule={effectiveMolecule} />
          </>
        )}
      </div>
    </aside>
  );
}

export default LeftPage;


