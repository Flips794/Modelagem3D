import { useMemo, useRef, useState } from "react";

import type {
  BondOrder,
  BondVisualStyle,
  CanvasViewport,
  EditorToolState,
  InternalAtomModel,
  InternalBondModel,
  InternalMoleculeModel,
  Position2D,
  SelectedMoleculeTarget,
} from "../../type/rdkit2d.types";

type NormalizedAtom = InternalAtomModel & {
  screenX: number;
  screenY: number;
};

type BondPath = {
  atomA: NormalizedAtom;
  atomB: NormalizedAtom;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
};

type EmptySectorPlacement = {
  angle: number;
  score: number;
};

type DecorationPlacement = {
  x: number;
  y: number;
  angle: number;
};

type DragState =
  | {
      kind: "none";
    }
  | {
      kind: "pan";
      startRootX: number;
      startRootY: number;
      startPanX: number;
      startPanY: number;
    }
  | {
      kind: "move-atom";
      atomId: string;
      startBaseX: number;
      startBaseY: number;
      hasMoved: boolean;
    }
  | {
      kind: "extend-atom";
      atomId: string;
      startBaseX: number;
      startBaseY: number;
      currentBaseX: number;
      currentBaseY: number;
      hasMoved: boolean;
    };

type Molecule2DViewerProps = {
  molecule: InternalMoleculeModel | null;
  selectedTarget: SelectedMoleculeTarget;
  viewport: CanvasViewport;
  tools: EditorToolState;
  selectedElement: string;
  showAtomIndices: boolean;
  selectedBondOrder: BondOrder;
  defaultFormalCharge: number;
  pendingBondAtomId: string | null;
  onCanvasAddAtom: (position: Position2D) => void;
  onMoveAtom: (atomId: string, position: Position2D) => void;
  onViewportChange: (viewport: CanvasViewport) => void;
  onSelectAtom: (atomId: string) => void;
  onSelectBond: (bondId: string) => void;
  onExtendAtomWithBond: (originAtomId: string, position: Position2D) => void;
  onToggleRadical: (atomId: string) => void;
  onClearRadical: (atomId: string) => void;
  onToggleLonePair: (atomId: string) => void;
  onClearLonePair: (atomId: string) => void;
  onSetAtomCharge: (atomId: string, charge: number) => void;
  onDeleteAtom: (atomId: string) => void;
  onDeleteBond: (bondId: string) => void;
};

const emptyDragState: DragState = {
  kind: "none",
};

const VIEW_WIDTH = 900;
const VIEW_HEIGHT = 520;
const MODEL_SCALE = 72;
const ATOM_ERASER_RADIUS = 24;
const BOND_TRIM = 22;
const DECORATION_RADIUS = 35;
const INDEX_RADIUS = 43;

function getAtomColor(element: string) {
  const colors: Record<string, string> = {
    H: "#f8fafc",
    C: "#94a3b8",
    N: "#3b82f6",
    O: "#ef4444",
    F: "#22c55e",
    Cl: "#22c55e",
    Br: "#92400e",
    I: "#7c3aed",
    P: "#f97316",
    S: "#eab308",
    B: "#fb923c",
    Li: "#a855f7",
    Na: "#a855f7",
    K: "#a855f7",
    Mg: "#10b981",
    Ca: "#10b981",
    Fe: "#f97316",
    Cu: "#f97316",
    Zn: "#94a3b8",
  };

  return colors[element] ?? "#67e8f9";
}

function getAtomTextColor(element: string) {
  if (element === "C") return "#020617";
  if (element === "H") return "#020617";
  if (element === "S") return "#020617";
  if (element === "P") return "#020617";

  return "#f8fafc";
}

function getVisualStyle(bond: InternalBondModel): BondVisualStyle {
  if (bond.visual_style) return bond.visual_style;
  if (bond.stereo_visual === "wedge") return "wedge-filled";
  if (bond.stereo_visual === "dash") return "wedge-dashed";
  if (bond.order === 3) return "triple";
  if (bond.order === 2) return "double";
  if (bond.order === 1.5 || bond.is_aromatic) return "aromatic";

  return "single";
}

function shouldRenderConjugationGlow(bond: InternalBondModel) {
  const visualStyle = getVisualStyle(bond);
  const possibleRdkitFlags = bond as InternalBondModel & {
    is_conjugated?: boolean;
  };

  return (
    Boolean(possibleRdkitFlags.is_conjugated) ||
    bond.is_aromatic ||
    bond.order === 1.5 ||
    visualStyle === "aromatic" ||
    visualStyle === "single-resonance" ||
    visualStyle === "double-resonance"
  );
}

/**
 * Coordenada química/modelo -> coordenada local da camada molecular.
 */
function modelToBaseScreen(position: Position2D): Position2D {
  return {
    x: VIEW_WIDTH / 2 + position.x * MODEL_SCALE,
    y: VIEW_HEIGHT / 2 - position.y * MODEL_SCALE,
  };
}

/**
 * Coordenada local da camada molecular -> coordenada química/modelo.
 */
function baseScreenToModel(position: Position2D): Position2D {
  return {
    x: (position.x - VIEW_WIDTH / 2) / MODEL_SCALE,
    y: -(position.y - VIEW_HEIGHT / 2) / MODEL_SCALE,
  };
}

function clientToSvgLocalPoint(
  event: React.PointerEvent<SVGElement> | React.MouseEvent<SVGElement>,
  element: SVGGraphicsElement | SVGSVGElement | null
): Position2D {
  if (!element) {
    return {
      x: VIEW_WIDTH / 2,
      y: VIEW_HEIGHT / 2,
    };
  }

  const matrix = element.getScreenCTM();

  if (!matrix) {
    return {
      x: VIEW_WIDTH / 2,
      y: VIEW_HEIGHT / 2,
    };
  }

  const svg =
    element.ownerSVGElement ?? (element instanceof SVGSVGElement ? element : null);

  if (!svg) {
    return {
      x: VIEW_WIDTH / 2,
      y: VIEW_HEIGHT / 2,
    };
  }

  const point = svg.createSVGPoint();
  point.x = event.clientX;
  point.y = event.clientY;

  const transformed = point.matrixTransform(matrix.inverse());

  return {
    x: transformed.x,
    y: transformed.y,
  };
}

function clientToBasePoint(
  event: React.PointerEvent<SVGElement> | React.MouseEvent<SVGElement>,
  viewportLayer: SVGGElement | null
): Position2D {
  return clientToSvgLocalPoint(event, viewportLayer);
}

function clientToModelPosition(
  event: React.PointerEvent<SVGElement>,
  viewportLayer: SVGGElement | null
): Position2D {
  return baseScreenToModel(clientToBasePoint(event, viewportLayer));
}

function distance(a: Position2D, b: Position2D) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

function normalizeAtoms(atoms: InternalAtomModel[]) {
  return atoms.map((atom) => {
    const position = modelToBaseScreen(atom.position_2d);

    return {
      ...atom,
      screenX: position.x,
      screenY: position.y,
    };
  });
}

function getBondPath(
  bond: InternalBondModel,
  atomMap: Map<string, NormalizedAtom>
): BondPath | null {
  const atomA = atomMap.get(bond.atom_a_id);
  const atomB = atomMap.get(bond.atom_b_id);

  if (!atomA || !atomB) return null;

  return {
    atomA,
    atomB,
    x1: atomA.screenX,
    y1: atomA.screenY,
    x2: atomB.screenX,
    y2: atomB.screenY,
  };
}

function trimBondPath(path: BondPath, trim = BOND_TRIM): BondPath {
  const dx = path.x2 - path.x1;
  const dy = path.y2 - path.y1;
  const length = Math.max(Math.hypot(dx, dy), 1);
  const ux = dx / length;
  const uy = dy / length;
  const safeTrim = Math.min(trim, length / 2 - 1);

  return {
    ...path,
    x1: path.x1 + ux * safeTrim,
    y1: path.y1 + uy * safeTrim,
    x2: path.x2 - ux * safeTrim,
    y2: path.y2 - uy * safeTrim,
  };
}

function offsetLine(path: BondPath, offset: number) {
  const dx = path.x2 - path.x1;
  const dy = path.y2 - path.y1;
  const length = Math.max(Math.hypot(dx, dy), 1);
  const nx = (-dy / length) * offset;
  const ny = (dx / length) * offset;

  return {
    x1: path.x1 + nx,
    y1: path.y1 + ny,
    x2: path.x2 + nx,
    y2: path.y2 + ny,
  };
}

function wedgePoints(path: BondPath) {
  const dx = path.x2 - path.x1;
  const dy = path.y2 - path.y1;
  const length = Math.max(Math.hypot(dx, dy), 1);
  const nx = (-dy / length) * 10;
  const ny = (dx / length) * 10;

  return `${path.x1},${path.y1} ${path.x2 + nx},${path.y2 + ny} ${path.x2 - nx},${path.y2 - ny}`;
}

function getDashedWedgeSegments(path: BondPath, segmentCount = 8) {
  const dx = path.x2 - path.x1;
  const dy = path.y2 - path.y1;
  const length = Math.max(Math.hypot(dx, dy), 1);
  const ux = dx / length;
  const uy = dy / length;
  const nx = -uy;
  const ny = ux;

  return Array.from({ length: segmentCount }, (_, index) => {
    const t = (index + 1) / (segmentCount + 1);
    const cx = path.x1 + dx * t;
    const cy = path.y1 + dy * t;
    const halfWidth = 1.5 + t * 9;

    return {
      key: index,
      x1: cx - nx * halfWidth,
      y1: cy - ny * halfWidth,
      x2: cx + nx * halfWidth,
      y2: cy + ny * halfWidth,
    };
  });
}

function angleOfVector(from: Position2D, to: Position2D) {
  return Math.atan2(to.y - from.y, to.x - from.x);
}

function normalizeAngle(angle: number) {
  const full = Math.PI * 2;
  let normalized = angle % full;

  if (normalized < 0) normalized += full;

  return normalized;
}

function angleToPoint(origin: Position2D, angle: number, radius: number) {
  return {
    x: origin.x + Math.cos(angle) * radius,
    y: origin.y + Math.sin(angle) * radius,
  };
}

function getConnectedBondAngles(
  atom: NormalizedAtom,
  bonds: InternalBondModel[],
  atomMap: Map<string, NormalizedAtom>
) {
  const angles: number[] = [];

  bonds.forEach((bond) => {
    let otherAtom: NormalizedAtom | undefined;

    if (bond.atom_a_id === atom.id) {
      otherAtom = atomMap.get(bond.atom_b_id);
    } else if (bond.atom_b_id === atom.id) {
      otherAtom = atomMap.get(bond.atom_a_id);
    }

    if (!otherAtom) return;

    angles.push(
      normalizeAngle(
        angleOfVector(
          {
            x: atom.screenX,
            y: atom.screenY,
          },
          {
            x: otherAtom.screenX,
            y: otherAtom.screenY,
          }
        )
      )
    );
  });

  return angles.sort((a, b) => a - b);
}

function getEmptySectorPlacements(
  atom: NormalizedAtom,
  bonds: InternalBondModel[],
  atomMap: Map<string, NormalizedAtom>
): EmptySectorPlacement[] {
  const angles = getConnectedBondAngles(atom, bonds, atomMap);

  if (angles.length === 0) {
    return [
      {
        angle: normalizeAngle((-3 * Math.PI) / 4),
        score: Math.PI * 2,
      },
      {
        angle: normalizeAngle(-Math.PI / 4),
        score: Math.PI * 2,
      },
      {
        angle: normalizeAngle(Math.PI / 2),
        score: Math.PI * 2,
      },
    ];
  }

  if (angles.length === 1) {
    const opposite = normalizeAngle(angles[0] + Math.PI);

    return [
      {
        angle: opposite,
        score: Math.PI,
      },
      {
        angle: normalizeAngle(opposite + Math.PI / 4),
        score: Math.PI / 2,
      },
      {
        angle: normalizeAngle(opposite - Math.PI / 4),
        score: Math.PI / 2,
      },
    ];
  }

  const sectors: EmptySectorPlacement[] = [];

  for (let index = 0; index < angles.length; index += 1) {
    const current = angles[index];
    const next =
      index === angles.length - 1 ? angles[0] + Math.PI * 2 : angles[index + 1];

    const gap = next - current;
    const middle = normalizeAngle(current + gap / 2);

    sectors.push({
      angle: middle,
      score: gap,
    });
  }

  return sectors.sort((a, b) => b.score - a.score);
}

function getDecorationPlacement(
  atom: NormalizedAtom,
  bonds: InternalBondModel[],
  atomMap: Map<string, NormalizedAtom>,
  role: "index" | "lonePair" | "radical",
  order = 0
): DecorationPlacement {
  const sectors = getEmptySectorPlacements(atom, bonds, atomMap);
  const sector = sectors[Math.min(order, sectors.length - 1)] ?? sectors[0];
  const radius =
    role === "index"
      ? INDEX_RADIUS
      : DECORATION_RADIUS + (role === "lonePair" ? 2 : 0);

  const point = angleToPoint(
    {
      x: atom.screenX,
      y: atom.screenY,
    },
    sector.angle,
    radius
  );

  return {
    ...point,
    angle: sector.angle,
  };
}

function getAtomIndexLabel(atom: InternalAtomModel) {
  return String(atom.rdkit_index + 1);
}

function getIndexBadgeMetrics(label: string, placement: DecorationPlacement) {
  const width = Math.max(16, label.length * 6.4 + 9);
  const height = 15;
  const isLeftSide = Math.cos(placement.angle) < 0;

  if (isLeftSide) {
    return {
      rectX: placement.x - width,
      rectY: placement.y - height / 2,
      textX: placement.x - 4,
      textY: placement.y,
      anchor: "end" as const,
      width,
      height,
    };
  }

  return {
    rectX: placement.x,
    rectY: placement.y - height / 2,
    textX: placement.x + 4,
    textY: placement.y,
    anchor: "start" as const,
    width,
    height,
  };
}

function getBondOrderLabel(order: BondOrder) {
  if (order === 1) return "simples";
  if (order === 2) return "dupla";
  if (order === 3) return "tripla";

  return "aromática/ressonância";
}

function renderBondLines(
  bond: InternalBondModel,
  path: BondPath,
  selected: boolean,
  onBondClick: (
    event: React.MouseEvent<SVGLineElement | SVGPolygonElement>
  ) => void
) {
  const visualStyle = getVisualStyle(bond);
  const trimmedPath = trimBondPath(path);
  const className = `molecule-2d-bond ${selected ? "selected" : ""}`;

  if (visualStyle === "wedge-filled") {
    return (
      <polygon
        points={wedgePoints(trimmedPath)}
        className={`molecule-2d-wedge ${selected ? "selected" : ""}`}
        onClick={onBondClick}
      />
    );
  }

  if (visualStyle === "wedge-dashed") {
    return (
      <g className={`molecule-2d-dashed-wedge ${selected ? "selected" : ""}`}>
        {getDashedWedgeSegments(trimmedPath).map((segment) => (
          <line
            key={segment.key}
            x1={segment.x1}
            y1={segment.y1}
            x2={segment.x2}
            y2={segment.y2}
            onClick={onBondClick}
          />
        ))}
      </g>
    );
  }

  if (visualStyle === "triple") {
    const lineA = offsetLine(trimmedPath, -6);
    const lineB = offsetLine(trimmedPath, 0);
    const lineC = offsetLine(trimmedPath, 6);

    return (
      <>
        <line {...lineA} className={className} strokeWidth={2.4} onClick={onBondClick} />
        <line {...lineB} className={className} strokeWidth={2.4} onClick={onBondClick} />
        <line {...lineC} className={className} strokeWidth={2.4} onClick={onBondClick} />
      </>
    );
  }

  if (visualStyle === "double") {
    const lineA = offsetLine(trimmedPath, -4);
    const lineB = offsetLine(trimmedPath, 4);

    return (
      <>
        <line {...lineA} className={className} strokeWidth={2.8} onClick={onBondClick} />
        <line {...lineB} className={className} strokeWidth={2.8} onClick={onBondClick} />
      </>
    );
  }

  if (visualStyle === "double-resonance") {
    const lineA = offsetLine(trimmedPath, -6);
    const lineB = offsetLine(trimmedPath, 1);
    const lineC = offsetLine(trimmedPath, 8);

    return (
      <>
        <line {...lineA} className={className} strokeWidth={2.6} onClick={onBondClick} />
        <line {...lineB} className={className} strokeWidth={2.6} onClick={onBondClick} />
        <line
          {...lineC}
          className={className}
          strokeWidth={2.2}
          strokeDasharray="7 7"
          onClick={onBondClick}
        />
      </>
    );
  }

  if (visualStyle === "single-resonance") {
    const lineA = offsetLine(trimmedPath, -4);
    const lineB = offsetLine(trimmedPath, 5);

    return (
      <>
        <line {...lineA} className={className} strokeWidth={3} onClick={onBondClick} />
        <line
          {...lineB}
          className={className}
          strokeWidth={2.2}
          strokeDasharray="7 7"
          onClick={onBondClick}
        />
      </>
    );
  }

  if (visualStyle === "dashed") {
    return (
      <line
        x1={trimmedPath.x1}
        y1={trimmedPath.y1}
        x2={trimmedPath.x2}
        y2={trimmedPath.y2}
        className={className}
        strokeWidth={3}
        strokeDasharray="8 8"
        onClick={onBondClick}
      />
    );
  }

  if (visualStyle === "aromatic") {
    const lineA = offsetLine(trimmedPath, -4);
    const lineB = offsetLine(trimmedPath, 5);

    return (
      <>
        <line {...lineA} className={className} strokeWidth={2.6} onClick={onBondClick} />
        <line
          {...lineB}
          className={className}
          strokeWidth={2.1}
          strokeDasharray="7 7"
          onClick={onBondClick}
        />
      </>
    );
  }

  return (
    <line
      x1={trimmedPath.x1}
      y1={trimmedPath.y1}
      x2={trimmedPath.x2}
      y2={trimmedPath.y2}
      className={className}
      strokeWidth={3.2}
      onClick={onBondClick}
    />
  );
}

export function Molecule2DViewer({
  molecule,
  selectedTarget,
  viewport,
  tools,
  selectedElement,
  showAtomIndices,
  selectedBondOrder,
  defaultFormalCharge,
  pendingBondAtomId,
  onCanvasAddAtom,
  onMoveAtom,
  onViewportChange,
  onSelectAtom,
  onSelectBond,
  onExtendAtomWithBond,
  onToggleRadical,
  onClearRadical,
  onToggleLonePair,
  onClearLonePair,
  onSetAtomCharge,
  onDeleteAtom,
  onDeleteBond,
}: Molecule2DViewerProps) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const viewportLayerRef = useRef<SVGGElement | null>(null);
  const [dragState, setDragState] = useState<DragState>(emptyDragState);

  const atoms = molecule?.atoms ?? [];
  const bonds = molecule?.bonds ?? [];

  const normalizedAtoms = useMemo(() => normalizeAtoms(atoms), [atoms]);

  const atomMap = useMemo(() => {
    return new Map(normalizedAtoms.map((atom) => [atom.id, atom]));
  }, [normalizedAtoms]);

  function beginPan(event: React.PointerEvent<SVGElement>) {
    const rootPoint = clientToSvgLocalPoint(event, svgRef.current);

    setDragState({
      kind: "pan",
      startRootX: rootPoint.x,
      startRootY: rootPoint.y,
      startPanX: viewport.panX,
      startPanY: viewport.panY,
    });

    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function handleCanvasPointerDown(event: React.PointerEvent<SVGSVGElement>) {
    if (tools.panToolActive) {
      beginPan(event);
      return;
    }

    if (event.target !== event.currentTarget) return;
    if (!tools.atomToolActive) return;

    const modelPosition = clientToModelPosition(
      event,
      viewportLayerRef.current
    );

    onCanvasAddAtom(modelPosition);
  }

  function handleCanvasPointerMove(event: React.PointerEvent<SVGSVGElement>) {
    if (dragState.kind !== "pan") return;

    const rootPoint = clientToSvgLocalPoint(event, svgRef.current);

    onViewportChange({
      ...viewport,
      panX: dragState.startPanX + (rootPoint.x - dragState.startRootX),
      panY: dragState.startPanY + (rootPoint.y - dragState.startRootY),
    });
  }

  function handleCanvasPointerUp() {
    if (dragState.kind === "pan") {
      setDragState(emptyDragState);
    }
  }

  function handleAtomPointerDown(
    event: React.PointerEvent<SVGGElement>,
    atom: NormalizedAtom
  ) {
    if (tools.panToolActive) {
      return;
    }

    event.stopPropagation();

    if (tools.deleteToolActive) {
      onDeleteAtom(atom.id);
      return;
    }

    if (tools.radicalToolActive) {
      onToggleRadical(atom.id);
      onSelectAtom(atom.id);
      return;
    }

    if (tools.lonePairToolActive) {
      onToggleLonePair(atom.id);
      onSelectAtom(atom.id);
      return;
    }

    if (tools.chargeToolActive) {
      onSetAtomCharge(atom.id, defaultFormalCharge);
      onSelectAtom(atom.id);
      return;
    }

    if (tools.atomBondToolActive) {
      const basePoint = clientToBasePoint(event, viewportLayerRef.current);

      setDragState({
        kind: "extend-atom",
        atomId: atom.id,
        startBaseX: basePoint.x,
        startBaseY: basePoint.y,
        currentBaseX: basePoint.x,
        currentBaseY: basePoint.y,
        hasMoved: false,
      });

      event.currentTarget.setPointerCapture(event.pointerId);
      return;
    }

    if (tools.bondToolActive) {
      onSelectAtom(atom.id);
      return;
    }

    if (!tools.moveAtomToolActive) {
      onSelectAtom(atom.id);
      return;
    }

    const basePoint = clientToBasePoint(event, viewportLayerRef.current);

    setDragState({
      kind: "move-atom",
      atomId: atom.id,
      startBaseX: basePoint.x,
      startBaseY: basePoint.y,
      hasMoved: false,
    });

    event.currentTarget.setPointerCapture(event.pointerId);
    onSelectAtom(atom.id);
  }

  function handleAtomPointerMove(event: React.PointerEvent<SVGGElement>) {
    if (dragState.kind === "none" || dragState.kind === "pan") return;

    event.stopPropagation();

    const basePoint = clientToBasePoint(event, viewportLayerRef.current);

    if (dragState.kind === "extend-atom") {
      const startPoint = {
        x: dragState.startBaseX,
        y: dragState.startBaseY,
      };

      setDragState({
        ...dragState,
        currentBaseX: basePoint.x,
        currentBaseY: basePoint.y,
        hasMoved: dragState.hasMoved || distance(startPoint, basePoint) > 8,
      });

      return;
    }

    if (dragState.kind === "move-atom") {
      const startPoint = {
        x: dragState.startBaseX,
        y: dragState.startBaseY,
      };

      const hasMoved = dragState.hasMoved || distance(startPoint, basePoint) > 6;
      const modelPosition = baseScreenToModel(basePoint);

      if (hasMoved) {
        onMoveAtom(dragState.atomId, modelPosition);
      }

      setDragState({
        ...dragState,
        hasMoved,
      });
    }
  }

  function handleAtomPointerUp(event: React.PointerEvent<SVGGElement>) {
    if (dragState.kind === "none" || dragState.kind === "pan") return;

    event.stopPropagation();

    const modelPosition = clientToModelPosition(
      event,
      viewportLayerRef.current
    );

    if (dragState.kind === "extend-atom" && dragState.hasMoved) {
      onExtendAtomWithBond(dragState.atomId, modelPosition);
    }

    if (dragState.kind === "move-atom" && !dragState.hasMoved) {
      onSelectAtom(dragState.atomId);
    }

    setDragState(emptyDragState);
  }

  function handleBondClick(
    event: React.MouseEvent<SVGLineElement | SVGPolygonElement>,
    bondId: string
  ) {
    event.stopPropagation();

    if (tools.deleteToolActive) {
      onDeleteBond(bondId);
      return;
    }

    onSelectBond(bondId);
  }

  const isEmpty = atoms.length === 0;

  return (
    <div className="molecule-2d-viewer">
      <svg
        ref={svgRef}
        className={`molecule-2d-svg ${
          tools.atomToolActive ? "mode-add-atom" : ""
        } ${tools.bondToolActive ? "mode-bond" : ""} ${
          tools.panToolActive ? "mode-pan" : ""
        } ${tools.deleteToolActive ? "mode-delete" : ""}`}
        viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label="Editor 2D interativo da molécula"
        onPointerDown={handleCanvasPointerDown}
        onPointerMove={handleCanvasPointerMove}
        onPointerUp={handleCanvasPointerUp}
        onPointerCancel={handleCanvasPointerUp}
      >
        {isEmpty && (
          <g className="molecule-2d-empty-svg">
            <text x={VIEW_WIDTH / 2} y={VIEW_HEIGHT / 2 - 10} textAnchor="middle">
              Nenhuma molécula no ambiente
            </text>
            <text x={VIEW_WIDTH / 2} y={VIEW_HEIGHT / 2 + 18} textAnchor="middle">
              Escolha um elemento, ative “+ átomo” e clique aqui.
            </text>
          </g>
        )}

        <g
          ref={viewportLayerRef}
          className="molecule-2d-viewport-layer"
          transform={`matrix(${viewport.zoom} 0 0 ${viewport.zoom} ${viewport.panX} ${viewport.panY})`}
        >
          {/* Camada 1: glows e destaques de conjugação/ressonância */}
          <g className="molecule-2d-glow-layer">
            {bonds.map((bond) => {
              if (!shouldRenderConjugationGlow(bond)) return null;

              const path = getBondPath(bond, atomMap);

              if (!path) return null;

              const trimmedPath = trimBondPath(path, 10);

              return (
                <line
                  key={`glow-${bond.id}`}
                  className="molecule-2d-conjugation-glow"
                  x1={trimmedPath.x1}
                  y1={trimmedPath.y1}
                  x2={trimmedPath.x2}
                  y2={trimmedPath.y2}
                />
              );
            })}
          </g>

          {/* Camada 2: ligações */}
          <g className="molecule-2d-bonds">
            {bonds.map((bond) => {
              const path = getBondPath(bond, atomMap);

              if (!path) return null;

              const selected =
                selectedTarget?.kind === "bond" && selectedTarget.id === bond.id;

              return (
                <g key={bond.id}>
                  <line
                    x1={path.x1}
                    y1={path.y1}
                    x2={path.x2}
                    y2={path.y2}
                    className="molecule-2d-bond-hit"
                    onClick={(event) => handleBondClick(event, bond.id)}
                  />

                  {renderBondLines(bond, path, selected, (event) =>
                    handleBondClick(event, bond.id)
                  )}
                </g>
              );
            })}
          </g>

          {dragState.kind === "extend-atom" && (
            <line
              x1={dragState.startBaseX}
              y1={dragState.startBaseY}
              x2={dragState.currentBaseX}
              y2={dragState.currentBaseY}
              className="molecule-2d-preview-bond"
            />
          )}

          {/* Camada 3: borracha atômica */}
          <g className="molecule-2d-atom-erasers" pointerEvents="none">
            {normalizedAtoms.map((atom) => (
              <circle
                key={`eraser-${atom.id}`}
                className="molecule-2d-atom-eraser"
                cx={atom.screenX}
                cy={atom.screenY}
                r={ATOM_ERASER_RADIUS}
              />
            ))}
          </g>

          {/* Camada 4: símbolos e cargas */}
          <g className="molecule-2d-atoms">
            {normalizedAtoms.map((atom) => {
              const selected =
                selectedTarget?.kind === "atom" && selectedTarget.id === atom.id;

              const pending = pendingBondAtomId === atom.id;

              return (
                <g
                  key={atom.id}
                  className={`molecule-2d-atom ${selected ? "selected" : ""} ${
                    pending ? "pending-bond" : ""
                  }`}
                  transform={`translate(${atom.screenX} ${atom.screenY})`}
                  onPointerDown={(event) => handleAtomPointerDown(event, atom)}
                  onPointerMove={handleAtomPointerMove}
                  onPointerUp={handleAtomPointerUp}
                >
                  <circle
                    r={22}
                    fill={getAtomColor(atom.element)}
                    className="molecule-2d-atom-circle"
                  />

                  <text
                    textAnchor="middle"
                    dominantBaseline="central"
                    className="molecule-2d-atom-label"
                    fill={getAtomTextColor(atom.element)}
                  >
                    {atom.element}
                  </text>

                  {atom.formal_charge !== 0 && (
                    <text
                      x={18}
                      y={-18}
                      textAnchor="middle"
                      dominantBaseline="central"
                      className="molecule-2d-charge-label"
                    >
                      {atom.formal_charge > 0
                        ? `+${atom.formal_charge}`
                        : atom.formal_charge}
                    </text>
                  )}
                </g>
              );
            })}
          </g>

          {/* Camada 5: pares livres e radicais em espaço vazio */}
          <g className="molecule-2d-decorations">
            {normalizedAtoms.map((atom) => {
              const radicalCount = atom.radical_count ?? 0;
              const lonePairCount = atom.lone_pair_count ?? 0;
              const lonePairPlacement = getDecorationPlacement(
                atom,
                bonds,
                atomMap,
                "lonePair",
                0
              );
              const radicalPlacement = getDecorationPlacement(
                atom,
                bonds,
                atomMap,
                "radical",
                lonePairCount > 0 ? 1 : 0
              );

              return (
                <g key={`decor-${atom.id}`}>
                  {lonePairCount > 0 && (
                    <g
                      className="molecule-2d-lonepair"
                      onPointerDown={(event) => {
                        event.stopPropagation();
                        if (tools.deleteToolActive) {
                          onClearLonePair(atom.id);
                        } else {
                          onSelectAtom(atom.id);
                        }
                      }}
                    >
                      <circle
                        cx={lonePairPlacement.x - 4}
                        cy={lonePairPlacement.y}
                        r="2.7"
                      />
                      <circle
                        cx={lonePairPlacement.x + 4}
                        cy={lonePairPlacement.y}
                        r="2.7"
                      />
                    </g>
                  )}

                  {radicalCount > 0 && (
                    <g
                      className="molecule-2d-radical"
                      onPointerDown={(event) => {
                        event.stopPropagation();
                        if (tools.deleteToolActive) {
                          onClearRadical(atom.id);
                        } else {
                          onSelectAtom(atom.id);
                        }
                      }}
                    >
                      <circle cx={radicalPlacement.x} cy={radicalPlacement.y} r="3.5" />
                    </g>
                  )}
                </g>
              );
            })}
          </g>

          {/* Camada 6: metadados e numeração acima de tudo */}
          <g className="molecule-2d-metadata-layer" pointerEvents="none">
            {showAtomIndices &&
              normalizedAtoms.map((atom) => {
                const indexLabel = getAtomIndexLabel(atom);
                const placement = getDecorationPlacement(
                  atom,
                  bonds,
                  atomMap,
                  "index",
                  (atom.lone_pair_count ?? 0) > 0 || (atom.radical_count ?? 0) > 0
                    ? 1
                    : 0
                );
                const metrics = getIndexBadgeMetrics(indexLabel, placement);

                return (
                  <g key={`idx-${atom.id}`} className="atom-index-badge">
                    <rect
                      className="atom-index-shield"
                      x={metrics.rectX}
                      y={metrics.rectY}
                      width={metrics.width}
                      height={metrics.height}
                      rx="7"
                    />

                    <text
                      className="atom-index-label"
                      x={metrics.textX}
                      y={metrics.textY}
                      textAnchor={metrics.anchor}
                      dominantBaseline="middle"
                    >
                      {indexLabel}
                    </text>
                  </g>
                );
              })}
          </g>
        </g>
      </svg>

      <div className="molecule-2d-help">
        {tools.atomToolActive && (
          <span>Clique no ambiente para adicionar {selectedElement || "um átomo"}.</span>
        )}

        {tools.panToolActive && <span>Arraste para mover o ambiente inteiro.</span>}

        {tools.moveAtomToolActive && <span>Arraste um átomo para movê-lo.</span>}

        {tools.bondToolActive && (
          <span>
            Clique em dois átomos para criar ligação{" "}
            {getBondOrderLabel(selectedBondOrder)}.
          </span>
        )}

        {tools.atomBondToolActive && (
          <span>
            Arraste de um átomo existente para criar {selectedElement || "átomo"} ligado.
          </span>
        )}

        {tools.radicalToolActive && <span>Clique em átomo para radical.</span>}

        {tools.lonePairToolActive && <span>Clique em átomo para par livre.</span>}

        {tools.chargeToolActive && (
          <span>
            Clique em átomo para aplicar carga{" "}
            {defaultFormalCharge > 0
              ? `+${defaultFormalCharge}`
              : defaultFormalCharge}
            .
          </span>
        )}
      </div>
    </div>
  );
}

export default Molecule2DViewer;


