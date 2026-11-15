import * as THREE from 'three'
import { Line2 } from 'three/addons/lines/Line2.js'
import { LineGeometry } from 'three/addons/lines/LineGeometry.js'
import { LineMaterial } from 'three/addons/lines/LineMaterial.js'
import { disposeTerrain } from './loadTerrain.js'

export function createTerrainAnnotations(scene) {
  const group=new THREE.Group();group.name='Geometric annotations';scene.add(group)
  let width=1,height=1
  function clear(){disposeTerrain(group);group.clear()}
  function update(points,vertices,inspection,selectedId){
    clear()
    if(vertices.length>1){
      const geometry=new LineGeometry().setPositions(vertices.flat())
      const material=new LineMaterial({color:0x42caff,linewidth:3,transparent:true,opacity:.95,depthTest:true})
      material.resolution.set(width,height)
      group.add(new Line2(geometry,material))
    }
    for(const point of [...points,...(inspection?[inspection]:[])]){
      const marker=new THREE.Group();marker.position.set(point.x,point.y+12,point.z);marker.userData.markerId=point.id
      const material=new THREE.MeshBasicMaterial({color:point.id===selectedId?0xc8f6ff:0x42caff,transparent:true,opacity:.9})
      if(point.type==='Waypoint' && point.id!==selectedId){
        const dot=new THREE.Mesh(new THREE.OctahedronGeometry(110),material);dot.position.y=110;dot.userData.markerId=point.id;marker.add(dot);group.add(marker);continue
      }
      const ring=new THREE.Mesh(new THREE.TorusGeometry(500,60,6,24),material);ring.rotation.x=-Math.PI/2;ring.userData.markerId=point.id;marker.add(ring)
      const stem=new THREE.Mesh(new THREE.CylinderGeometry(35,35,1800,6),material);stem.position.y=900;stem.userData.markerId=point.id;marker.add(stem)
      const tip=new THREE.Mesh(new THREE.OctahedronGeometry(250),material);tip.position.y=1800;tip.userData.markerId=point.id;marker.add(tip)
      const canvas=document.createElement('canvas');canvas.width=512;canvas.height=80;const ctx=canvas.getContext('2d');ctx.fillStyle='#9ce7ff';ctx.font='bold 28px Segoe UI';ctx.textAlign='center';ctx.fillText(`${point.type} · ${point.label}`.slice(0,45),256,45)
      const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace
      const sprite=new THREE.Sprite(new THREE.SpriteMaterial({map:texture,depthTest:true,transparent:true}));sprite.scale.set(6000,938,1);sprite.position.y=2800;sprite.userData.markerId=point.id;marker.add(sprite)
      group.add(marker)
    }
  }
  return {update,group,resize:(w,h)=>{width=w;height=h;group.traverse(o=>{if(o.material?.isLineMaterial)o.material.resolution.set(w,h)})},dispose:()=>{clear();scene.remove(group)}}
}
