import type { BondOrder } from "../../../type/rdkit2d.types";

import "./addatom.css";

type AddAtomPanelProps = {
  selectedElement: string;
  defaultFormalCharge: number;
  moveAtomToolActive: boolean;
  panToolActive: boolean;
  atomToolActive: boolean;
  atomBondToolActive: boolean;
  radicalToolActive: boolean;
  lonePairToolActive: boolean;
  chargeToolActive: boolean;
  selectedBondOrder: BondOrder;
  onActivateMoveTool: () => void;
  onActivatePanTool: () => void;
  onToggleAtomTool: () => void;
  onToggleAtomBondTool: () => void;
  onToggleRadicalTool: () => void;
  onToggleLonePairTool: () => void;
  onToggleChargeTool: () => void;
  onChangeFormalCharge: (charge: number) => void;
};

export function AddAtomPanel({
  selectedElement,
  defaultFormalCharge,
  moveAtomToolActive,
  panToolActive,
  atomToolActive,
  atomBondToolActive,
  radicalToolActive,
  lonePairToolActive,
  chargeToolActive,
  selectedBondOrder,
  onActivateMoveTool,
  onActivatePanTool,
  onToggleAtomTool,
  onToggleAtomBondTool,
  onToggleRadicalTool,
  onToggleLonePairTool,
  onToggleChargeTool,
  onChangeFormalCharge,
}: AddAtomPanelProps) {
  const atomLabel = selectedElement || "átomo";

  return (
    <section className="addatom-panel" aria-label="Ferramentas de edição de átomo">
      <button
        className={`addatom-tool square ${moveAtomToolActive ? "active" : ""}`}
        type="button"
        onClick={onActivateMoveTool}
        title="Mover átomo existente"
      >
        ⊙
      </button>

      <button
        className={`addatom-tool square ${panToolActive ? "active" : ""}`}
        type="button"
        onClick={onActivatePanTool}
        title="Mover todas as moléculas no ambiente 2D"
      >
        ✥
      </button>

      <button
        className={`addatom-tool ${atomToolActive ? "active" : ""}`}
        type="button"
        onClick={onToggleAtomTool}
        title="Clique no ambiente para adicionar o átomo selecionado"
      >
        + {atomLabel}
      </button>

      <button
        className={`addatom-tool ${atomBondToolActive ? "active" : ""}`}
        type="button"
        onClick={onToggleAtomBondTool}
        title="Arraste de um átomo existente para criar outro átomo já ligado"
      >
        {atomLabel} + ligação {selectedBondOrder}
      </button>

      <button
        className={`addatom-tool square ${radicalToolActive ? "active" : ""}`}
        type="button"
        onClick={onToggleRadicalTool}
        title="Adicionar/remover radical no átomo clicado"
      >
        •
      </button>

      <button
        className={`addatom-tool square ${lonePairToolActive ? "active" : ""}`}
        type="button"
        onClick={onToggleLonePairTool}
        title="Adicionar/remover par livre no átomo clicado"
      >
        :
      </button>

      <div className={`addatom-charge ${chargeToolActive ? "active" : ""}`}>
        <button
          type="button"
          onClick={() => onChangeFormalCharge(defaultFormalCharge - 1)}
          title="Diminuir carga"
        >
          −
        </button>

        <button
          className="charge-value"
          type="button"
          onClick={onToggleChargeTool}
          title="Ativar ferramenta de carga: clique em um átomo para aplicar"
        >
          {defaultFormalCharge > 0 ? `+${defaultFormalCharge}` : defaultFormalCharge}
        </button>

        <button
          type="button"
          onClick={() => onChangeFormalCharge(defaultFormalCharge + 1)}
          title="Aumentar carga"
        >
          +
        </button>
      </div>
    </section>
  );
}

export default AddAtomPanel;


