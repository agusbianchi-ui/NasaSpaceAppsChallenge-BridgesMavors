import { readFile, access } from 'node:fs/promises'
import path from 'node:path'

const root = path.resolve('public/terrain')
const manifest = JSON.parse(await readFile(path.join(root, 'manifest.json'), 'utf8'))
const chunks = manifest.assets.filter(asset => asset.file.startsWith('chunks/'))
if (!chunks.length) throw new Error('No terrain chunks in manifest')
await Promise.all([
  ...chunks.map(asset => access(path.join(root, asset.file))),
  ...['terrain_metadata.json', 'visual_elevation.bin', 'valid_mask.bin', 'preliminary-route.json'].map(file => access(path.join(root, file))),
])
console.log(`Found ${chunks.length} terrain chunks and viewer data`)
