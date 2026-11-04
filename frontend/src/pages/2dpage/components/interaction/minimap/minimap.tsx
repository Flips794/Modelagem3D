import { useMemo, useRef, useState } from "react";

import type {
  CanvasViewport,
  InternalAtomModel,
  InternalMoleculeModel,
  Position2D,
} from "../../../type/rdkit2d.types";

import "./minimap.css";

type MinimapProps = {
  molecule: InternalMoleculeModel | null;
  viewport: CanvasViewport;
  onViewportChange: (viewport: CanvasViewport) => void;
  onResetViewport: () => void;
};

type MinimapAtom = InternalAtomModel & {
  x: number;
  y: number;
};

type MinimapWorld = {
  x: number;
  y: number;
  width: number;
  height: number;
};

type ViewportRect = {
  x: number;
  y: number;
  width: number;
  height: number;
};

const VIEW_WIDTH = 900;
const VIEW_HEIGHT = 520;
const MODEL_SCALE = 72;
const MIN_ZOOM = 0.45;
const MAX_ZOOM = 3;

/*
 * O minimapa não deve recalcular dados químicos nem emitir eventos de molécula.
 * Ele só altera viewport. A área do mapa é deliberadamente maior do que o
 * canvas base para que o retângulo de zoom não preencha sempre o minimapa.
 */
const MINIMAP_WORLD_PADDING = 0.18;
const MINIMAP_EXTRA_VIEW_MARGIN = 80;

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function modelToScreen(position: Position2D): Position2D {
  return {
    x: VIEW_WIDTH / 2 + position.x * MODEL_SCALE,
    y: VIEW_HEIGHT / 2 - position.y * MODEL_SCALE,
  };
}

function atomsForMinimap(atoms: InternalAtomModel[]): MinimapAtom[] {
  return atoms.map((atom) => {
    const position = modelToScreen(atom.position_2d);

    return {
      ...atom,
      x: position.x,
      y: position.y,
    };
  });
}

function viewportToRect(viewport: CanvasViewport): ViewportRect {
  const zoom = Math.max(0.001, viewport.zoom);

  return {
    x: -viewport.panX / zoom,
    y: -viewport.panY / zoom,
    width: VIEW_WIDTH / zoom,
    height: VIEW_HEIGHT / zoom,
  };
}

function getMinimapWorld(
  atoms: MinimapAtom[],
  viewportRect: ViewportRect
): MinimapWorld {
  /*
   * Base fixa do canvas + margem.
   * Isso impede o comportamento visual antigo em que a área visível ocupava
   * sempre o minimapa inteiro, principalmente em zoom 100%.
   */
  const basePaddingX = VIEW_WIDTH * MINIMAP_WORLD_PADDING;
  const basePaddingY = VIEW_HEIGHT * MINIMAP_WORLD_PADDING;

  let minX = -basePaddingX;
  let minY = -basePaddingY;
  let maxX = VIEW_WIDTH + basePaddingX;
  let maxY = VIEW_HEIGHT + basePaddingY;

  atoms.forEach((atom) => {
    minX = Math.min(minX, atom.x - MINIMAP_EXTRA_VIEW_MARGIN);
    minY = Math.min(minY, atom.y - MINIMAP_EXTRA_VIEW_MARGIN);
    maxX = Math.max(maxX, atom.x + MINIMAP_EXTRA_VIEW_MARGIN);
    maxY = Math.max(maxY, atom.y + MINIMAP_EXTRA_VIEW_MARGIN);
  });

  /*
   * Inclui o retângulo de viewport quando o usuário arrasta/pan para fora
   * da região molecular. Assim o indicador não some do minimapa.
   */
  minX = Math.min(minX, viewportRect.x - MINIMAP_EXTRA_VIEW_MARGIN);
  minY = Math.min(minY, viewportRect.y - MINIMAP_EXTRA_VIEW_MARGIN);
  maxX = Math.max(
    maxX,
    viewportRect.x + viewportRect.width + MINIMAP_EXTRA_VIEW_MARGIN
  );
  maxY = Math.max(
    maxY,
    viewportRect.y + viewportRect.height + MINIMAP_EXTRA_VIEW_MARGIN
  );

  return {
    x: minX,
    y: minY,
    width: Math.max(1, maxX - minX),
    height: Math.max(1, maxY - minY),
  };
}

/**
 * Conversão do ponteiro para a coordenada real do minimapa.
 * Usa o viewBox dinâmico do minimapa e respeita preserveAspectRatio="xMidYMid meet".
 */
function clientToMinimapWorldPoint(
  event: React.PointerEvent<SVGSVGElement>,
  svg: SVGSVGElement | null,
  world: MinimapWorld
): Position2D {
  if (!svg) {
    return {
      x: VIEW_WIDTH / 2,
      y: VIEW_HEIGHT / 2,
    };
  }

  const rect = svg.getBoundingClientRect();

  if (rect.width <= 0 || rect.height <= 0) {
    return {
      x: VIEW_WIDTH / 2,
      y: VIEW_HEIGHT / 2,
    };
  }

  const svgAspect = world.width / world.height;
  const rectAspect = rect.width / rect.height;

  let renderedWidth = rect.width;
  let renderedHeight = rect.height;
  let offsetX = 0;
  let offsetY = 0;

  if (rectAspect > svgAspect) {
    renderedHeight = rect.height;
    renderedWidth = renderedHeight * svgAspect;
    offsetX = (rect.width - renderedWidth) / 2;
  } else {
    renderedWidth = rect.width;
    renderedHeight = renderedWidth / svgAspect;
    offsetY = (rect.height - renderedHeight) / 2;
  }

  const localX = clamp(event.clientX - rect.left - offsetX, 0, renderedWidth);
  const localY = clamp(event.clientY - rect.top - offsetY, 0, renderedHeight);

  return {
    x: world.x + (localX / renderedWidth) * world.width,
    y: world.y + (localY / renderedHeight) * world.height,
  };
}

function centerViewportAt(point: Position2D, viewport: CanvasViewport) {
  return {
    ...viewport,
    panX: VIEW_WIDTH / 2 - point.x * viewport.zoom,
    panY: VIEW_HEIGHT / 2 - point.y * viewport.zoom,
  };
}

function zoomViewportAtCenter(viewport: CanvasViewport, nextZoom: number) {
  const centerPoint = {
    x: VIEW_WIDTH / 2,
    y: VIEW_HEIGHT / 2,
  };

  const baseCenterBeforeZoom = {
    x: (centerPoint.x - viewport.panX) / viewport.zoom,
    y: (centerPoint.y - viewport.panY) / viewport.zoom,
  };

  return {
    zoom: nextZoom,
    panX: centerPoint.x - baseCenterBeforeZoom.x * nextZoom,
    panY: centerPoint.y - baseCenterBeforeZoom.y * nextZoom,
  };
}

function rectStrokeWidth(world: MinimapWorld) {
  return Math.max(3, Math.min(12, world.width / 220));
}

function atomRadius(world: MinimapWorld) {
  return Math.max(7, Math.min(13, world.width / 110));
}

export function Minimap({
  molecule,
  viewport,
  onViewportChange,
  onResetViewport,
}: MinimapProps) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [dragging, setDragging] = useState(false);

  const atoms = useMemo(() => atomsForMinimap(molecule?.atoms ?? []), [molecule]);

  const atomMap = useMemo(() => {
    return new Map(atoms.map((atom) => [atom.id, atom]));
  }, [atoms]);

  const viewportRect = useMemo(() => viewportToRect(viewport), [viewport]);

  const minimapWorld = useMemo(
    () => getMinimapWorld(atoms, viewportRect),
    [atoms, viewportRect]
  );

  const markerRadius = atomRadius(minimapWorld);
  const viewportStrokeWidth = rectStrokeWidth(minimapWorld);

  function handlePointerDown(event: React.PointerEvent<SVGSVGElement>) {
    const point = clientToMinimapWorldPoint(event, svgRef.current, minimapWorld);

    setDragging(true);
    onViewportChange(centerViewportAt(point, viewport));
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function handlePointerMove(event: React.PointerEvent<SVGSVGElement>) {
    if (!dragging) return;

    const point = clientToMinimapWorldPoint(event, svgRef.current, minimapWorld);
    onViewportChange(centerViewportAt(point, viewport));
  }

  function handlePointerUp() {
    setDragging(false);
  }

  function zoomIn() {
    const nextZoom = Math.min(
      MAX_ZOOM,
      Number((viewport.zoom * 1.12).toFixed(3))
    );

    onViewportChange(zoomViewportAtCenter(viewport, nextZoom));
  }

  function zoomOut() {
    const nextZoom = Math.max(
      MIN_ZOOM,
      Number((viewport.zoom / 1.12).toFixed(3))
    );

    onViewportChange(zoomViewportAtCenter(viewport, nextZoom));
  }

  return (
    <div className="minimap-panel">
      <div className="minimap-topbar">
        <strong>Minimapa</strong>

        <div className="minimap-actions">
          <button type="button" onClick={zoomOut}>
            −
          </button>

          <span>{Math.round(viewport.zoom * 100)}%</span>

          <button type="button" onClick={zoomIn}>
            +
          </button>

          <button type="button" onClick={onResetViewport}>
            Centralizar
          </button>
        </div>
      </div>

      <svg
        ref={svgRef}
        className="minimap-svg"
        viewBox={`${minimapWorld.x} ${minimapWorld.y} ${minimapWorld.width} ${minimapWorld.height}`}
        preserveAspectRatio="xMidYMid meet"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
      >
        <rect
          className="minimap-bg"
          x={minimapWorld.x}
          y={minimapWorld.y}
          width={minimapWorld.width}
          height={minimapWorld.height}
        />

        <rect
          className="minimap-world-outline"
          x="0"
          y="0"
          width={VIEW_WIDTH}
          height={VIEW_HEIGHT}
        />

        <line
          className="minimap-axis"
          x1={VIEW_WIDTH / 2}
          y1="0"
          x2={VIEW_WIDTH / 2}
          y2={VIEW_HEIGHT}
        />
        <line
          className="minimap-axis"
          x1="0"
          y1={VIEW_HEIGHT / 2}
          x2={VIEW_WIDTH}
          y2={VIEW_HEIGHT / 2}
        />

        {molecule?.bonds.map((bond) => {
          const atomA = atomMap.get(bond.atom_a_id);
          const atomB = atomMap.get(bond.atom_b_id);

          if (!atomA || !atomB) return null;

          return (
            <line
              key={bond.id}
              className="minimap-bond"
              x1={atomA.x}
              y1={atomA.y}
              x2={atomB.x}
              y2={atomB.y}
            />
          );
        })}

        {atoms.map((atom) => (
          <circle
            key={atom.id}
            className="minimap-atom"
            cx={atom.x}
            cy={atom.y}
            r={markerRadius}
          />
        ))}

        <rect
          className="minimap-viewport-rect"
          x={viewportRect.x}
          y={viewportRect.y}
          width={viewportRect.width}
          height={viewportRect.height}
          strokeWidth={viewportStrokeWidth}
          vectorEffect="non-scaling-stroke"
        />
      </svg>
    </div>
  );
}

export default Minimap;


