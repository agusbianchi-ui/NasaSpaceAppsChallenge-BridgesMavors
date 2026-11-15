import { MathUtils } from 'three'

// All values are original GLB local units, not a geographic coordinate system.
export const TERRAIN_NAVIGATION = Object.freeze({ minDistance: 5000, maxDistance: 850000, targetRadius: 95000, minHeight: 1800, maxHeight: 15462, clearance: 1000 })
export function constrainTerrainCamera(camera, target) {
  const limits = TERRAIN_NAVIGATION, radius = Math.hypot(target.x, target.z)
  if (radius > limits.targetRadius) {
    const dx = target.x * (limits.targetRadius / radius - 1), dz = target.z * (limits.targetRadius / radius - 1)
    target.x += dx; target.z += dz; camera.position.x += dx; camera.position.z += dz
  }
  target.y = MathUtils.clamp(target.y, limits.minHeight, limits.maxHeight)
  // This whole-model bound also protects a camera moving over an unloaded sector.
  camera.position.y = Math.max(limits.maxHeight + limits.clearance, camera.position.y)
  camera.lookAt(target)
}
