import { useState } from "react";

import AddAtomPanel from "../addatom/addatom";
import LinkPanel from "../link/link";
import FastMol, { type FastMolItem } from "./fastmol/fastmol";

import type {
  BondOrder,
  BondVisualStyle,
} from "../../../type/rdkit2d.types";

import "./toolsbar.css";

type ToolsBarProps = {
  quickElements: string[];
  selectedElement: string;
  showPeriodicTable: boolean;
  defaultFormalCharge: number;

  moveAtomToolActive: boolean;
  panToolActive: boolean;
  atomToolActive: boolean;
  atomBondToolActive: boolean;
  radicalToolActive: boolean;
  lonePairToolActive: boolean;
  chargeToolActive: boolean;
  bondToolActive: boolean;
  deleteToolActive: boolean;

  selectedBondOrder: BondOrder;
  selectedBondStyle: BondVisualStyle;
  selectedBondId: string | null;
  pendingBondAtomId: string | null;

  showExplicitHs: boolean;

  onSelectElement: (element: string) => void;
  onOpenPeriodicTable: () => void;

  onActivateMoveTool: () => void;
  onActivatePanTool: () => void;
  onToggleAtomTool: () => void;
  onToggleAtomBondTool: () => void;
  onToggleRadicalTool: () => void;
  onToggleLonePairTool: () => void;
  onToggleChargeTool: () => void;
  onToggleBondTool: () => void;
  onToggleDeleteTool: () => void;

  onChangeFormalCharge: (charge: number) => void;
  onChangeBondTool: (style: BondVisualStyle, order: BondOrder) => void;
  onApplyBondStyleToSelected: () => void;
  onApplyFormalChemistry: () => void;

  onClearCanvas: () => void;
  onOptimizeStructure: () => void;
  onToggleHydrogens: () => void;
  onLoadFastMolecule: (smiles: string, molecule: FastMolItem) => void;
};

export function ToolsBar({
  quickElements,
  selectedElement,
  showPeriodicTable,

  defaultFormalCharge,
  moveAtomToolActive,
  panToolActive,
  atomToolActive,
  atomBondToolActive,
  radicalToolActive,
  lonePairToolActive,
  chargeToolActive,

  bondToolActive,
  deleteToolActive,
  selectedBondOrder,
  selectedBondStyle,
  selectedBondId,
  pendingBondAtomId,

  showExplicitHs,

  onSelectElement,
  onOpenPeriodicTable,

  onActivateMoveTool,
  onActivatePanTool,
  onToggleAtomTool,
  onToggleAtomBondTool,
  onToggleRadicalTool,
  onToggleLonePairTool,
  onToggleChargeTool,
  onChangeFormalCharge,

  onToggleBondTool,
  onToggleDeleteTool,
  onChangeBondTool,
  onApplyBondStyleToSelected,
  onApplyFormalChemistry,
  onClearCanvas,

  onOptimizeStructure,
  onToggleHydrogens,
  onLoadFastMolecule,
}: ToolsBarProps) {
  const [showFastMol, setShowFastMol] = useState(false);

  return (
    <div className="toolsbar-shell">
      <button
        className={`toolsbar-fixed-eraser ${deleteToolActive ? "active" : ""}`}
        type="button"
        onClick={onToggleDeleteTool}
        title="Borracha fixa: clique novamente para desativar"
      >
        🧽
      </button>

      <div className="toolsbar-scroll" aria-label="Barra de ferramentas 2D">
        <div className="toolsbar-section periodic-section">
          <button
            className={`periodic-open ${showPeriodicTable ? "active" : ""}`}
            onClick={onOpenPeriodicTable}
            type="button"
            title="Abrir tabela periódica e adicionar elementos à barra"
          >
            Tabela periódica
          </button>
        </div>

        <div className="tool-separator" />

        <div className="selected-atoms-strip" aria-label="Átomos selecionados">
          {quickElements.length === 0 && (
            <span className="selected-atoms-empty">Escolha na tabela</span>
          )}

          {quickElements.map((element) => (
            <button
              key={element}
              className={`element-chip ${
                selectedElement === element ? "active" : ""
              }`}
              onClick={() => onSelectElement(element)}
              title={`Selecionar ${element}`}
              type="button"
            >
              {element}
            </button>
          ))}
        </div>

        <div className="tool-separator" />

        <AddAtomPanel
          selectedElement={selectedElement}
          defaultFormalCharge={defaultFormalCharge}
          moveAtomToolActive={moveAtomToolActive}
          panToolActive={panToolActive}
          atomToolActive={atomToolActive}
          atomBondToolActive={atomBondToolActive}
          radicalToolActive={radicalToolActive}
          lonePairToolActive={lonePairToolActive}
          chargeToolActive={chargeToolActive}
          selectedBondOrder={selectedBondOrder}
          onActivateMoveTool={onActivateMoveTool}
          onActivatePanTool={onActivatePanTool}
          onToggleAtomTool={onToggleAtomTool}
          onToggleAtomBondTool={onToggleAtomBondTool}
          onToggleRadicalTool={onToggleRadicalTool}
          onToggleLonePairTool={onToggleLonePairTool}
          onToggleChargeTool={onToggleChargeTool}
          onChangeFormalCharge={onChangeFormalCharge}
        />

        <div className="tool-separator" />

        <LinkPanel
          bondToolActive={bondToolActive}
          deleteToolActive={deleteToolActive}
          selectedBondOrder={selectedBondOrder}
          selectedBondStyle={selectedBondStyle}
          selectedBondId={selectedBondId}
          pendingBondAtomId={pendingBondAtomId}
          onToggleBondTool={onToggleBondTool}
          onToggleDeleteTool={onToggleDeleteTool}
          onChangeBondTool={onChangeBondTool}
          onApplyBondStyleToSelected={onApplyBondStyleToSelected}
          onClearCanvas={onClearCanvas}
        />

        <div className="tool-separator" />

        <div className="toolsbar-section">
          <button
            className="tool-btn compact-text"
            title="Distribuir cargas formais e pares livres automaticamente antes da otimização"
            type="button"
            onClick={onApplyFormalChemistry}
          >
            ⚖ Cargas/pares
          </button>

          <button
            className="tool-btn highlight compact-text"
            title="Ajustar posição, tamanho e distribuição visual"
            type="button"
            onClick={onOptimizeStructure}
          >
            ✨ Otimizar
          </button>

          <button
            className={`tool-btn hydrogen-toggle compact-text ${
              showExplicitHs ? "active" : ""
            }`}
            title="Adicionar ou remover átomos de Hidrogênio explícitos usando RDKit (AddHs/RemoveHs)"
            type="button"
            onClick={onToggleHydrogens}
          >
            {showExplicitHs ? "Ⓗ Ocultar H" : "Ⓗ Mostrar H"}
          </button>

          <button
            className="tool-btn compact-text"
            title="Abrir compostos comuns e surfactantes para carregar via SMILES no ambiente 2D"
            type="button"
            onClick={() => setShowFastMol(true)}
          >
            ⚗ Moléculas
          </button>
        </div>
      </div>

      <FastMol
        isOpen={showFastMol}
        onClose={() => setShowFastMol(false)}
        onSelectSmiles={(smiles, molecule) => {
          onLoadFastMolecule(smiles, molecule);
          setShowFastMol(false);
        }}
      />
    </div>
  );
}

export default ToolsBar;


