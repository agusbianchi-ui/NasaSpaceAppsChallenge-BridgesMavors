import { createTerrainHazards } from "./terrainHazards.js";
import { MeshBVH, acceleratedRaycast } from "three-mesh-bvh";
import { loadVisualGrid } from "./visualGrid.js";
import { createTerrainAnnotations } from "./terrainAnnotations.js";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { constrainTerrainCamera, TERRAIN_NAVIGATION } from "./terrainCamera.js";
import { bindTerrainInput } from "./terrainInput.js";
import { disposeTerrain, loadTerrain } from "./loadTerrain.js";

const { minDistance: MIN_DISTANCE, maxDistance: MAX_DISTANCE } =
  TERRAIN_NAVIGATION;
const RATIOS = { low: 0.75, medium: 1, high: 1.5 };

export function createTerrainEngine(
  host,
  {
    baseUrl,
    onProgress,
    onReady,
    onError,
    onStats,
    onInspect,
    onPlace,
    onGeometry,
  },
) {
  const renderer = new THREE.WebGLRenderer({
    antialias: true,
    powerPreference: "high-performance",
  });
  renderer.setClearColor(
    getComputedStyle(host).getPropertyValue("--bg").trim() || "#090d14",
  );
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.NoToneMapping;
  const canvas = renderer.domElement;
  canvas.tabIndex = 0;
  canvas.setAttribute(
    "aria-label",
    "Interactive 3D terrain. Drag to pan, right-drag to orbit. Use camera buttons for keyboard navigation.",
  );
  host.append(canvas);
  const scene = new THREE.Scene(),
    terrain = new THREE.Group();
  scene.add(terrain, new THREE.HemisphereLight(0xffffff, 0x475366, 1.6));
  const sun = new THREE.DirectionalLight(0xffffff, 2.2);
  sun.position.set(-90000, 130000, 40000);
  scene.add(sun);
  const annotations = createTerrainAnnotations(scene);
  const hazards = createTerrainHazards(scene);
  let visualGrid = null,
    geometryReady = false;
  const selectable = [],
    raycaster = new THREE.Raycaster();
  raycaster.firstHitOnly = true;
  const camera = new THREE.PerspectiveCamera(45, 1, 50, 1200000);
  const controls = new OrbitControls(camera, canvas);
  controls.mouseButtons = {
    LEFT: THREE.MOUSE.PAN,
    MIDDLE: THREE.MOUSE.DOLLY,
    RIGHT: THREE.MOUSE.ROTATE,
  };
  controls.screenSpacePanning = false;
  controls.enableDamping = true;
  controls.dampingFactor = 0.12;
  controls.zoomSpeed = 0.7;
  controls.rotateSpeed = 0.6;
  controls.panSpeed = 0.8;
  controls.minDistance = MIN_DISTANCE;
  controls.maxDistance = MAX_DISTANCE;
  controls.minPolarAngle = 0.001;
  controls.maxPolarAngle = Math.PI * 0.44;
  controls.zoomToCursor = true;
  const abort = new AbortController();
  let disposed = false,
    failed = false,
    visible = true,
    frame = null,
    dirty = true,
    quality = "medium",
    transition = null;
  let frames = 0,
    lastStats = performance.now(),
    renderMs = 0,
    loadStarted = performance.now(),
    loadMs = null;
  let lastHeading = null;
  const offset = new THREE.Vector3(),
    spherical = new THREE.Spherical();
  const wake = () => {
    dirty = true;
    if (!disposed && visible && !document.hidden && frame === null)
      frame = requestAnimationFrame(tick);
  };
  function constrain() {
    constrainTerrainCamera(camera, controls.target);
  }
  function tick(now) {
    frame = null;
    if (disposed || failed || !visible || document.hidden) return;
    if (transition) {
      const t = Math.min(1, (now - transition.time) / 350),
        ease = t * t * (3 - 2 * t);
      camera.position.lerpVectors(transition.from, transition.to, ease);
      controls.target.lerpVectors(
        transition.targetFrom,
        transition.targetTo,
        ease,
      );
      if (t === 1) transition = null;
      dirty = true;
    }
    const changed = controls.update();
    constrain();
    if (dirty || changed) {
      hazards.camera(camera, controls.target);
      const start = performance.now();
      renderer.render(scene, camera);
      renderMs += performance.now() - start;
      frames++;
      const heading = Math.round(
        THREE.MathUtils.radToDeg(controls.getAzimuthalAngle()),
      );
      if (heading !== lastHeading) {
        host.parentElement.style.setProperty(
          "--terrain-heading",
          `${-heading}deg`,
        );
        lastHeading = heading;
      }
      if (now - lastStats >= 1000) {
        onStats({
          renderMs: renderMs / frames,
          frames,
          sampleMs: now - lastStats,
          calls: renderer.info.render.calls,
          triangles: renderer.info.render.triangles,
          geometries: renderer.info.memory.geometries,
          pixelRatio: renderer.getPixelRatio(),
          loadMs,
          camera: camera.position.toArray().map(Math.round),
          target: controls.target.toArray().map(Math.round),
          renderer: renderer
            .getContext()
            .getParameter(renderer.getContext().RENDERER),
        });
        frames = 0;
        renderMs = 0;
        lastStats = now;
      }
      dirty = false;
    }
    if (changed || transition) wake();
  }
  controls.addEventListener("change", wake);
  const cancelTransition = () => {
    transition = null;
  };
  controls.addEventListener("start", cancelTransition);
  function moveTo(position, target, animate = true) {
    // Reset residual OrbitControls momentum before deliberate camera commands.
    controls.enableDamping = false;
    controls.update();
    controls.enableDamping = true;
    if (animate)
      transition = {
        from: camera.position.clone(),
        to: position,
        targetFrom: controls.target.clone(),
        targetTo: target,
        time: performance.now(),
      };
    else {
      camera.position.copy(position);
      controls.target.copy(target);
    }
    wake();
  }
  function fitDistance() {
    return Math.min(
      800000,
      Math.max(
        280000,
        120000 / (Math.tan(Math.PI / 8) * Math.min(camera.aspect, 1)),
      ),
    );
  }
  function reset(animate = true) {
    const target = new THREE.Vector3(0, 6500, 0);
    moveTo(
      target
        .clone()
        .add(
          new THREE.Vector3(130000, 153500, 180000)
            .normalize()
            .multiplyScalar(fitDistance()),
        ),
      target,
      animate,
    );
  }
  function orbit(theta, phi, zoom = 1) {
    transition = null;
    offset.copy(camera.position).sub(controls.target);
    spherical.setFromVector3(offset);
    spherical.theta += theta;
    spherical.phi = THREE.MathUtils.clamp(
      spherical.phi + phi,
      controls.minPolarAngle,
      controls.maxPolarAngle,
    );
    spherical.radius = THREE.MathUtils.clamp(
      spherical.radius * zoom,
      MIN_DISTANCE,
      MAX_DISTANCE,
    );
    camera.position
      .copy(controls.target)
      .add(offset.setFromSpherical(spherical));
    constrain();
    wake();
  }
  function pan(dx, dy) {
    transition = null;
    const amount = camera.position.distanceTo(controls.target) * 0.0015;
    const right = new THREE.Vector3().setFromMatrixColumn(camera.matrix, 0);
    right.y = 0;
    right.normalize();
    const forward = new THREE.Vector3()
      .crossVectors(camera.up, right)
      .normalize();
    const delta = right
      .multiplyScalar(-dx * amount)
      .addScaledVector(forward, dy * amount);
    controls.target.add(delta);
    camera.position.add(delta);
    constrain();
    wake();
  }
  function pick(clientX, clientY) {
    if (!visualGrid || !geometryReady || failed) return null;
    const rect = canvas.getBoundingClientRect();
    camera.updateMatrixWorld();
    scene.updateMatrixWorld(true);
    raycaster.setFromCamera(
      new THREE.Vector2(
        ((clientX - rect.left) / rect.width) * 2 - 1,
        (-(clientY - rect.top) / rect.height) * 2 + 1,
      ),
      camera,
    );
    const terrainHit = raycaster.intersectObjects(selectable, false)[0];
    const hazardHit = raycaster.intersectObjects(
      hazards.group.children.filter((o) => o.isSprite && o.visible),
      false,
    )[0];
    if (hazardHit && (!terrainHit || hazardHit.distance < terrainHit.distance))
      return { hazardId: hazardHit.object.userData.hazardId };
    const markerHit = raycaster
      .intersectObjects(
        annotations.group.children.filter((object) => object.userData.markerId),
        true,
      )
      .find((hit) => hit.object.userData.markerId);
    if (markerHit && (!terrainHit || markerHit.distance < terrainHit.distance))
      return { markerId: markerHit.object.userData.markerId };
    if (!terrainHit) return null;
    const { point, face } = terrainHit;
    // Move infinitesimally into the hit column at a vertical face; never select its base.
    const x = point.x - (face?.normal.x || 0) * 0.01,
      z = point.z - (face?.normal.z || 0) * 0.01;
    const y = visualGrid.getVisualElevation(x, z);
    return y === null ? null : { x, y, z, ...visualGrid.modelToGrid(x, z) };
  }
  const unbind = bindTerrainInput(canvas, {
    pan,
    gesture: ({ zoom, twist, tilt }) => orbit(-twist, tilt * 0.004, zoom),
    inspect: (x, y) => onInspect?.(pick(x, y)),
    place: (x, y) => onPlace?.(pick(x, y)),
  });
  function resize() {
    if (disposed) return;
    const { width, height } = host.getBoundingClientRect();
    if (!width || !height) return;
    renderer.setPixelRatio(
      Math.min(window.devicePixelRatio || 1, RATIOS[quality]),
    );
    renderer.setSize(width, height);
    annotations.resize(width, height);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    wake();
  }
  const observer = new ResizeObserver(resize);
  observer.observe(host);
  const intersection = new IntersectionObserver(([entry]) => {
    visible = entry.isIntersecting;
    if (visible) wake();
  });
  intersection.observe(host);
  const visibility = () => {
    if (!document.hidden) wake();
  };
  document.addEventListener("visibilitychange", visibility);
  const lost = (event) => {
    event.preventDefault();
    fail(new Error("Graphics context lost. Retry to restore the terrain."));
  };
  canvas.addEventListener("webglcontextlost", lost);
  function fail(error) {
    if (disposed || failed) return;
    failed = true;
    abort.abort();
    cancelAnimationFrame(frame);
    frame = null;
    visible = false;
    onError(error.message || "Unable to open the terrain.");
  }
  resize();
  reset(false);
  Promise.all([
    loadVisualGrid(baseUrl, abort.signal).then((grid) => {
      if (!disposed) {
        visualGrid = grid;
        onGeometry?.(grid);
      }
    }),
    loadTerrain({
      baseUrl,
      signal: abort.signal,
      onProgress,
      onChunk: (chunk) => {
        if (disposed || failed) {
          disposeTerrain(chunk);
          return;
        }
        chunk.traverse((mesh) => {
          if (mesh.isMesh) {
            mesh.geometry.boundsTree = new MeshBVH(mesh.geometry, {
              indirect: true,
            });
            mesh.raycast = acceleratedRaycast;
            selectable.push(mesh);
          }
        });
        terrain.add(chunk);
        wake();
      },
    }),
  ])
    .then(([, manifest]) => {
      if (disposed || failed) return;
      const identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
      if (
        manifest.source_sha256 !== visualGrid.metadata.source_sha256 ||
        !identity.every(
          (v, i) =>
            manifest.original_to_optimized?.[i] === v &&
            visualGrid.metadata.modelToOptimized?.[i] === v,
        )
      )
        throw new Error(
          "Visual grid and terrain use incompatible sources or transforms.",
        );
      geometryReady = true;
      loadMs = performance.now() - loadStarted;
      onReady();
      wake();
    })
    .catch((error) => {
      if (error.name !== "AbortError") fail(error);
    });
  return {
    reset,
    setHazards: (regions, categories, selected) => {
      hazards.set(regions, categories, selected);
      wake();
    },
    setAnnotations: (points, vertices, inspection, selectedId) => {
      annotations.update(points, vertices, inspection, selectedId);
      wake();
    },
    top: () =>
      moveTo(
        new THREE.Vector3(
          controls.target.x,
          controls.target.y + fitDistance(),
          controls.target.z + 1,
        ),
        controls.target.clone(),
      ),
    perspective: () =>
      moveTo(
        controls.target
          .clone()
          .add(
            new THREE.Vector3(110000, 135000, 150000)
              .normalize()
              .multiplyScalar(fitDistance()),
          ),
        controls.target.clone(),
      ),
    focus: (position) => {
      if (
        !Array.isArray(position) ||
        position.length !== 3 ||
        !position.every(Number.isFinite)
      )
        return;
      const target = new THREE.Vector3(...position);
      moveTo(
        target
          .clone()
          .add(
            camera.position
              .clone()
              .sub(controls.target)
              .normalize()
              .multiplyScalar(60000),
          ),
        target,
      );
    },
    orbit,
    pan,
    zoom: (factor) => orbit(0, 0, factor),
    setQuality: (value) => {
      quality = value in RATIOS ? value : "medium";
      resize();
    },
    dispose: () => {
      disposed = true;
      abort.abort();
      cancelAnimationFrame(frame);
      observer.disconnect();
      intersection.disconnect();
      unbind();
      document.removeEventListener("visibilitychange", visibility);
      canvas.removeEventListener("webglcontextlost", lost);
      controls.removeEventListener("change", wake);
      controls.removeEventListener("start", cancelTransition);
      controls.dispose();
      hazards.dispose();
      annotations.dispose();
      for (const mesh of selectable) mesh.geometry.boundsTree = null;
      selectable.length = 0;
      visualGrid = null;
      disposeTerrain(terrain);
      scene.clear();
      renderer.renderLists.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
      canvas.remove();
    },
  };
}
