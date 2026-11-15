export function createVisualGrid(metadata, elevations, mask) {
  const { rows, columns, cellSize: size, originX, originZ } = metadata
  if (!(rows > 0 && columns > 0 && size > 0) || elevations.length !== rows * columns || mask.length !== elevations.length) throw new Error('Invalid visual terrain grid.')
  const modelToGrid = (x, z) => {
    if (!Number.isFinite(x) || !Number.isFinite(z)) return null
    const row = Math.floor((z - originZ) / size), column = Math.floor((x - originX) / size)
    return row >= 0 && row < rows && column >= 0 && column < columns ? { row, column } : null
  }
  const cellHeight = (row, column) => {
    if (row < 0 || column < 0 || row >= rows || column >= columns) return null
    const i = row * columns + column
    return mask[i] === 1 && Number.isFinite(elevations[i]) ? elevations[i] : null
  }
  const gridToModel = (row, column) => {
    if (!Number.isInteger(row) || !Number.isInteger(column) || cellHeight(row, column) === null) return null
    return { x: originX + (column + .5) * size, y: cellHeight(row, column), z: originZ + (row + .5) * size }
  }
  const getVisualElevation = (x, z) => { const cell = modelToGrid(x, z); return cell ? cellHeight(cell.row, cell.column) : null }
  // At an exact edge/corner use the upper envelope of every touching column.
  // This prevents a route on a grid boundary from running inside a taller neighbor.
  const boundaryHeight = (x, z) => {
    const c = (x - originX) / size, r = (z - originZ) / size
    const cs = Math.abs(c - Math.round(c)) < 1e-8 ? [Math.round(c)-1, Math.round(c)] : [Math.floor(c)]
    const rs = Math.abs(r - Math.round(r)) < 1e-8 ? [Math.round(r)-1, Math.round(r)] : [Math.floor(r)]
    const heights = rs.flatMap(row => cs.map(col => cellHeight(row, col)))
    return heights.some(h => h === null) ? null : Math.max(...heights)
  }
  return { metadata, modelToGrid, gridToModel, cellHeight, getVisualElevation, boundaryHeight, isValidTerrainPosition: (x,z) => getVisualElevation(x,z) !== null }
}

export async function loadVisualGrid(baseUrl, signal) {
  const response = await fetch(`${baseUrl}/terrain_metadata.json`, { signal })
  if (!response.ok || !response.headers.get('content-type')?.includes('json')) throw new Error('Visual terrain geometry is unavailable.')
  const metadata = await response.json()
  const arrays = await Promise.all(['visual_elevation.bin', 'valid_mask.bin'].map(async name => {
    const response = await fetch(`${baseUrl}/${name}`, { signal })
    if (!response.ok) throw new Error('Visual terrain data could not be downloaded.')
    const buffer = await response.arrayBuffer()
    const hash = [...new Uint8Array(await crypto.subtle.digest('SHA-256',buffer))].map(v=>v.toString(16).padStart(2,'0')).join('')
    if (hash !== metadata[name].sha256 || buffer.byteLength !== metadata[name].bytes) throw new Error('Visual terrain integrity check failed.')
    return buffer
  }))
  const view = new DataView(arrays[0]), values = new Float32Array(metadata.rows * metadata.columns)
  for (let i=0; i<values.length; i++) values[i] = view.getFloat32(i*4,true)
  return createVisualGrid(metadata, values, new Uint8Array(arrays[1]))
}
