import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { createVisualGrid } from '../src/terrain/visualGrid.js'
import { traceVisualSegment, buildVisualRoute, importPreliminaryRoute } from '../src/terrain/visualRoute.js'
const fixture=(values,mask=values.map(()=>1),rows=1)=>createVisualGrid({rows,columns:values.length/rows,cellSize:250,originX:-500,originZ:-250},Float32Array.from(values),Uint8Array.from(mask))
function assertAbove(grid,vertices){
 for(let i=1;i<vertices.length;i++){
  const a=vertices[i-1],b=vertices[i]
  for(let k=0;k<=40;k++){
   const t=k/40,x=a[0]+(b[0]-a[0])*t,z=a[2]+(b[2]-a[2])*t,y=a[1]+(b[1]-a[1])*t,h=grid.getVisualElevation(x,z)
   if(h!==null)assert.ok(y>=h+7.999,`route under surface: ${x}, ${z}, ${y} < ${h}`)
  }
 }
}
test('grid centers round-trip; bounds half-open; missing/NaN data never zero-filled',()=>{
 const g=fixture([10,20,NaN,40],[1,1,0,1],2)
 assert.deepEqual(g.modelToGrid(-375,-125),{row:0,column:0});assert.deepEqual(g.gridToModel(0,0),{x:-375,y:10,z:-125})
 assert.equal(g.getVisualElevation(-250,-125),20);assert.equal(g.modelToGrid(0,0),null)
 assert.equal(g.getVisualElevation(-375,125),null);assert.equal(g.isValidTerrainPosition(NaN,0),false)
 assert.equal(g.gridToModel(.5,0),null);assert.equal(g.gridToModel(1,0),null)
})
test('manual route climbs mountain, descends valley, and stays on each flat cell',()=>{
 const g=fixture([10,1000,20,500,10]),a=g.gridToModel(0,0),b=g.gridToModel(0,4),r=traceVisualSegment(g,a,b)
 assert.equal(r.error,null);assertAbove(g,r.vertices)
 for(let c=0;c<5;c++){const p=g.gridToModel(0,c);let found=false;for(let i=1;i<r.vertices.length;i++){const a=r.vertices[i-1],b=r.vertices[i];if(a[0]<=p.x&&p.x<=b[0]&&a[1]===p.y+8&&b[1]===p.y+8)found=true}assert.ok(found)}
 assertAbove(g,traceVisualSegment(g,b,a).vertices)
})
test('NoData interrupts route prefix and exact corners cannot cut invalid neighbors',()=>{
 const g=fixture([10,20,30,40],[1,1,0,1]),r=traceVisualSegment(g,g.gridToModel(0,0),g.gridToModel(0,3))
 assert.match(r.error,/invalid/);assert.ok(r.vertices.every(p=>p[0]<=0))
 const corner=fixture([10,20,30,40],[1,0,1,1],2)
 assert.match(traceVisualSegment(corner,corner.gridToModel(0,0),corner.gridToModel(1,1)).error,/invalid/)
 assert.match(traceVisualSegment(g,{x:-501,z:-125},g.gridToModel(0,1)).error,/outside/)
})
test('routes on shared edges follow higher adjoining cells, not buried in walls',()=>{
 const g=fixture([10,20,100,200],undefined,2)
 const r=traceVisualSegment(g,{x:-375,z:0},{x:-125,z:0})
 assert.equal(r.error,null);assert.ok(r.vertices.every(v=>v[1]>=108));assertAbove(g,r.vertices)
})
const meta=JSON.parse(await readFile(new URL('../public/terrain/terrain_metadata.json',import.meta.url)))
const raw=await readFile(new URL('../public/terrain/visual_elevation.bin',import.meta.url))
const heights=new Float32Array(meta.rows*meta.columns);for(let i=0;i<heights.length;i++)heights[i]=raw.readFloatLE(i*4)
const grid=createVisualGrid(meta,heights,await readFile(new URL('../public/terrain/valid_mask.bin',import.meta.url)))
const reference=JSON.parse(await readFile(new URL('../public/terrain/preliminary-route.json',import.meta.url)))
test('original 155-point route imports in identity coordinates and every drawn segment clears original visual heights',()=>{
 const points=importPreliminaryRoute(reference,grid)
 assert.equal(points.length,155);assert.equal(points[0].x,24875);assert.equal(points.at(-1).z,-20625)
 assert.equal(points[0].y,5790);assert.equal(points.at(-1).y,7350)
 const route=buildVisualRoute(grid,points);assert.equal(route.error,null);assertAbove(grid,route.vertices)
 const bad=structuredClone(reference);bad.points[4].y+=1;assert.throws(()=>importPreliminaryRoute(bad,grid),/does not match/)
})
test('real grid all valid centers round-trip and finite mask count matches extraction',()=>{
 let count=0
 for(let r=0;r<meta.rows;r++)for(let c=0;c<meta.columns;c++){
  const p=grid.gridToModel(r,c);if(!p)continue;count++;assert.deepEqual(grid.modelToGrid(p.x,p.z),{row:r,column:c});assert.equal(grid.getVisualElevation(p.x,p.z),p.y)
 }
 assert.equal(count,507538);assert.equal(count,meta.validCells)
})
test('BVH raycaster on an actual optimized chunk hits column tops matching original grid',async()=>{
 const {GLTFLoader}=await import('three/addons/loaders/GLTFLoader.js'),{MeshoptDecoder}=await import('meshoptimizer')
 const {MeshBVH,acceleratedRaycast}=await import('three-mesh-bvh'),{Raycaster,Vector3}=await import('three')
 const manifest=JSON.parse(await readFile(new URL('../public/terrain/manifest.json',import.meta.url)))
 const file=manifest.assets.find(asset=>asset.file.startsWith('chunks/')).file
 const bytes=await readFile(new URL(`../public/terrain/${file}`,import.meta.url))
 const gltf=await new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'')
 const meshes=[];gltf.scene.traverse(o=>{if(o.isMesh){o.geometry.boundsTree=new MeshBVH(o.geometry,{indirect:true});o.raycast=acceleratedRaycast;meshes.push(o)}});gltf.scene.updateMatrixWorld(true)
 const ray=new Raycaster();ray.firstHitOnly=true;let checked=0
 for(let r=0;r<meta.rows;r+=7)for(let c=0;c<meta.columns;c+=7){const p=grid.gridToModel(r,c);if(!p)continue;ray.set(new Vector3(p.x,20000,p.z),new Vector3(0,-1,0));const hit=ray.intersectObjects(meshes,false)[0];if(hit){assert.ok(Math.abs(hit.point.y-p.y)<.001);checked++}}
 assert.ok(checked>20);for(const mesh of meshes){mesh.geometry.dispose();mesh.material.dispose()}
})


test('route endpoints at exact steps clear the higher touching column',()=>{
 const g=fixture([1000,10,2000])
 for(const [a,b] of [[{x:-250,z:-125},{x:-125,z:-125}],[{x:-125,z:-125},{x:0,z:-125}]]){
  const route=traceVisualSegment(g,a,b);assert.equal(route.error,null);assertAbove(g,route.vertices)
 }
 assert.match(traceVisualSegment(g,{x:-500,z:-125},{x:-375,z:-125}).error,/invalid edge/)
})
