import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";

import type {
  Molecule3DAtom,
  Molecule3DBond,
  Molecule3DItem,
  SimulationSettings3D,
} from "../../type/3dpage.types";

import "./rendering.css";

type RenderingSceneProps = {
  molecules: Molecule3DItem[];
  selectedMoleculeId: string | null;
  settings: SimulationSettings3D;
  onSelectMolecule: (id: string | null) => void;
};

const CPK_COLORS: Record<string, string> = {
  H: "#f8fafc",
  C: "#334155",
  N: "#2563eb",
  O: "#dc2626",
  F: "#22c55e",
  Cl: "#16a34a",
  Br: "#92400e",
  I: "#7c3aed",
  P: "#f97316",
  S: "#facc15",
  B: "#f59e0b",
  Si: "#a78bfa",
  Na: "#38bdf8",
  K: "#a855f7",
  Ca: "#94a3b8",
  Fe: "#b45309",
  Cu: "#ea580c",
  Zn: "#64748b",
};

const VDW_RADIUS: Record<string, number> = {
  H: 0.22,
  C: 0.38,
  N: 0.36,
  O: 0.36,
  F: 0.34,
  Cl: 0.46,
  Br: 0.5,
  I: 0.56,
  P: 0.48,
  S: 0.48,
  B: 0.42,
  Si: 0.48,
  Na: 0.52,
  K: 0.6,
  Ca: 0.56,
  Fe: 0.46,
  Cu: 0.46,
  Zn: 0.46,
};

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function getAtomColor(element: string) {
  return CPK_COLORS[element] ?? "#cbd5e1";
}

function getAtomRadius(element: string) {
  return VDW_RADIUS[element] ?? 0.4;
}

function getConcentrationFactor(molecule: Molecule3DItem) {
  const value = Number.isFinite(molecule.concentration)
    ? Math.max(0, molecule.concentration)
    : 0;

  if (molecule.unit === "mol/L") return clamp(value, 0, 5);
  if (molecule.unit === "mmol/L") return clamp(value / 1000, 0, 5);
  if (molecule.unit === "µmol/L") return clamp(value / 1_000_000, 0, 5);
  if (molecule.unit === "g/L") return clamp(value / 100, 0, 5);
  if (molecule.unit === "mg/L") return clamp(value / 100_000, 0, 5);

  return clamp(value, 0, 5);
}






function normalizeAtomPositions(atoms: Molecule3DAtom[]) {
  if (atoms.length === 0) return [];

  const center = atoms.reduce(
    (acc, atom) => {
      acc.x += atom.x;
      acc.y += atom.y;
      acc.z += atom.z;
      return acc;
    },
    { x: 0, y: 0, z: 0 }
  );

  center.x /= atoms.length;
  center.y /= atoms.length;
  center.z /= atoms.length;

  const centered = atoms.map((atom) => ({
    ...atom,
    x: atom.x - center.x,
    y: atom.y - center.y,
    z: atom.z - center.z,
  }));

  const maxDistance = centered.reduce((max, atom) => {
    const distance = Math.sqrt(atom.x * atom.x + atom.y * atom.y + atom.z * atom.z);
    return Math.max(max, distance);
  }, 1);

  const scale = maxDistance > 0 ? 2.35 / maxDistance : 1;

  return centered.map((atom) => ({
    ...atom,
    x: atom.x * scale,
    y: atom.y * scale,
    z: atom.z * scale,
  }));
}

function createBondCylinder(
  start: THREE.Vector3,
  end: THREE.Vector3,
  radius: number,
  material: THREE.Material
) {
  const direction = new THREE.Vector3().subVectors(end, start);
  const length = Math.max(direction.length(), 0.001);
  const midpoint = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5);

  const geometry = new THREE.CylinderGeometry(radius, radius, length, 16);
  const cylinder = new THREE.Mesh(geometry, material);

  cylinder.position.copy(midpoint);
  cylinder.quaternion.setFromUnitVectors(
    new THREE.Vector3(0, 1, 0),
    direction.clone().normalize()
  );

  return cylinder;
}

function createBondMeshes(
  start: THREE.Vector3,
  end: THREE.Vector3,
  order: number,
  material: THREE.Material
) {
  const meshes: THREE.Mesh[] = [];
  const bondRadius = order >= 3 ? 0.035 : 0.045;

  if (order <= 1.1 || order === 1.5) {
    meshes.push(createBondCylinder(start, end, bondRadius, material));
    return meshes;
  }

  const direction = new THREE.Vector3().subVectors(end, start).normalize();
  const side = new THREE.Vector3().crossVectors(direction, new THREE.Vector3(0, 1, 0));

  if (side.length() < 0.001) {
    side.crossVectors(direction, new THREE.Vector3(1, 0, 0));
  }

  side.normalize();

  if (order === 2) {
    const offset = side.multiplyScalar(0.08);
    meshes.push(
      createBondCylinder(start.clone().add(offset), end.clone().add(offset), bondRadius, material),
      createBondCylinder(start.clone().sub(offset), end.clone().sub(offset), bondRadius, material)
    );
    return meshes;
  }

  const offset = side.multiplyScalar(0.11);
  meshes.push(
    createBondCylinder(start, end, bondRadius, material),
    createBondCylinder(start.clone().add(offset), end.clone().add(offset), bondRadius, material),
    createBondCylinder(start.clone().sub(offset), end.clone().sub(offset), bondRadius, material)
  );

  return meshes;
}

function createTextSprite(text: string) {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 128;

  const context = canvas.getContext("2d");

  if (!context) {
    return new THREE.Sprite(new THREE.SpriteMaterial());
  }

  context.clearRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = "rgba(2, 6, 23, 0.82)";
  context.fillRect(10, 22, 492, 76);
  context.strokeStyle = "rgba(125, 211, 252, 0.45)";
  context.lineWidth = 3;
  context.strokeRect(10, 22, 492, 76);

  context.fillStyle = "#e0f2fe";
  context.font = "700 34px Arial";
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.fillText(text.slice(0, 28), 256, 62);

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;

  const sprite = new THREE.Sprite(
    new THREE.SpriteMaterial({
      map: texture,
      transparent: true,
      depthWrite: false,
    })
  );

  sprite.scale.set(3.2, 0.8, 1);

  return sprite;
}

function createMoleculeGroup(
  molecule: Molecule3DItem,
  moleculeIndex: number,
  selected: boolean,
  settings: SimulationSettings3D
) {
  const group = new THREE.Group();
  group.name = molecule.id;
  group.userData = {
    moleculeId: molecule.id,
    baseY: 0,
    phase: moleculeIndex * 0.77,
  };

  const normalizedAtoms = normalizeAtomPositions(molecule.atoms);
  const atomByIndex = new Map<number, Molecule3DAtom>();

  normalizedAtoms.forEach((atom) => {
    atomByIndex.set(atom.index, atom);
  });

  const atomMaterialByElement = new Map<string, THREE.MeshStandardMaterial>();
  const bondMaterial = new THREE.MeshStandardMaterial({
    color: selected ? "#38bdf8" : "#94a3b8",
    roughness: 0.42,
    metalness: 0.08,
  });

  /*
   * Ligações renderizadas vêm do grafo/topologia da molécula.
   * Nunca são recalculadas por distância durante animação.
   */
  molecule.bonds.forEach((bond: Molecule3DBond) => {
    const atomA = atomByIndex.get(bond.atomAIndex);
    const atomB = atomByIndex.get(bond.atomBIndex);

    if (!atomA || !atomB) return;

    const start = new THREE.Vector3(atomA.x, atomA.y, atomA.z);
    const end = new THREE.Vector3(atomB.x, atomB.y, atomB.z);

    createBondMeshes(start, end, bond.order, bondMaterial).forEach((mesh) => {
      mesh.userData = { moleculeId: molecule.id };
      group.add(mesh);
    });
  });

  normalizedAtoms.forEach((atom) => {
    const color = getAtomColor(atom.element);

    if (!atomMaterialByElement.has(atom.element)) {
      atomMaterialByElement.set(
        atom.element,
        new THREE.MeshStandardMaterial({
          color,
          roughness: 0.34,
          metalness: atom.element === "Fe" || atom.element === "Cu" ? 0.45 : 0.08,
        })
      );
    }

    const atomGeometry = new THREE.SphereGeometry(getAtomRadius(atom.element), 32, 24);
    const atomMesh = new THREE.Mesh(
      atomGeometry,
      atomMaterialByElement.get(atom.element)!
    );

    atomMesh.position.set(atom.x, atom.y, atom.z);
    atomMesh.userData = {
      moleculeId: molecule.id,
      atomIndex: atom.index,
      element: atom.element,
    };

    group.add(atomMesh);

    if (settings.showInteractionField && atom.charge !== null && atom.charge !== undefined) {
      const ionicEffect = 1 + settings.ionicStrength * 0.18;
      const polarityEffect = 1 + settings.solventPolarity * 0.16;
      const intensity = clamp(
        Math.abs(atom.charge) * 3 * ionicEffect * polarityEffect,
        0.08,
        0.65
      );
      const chargeColor = atom.charge >= 0 ? "#f97316" : "#38bdf8";

      const fieldMesh = new THREE.Mesh(
        new THREE.SphereGeometry(getAtomRadius(atom.element) * (1.8 + intensity), 24, 16),
        new THREE.MeshBasicMaterial({
          color: chargeColor,
          transparent: true,
          opacity: 0.07 + intensity * 0.08,
          depthWrite: false,
        })
      );

      fieldMesh.position.copy(atomMesh.position);
      fieldMesh.userData = { moleculeId: molecule.id };
      group.add(fieldMesh);
    }
  });

  const concentrationFactor = getConcentrationFactor(molecule);
  const phEffect = Math.abs(settings.ph - 7) * 0.025;
  const shellRadius = 2.8 + concentrationFactor * 1.4 + phEffect;

  if (settings.showReactionAura || concentrationFactor > 0.001) {
    const shell = new THREE.Mesh(
      new THREE.SphereGeometry(shellRadius, 40, 24),
      new THREE.MeshBasicMaterial({
        color: molecule.metadata?.isSurfactant ? "#22c55e" : "#0ea5e9",
        transparent: true,
        opacity: settings.showReactionAura ? 0.06 + concentrationFactor * 0.04 : 0.03,
        wireframe: true,
        depthWrite: false,
      })
    );

    shell.userData = { moleculeId: molecule.id };
    group.add(shell);
  }

  const label = createTextSprite(`${molecule.name} · ${molecule.concentration} ${molecule.unit}`);
  label.position.set(0, shellRadius + 0.65, 0);
  label.userData = { moleculeId: molecule.id };
  group.add(label);

  const orbitRadius = 8.5 + Math.floor(moleculeIndex / 6) * 4.25;
  const angle = (moleculeIndex / Math.max(1, 6)) * Math.PI * 2;
  group.position.set(
    Math.cos(angle) * orbitRadius,
    0,
    Math.sin(angle) * orbitRadius
  );
  group.userData.baseY = group.position.y;

  if (selected) {
    const selectionRing = new THREE.Mesh(
      new THREE.TorusGeometry(shellRadius + 0.35, 0.045, 16, 96),
      new THREE.MeshBasicMaterial({
        color: "#38bdf8",
        transparent: true,
        opacity: 0.88,
      })
    );

    selectionRing.rotation.x = Math.PI / 2;
    selectionRing.userData = { moleculeId: molecule.id };
    group.add(selectionRing);
  }

  return group;
}


type LegacySpatialGroupGrid = {
  cellSize: number;
  cells: Map<string, number[]>;
};

function legacySpatialKey(position: THREE.Vector3, cellSize: number) {
  return `${Math.floor(position.x / cellSize)}:${Math.floor(position.y / cellSize)}:${Math.floor(position.z / cellSize)}`;
}

function buildLegacySpatialGrid(groups: THREE.Group[], cellSize: number) {
  const cells = new Map<string, number[]>();

  groups.forEach((group, index) => {
    const key = legacySpatialKey(group.position, cellSize);
    const bucket = cells.get(key) ?? [];

    bucket.push(index);
    cells.set(key, bucket);
  });

  return {
    cellSize,
    cells,
  };
}

function getLegacyNearbyGroupIndexes(
  grid: LegacySpatialGroupGrid,
  groups: THREE.Group[],
  sourceIndex: number,
  maxDistance: number
) {
  const source = groups[sourceIndex];

  if (!source) return [];

  const sourceX = Math.floor(source.position.x / grid.cellSize);
  const sourceY = Math.floor(source.position.y / grid.cellSize);
  const sourceZ = Math.floor(source.position.z / grid.cellSize);
  const range = Math.max(1, Math.ceil(maxDistance / grid.cellSize));
  const results: number[] = [];

  for (let dx = -range; dx <= range; dx += 1) {
    for (let dy = -range; dy <= range; dy += 1) {
      for (let dz = -range; dz <= range; dz += 1) {
        const bucket = grid.cells.get(
          `${sourceX + dx}:${sourceY + dy}:${sourceZ + dz}`
        );

        if (!bucket) continue;

        bucket.forEach((candidateIndex) => {
          if (candidateIndex <= sourceIndex) return;

          const candidate = groups[candidateIndex];

          if (!candidate) return;

          if (source.position.distanceTo(candidate.position) <= maxDistance) {
            results.push(candidateIndex);
          }
        });
      }
    }
  }

  return results;
}

function createInteractionLines(
  molecules: Molecule3DItem[],
  groups: THREE.Group[],
  settings: SimulationSettings3D
) {
  const lineGroup = new THREE.Group();
  lineGroup.name = "interaction-lines";

  /*
   * Interações visuais usam spatial hash + cutoff.
   * Não são ligações químicas e não alteram a topologia molecular.
   */
  const grid = buildLegacySpatialGrid(groups, 7.5);
  let lineCount = 0;
  const maxLines = 180;

  for (let i = 0; i < groups.length; i += 1) {
    if (lineCount >= maxLines) break;

    const nearbyIndexes = getLegacyNearbyGroupIndexes(grid, groups, i, 9.0);

    for (const j of nearbyIndexes) {
      if (lineCount >= maxLines) break;

      const moleculeA = molecules[i];
      const moleculeB = molecules[j];

      if (!moleculeA || !moleculeB) continue;

      const factorA = getConcentrationFactor(moleculeA);
      const factorB = getConcentrationFactor(moleculeB);
      const shouldLink =
        factorA + factorB > 0.001 ||
        moleculeA.metadata?.isSurfactant ||
        moleculeB.metadata?.isSurfactant;

      if (!shouldLink) continue;

      const geometry = new THREE.BufferGeometry().setFromPoints([
        groups[i].position.clone(),
        groups[j].position.clone(),
      ]);

      const line = new THREE.Line(
        geometry,
        new THREE.LineBasicMaterial({
          color: "#22d3ee",
          transparent: true,
          opacity: clamp(
            0.07 + (factorA + factorB) * 0.08 + settings.ionicStrength * 0.025,
            0.06,
            0.34
          ),
        })
      );

      line.userData = { interactionLine: true };
      lineGroup.add(line);
      lineCount += 1;
    }
  }

  return lineGroup;
}
function disposeObject3D(object: THREE.Object3D) {
  object.traverse((child) => {
    if (child instanceof THREE.Mesh || child instanceof THREE.Line || child instanceof THREE.Sprite) {
      if ("geometry" in child && child.geometry) {
        child.geometry.dispose();
      }

      const material = child.material;

      if (Array.isArray(material)) {
        material.forEach((item) => item.dispose());
      } else if (material) {
        material.dispose();
      }
    }
  });
}

export default function RenderingScene({
  molecules,
  selectedMoleculeId,
  settings,
  onSelectMolecule,
}: RenderingSceneProps) {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const moleculeGroupsRef = useRef<THREE.Group[]>([]);
  const frameRef = useRef<number | null>(null);
  const raycasterRef = useRef(new THREE.Raycaster());
  const pointerRef = useRef(new THREE.Vector2());
  const cameraStateRef = useRef({
    angle: 0,
    distance: 27,
  });

  const moleculeCountLabel = useMemo(() => {
    if (molecules.length === 0) return "Nenhuma molécula enviada pelo 2D";
    if (molecules.length === 1) return "1 molécula enviada pelo 2D";
    return `${molecules.length} moléculas enviadas pelo 2D`;
  }, [molecules.length]);

  useEffect(() => {
    const mount = mountRef.current;

    if (!mount) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#020617");
    scene.fog = new THREE.Fog("#020617", 22, 72);

    const camera = new THREE.PerspectiveCamera(54, 1, 0.1, 1000);
    camera.position.set(0, 13, 27);
    camera.lookAt(0, 0, 0);

    let renderer: THREE.WebGLRenderer;

    try {
      renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: false,
        powerPreference: "high-performance",
        failIfMajorPerformanceCaveat: false,
      });
    } catch (error) {
      console.error("Falha ao criar contexto WebGL no renderer antigo:", error);

      mount.innerHTML = `
        <div style="
          width: 100%;
          height: 100%;
          min-height: 420px;
          display: grid;
          place-items: center;
          padding: 24px;
          color: #e5e7eb;
          background: #020617;
          border-radius: 20px;
          text-align: center;
          font-family: system-ui, sans-serif;
        ">
          <div style="
            max-width: 520px;
            display: grid;
            gap: 10px;
            border: 1px solid rgba(248, 113, 113, 0.28);
            border-radius: 18px;
            padding: 18px;
            background: rgba(15, 23, 42, 0.92);
          ">
            <strong style="color:#fecaca;">WebGL indisponível</strong>
            <span style="color:#cbd5e1;font-size:13px;line-height:1.5;">
              O navegador não conseguiu iniciar o motor 3D. Ative a aceleração de hardware,
              atualize o driver de vídeo ou teste em outro navegador.
            </span>
          </div>
        </div>
      `;

      scene.clear();
      return;
    }

    renderer.setClearColor("#020617", 1);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    mount.appendChild(renderer.domElement);

    const ambient = new THREE.AmbientLight("#e0f2fe", 0.42);
    scene.add(ambient);

    const keyLight = new THREE.DirectionalLight("#ffffff", 1.35);
    keyLight.position.set(10, 14, 11);
    keyLight.castShadow = true;
    scene.add(keyLight);

    const cyanLight = new THREE.PointLight("#22d3ee", 1.2, 55);
    cyanLight.position.set(-14, 7, 12);
    scene.add(cyanLight);

    const floor = new THREE.Mesh(
      new THREE.CircleGeometry(34, 96),
      new THREE.MeshStandardMaterial({
        color: "#0f172a",
        roughness: 0.82,
        metalness: 0.18,
      })
    );
    floor.rotation.x = -Math.PI / 2;
    floor.position.y = -3.2;
    floor.receiveShadow = true;
    scene.add(floor);

    const grid = new THREE.GridHelper(68, 34, "#155e75", "#1e293b");
    grid.position.y = -3.18;
    scene.add(grid);

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

    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(mount);

    const handlePointerDown = (event: PointerEvent) => {
      const rendererInstance = rendererRef.current;
      const cameraInstance = cameraRef.current;

      if (!rendererInstance || !cameraInstance) return;

      const rect = rendererInstance.domElement.getBoundingClientRect();

      if (rect.width <= 0 || rect.height <= 0) return;

      pointerRef.current.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      pointerRef.current.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

      raycasterRef.current.setFromCamera(pointerRef.current, cameraInstance);

      const intersects = raycasterRef.current.intersectObjects(
        moleculeGroupsRef.current,
        true
      );

      if (intersects.length === 0) {
        onSelectMolecule(null);
        return;
      }

      const moleculeId = intersects[0].object.userData?.moleculeId;

      onSelectMolecule(typeof moleculeId === "string" ? moleculeId : null);
    };

    renderer.domElement.addEventListener("pointerdown", handlePointerDown);

    const wheel = (event: WheelEvent) => {
      event.preventDefault();
      cameraStateRef.current.distance = clamp(
        cameraStateRef.current.distance + event.deltaY * 0.018,
        12,
        52
      );
    };

    const pointerMove = (event: PointerEvent) => {
      if (event.buttons !== 1) return;
      cameraStateRef.current.angle += event.movementX * 0.006;
    };

    renderer.domElement.addEventListener("wheel", wheel, { passive: false });
    renderer.domElement.addEventListener("pointermove", pointerMove);

    const animate = () => {
      const elapsed = performance.now() * 0.001;
      const sceneInstance = sceneRef.current;
      const cameraInstance = cameraRef.current;
      const rendererInstance = rendererRef.current;

      if (!sceneInstance || !cameraInstance || !rendererInstance) return;

      cameraInstance.position.x =
        Math.sin(cameraStateRef.current.angle) * cameraStateRef.current.distance;
      cameraInstance.position.z =
        Math.cos(cameraStateRef.current.angle) * cameraStateRef.current.distance;
      cameraInstance.lookAt(0, 0, 0);

      moleculeGroupsRef.current.forEach((group, index) => {
        if (!settings.dynamicMode) return;

        const phase = group.userData.phase ?? index;
        const agitation = clamp(settings.agitation, 0, 10);
        const tempFactor = clamp(settings.temperature / 298, 0.55, 1.45);

        group.rotation.y += 0.0035 * (1 + agitation * 0.3) * tempFactor;
        group.rotation.x = Math.sin(elapsed * 0.55 + phase) * 0.025 * agitation;
        group.position.y =
          (group.userData.baseY ?? 0) +
          Math.sin(elapsed * (0.7 + agitation * 0.18) + phase) * 0.08 * agitation;
      });

      rendererInstance.render(sceneInstance, cameraInstance);
      frameRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (frameRef.current !== null) {
        cancelAnimationFrame(frameRef.current);
      }

      resizeObserver.disconnect();
      renderer.domElement.removeEventListener("pointerdown", handlePointerDown);
      renderer.domElement.removeEventListener("wheel", wheel);
      renderer.domElement.removeEventListener("pointermove", pointerMove);

      moleculeGroupsRef.current.forEach((group) => {
        disposeObject3D(group);
        scene.remove(group);
      });

      disposeObject3D(scene);

      renderer.dispose();

      if (renderer.domElement.parentElement === mount) {
        mount.removeChild(renderer.domElement);
      }

      scene.clear();
      rendererRef.current = null;
      sceneRef.current = null;
      cameraRef.current = null;
      moleculeGroupsRef.current = [];
    };
  }, [onSelectMolecule, settings.agitation, settings.dynamicMode, settings.temperature]);

  useEffect(() => {
    const scene = sceneRef.current;

    if (!scene) return;

    moleculeGroupsRef.current.forEach((group) => {
      disposeObject3D(group);
      scene.remove(group);
    });

    const oldInteractionLines = scene.getObjectByName("interaction-lines");

    if (oldInteractionLines) {
      disposeObject3D(oldInteractionLines);
      scene.remove(oldInteractionLines);
    }

    const oldMicelleGuide = scene.getObjectByName("legacy-micelle-guide");

    if (oldMicelleGuide) {
      disposeObject3D(oldMicelleGuide);
      scene.remove(oldMicelleGuide);
    }

    const groups = molecules.map((molecule, index) => {
      const group = createMoleculeGroup(
        molecule,
        index,
        selectedMoleculeId === molecule.id,
        settings
      );

      scene.add(group);
      return group;
    });

    moleculeGroupsRef.current = groups;

    // Guia esférico legado desativado por padrão.

    if (settings.showReactionAura && groups.length > 1) {
      scene.add(createInteractionLines(molecules, groups, settings));
    }
  }, [
    molecules,
    selectedMoleculeId,
    settings.showInteractionField,
    settings.showReactionAura,
    settings.ionicStrength,
    settings.ph,
    settings.solventPolarity,
  ]);

  return (
    <section className="rendering-shell">
      <div className="rendering-top-overlay">
        <div>
          <strong>Campo 3D molecular</strong>
          <span>{moleculeCountLabel}</span>
        </div>

        <div className="rendering-badges">
          <span>{settings.dynamicMode ? "dinâmica visual ativa" : "dinâmica pausada"}</span>
          <span>{settings.temperature} K</span>
          <span>pH {settings.ph.toFixed(1)}</span>
          <span>µ {settings.ionicStrength.toFixed(2)}</span>
        </div>
      </div>

      <div ref={mountRef} className="rendering-canvas" />

      {molecules.length === 0 && (
        <div className="rendering-empty-state">
          <strong>Campo 3D ativo</strong>
          <span>
            Nenhuma molécula recebida do 2D ainda. Use “Adicionar ao 3D” na área
            de transferência 2D → 3D.
          </span>
        </div>
      )}

      <div className="rendering-bottom-hint">
        Arraste para orbitar · Scroll para aproximar · Clique em uma molécula para selecionar
      </div>
    </section>
  );
}


