import test from 'node:test'
import assert from 'node:assert/strict'
import { bindTerrainInput, touchDelta } from '../src/terrain/terrainInput.js'
import { PerspectiveCamera, MOUSE } from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
class Canvas extends EventTarget {
  style = {}; ownerDocument = new EventTarget(); clientHeight = 800; clientWidth = 1200
  setPointerCapture() {} releasePointerCapture() {}
  getBoundingClientRect() { return {left:0,top:0,width:1200,height:800} }
}
function send(target, type, x, y, extra = {}) {
  const e = new Event(type, {cancelable:true});Object.assign(e,{clientX:x,clientY:y,pageX:x,pageY:y,pointerId:1,pointerType:'touch',button:0,...extra});target.dispatchEvent(e)
}
test('touch pinch, twist and tilt independently map to expected camera deltas', () => {
 const a=[{x:0,y:0},{x:100,y:0}]
 assert.equal(touchDelta(a,[{x:-50,y:0},{x:150,y:0}]).zoom,0.5)
 assert.ok(Math.abs(touchDelta(a,[{x:50,y:-50},{x:50,y:50}]).twist-Math.PI/2)<1e-10)
 assert.equal(touchDelta(a,[{x:0,y:30},{x:100,y:30}]).tilt,30)
})
test('emulated touch stream pans; drag is not a tap; two fingers never place markers', () => {
 const c=new Canvas(),pans=[],gestures=[];let taps=0
 const remove=bindTerrainInput(c,{pan:(...p)=>pans.push(p),gesture:g=>gestures.push(g),place:()=>taps++})
 send(c,'pointerdown',0,0);send(c,'pointermove',20,10);send(c,'pointerup',20,10)
 assert.equal(pans.length,1);assert.equal(taps,0)
 send(c,'pointerdown',0,0);send(c,'pointerdown',100,0,{pointerId:2});send(c,'pointermove',200,0,{pointerId:2});send(c,'pointerup',0,0);send(c,'pointerup',200,0,{pointerId:2})
 assert.equal(gestures.length,1);assert.equal(gestures[0].zoom,.5);assert.equal(taps,0)
 send(c,'pointerdown',0,0);send(c,'pointerup',0,0);assert.equal(taps,1)
 remove();send(c,'pointerdown',0,0);send(c,'pointermove',50,50);assert.equal(pans.length,1)
})
test('long press reserves inspection, never also places a marker', async () => {
 const c=new Canvas();let inspect=0,place=0;const remove=bindTerrainInput(c,{inspect:()=>inspect++,place:()=>place++})
 send(c,'pointerdown',20,20);await new Promise(r=>setTimeout(r,580));send(c,'pointerup',20,20)
 assert.equal(inspect,1);assert.equal(place,0);remove()
})
test('cancelled touch and right drag never become inspection clicks',()=>{
 const c=new Canvas();let inspect=0,place=0;const remove=bindTerrainInput(c,{inspect:()=>inspect++,place:()=>place++})
 send(c,'pointerdown',0,0);send(c,'pointercancel',0,0)
 send(c,'pointerdown',0,0,{pointerType:'mouse',button:2});send(c,'pointermove',40,20,{pointerType:'mouse',button:2});send(c,'pointerup',40,20,{pointerType:'mouse',button:2});assert.equal(inspect,0);assert.equal(place,0)
 send(c,'pointerdown',0,0,{pointerType:'mouse',button:2});send(c,'pointerup',0,0,{pointerType:'mouse',button:2});assert.equal(inspect,1);remove()
})
test('actual OrbitControls desktop mapping pans left, rotates right and zooms wheel',()=>{
 const c=new Canvas(),camera=new PerspectiveCamera(45,1.5,50,1200000);camera.position.set(130000,160000,180000)
 const controls=new OrbitControls(camera,c);controls.mouseButtons={LEFT:MOUSE.PAN,MIDDLE:MOUSE.DOLLY,RIGHT:MOUSE.ROTATE};controls.screenSpacePanning=false
 const before=controls.target.clone()
 send(c,'pointerdown',400,400,{pointerType:'mouse'});send(c.ownerDocument,'pointermove',500,400,{pointerType:'mouse'});send(c.ownerDocument,'pointerup',500,400,{pointerType:'mouse'})
 assert.ok(before.distanceTo(controls.target)>0);assert.equal(controls.target.y,0)
 const angle=controls.getAzimuthalAngle(),tilt=controls.getPolarAngle()
 send(c,'pointerdown',400,400,{pointerType:'mouse',button:2});send(c.ownerDocument,'pointermove',500,450,{pointerType:'mouse',button:2});send(c.ownerDocument,'pointerup',500,450,{pointerType:'mouse',button:2})
 assert.notEqual(angle,controls.getAzimuthalAngle());assert.notEqual(tilt,controls.getPolarAngle())
 const distance=camera.position.distanceTo(controls.target)
 send(c,'wheel',400,400,{pointerType:'mouse',deltaY:-100,deltaMode:0});assert.ok(camera.position.distanceTo(controls.target)<distance)
 controls.dispose()
})

// The safety envelope is conservative over every original triangle, including chunks not yet loaded.
test('camera cannot enter the terrain and focus remains bounded after extreme movement', async () => {
 const { constrainTerrainCamera } = await import('../src/terrain/terrainCamera.js')
 const { Vector3 } = await import('three')
 const camera = new PerspectiveCamera();camera.position.set(400000,-10000,200000)
 const target = new Vector3(200000,-5000,200000)
 constrainTerrainCamera(camera,target)
 assert.ok(Math.hypot(target.x,target.z) <= 95000.00001)
 assert.equal(target.y,1800);assert.equal(camera.position.y,16462)
 assert.ok(camera.position.y - camera.near > 15462)
})
