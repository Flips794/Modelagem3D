import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";

import type {
  MiceliumAnalysis3D,
  MiceliumCluster3D,
  SimulationAtom3D,
  SimulationBond3D,
  SimulationBox3D,
  SimulationFrame3D,
  SimulationStreamMessage3D,
  SimulationTopology3D,
} from "../../type/3dpage.types";

import { API_BASE_URL } from "../../../../config/apiBaseUrl";

import "./SimulationViewer3D.css";

type SimulationViewer3DProps = {
  topology: SimulationTopology3D | null;
  frame: SimulationFrame3D | null;
  websocketUrl?: string;
  showSolvent: boolean;
  selectedMoleculeId: string | null;
  onSelectMolecule: (moleculeId: string | null) => void;
  onStatus?: (message: string) => void;
};

type ElementColorMap = Record<string, string>;

type BackendElement = {
  symbol?: string;
  color?: string | null;
  color_hex?: string | null;
  colorHex?: string | null;
};

type BackendElementsPayload =
  | BackendElement[]
  | {
      elements?: BackendElement[];
      items?: BackendElement[];
      data?: BackendElement[];
      results?: BackendElement[];
    };

type AtomMeshGroup = {
  mesh: THREE.InstancedMesh;
  atoms: SimulationAtom3D[];
  color: string;
};

type MoleculeCenter3D = {
  moleculeId: string;
  kind: "surfactant" | "solute" | "solvent";
  center: THREE.Vector3;
  atomCount: number;
};

type SpatialCenterGrid3D = {
  cellSize: number;
  cells: Map<string, MoleculeCenter3D[]>;
};

function spatialKeyFromVector(vector: THREE.Vector3, cellSize: number) {
  return `${Math.floor(vector.x / cellSize)}:${Math.floor(vector.y / cellSize)}:${Math.floor(vector.z / cellSize)}`;
}

function buildSpatialCenterGrid(
  centers: MoleculeCenter3D[],
  cellSize: number
): SpatialCenterGrid3D {
  const cells = new Map<string, MoleculeCenter3D[]>();

  centers.forEach((center) => {
    const key = spatialKeyFromVector(center.center, cellSize);
    const bucket = cells.get(key) ?? [];

    bucket.push(center);
    cells.set(key, bucket);
  });

  return {
    cellSize,
    cells,
  };
}

function collectNearbyCenters(
  grid: SpatialCenterGrid3D,
  source: THREE.Vector3,
  maxDistance: number,
  excludeMoleculeId?: string
): MoleculeCenter3D[] {
  const results: MoleculeCenter3D[] = [];
  const range = Math.max(1, Math.ceil(maxDistance / grid.cellSize));
  const sourceX = Math.floor(source.x / grid.cellSize);
  const sourceY = Math.floor(source.y / grid.cellSize);
  const sourceZ = Math.floor(source.z / grid.cellSize);

  for (let dx = -range; dx <= range; dx += 1) {
    for (let dy = -range; dy <= range; dy += 1) {
      for (let dz = -range; dz <= range; dz += 1) {
        const bucket = grid.cells.get(
          `${sourceX + dx}:${sourceY + dy}:${sourceZ + dz}`
        );

        if (!bucket) continue;

        bucket.forEach((candidate) => {
          if (excludeMoleculeId && candidate.moleculeId === excludeMoleculeId) {
            return;
          }

          if (source.distanceTo(candidate.center) <= maxDistance) {
            results.push(candidate);
          }
        });
      }
    }
  }

  return results;
}

const ELEMENT_COLOR_ENDPOINTS = [
  "/reference-data/elements",
  "/chemical-parameters/elements",
  "/reference-data/elements/raw",
  "/chemical-parameters/elements/raw",
];

const CPK_COLORS: ElementColorMap = {
  H: "#FFFFFF",
  C: "#9099A5",
  N: "#3050F8",
  O: "#FF0D0D",
  F: "#90E050",
  Cl: "#1FF01F",
  Br: "#A62929",
  I: "#940094",
  P: "#FF8000",
  S: "#FFFF30",
  B: "#FFB5B5",
  Si: "#F0C8A0",
  Na: "#AB5CF2",
  K: "#8F40D4",
  Ca: "#3DFF00",
  Fe: "#E06633",
  Cu: "#C88033",
  Zn: "#7D80B0",
};

const FALLBACK_ELEMENT_COLORS: ElementColorMap = {
  H: "#FFFFFF",
  C: "#9099A5",
  N: "#3050F8",
  O: "#FF0D0D",
  F: "#90E050",
  Cl: "#1FF01F",
  Br: "#A62929",
  I: "#940094",
  P: "#FF8000",
  S: "#FFFF30",
  Na: "#AB5CF2",
  K: "#8F40D4",
  Ca: "#3DFF00",
  Fe: "#E06633",
  Cu: "#C88033",
  Zn: "#7D80B0",
};

const ATOM_RADIUS: Record<string, number> = {
  H: 0.18,
  C: 0.34,
  N: 0.32,
  O: 0.32,
  F: 0.3,
  Cl: 0.42,
  Br: 0.46,
  I: 0.52,
  P: 0.45,
  S: 0.45,
  Na: 0.48,
  K: 0.55,
};

const CYLINDER_UP_AXIS = new THREE.Vector3(0, 1, 0);
const BOND_RADIUS = 0.075;
const SHOW_GLOBAL_MICELLE_OVERLAY = false;

/*
 * Segurança visual: ligações topológicas muito longas geralmente indicam
 * artefato de fronteira/teletransporte. A ligação química continua existindo
 * na topologia, mas não é desenhada atravessando a cena inteira.
 */
const MAX_RENDERED_TOPOLOGICAL_BOND_LENGTH = 1.65;
const MIN_VISIBLE_LUMINANCE = 0.34;
const DARK_COLOR_LIFT_TARGET = new THREE.Color("#CBD5E1");

export const REPRESENTATION_LABEL = "Visualização representativa — não é simulação física";
const CAMERA_MIN_DISTANCE = 8;
const CAMERA_MAX_DISTANCE = 220;

/** Selo permanente: vem da análise quando houver, senão a mesma frase fixa. */
export function viewerSealText(analysis: { representation_label?: string | null } | null | undefined) {
  return analysis?.representation_label || REPRESENTATION_LABEL;
}

/** Zoom de pinça: afastar os dedos (span maior) aproxima a câmera, dentro dos limites da roda. */
export function pinchDistance(current: number, previousSpan: number, nextSpan: number) {
  if (previousSpan <= 0 || nextSpan <= 0) return current;
  return clamp(current * (previousSpan / nextSpan), CAMERA_MIN_DISTANCE, CAMERA_MAX_DISTANCE);
}

/** Rótulo da cena; forma confirmada de exemplo documentado vem de molde/força visual e é identificada. */
export function sceneMorphologyLabel(analysis: MiceliumAnalysis3D | null | undefined, fallback = "—") {
  const label = analysis?.dominant_morphology ?? fallback;
  const fromTemplate = analysis?.morphology_source === "documented_example" && label === analysis?.predicted_morphology;
  return fromTemplate ? `${label} (recurso visual ilustrativo)` : label;
}

/** Enquadramento: centro do maior agregado e distância proporcional ao raio, dentro dos limites do zoom. */
export function cameraFrameForClusters(clusters: MiceliumCluster3D[] | null | undefined) {
  const largest = [...(clusters ?? [])].sort((a, b) => b.surfactant_count - a.surfactant_count)[0];
  if (!largest || largest.center.length < 3) return null;
  return {
    target: largest.center.slice(0, 3) as [number, number, number],
    distance: clamp(3.4 * largest.radius + 12, CAMERA_MIN_DISTANCE, CAMERA_MAX_DISTANCE),
  };
}

/** Posição da câmera na órbita em volta do alvo (ângulos e distância do controle de arrastar e zoom). */
export function orbitCameraPosition(angleX: number, angleY: number, distance: number,
  target: [number, number, number]): [number, number, number] {
  return [
    target[0] + Math.cos(angleX) * Math.sin(angleY) * distance,
    target[1] + Math.sin(angleX) * distance,
    target[2] + Math.cos(angleX) * Math.cos(angleY) * distance,
  ];
}

/** Mesma mistura (trechos seguidos) → mesma chave: a câmera só é reenquadrada quando a mistura muda. */
export function framingKey(topology: { atoms: unknown[]; analysis?: MiceliumAnalysis3D | null } | null | undefined) {
  if (!topology) return "";
  const analysis = topology.analysis;
  return `${topology.atoms.length}|${analysis?.predicted_morphology ?? ""}|${analysis?.documented_example?.id ?? ""}`;
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function normalizeSymbol(value: unknown) {
  const symbol = String(value ?? "").trim();

  if (!symbol) return "";
  if (symbol.length === 1) return symbol.toUpperCase();

  return `${symbol.charAt(0).toUpperCase()}${symbol.slice(1).toLowerCase()}`;
}

function normalizeHexColor(value: unknown): string | null {
  if (typeof value !== "string") return null;

  const trimmed = value.trim();

  if (/^#[0-9a-fA-F]{6}$/.test(trimmed)) {
    return trimmed.toUpperCase();
  }

  if (/^[0-9a-fA-F]{6}$/.test(trimmed)) {
    return `#${trimmed.toUpperCase()}`;
  }

  return null;
}

function getColorLuminance(color: THREE.Color) {
  return 0.2126 * color.r + 0.7152 * color.g + 0.0722 * color.b;
}

function makeRenderableColor(preferredColor: unknown, fallbackColor = "#CBD5E1") {
  const safePreferred = normalizeHexColor(preferredColor);
  const safeFallback = normalizeHexColor(fallbackColor) ?? "#CBD5E1";
  const color = new THREE.Color(safePreferred ?? safeFallback);
  const luminance = getColorLuminance(color);

  if (luminance < MIN_VISIBLE_LUMINANCE) {
    const liftAmount = clamp(
      ((MIN_VISIBLE_LUMINANCE - luminance) / MIN_VISIBLE_LUMINANCE) * 0.76,
      0.24,
      0.76
    );

    color.lerp(DARK_COLOR_LIFT_TARGET, liftAmount);
  }

  return `#${color.getHexString().toUpperCase()}`;
}

function extractElementItems(data: unknown): BackendElement[] {
  if (Array.isArray(data)) return data as BackendElement[];

  if (!data || typeof data !== "object") return [];

  const wrapped = data as {
    items?: BackendElement[];
    elements?: BackendElement[];
    data?: BackendElement[];
    results?: BackendElement[];
  };

  return wrapped.items ?? wrapped.elements ?? wrapped.data ?? wrapped.results ?? [];
}

async function loadElementColorMapForViewer(): Promise<ElementColorMap> {
  const nextMap: ElementColorMap = {};

  for (const path of ELEMENT_COLOR_ENDPOINTS) {
    try {
      const response = await fetch(`${API_BASE_URL}${path}`);

      if (!response.ok) continue;

      const data = (await response.json()) as BackendElementsPayload;
      const items = extractElementItems(data);

      items.forEach((item) => {
        const symbol = normalizeSymbol(item.symbol);
        const color = normalizeHexColor(
          item.colorHex ?? item.color_hex ?? item.color
        );

        if (!symbol || !color) return;

        nextMap[symbol] = color;
      });

      if (Object.keys(nextMap).length > 0) {
        return nextMap;
      }
    } catch {
      // Fallback CPK mantém o visual funcionando mesmo se o backend cair.
    }
  }

  return FALLBACK_ELEMENT_COLORS;
}

function getAtomColor(atom: SimulationAtom3D, elementColorMap: ElementColorMap) {
  const symbol = normalizeSymbol(atom.element);
  const databaseColor = elementColorMap[symbol];
  const fallback = CPK_COLORS[symbol] ?? FALLBACK_ELEMENT_COLORS[symbol] ?? "#CBD5E1";

  return makeRenderableColor(atom.color ?? databaseColor, fallback);
}

function getAtomRadius(atom: SimulationAtom3D) {
  const symbol = normalizeSymbol(atom.element);

  return atom.radius ?? ATOM_RADIUS[symbol] ?? 0.34;
}

function getBoxCenter(box: SimulationBox3D) {
  return box.center ?? { x: 0, y: 0, z: 0 };
}

function createBoxGeometry(box: SimulationBox3D) {
  const center = getBoxCenter(box);

  const hx = box.x / 2;
  const hy = box.y / 2;
  const hz = box.z / 2;

  const x0 = center.x - hx;
  const x1 = center.x + hx;
  const y0 = center.y - hy;
  const y1 = center.y + hy;
  const z0 = center.z - hz;
  const z1 = center.z + hz;

  const vertices = new Float32Array([
    x0, y0, z0, x1, y0, z0,
    x1, y0, z0, x1, y0, z1,
    x1, y0, z1, x0, y0, z1,
    x0, y0, z1, x0, y0, z0,

    x0, y1, z0, x1, y1, z0,
    x1, y1, z0, x1, y1, z1,
    x1, y1, z1, x0, y1, z1,
    x0, y1, z1, x0, y1, z0,

    x0, y0, z0, x0, y1, z0,
    x1, y0, z0, x1, y1, z0,
    x1, y0, z1, x1, y1, z1,
    x0, y0, z1, x0, y1, z1,
  ]);

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(vertices, 3));

  return geometry;
}

function isSolventAtom(atom: SimulationAtom3D) {
  if (atom.isSolvent) return true;

  const residue = atom.residueName?.toUpperCase();

  return (
    residue === "HOH" ||
    residue === "WAT" ||
    residue === "SOL" ||
    residue === "H2O"
  );
}

function isSurfactantAtom(atom: SimulationAtom3D) {
  return atom.residueName === "SURF";
}

function isLigandOrSoluteAtom(atom: SimulationAtom3D) {
  return atom.residueName === "LIG";
}

function shouldRenderAtom(atom: SimulationAtom3D, showSolvent: boolean) {
  return showSolvent || !isSolventAtom(atom);
}

function isLongPbcBond(
  atomA: [number, number, number],
  atomB: [number, number, number],
  box: SimulationBox3D | undefined
) {
  if (!box) return false;

  const dx = atomA[0] - atomB[0];
  const dy = atomA[1] - atomB[1];
  const dz = atomA[2] - atomB[2];

  const distance = Math.sqrt(dx * dx + dy * dy + dz * dz);
  const cutoff = Math.min(MAX_RENDERED_TOPOLOGICAL_BOND_LENGTH, Math.min(box.x, box.y, box.z) * 0.48);

  return distance > cutoff;
}

function disposeObject(object: THREE.Object3D) {
  object.traverse((child) => {
    if (child instanceof THREE.Mesh || child instanceof THREE.LineSegments || child instanceof THREE.Line) {
      if (child.geometry) child.geometry.dispose();

      if (Array.isArray(child.material)) {
        child.material.forEach((material) => material.dispose());
      } else if (child.material) {
        child.material.dispose();
      }
    }
  });
}

function toFiniteCoordinate(value: unknown, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function cloneCoordinates(
  coordinates: Array<[number, number, number]> | unknown
): Array<[number, number, number]> {
  if (!Array.isArray(coordinates)) return [];

  return coordinates.map((coordinate) => [
    toFiniteCoordinate((coordinate as unknown[] | undefined)?.[0]),
    toFiniteCoordinate((coordinate as unknown[] | undefined)?.[1]),
    toFiniteCoordinate((coordinate as unknown[] | undefined)?.[2]),
  ]);
}

function getFrameKey(frame: SimulationFrame3D) {
  const coordinatesLength = Array.isArray(frame.coordinates)
    ? frame.coordinates.length
    : 0;

  return `${frame.frameIndex}:${frame.timePs}:${coordinatesLength}`;
}

function renderWebGLError(mount: HTMLDivElement) {
  mount.innerHTML = `
    <div style="
      width: 100%;
      height: 100%;
      min-height: 420px;
      display: grid;
      place-items: center;
      padding: 24px;
      background:
        radial-gradient(circle at center, rgba(239, 68, 68, 0.12), transparent 42%),
        #020617;
      color: #e5e7eb;
      border-radius: 22px;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    ">
      <div style="
        max-width: 560px;
        display: grid;
        gap: 10px;
        border: 1px solid rgba(248, 113, 113, 0.28);
        border-radius: 18px;
        padding: 18px;
        background: rgba(15, 23, 42, 0.92);
        text-align: center;
      ">
        <strong style="color:#fecaca;font-size:1rem;font-weight:950;">
          WebGL indisponível
        </strong>
        <span style="color:#cbd5e1;font-size:0.82rem;line-height:1.5;">
          O navegador não conseguiu iniciar o motor 3D. Ative a aceleração de
          hardware, atualize o driver de vídeo ou teste em outro navegador.
        </span>
      </div>
    </div>
  `;
}

function createSafeRenderer(
  mount: HTMLDivElement,
  onStatus?: (message: string) => void
) {
  try {
    return new THREE.WebGLRenderer({
      antialias: true,
      alpha: false,
      powerPreference: "high-performance",
      failIfMajorPerformanceCaveat: false,
    });
  } catch (error) {
    console.error("Falha ao criar contexto WebGL:", error);

    onStatus?.(
      "WebGL indisponível. Ative a aceleração de hardware no navegador ou atualize o driver de vídeo."
    );

    renderWebGLError(mount);

    return null;
  }
}

function collectMoleculeCenters(
  atoms: SimulationAtom3D[],
  coordinates: Array<[number, number, number]>
): MoleculeCenter3D[] {
  const entries = new Map<
    string,
    {
      kind: MoleculeCenter3D["kind"];
      sum: THREE.Vector3;
      atomCount: number;
    }
  >();

  atoms.forEach((atom) => {
    const coordinate = coordinates[atom.index];

    if (!coordinate) return;

    const kind: MoleculeCenter3D["kind"] = isSurfactantAtom(atom)
      ? "surfactant"
      : isLigandOrSoluteAtom(atom)
        ? "solute"
        : "solvent";

    const entry =
      entries.get(atom.moleculeId) ??
      {
        kind,
        sum: new THREE.Vector3(),
        atomCount: 0,
      };

    entry.sum.add(new THREE.Vector3(coordinate[0], coordinate[1], coordinate[2]));
    entry.atomCount += 1;

    if (kind === "surfactant" || entry.kind === "solvent") {
      entry.kind = kind;
    }

    entries.set(atom.moleculeId, entry);
  });

  return Array.from(entries.entries()).map(([moleculeId, entry]) => ({
    moleculeId,
    kind: entry.kind,
    center: entry.sum.multiplyScalar(1 / Math.max(entry.atomCount, 1)),
    atomCount: entry.atomCount,
  }));
}

export default function SimulationViewer3D({
  topology,
  frame,
  websocketUrl,
  showSolvent,
  selectedMoleculeId,
  onSelectMolecule,
  onStatus,
}: SimulationViewer3DProps) {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);

  const atomMeshGroupsRef = useRef<AtomMeshGroup[]>([]);
  const bondMeshRef = useRef<THREE.InstancedMesh | null>(null);
  const boxLinesRef = useRef<THREE.LineSegments | null>(null);
  const supramolecularOverlayRef = useRef<THREE.Group | null>(null);
  const interactionLinesRef = useRef<THREE.LineSegments | null>(null);
  const overlayFrameCounterRef = useRef(0);

  const visibleAtomsRef = useRef<SimulationAtom3D[]>([]);
  const visibleBondsRef = useRef<SimulationBond3D[]>([]);

  const latestFrameRef = useRef<SimulationFrame3D | null>(frame);
  const latestTopologyRef = useRef<SimulationTopology3D | null>(topology);

  const previousCoordinatesRef = useRef<Array<[number, number, number]> | null>(
    null
  );
  const targetCoordinatesRef = useRef<Array<[number, number, number]> | null>(
    null
  );
  const currentCoordinatesRef = useRef<Array<[number, number, number]>>([]);

  const interpolationStartTimeRef = useRef(0);
  const interpolationDurationMsRef = useRef(100);
  const lastIncomingFrameAtRef = useRef<number | null>(null);
  const lastAcceptedFrameKeyRef = useRef("");

  const reusableAtomObjectRef = useRef(new THREE.Object3D());
  const reusableBondObjectRef = useRef(new THREE.Object3D());

  const startVectorRef = useRef(new THREE.Vector3());
  const targetVectorRef = useRef(new THREE.Vector3());
  const renderVectorRef = useRef(new THREE.Vector3());

  const bondStartRef = useRef(new THREE.Vector3());
  const bondEndRef = useRef(new THREE.Vector3());
  const bondMidpointRef = useRef(new THREE.Vector3());
  const bondDirectionRef = useRef(new THREE.Vector3());
  const bondQuaternionRef = useRef(new THREE.Quaternion());

  const animationRef = useRef<number | null>(null);
  const raycasterRef = useRef(new THREE.Raycaster());
  const pointerRef = useRef(new THREE.Vector2());

  const cameraStateRef = useRef({
    angleX: -0.62,
    angleY: 0.74,
    distance: 42,
    target: new THREE.Vector3(0, 0, 0),
  });

  const [streamTopology, setStreamTopology] =
    useState<SimulationTopology3D | null>(null);
  const [streamFrame, setStreamFrame] = useState<SimulationFrame3D | null>(
    null
  );
  const [elementColorMap, setElementColorMap] = useState<ElementColorMap>({});

  const activeTopology = streamTopology ?? topology;
  const activeFrame = streamFrame ?? frame;

  const atomCountLabel = useMemo(() => {
    if (!activeTopology) return "sem topologia";
    return `${activeTopology.atoms.length} partículas · ${activeTopology.bonds.length} ligações`;
  }, [activeTopology]);

  const morphologyLabel = sceneMorphologyLabel(activeTopology?.analysis, activeTopology?.clusters?.[0]?.morphology ?? "emergente");
  const formationPhaseLabel = activeTopology?.analysis?.formation_phase ?? "formação";

  useEffect(() => {
    latestTopologyRef.current = activeTopology;
  }, [activeTopology]);

  // Mistura nova: enquadra o maior agregado (sem isso, agregados fora da origem ficavam cortados).
  const framedKeyRef = useRef("");
  useEffect(() => {
    const key = framingKey(activeTopology);
    if (!key || key === framedKeyRef.current) return;
    const frame = cameraFrameForClusters(activeTopology?.clusters);
    if (!frame) return;
    framedKeyRef.current = key;
    cameraStateRef.current.target.set(...frame.target);
    cameraStateRef.current.distance = frame.distance;
  }, [activeTopology]);

  useEffect(() => {
    if (!activeFrame) return;

    acceptTargetFrame(activeFrame);
  }, [activeFrame]);

  useEffect(() => {
    let alive = true;

    async function loadColors() {
      const colors = await loadElementColorMapForViewer();

      if (!alive) return;

      setElementColorMap(colors);
    }

    void loadColors();

    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!websocketUrl) return;

    const socket = new WebSocket(websocketUrl);

    socket.onopen = () => onStatus?.("Stream 3D conectada.");
    socket.onclose = () => onStatus?.("Stream 3D desconectada.");
    socket.onerror = () => onStatus?.("Erro na stream 3D.");

    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as SimulationStreamMessage3D;

        if (message.type === "topology") {
          setStreamTopology(message.topology);
          onStatus?.("Topologia 3D recebida.");
        }

        if (message.type === "frame") {
          setStreamFrame(message.frame);
        }

        if (message.type === "status" || message.type === "error") {
          onStatus?.(message.message);
        }
      } catch {
        onStatus?.("Frame 3D inválido recebido pela stream.");
      }
    };

    return () => socket.close();
  }, [websocketUrl, onStatus]);

  useEffect(() => {
    const mount = mountRef.current;

    if (!mount) return;

    mount.innerHTML = "";

    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#020617");
    scene.fog = new THREE.Fog("#020617", 80, 220);

    const camera = new THREE.PerspectiveCamera(54, 1, 0.1, 2500);
    camera.position.set(0, 18, 42);
    camera.lookAt(0, 0, 0);

    const renderer = createSafeRenderer(mount, onStatus);

    if (!renderer) {
      scene.clear();
      return;
    }

    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor("#020617", 1);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.NoToneMapping;

    mount.appendChild(renderer.domElement);

    scene.add(new THREE.AmbientLight("#ffffff", 1.35));

    const hemisphere = new THREE.HemisphereLight("#e0f2fe", "#0f172a", 1.25);
    scene.add(hemisphere);

    const keyLight = new THREE.DirectionalLight("#ffffff", 2.2);
    keyLight.position.set(18, 26, 20);
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight("#bae6fd", 1.15);
    fillLight.position.set(-22, 12, -18);
    scene.add(fillLight);

    sceneRef.current = scene;
    cameraRef.current = camera;
    rendererRef.current = renderer;

    const resize = () => {
      if (!mountRef.current || !rendererRef.current || !cameraRef.current) return;

      const width = Math.max(mountRef.current.clientWidth, 320);
      const height = Math.max(mountRef.current.clientHeight, 420);

      rendererRef.current.setSize(width, height, false);
      cameraRef.current.aspect = width / height;
      cameraRef.current.updateProjectionMatrix();
    };

    resize();

    const observer = new ResizeObserver(resize);
    observer.observe(mount);

    // Ponteiros ativos (mouse, dedo, caneta): 1 gira, 2 fazem pinça.
    const activePointers = new Map<number, { x: number; y: number }>();
    let pinchSpan: number | null = null;
    const currentSpan = () => {
      const [a, b] = [...activePointers.values()];
      return a && b ? Math.hypot(a.x - b.x, a.y - b.y) : 0;
    };

    const handlePointerDown = (event: PointerEvent) => {
      activePointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
      renderer.domElement.setPointerCapture?.(event.pointerId);
      if (activePointers.size === 2) {
        pinchSpan = currentSpan();
        return; // segundo dedo: começa a pinça, não seleciona molécula
      }

      const rendererInstance = rendererRef.current;
      const cameraInstance = cameraRef.current;
      const atomMeshes = atomMeshGroupsRef.current.map((group) => group.mesh);

      if (!rendererInstance || !cameraInstance || atomMeshes.length === 0) return;

      const rect = rendererInstance.domElement.getBoundingClientRect();

      pointerRef.current.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      pointerRef.current.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

      raycasterRef.current.setFromCamera(pointerRef.current, cameraInstance);

      const intersections = raycasterRef.current.intersectObjects(atomMeshes, false);

      if (intersections.length === 0) {
        onSelectMolecule(null);
        return;
      }

      const hit = intersections[0];
      const instanceId = hit.instanceId;

      if (instanceId === undefined) {
        onSelectMolecule(null);
        return;
      }

      const group = atomMeshGroupsRef.current.find(
        (item) => item.mesh === hit.object
      );
      const atom = group?.atoms[instanceId];

      onSelectMolecule(atom?.moleculeId ?? null);
    };

    const handlePointerMove = (event: PointerEvent) => {
      const previous = activePointers.get(event.pointerId);
      if (!previous) return;
      if (event.pointerType === "mouse" && event.buttons !== 1) return;
      activePointers.set(event.pointerId, { x: event.clientX, y: event.clientY });

      if (activePointers.size >= 2) {
        const span = currentSpan();
        if (pinchSpan) {
          cameraStateRef.current.distance = pinchDistance(cameraStateRef.current.distance, pinchSpan, span);
        }
        pinchSpan = span;
        return;
      }

      // Delta pela posição (movementX falta em alguns navegadores para toque).
      cameraStateRef.current.angleY -= (event.clientX - previous.x) * 0.005;
      cameraStateRef.current.angleX = clamp(
        cameraStateRef.current.angleX - (event.clientY - previous.y) * 0.004,
        -1.35,
        1.35
      );
    };

    const handlePointerEnd = (event: PointerEvent) => {
      activePointers.delete(event.pointerId);
      if (activePointers.size < 2) pinchSpan = null;
    };

    const handleWheel = (event: WheelEvent) => {
      event.preventDefault();

      cameraStateRef.current.distance = clamp(
        cameraStateRef.current.distance + event.deltaY * 0.04,
        CAMERA_MIN_DISTANCE,
        CAMERA_MAX_DISTANCE
      );
    };

    renderer.domElement.addEventListener("pointerdown", handlePointerDown);
    renderer.domElement.addEventListener("pointermove", handlePointerMove);
    renderer.domElement.addEventListener("pointerup", handlePointerEnd);
    renderer.domElement.addEventListener("pointercancel", handlePointerEnd);
    renderer.domElement.addEventListener("lostpointercapture", handlePointerEnd);
    renderer.domElement.addEventListener("wheel", handleWheel, {
      passive: false,
    });

    const renderLoop = () => {
      const sceneInstance = sceneRef.current;
      const rendererInstance = rendererRef.current;
      const cameraInstance = cameraRef.current;

      if (!sceneInstance || !rendererInstance || !cameraInstance) return;

      const cameraState = cameraStateRef.current;

      const target = cameraState.target;
      cameraInstance.position.set(...orbitCameraPosition(
        cameraState.angleX, cameraState.angleY, cameraState.distance, [target.x, target.y, target.z]));
      cameraInstance.lookAt(target);

      const topologyNow = latestTopologyRef.current;
      const frameNow = latestFrameRef.current;

      if (topologyNow && frameNow) {
        try {
          const alpha = getInterpolationAlpha(performance.now());

          updateAtomInstances(topologyNow, frameNow, alpha);
          updateBondInstances(topologyNow, frameNow);
          updateSupramolecularOverlays();
        } catch (error) {
          console.error("[Modelagem3D] Falha controlada no loop 3D:", error);
          onStatus?.(
            error instanceof Error
              ? `Falha controlada no render 3D: ${error.message}`
              : "Falha controlada no render 3D."
          );
        }
      }

      rendererInstance.render(sceneInstance, cameraInstance);
      animationRef.current = requestAnimationFrame(renderLoop);
    };

    renderLoop();

    return () => {
      if (animationRef.current !== null) {
        cancelAnimationFrame(animationRef.current);
      }

      observer.disconnect();

      renderer.domElement.removeEventListener("pointerdown", handlePointerDown);
      renderer.domElement.removeEventListener("pointermove", handlePointerMove);
      renderer.domElement.removeEventListener("pointerup", handlePointerEnd);
      renderer.domElement.removeEventListener("pointercancel", handlePointerEnd);
      renderer.domElement.removeEventListener("lostpointercapture", handlePointerEnd);
      renderer.domElement.removeEventListener("wheel", handleWheel);

      disposeAtomMeshes();
      disposeSupramolecularOverlays();

      if (bondMeshRef.current) {
        disposeObject(bondMeshRef.current);
      }

      if (boxLinesRef.current) {
        disposeObject(boxLinesRef.current);
      }

      disposeObject(scene);
      renderer.dispose();

      if (renderer.domElement.parentElement === mount) {
        mount.removeChild(renderer.domElement);
      }

      scene.clear();
      sceneRef.current = null;
      rendererRef.current = null;
      cameraRef.current = null;
      bondMeshRef.current = null;
      boxLinesRef.current = null;
    };
  }, [onSelectMolecule, onStatus]);

  useEffect(() => {
    try {
      rebuildSceneObjects();

      if (activeFrame) {
        acceptTargetFrame(activeFrame, true);
      }
    } catch (error) {
      console.error("[Modelagem3D] Falha controlada ao reconstruir cena 3D:", error);
      onStatus?.(
        error instanceof Error
          ? `Falha controlada ao reconstruir cena 3D: ${error.message}`
          : "Falha controlada ao reconstruir cena 3D."
      );
    }
  }, [activeTopology, showSolvent, selectedMoleculeId, elementColorMap]);

  function disposeAtomMeshes() {
    const scene = sceneRef.current;

    atomMeshGroupsRef.current.forEach((group) => {
      if (scene) {
        scene.remove(group.mesh);
      }

      disposeObject(group.mesh);
    });

    atomMeshGroupsRef.current = [];
  }

  function acceptTargetFrame(nextFrame: SimulationFrame3D, force = false) {
    const frameKey = getFrameKey(nextFrame);

    if (!force && frameKey === lastAcceptedFrameKeyRef.current) return;

    const now = performance.now();

    const previousDisplayedCoordinates =
      currentCoordinatesRef.current.length === nextFrame.coordinates.length
        ? cloneCoordinates(currentCoordinatesRef.current)
        : targetCoordinatesRef.current?.length === nextFrame.coordinates.length
          ? cloneCoordinates(targetCoordinatesRef.current)
          : cloneCoordinates(nextFrame.coordinates);

    const previousArrival = lastIncomingFrameAtRef.current;
    const estimatedInterval =
      previousArrival === null
        ? 100
        : clamp(now - previousArrival, 24, 180);

    previousCoordinatesRef.current = previousDisplayedCoordinates;
    targetCoordinatesRef.current = cloneCoordinates(nextFrame.coordinates);
    latestFrameRef.current = nextFrame;

    interpolationStartTimeRef.current = now;
    interpolationDurationMsRef.current = estimatedInterval;
    lastIncomingFrameAtRef.current = now;
    lastAcceptedFrameKeyRef.current = frameKey;

    if (currentCoordinatesRef.current.length !== nextFrame.coordinates.length) {
      currentCoordinatesRef.current = cloneCoordinates(nextFrame.coordinates);
    }
  }

  function getInterpolationAlpha(now: number) {
    const duration = Math.max(interpolationDurationMsRef.current, 1);
    const elapsed = now - interpolationStartTimeRef.current;

    return clamp(elapsed / duration, 0, 1);
  }

  function updateInterpolatedCoordinates(alpha: number) {
    const targetCoordinates =
      targetCoordinatesRef.current ?? latestFrameRef.current?.coordinates ?? null;

    if (!targetCoordinates) return;

    const previousCoordinates = previousCoordinatesRef.current ?? targetCoordinates;
    const currentCoordinates = currentCoordinatesRef.current;

    for (let index = 0; index < targetCoordinates.length; index += 1) {
      const target = targetCoordinates[index];
      const previous = previousCoordinates[index] ?? target;

      startVectorRef.current.set(previous[0], previous[1], previous[2]);
      targetVectorRef.current.set(target[0], target[1], target[2]);
      renderVectorRef.current
        .copy(startVectorRef.current)
        .lerp(targetVectorRef.current, alpha);

      if (!currentCoordinates[index]) {
        currentCoordinates[index] = [0, 0, 0];
      }

      currentCoordinates[index][0] = renderVectorRef.current.x;
      currentCoordinates[index][1] = renderVectorRef.current.y;
      currentCoordinates[index][2] = renderVectorRef.current.z;
    }
  }

  function disposeSupramolecularOverlays() {
    const scene = sceneRef.current;

    if (supramolecularOverlayRef.current) {
      disposeObject(supramolecularOverlayRef.current);
      scene?.remove(supramolecularOverlayRef.current);
      supramolecularOverlayRef.current = null;
    }

    if (interactionLinesRef.current) {
      disposeObject(interactionLinesRef.current);
      scene?.remove(interactionLinesRef.current);
      interactionLinesRef.current = null;
    }
  }

  function updateSupramolecularOverlays() {
    const scene = sceneRef.current;
    const coordinates = currentCoordinatesRef.current;

    if (!scene || coordinates.length === 0) return;

    overlayFrameCounterRef.current += 1;

    /*
     * A micela deve ser percebida pelas partículas e pela análise do backend.
     * O overlay global de casca/núcleo fica desligado para não criar a aparência
     * de uma esfera pronta. Se algum dia for reativado, deve ser somente modo
     * diagnóstico, nunca visual padrão.
     */
    if (SHOW_GLOBAL_MICELLE_OVERLAY) {
      return;
    }

    if (overlayFrameCounterRef.current % 10 !== 1) return;

    const centers = collectMoleculeCenters(visibleAtomsRef.current, coordinates);

    disposeSupramolecularOverlays();

    if (!selectedMoleculeId || centers.length < 2) return;

    const selectedCenter = centers.find(
      (center) => center.moleculeId === selectedMoleculeId
    );

    if (!selectedCenter) return;

    const grid = buildSpatialCenterGrid(centers, 4.2);
    const nearby = collectNearbyCenters(
      grid,
      selectedCenter.center,
      4.8,
      selectedCenter.moleculeId
    )
      .filter((candidate) => candidate.kind !== "solvent")
      .slice(0, 10);

    if (nearby.length === 0) return;

    const positions: number[] = [];

    nearby.forEach((target) => {
      positions.push(
        selectedCenter.center.x,
        selectedCenter.center.y,
        selectedCenter.center.z,
        target.center.x,
        target.center.y,
        target.center.z
      );
    });

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute(
      "position",
      new THREE.Float32BufferAttribute(positions, 3)
    );

    const material = new THREE.LineBasicMaterial({
      color: "#38bdf8",
      transparent: true,
      opacity: 0.22,
      depthWrite: false,
    });

    const lines = new THREE.LineSegments(geometry, material);
    lines.name = "selected-local-interaction-lines";

    scene.add(lines);
    interactionLinesRef.current = lines;
  }

  function rebuildSceneObjects() {
    const scene = sceneRef.current;
    const currentTopology = latestTopologyRef.current ?? activeTopology;

    if (!scene) return;

    disposeAtomMeshes();
    disposeSupramolecularOverlays();

    if (bondMeshRef.current) {
      disposeObject(bondMeshRef.current);
      scene.remove(bondMeshRef.current);
      bondMeshRef.current = null;
    }

    if (boxLinesRef.current) {
      disposeObject(boxLinesRef.current);
      scene.remove(boxLinesRef.current);
      boxLinesRef.current = null;
    }

    if (!currentTopology) return;

    const visibleAtoms = currentTopology.atoms.filter((atom) =>
      shouldRenderAtom(atom, showSolvent)
    );
    const visibleAtomIndexSet = new Set(visibleAtoms.map((atom) => atom.index));

    /*
     * Ligações vêm exclusivamente da topologia fixa enviada pelo backend.
     * Não existe detecção de ligação por distância no loop de renderização.
     */
    const visibleBonds = currentTopology.bonds.filter(
      (bond) =>
        visibleAtomIndexSet.has(bond.atomAIndex) &&
        visibleAtomIndexSet.has(bond.atomBIndex)
    );

    visibleAtomsRef.current = visibleAtoms;
    visibleBondsRef.current = visibleBonds;

    const groupedAtoms = new Map<string, AtomMeshGroup["atoms"]>();

    visibleAtoms.forEach((atom) => {
      const color = getAtomColor(atom, elementColorMap);
      const key = `${normalizeSymbol(atom.element)}:${color}`;

      const list = groupedAtoms.get(key) ?? [];
      list.push(atom);
      groupedAtoms.set(key, list);
    });

    atomMeshGroupsRef.current = Array.from(groupedAtoms.entries()).map(
      ([key, atoms]) => {
        const color = key.split(":").slice(1).join(":") || "#CBD5E1";

        const sphereGeometry = new THREE.SphereGeometry(1, 22, 16);
        const material = new THREE.MeshBasicMaterial({
          color,
        });

        material.toneMapped = false;

        const mesh = new THREE.InstancedMesh(
          sphereGeometry,
          material,
          Math.max(atoms.length, 1)
        );

        mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
        mesh.count = atoms.length;
        mesh.name = `simulation-atoms-${key}`;
        mesh.frustumCulled = false;

        scene.add(mesh);

        return {
          mesh,
          atoms,
          color,
        };
      }
    );

    const bondGeometry = new THREE.CylinderGeometry(1, 1, 1, 5, 1, false);

    const bondMaterial = new THREE.MeshBasicMaterial({
      color: "#CBD5E1",
    });

    bondMaterial.toneMapped = false;

    const bondMesh = new THREE.InstancedMesh(
      bondGeometry,
      bondMaterial,
      Math.max(visibleBonds.length, 1)
    );

    bondMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    bondMesh.count = visibleBonds.length;
    bondMesh.name = "simulation-bond-cylinders";
    bondMesh.frustumCulled = false;

    scene.add(bondMesh);
    bondMeshRef.current = bondMesh;

    const boxLines = new THREE.LineSegments(
      createBoxGeometry(currentTopology.box),
      new THREE.LineBasicMaterial({
        color: "#22d3ee",
        transparent: true,
        opacity: 0.32,
      })
    );

    boxLines.name = "simulation-box";
    boxLines.frustumCulled = false;
    scene.add(boxLines);
    boxLinesRef.current = boxLines;
  }

  function updateAtomInstances(
    _topologyNow: SimulationTopology3D,
    frameNow: SimulationFrame3D,
    alpha: number
  ) {
    void _topologyNow;

    updateInterpolatedCoordinates(alpha);

    const currentCoordinates = currentCoordinatesRef.current;
    const dummy = reusableAtomObjectRef.current;

    atomMeshGroupsRef.current.forEach((group) => {
      group.atoms.forEach((atom, instanceIndex) => {
        const position =
          currentCoordinates[atom.index] ?? frameNow.coordinates[atom.index];

        if (!position) return;

        dummy.position.set(position[0], position[1], position[2]);

        const radius = getAtomRadius(atom);
        const selectedScale =
          selectedMoleculeId && selectedMoleculeId === atom.moleculeId ? 1.22 : 1;

        dummy.scale.setScalar(radius * selectedScale);
        dummy.updateMatrix();

        group.mesh.setMatrixAt(instanceIndex, dummy.matrix);
      });

      group.mesh.instanceMatrix.needsUpdate = true;
      group.mesh.computeBoundingSphere();
    });
  }

  function updateBondInstances(
    topologyNow: SimulationTopology3D,
    frameNow: SimulationFrame3D
  ) {
    const bondMesh = bondMeshRef.current;

    if (!bondMesh) return;

    const coordinates = currentCoordinatesRef.current;
    const hiddenBonds = new Set(frameNow.hiddenBonds ?? []);

    let instanceIndex = 0;

    visibleBondsRef.current.forEach((bond) => {
      const atomA =
        coordinates[bond.atomAIndex] ?? frameNow.coordinates[bond.atomAIndex];
      const atomB =
        coordinates[bond.atomBIndex] ?? frameNow.coordinates[bond.atomBIndex];

      if (!atomA || !atomB) {
        hideBondInstance(instanceIndex);
        instanceIndex += 1;
        return;
      }

      const hideByPbc =
        !bond.drawAcrossPbc &&
        isLongPbcBond(atomA, atomB, frameNow.box ?? topologyNow.box);

      if (hiddenBonds.has(bond.index) || hideByPbc) {
        hideBondInstance(instanceIndex);
        instanceIndex += 1;
        return;
      }

      bondStartRef.current.set(atomA[0], atomA[1], atomA[2]);
      bondEndRef.current.set(atomB[0], atomB[1], atomB[2]);

      bondMidpointRef.current
        .copy(bondStartRef.current)
        .add(bondEndRef.current)
        .multiplyScalar(0.5);

      bondDirectionRef.current
        .copy(bondEndRef.current)
        .sub(bondStartRef.current);

      const bondLength = bondDirectionRef.current.length();

      if (bondLength <= 0.0001 || bondLength > MAX_RENDERED_TOPOLOGICAL_BOND_LENGTH) {
        hideBondInstance(instanceIndex);
        instanceIndex += 1;
        return;
      }

      bondDirectionRef.current.normalize();

      bondQuaternionRef.current.setFromUnitVectors(
        CYLINDER_UP_AXIS,
        bondDirectionRef.current
      );

      const radius =
        bond.order >= 3
          ? BOND_RADIUS * 1.18
          : bond.order >= 2
            ? BOND_RADIUS * 1.08
            : BOND_RADIUS;

      const dummy = reusableBondObjectRef.current;

      dummy.position.copy(bondMidpointRef.current);
      dummy.quaternion.copy(bondQuaternionRef.current);
      dummy.scale.set(radius, bondLength, radius);
      dummy.updateMatrix();

      bondMesh.setMatrixAt(instanceIndex, dummy.matrix);

      instanceIndex += 1;
    });

    for (; instanceIndex < bondMesh.count; instanceIndex += 1) {
      hideBondInstance(instanceIndex);
    }

    bondMesh.instanceMatrix.needsUpdate = true;
    bondMesh.computeBoundingSphere();
  }

  function hideBondInstance(instanceIndex: number) {
    const bondMesh = bondMeshRef.current;

    if (!bondMesh) return;

    const dummy = reusableBondObjectRef.current;

    dummy.position.set(0, 0, 0);
    dummy.quaternion.identity();
    dummy.scale.set(0, 0, 0);
    dummy.updateMatrix();

    bondMesh.setMatrixAt(instanceIndex, dummy.matrix);
  }

  return (
    <section className="simulation-viewer-shell">
      <div className="simulation-viewer-overlay">
        <div>
          <strong>{activeTopology?.title ?? "Visualizador molecular 3D"}</strong>
          <span>{atomCountLabel}</span>
          <span className="simulation-viewer-seal" role="note">{viewerSealText(activeTopology?.analysis)}</span>
        </div>

        <div className="simulation-viewer-badges">
          <span>{showSolvent ? "solvente visível" : "solvente oculto"}</span>
          <span>Micelium</span>
          <span>{formationPhaseLabel}</span>
          <span>na cena: {morphologyLabel}</span>
          <span>clusters</span>
          <span>interações</span>
        </div>
      </div>

      <div ref={mountRef} className="simulation-viewer-canvas" />

      {!activeTopology && (
        <div className="simulation-viewer-empty">
          <strong>Nenhuma solução misturada</strong>
          <span>
            Monte a solução no painel 2D e clique em Misturar para enviar a mistura ao Micelium.
          </span>
        </div>
      )}

      <div className="simulation-viewer-help">
        Arraste para rotacionar · Scroll ou pinça (dois dedos) para zoom · Toque/clique em uma partícula para selecionar a molécula
      </div>
    </section>
  );
}


