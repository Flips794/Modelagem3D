import type { SimulationSettings3D } from "../../type/3dpage.types";

import "./toolsbar.css";

type ToolsBar3DProps = {
  settings: SimulationSettings3D;
  moleculeCount: number;
  onChangeSettings: (settings: SimulationSettings3D) => void;
  onClearEnvironment: () => void;
};

/**
 * ToolsBar3D
 * ---------------------------------------------------------------------------
 * Componente mantido apenas para preservar compatibilidade com o Page3D.
 *
 * A barra antiga mostrava:
 * - quantidade de molÃ©culas;
 * - temperatura;
 * - pH;
 * - forÃ§a iÃ´nica;
 * - DinÃ¢mica ON/OFF;
 * - Campo de carga;
 * - Aura;
 * - Limpar 3D;
 * - controles numÃ©ricos de ambiente.
 *
 * Esses controles foram removidos da interface do ambiente 3D.
 * O ambiente 3D agora fica limpo, focado somente na visualizaÃ§Ã£o molecular.
 *
 * Importante:
 * - NÃ£o remove os tipos.
 * - NÃ£o quebra a chamada existente no Page3D.
 * - NÃ£o altera WebSocket, OpenMM, SimulationViewer3D ou renderizaÃ§Ã£o.
 * - Os parÃ¢metros de mistura continuam devendo ser controlados no ambiente
 *   de mistura/transferÃªncia, nÃ£o na visualizaÃ§Ã£o 3D.
 */
export default function ToolsBar3D(_props: ToolsBar3DProps) {
  return null;
}


