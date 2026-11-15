import test from 'node:test'
import assert from 'node:assert/strict'
import {createVisualGrid} from '../src/terrain/visualGrid.js'
import {getMissionSession,updateMissionSession,exportMission,validateMissionImport,DEFAULT_MISSION} from '../src/services/missionSession.js'
const grid=createVisualGrid({rows:2,columns:2,originX:0,originZ:0,cellSize:250},Float32Array.from([100,200,300,400]),Uint8Array.from([1,1,1,0]))
test('mission export/import preserves valid inputs, reanchors Y, rejects untrusted results and wrong source',()=>{
 const points=[{id:'one',type:'Start',label:'Start',x:125,z:125,y:-999},{id:'two',type:'Destination',label:'Destination',x:375,z:125,y:-999}]
 updateMissionSession({points,mission:DEFAULT_MISSION,strategy:'balanced',results:{routes:[{total_cost:0}]}})
 const exported=exportMission(getMissionSession()),imported=validateMissionImport(exported,grid)
 assert.equal(imported.points[0].y,100);assert.equal(imported.points[1].y,200);assert.equal(imported.results,null)
 assert.throws(()=>validateMissionImport({...exported,source_sha256:'wrong'},grid),/source/)
 assert.throws(()=>validateMissionImport({...exported,points:[{...points[0],x:375,z:375}]},grid),/Invalid/)
 assert.throws(()=>validateMissionImport({...exported,excluded_cells:[[1,2]]},grid),/excluded/)
 updateMissionSession({hazards:{regions:['preserved']},science:{value:10}})
 updateMissionSession(imported)
 assert.deepEqual(getMissionSession().hazards.regions,['preserved'])
 assert.equal(getMissionSession().science.value,10)
})
test('shared conditions invalidate routes and scientific hazards across pages',()=>{
 updateMissionSession({results:{routes:[]},hazards:{regions:[1]},science:{value:10}})
 updateMissionSession({mission:{...DEFAULT_MISSION,max_slope:5}},true)
 assert.equal(getMissionSession().stale,true);assert.equal(getMissionSession().hazards,null);assert.equal(getMissionSession().science,null)
 updateMissionSession({points:[],results:null,stale:false})
})
