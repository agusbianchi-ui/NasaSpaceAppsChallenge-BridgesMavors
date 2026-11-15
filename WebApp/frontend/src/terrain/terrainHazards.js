import * as THREE from "three";
import { disposeTerrain } from "./loadTerrain.js";

export function createTerrainHazards(scene) {
  const group = new THREE.Group();
  group.name = "Scientific hazard annotations";
  scene.add(group);
  let regions = [],
    categories = new Set(),
    far = null,
    selected = null,
    boundary = null;
  function clear() {
    disposeTerrain(group);
    group.clear();
    boundary = null;
  }
  function rebuild(isFar) {
    clear();
    far = isFar;
    const visible = regions.filter((r) => categories.has(r.category)),
      items = [];
    if (isFar) {
      const buckets = new Map();
      for (const r of visible) {
        const key = `${r.category}:${Math.floor(r.x / 50000)}:${Math.floor(r.z / 50000)}`;
        const current = buckets.get(key);
        if (current) {
          current.count++;
          current.cells += r.cell_count;
          if (r.severity === "high") current.severity = "high";
        } else buckets.set(key, { ...r, count: 1, cells: r.cell_count });
      }
      items.push(...buckets.values());
    } else
      items.push(
        ...visible.map((r) => ({ ...r, count: 1, cells: r.cell_count })),
      );
    items.sort(
      (a, b) =>
        (b.id === selected ? 100 : b.severity === "high" ? 10 : 0) -
        (a.id === selected ? 100 : a.severity === "high" ? 10 : 0),
    );
    for (const item of items) {
      const canvas = document.createElement("canvas");
      canvas.width = 512;
      canvas.height = 128;
      const ctx = canvas.getContext("2d");
      ctx.strokeStyle = item.severity === "high" ? "#ffaf63" : "#65d8ff";
      ctx.lineWidth = 6;
      ctx.beginPath();
      ctx.moveTo(18, 25);
      ctx.lineTo(18, 104);
      ctx.lineTo(490, 104);
      ctx.stroke();
      ctx.fillStyle = ctx.strokeStyle;
      ctx.textAlign = "center";
      ctx.font = "bold 38px Segoe UI";
      ctx.fillText(
        `${item.icon || "!"} ${item.category.replaceAll("_", " ")}${item.count > 1 ? ` ×${item.count}` : ""}`,
        256,
        52,
      );
      ctx.font = "24px Segoe UI";
      ctx.fillText(
        `${item.severity.toUpperCase()} · ${item.cells} cells`,
        256,
        96,
      );
      const texture = new THREE.CanvasTexture(canvas);
      texture.colorSpace = THREE.SRGBColorSpace;
      const sprite = new THREE.Sprite(
        new THREE.SpriteMaterial({
          map: texture,
          depthTest: true,
          transparent: true,
        }),
      );
      sprite.position.set(item.x, item.y + 4500, item.z);
      sprite.userData.hazardId = item.id;
      sprite.userData.region = item;
      group.add(sprite);
      const glyphCanvas = document.createElement("canvas");
      glyphCanvas.width = 64;
      glyphCanvas.height = 64;
      const glyphContext = glyphCanvas.getContext("2d");
      glyphContext.fillStyle = item.severity === "high" ? "#ffaf63" : "#65d8ff";
      glyphContext.textAlign = "center";
      glyphContext.font = "bold 52px Segoe UI";
      glyphContext.fillText(item.icon || "!", 32, 54);
      const glyphTexture = new THREE.CanvasTexture(glyphCanvas);
      glyphTexture.colorSpace = THREE.SRGBColorSpace;
      const glyph = new THREE.Sprite(
        new THREE.SpriteMaterial({
          map: glyphTexture,
          depthTest: true,
          transparent: true,
        }),
      );
      glyph.position.set(item.x, item.y + 1000, item.z);
      glyph.userData.hazardId = item.id;
      glyph.userData.glyph = true;
      group.add(glyph);
      const line = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(item.x, item.y + 20, item.z),
          new THREE.Vector3(item.x, item.y + 4200, item.z),
        ]),
        new THREE.LineBasicMaterial({
          color: 0x65d8ff,
          transparent: true,
          opacity: 0.6,
        }),
      );
      group.add(line);
    }
    if (selected) {
      const region = regions.find((r) => r.id === selected);
      if (region?.boundary?.length && categories.has(region.category)) {
        const geometry = new THREE.BufferGeometry().setAttribute(
          "position",
          new THREE.Float32BufferAttribute(
            region.boundary.flatMap((p) => [p.x, p.y + 24, p.z]),
            3,
          ),
        );
        boundary = new THREE.Points(
          geometry,
          new THREE.PointsMaterial({
            color: 0xffb75e,
            size: 5,
            sizeAttenuation: false,
            depthTest: true,
          }),
        );
        group.add(boundary);
      }
    }
  }
  return {
    group,
    set: (next, enabled, selection) => {
      regions = next || [];
      categories = new Set(enabled);
      selected = selection;
      rebuild(far ?? true);
    },
    camera: (camera, target) => {
      const distance = camera.position.distanceTo(target),
        isFar = distance > 180000;
      if (far !== isFar) rebuild(isFar);
      const occupied = [],
        projected = new THREE.Vector3();
      for (const object of group.children)
        if (object.isSprite) {
          const depth = camera.position.distanceTo(object.position);
          if (object.userData.glyph) {
            const size = THREE.MathUtils.clamp(depth * 0.025, 300, 15000);
            object.scale.set(size, size, 1);
            continue;
          }
          const size = THREE.MathUtils.clamp(depth * 0.18, 1200, 120000);
          object.scale.set(size, size / 4, 1);
          projected.copy(object.position).project(camera);
          const rect = { x: projected.x, y: projected.y, w: 0.27, h: 0.085 };
          object.visible =
            projected.z <= 1 &&
            projected.z >= -1 &&
            !occupied.some(
              (r) =>
                Math.abs(r.x - rect.x) < (r.w + rect.w) / 2 &&
                Math.abs(r.y - rect.y) < (r.h + rect.h) / 2,
            );
          if (object.visible) occupied.push(rect);
        }
    },
    dispose: () => {
      clear();
      scene.remove(group);
    },
  };
}
