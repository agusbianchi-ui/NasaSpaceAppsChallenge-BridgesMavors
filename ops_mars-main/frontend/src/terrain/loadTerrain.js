import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { MeshoptDecoder } from 'meshoptimizer'

export function disposeTerrain(root) {
  const geometries = new Set(), materials = new Set(), textures = new Set()
  root.traverse((object) => {
    if (object.geometry) geometries.add(object.geometry)
    for (const material of [object.material].flat().filter(Boolean)) {
      materials.add(material)
      for (const value of Object.values(material)) if (value?.isTexture) textures.add(value)
    }
  })
  for (const texture of textures) { texture.source?.data?.close?.(); texture.dispose() }
  for (const material of materials) material.dispose()
  for (const geometry of geometries) geometry.dispose()
}

// Fetch is cancellable; GLTF parsing is not. Dispose late parse results on cancellation.
export async function loadTerrain({ baseUrl, signal, onChunk, onProgress }) {
  const response = await fetch(`${baseUrl}/manifest.json`, { signal })
  if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) throw new Error('Terrain resources are unavailable. Please retry when the download is available.')
  const manifest = await response.json()
  const files = manifest.assets.filter((a) => a.file.startsWith('chunks/') && a.lod === 0)
  if (!files.length) throw new Error('The terrain manifest has no LOD0 chunks.')
  const total = files.reduce((sum, a) => sum + a.bytes, 0)
  const received = new Map()
  let next = 0, complete = 0
  const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder)
  await MeshoptDecoder.ready
  const progress = () => onProgress({ bytes: [...received.values()].reduce((a, b) => a + b, 0), total, complete, count: files.length })
  async function worker() {
    while (next < files.length) {
      signal.throwIfAborted()
      const file = files[next++]
      const response = await fetch(`${baseUrl}/${file.file}`, { signal })
      if (!response.ok) throw new Error(`A terrain sector could not be loaded (${response.status}).`)
      const reader = response.body.getReader(), pieces = []
      let length = 0
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        pieces.push(value); length += value.length; received.set(file.file, length); progress()
      }
      if (length !== file.bytes) throw new Error('Terrain download size does not match its manifest.')
      const data = new Uint8Array(length)
      let offset = 0
      for (const part of pieces) { data.set(part, offset); offset += part.length }
      const hash = [...new Uint8Array(await crypto.subtle.digest('SHA-256', data))].map(v => v.toString(16).padStart(2, '0')).join('')
      if (hash !== file.sha256) throw new Error('Terrain integrity check failed.')
      signal.throwIfAborted()
      const gltf = await loader.parseAsync(data.buffer, `${baseUrl}/`)
      if (signal.aborted) { disposeTerrain(gltf.scene); signal.throwIfAborted() }
      onChunk(gltf.scene); complete++; progress()
    }
  }
  await Promise.all([worker(), worker()])
  return manifest
}
