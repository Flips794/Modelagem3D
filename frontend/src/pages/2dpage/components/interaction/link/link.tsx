import type {
  BondOrder,
  BondVisualStyle,
} from "../../../type/rdkit2d.types";

import "./link.css";

type LinkPanelProps = {
  bondToolActive: boolean;
  deleteToolActive: boolean;
  selectedBondOrder: BondOrder;
  selectedBondStyle: BondVisualStyle;
  selectedBondId: string | null;
  pendingBondAtomId: string | null;
  onToggleBondTool: () => void;
  onToggleDeleteTool: () => void;
  onChangeBondTool: (style: BondVisualStyle, order: BondOrder) => void;
  onApplyBondStyleToSelected: () => void;
  onClearCanvas: () => void;
};

const bondOptions: Array<{
  label: string;
  value: BondVisualStyle;
  order: BondOrder;
  title: string;
}> = [
  {
    label: "―",
    value: "single",
    order: 1,
    title: "Ligação simples",
  },
  {
    label: "＝",
    value: "double",
    order: 2,
    title: "Ligação dupla",
  },
  {
    label: "≡",
    value: "triple",
    order: 3,
    title: "Ligação tripla",
  },
  {
    label: "▲",
    value: "wedge-filled",
    order: 1,
    title: "Cunha cheia",
  },
  {
    label: "▤",
    value: "wedge-dashed",
    order: 1,
    title: "Cunha tracejada",
  },
  {
    label: "⋯",
    value: "dashed",
    order: 1,
    title: "Ligação tracejada",
  },
  {
    label: "―⋯",
    value: "single-resonance",
    order: 1.5,
    title: "Ligação simples + tracejada, ressonância",
  },
  {
    label: "＝⋯",
    value: "double-resonance",
    order: 1.5,
    title: "Ligação dupla + tracejada, ressonância",
  },
];

export function LinkPanel({
  bondToolActive,
  deleteToolActive,
  selectedBondStyle,
  selectedBondId,
  pendingBondAtomId,
  onToggleBondTool,
  onToggleDeleteTool,
  onChangeBondTool,
  onApplyBondStyleToSelected,
  onClearCanvas,
}: LinkPanelProps) {
  return (
    <section className="link-panel" aria-label="Ferramentas de ligação">
      <button
        className={`link-mode ${bondToolActive ? "active" : ""}`}
        type="button"
        onClick={onToggleBondTool}
        title="Clique em dois átomos para criar uma ligação"
      >
        Ligar
      </button>

      <div className="link-orders">
        {bondOptions.map((option) => (
          <button
            key={option.value}
            className={`link-order ${
              selectedBondStyle === option.value ? "active" : ""
            }`}
            type="button"
            title={option.title}
            onClick={() => onChangeBondTool(option.value, option.order)}
          >
            {option.label}
          </button>
        ))}
      </div>

      <button
        className="link-mode ghost"
        type="button"
        disabled={!selectedBondId}
        onClick={onApplyBondStyleToSelected}
        title="Aplica o tipo de ligação ativo na ligação selecionada"
      >
        Aplicar
      </button>

      <button
        className="link-mode clear"
        type="button"
        onClick={onClearCanvas}
        title="Limpar todo o ambiente 2D"
      >
        Limpar tudo
      </button>

      <button
        className={`link-mode eraser-inline ${deleteToolActive ? "active" : ""}`}
        type="button"
        onClick={onToggleDeleteTool}
        title="Borracha: clique em átomo, ligação, radical ou par livre para apagar"
      >
        Borracha
      </button>

      {pendingBondAtomId && (
        <span className="link-pending">Origem: {pendingBondAtomId}</span>
      )}
    </section>
  );
}

export default LinkPanel;


