import test from 'node:test'
import assert from 'node:assert/strict'
import {readFile} from 'node:fs/promises'
import {createVisualGrid} from '../src/terrain/visualGrid.js'
import {buildVisualRoute} from '../src/terrain/visualRoute.js'
test('calculated A* alternatives follow every original visual block without cutting mountains',async()=>{
 const meta=JSON.parse(await readFile(new URL('../public/terrain/terrain_metadata.json',import.meta.url)))
 const bytes=await readFile(new URL('../public/terrain/visual_elevation.bin',import.meta.url)),values=new Float32Array(meta.rows*meta.columns)
 for(let i=0;i<values.length;i++)values[i]=bytes.readFloatLE(i*4)
 const grid=createVisualGrid(meta,values,await readFile(new URL('../public/terrain/valid_mask.bin',import.meta.url)))
 const result=JSON.parse(await readFile(new URL('../../../docs/stages/05-06-evidence/real-route-validation.json',import.meta.url)))
 for(const route of result.routes.filter(r=>r.success)){
  const trace=buildVisualRoute(grid,route.path_local);assert.equal(trace.error,null)
  for(let i=1;i<trace.vertices.length;i++){
   const a=trace.vertices[i-1],b=trace.vertices[i]
   for(let step=0;step<=20;step++){
    const t=step/20,x=a[0]+(b[0]-a[0])*t,y=a[1]+(b[1]-a[1])*t,z=a[2]+(b[2]-a[2])*t,h=grid.getVisualElevation(x,z)
    assert.notEqual(h,null);assert.ok(y>=h+7.999,'Calculated route entered a visual column')
   }
  }
 }
})
