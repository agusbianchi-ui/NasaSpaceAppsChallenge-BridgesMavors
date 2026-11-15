import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {NodeIO,Document} from '@gltf-transform/core';
import {EXTMeshoptCompression} from '@gltf-transform/extensions';
import {prune} from '@gltf-transform/functions';
import {MeshoptEncoder,MeshoptDecoder} from 'meshoptimizer';
import validator from 'gltf-validator';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {Box3} from 'three';
const root=path.resolve(import.meta.dirname,'..'),out=path.join(root,'output-stage1');
fs.mkdirSync(out,{recursive:true});fs.mkdirSync(path.join(out,'chunks'),{recursive:true});
await MeshoptEncoder.ready;await MeshoptDecoder.ready;
const io=new NodeIO().registerExtensions([EXTMeshoptCompression]).registerDependencies({'meshopt.encoder':MeshoptEncoder,'meshopt.decoder':MeshoptDecoder});
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const source=fs.readFileSync(path.join(root,'MapaMarteN.glb')),originalHash=sha(source);
const doc=await io.readBinary(source),r=doc.getRoot();
const identity=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];
const nodes=r.listNodes().filter(n=>n.getMesh());
for(const n of nodes)if(JSON.stringify(n.getWorldMatrix())!==JSON.stringify(identity))throw Error('Nonidentity transform requires explicit handling');
const prims=nodes.map(n=>{const ps=n.getMesh().listPrimitives();if(ps.length!==1||ps[0].getMode()!==4)throw Error('Unexpected primitive');return ps[0]});
function snapshot(ps){return ps.map(p=>({attributes:Object.fromEntries(p.listSemantics().map(s=>[s,p.getAttribute(s).getArray().slice()])),indices:p.getIndices().getArray().slice()}))}
function compare(ps,before){if(ps.length!==before.length)throw Error('count');ps.forEach((p,i)=>{for(const [s,a] of Object.entries(before[i].attributes)){const b=p.getAttribute(s).getArray();if(a.length!==b.length||a.some((v,k)=>v!==b[k]))throw Error('Attribute changed '+s)}const a=before[i].indices,b=p.getIndices().getArray();if(a.length!==b.length)throw Error('indices');for(let k=0;k<a.length;k+=3){let valid=false;for(let shift=0;shift<3;shift++)if([0,1,2].every(t=>a[k+t]===b[k+(t+shift)%3]))valid=true;if(!valid)throw Error('Triangle changed');}})}
const before=snapshot(prims);
// Materials must match in every rendering property. Names are identifiers only.
const matJSON=(await io.writeJSON(doc)).json.materials.map(({name,...v})=>JSON.stringify(v));
if(new Set(matJSON).size!==1)throw Error('Materials differ');
const material=prims[0].getMaterial();for(const p of prims)p.setMaterial(material);
const removed=r.listNodes().filter(n=>!n.getMesh()).map(n=>n.getName());
const animationAccessors=new Set(r.listAnimations().flatMap(a=>a.listSamplers().flatMap(s=>[s.getInput(),s.getOutput()])));
for(const a of [...r.listAnimations()])a.dispose();
for(const a of animationAccessors){if(prims.some(p=>p.listAttributes().includes(a)||p.getIndices()===a))throw Error('Shared animation accessor');a.dispose()}
for(const n of [...r.listNodes()])if(!n.getMesh()){if(n.listChildren().length)throw Error('Auxiliary has children');n.dispose()}
await doc.transform(prune());
const baseline='terrain-lod0.glb';await io.write(path.join(out,baseline),doc);
compare((await io.read(path.join(out,baseline))).getRoot().listMeshes().map(m=>m.listPrimitives()[0]),before);
const records=[];
async function publish(d,file,expected){
 d.createExtension(EXTMeshoptCompression).setRequired(true).setEncoderOptions({method:EXTMeshoptCompression.EncoderMethod.QUANTIZE});
 await io.write(path.join(out,file),d);
 const decoded=await io.read(path.join(out,file));compare(decoded.getRoot().listMeshes().map(m=>m.listPrimitives()[0]),expected);
 const bytes=fs.readFileSync(path.join(out,file));const gltf=await new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
 const box=new Box3().setFromObject(gltf.scene);const validation=await validator.validateBytes(bytes,{uri:file,maxIssues:30});
 if(validation.issues.numErrors)throw Error(JSON.stringify(validation.issues));
 const decodedBytes=await new NodeIO().writeBinary(decoded);const decodedValidation=await validator.validateBytes(decodedBytes,{maxIssues:30});if(decodedValidation.issues.numErrors)throw Error('decoded invalid');
 const ps=decoded.getRoot().listMeshes().flatMap(m=>m.listPrimitives());
 const item={file,lod:0,bytes:bytes.length,sha256:sha(bytes),bounds:[box.min.toArray(),box.max.toArray()],position:[0,0,0],transform:identity,resolution_model_units:250,resolution_scientific:null,triangles:ps.reduce((s,p)=>s+p.getIndices().getCount()/3,0),meshes:decoded.getRoot().listMeshes().length,materials:decoded.getRoot().listMaterials().length,primitives:ps.length,draw_calls_single_pass_estimate:ps.length,compression:'EXT_meshopt_compression; no quantization transform',max_position_error:0,color_normal_index_equivalence:true,threejs_node_load:true,validation:validation.issues,decoded_validation:decodedValidation.issues};records.push(item);return item;
}
await publish(doc,'terrain-lod0-meshopt.glb',before);
// Independent chunk files keep the original global coordinates and material definition.
for(let i=0;i<prims.length;i++){
 const d=new Document(),buf=d.createBuffer(),p=d.createPrimitive();
 for(const s of prims[i].listSemantics()){const a=prims[i].getAttribute(s);p.setAttribute(s,d.createAccessor().setType(a.getType()).setNormalized(a.getNormalized()).setArray(a.getArray().slice()).setBuffer(buf))}
 p.setIndices(d.createAccessor().setType('SCALAR').setArray(prims[i].getIndices().getArray().slice()).setBuffer(buf));
 p.setMaterial(d.createMaterial().setBaseColorFactor(material.getBaseColorFactor()).setMetallicFactor(material.getMetallicFactor()).setRoughnessFactor(material.getRoughnessFactor()));
 d.createScene().addChild(d.createNode(nodes[i].getName()).setMesh(d.createMesh().addPrimitive(p)));
 await publish(d,`chunks/chunk-${String(i).padStart(2,'0')}.glb`,[before[i]]);
}
// Explicit concatenation: no simplification, reordering of vertices or rescaling.
const joined=new Document(),buf=joined.createBuffer(),jp=joined.createPrimitive();
for(const s of prims[0].listSemantics()){
 const a=prims[0].getAttribute(s),arrays=before.map(v=>v.attributes[s]),total=arrays.reduce((n,a)=>n+a.length,0),merged=new arrays[0].constructor(total);let offset=0;for(const a of arrays){merged.set(a,offset);offset+=a.length}
 jp.setAttribute(s,joined.createAccessor().setType(a.getType()).setNormalized(a.getNormalized()).setArray(merged).setBuffer(buf));
}
const ix=new Uint32Array(before.reduce((n,b)=>n+b.indices.length,0));let offset=0,vertex=0;for(const b of before){for(const v of b.indices)ix[offset++]=v+vertex;vertex+=b.attributes.POSITION.length/3}
jp.setIndices(joined.createAccessor().setType('SCALAR').setArray(ix).setBuffer(buf));jp.setMaterial(joined.createMaterial().setBaseColorFactor(material.getBaseColorFactor()).setMetallicFactor(material.getMetallicFactor()).setRoughnessFactor(material.getRoughnessFactor()));joined.createScene().addChild(joined.createNode('Terrain').setMesh(joined.createMesh('Terrain').addPrimitive(jp)));
await publish(joined,'terrain-joined-meshopt.glb',snapshot([jp]));
// Decode final compressed delivery for Blender, whose importer need not support Meshopt.
const decoded=await io.read(path.join(out,'terrain-joined-meshopt.glb'));
await new NodeIO().write(path.join(out,'terrain-joined-decoded.glb'),decoded);
if(sha(fs.readFileSync(path.join(root,'MapaMarteN.glb')))!==originalHash)throw Error('Original modified');
fs.writeFileSync(path.join(out,'manifest.json'),JSON.stringify({source:'../MapaMarteN.glb',source_sha256:originalHash,removed,original_to_optimized:identity,optimized_to_original:identity,georeference_verified:false,lods:[0],assets:records},null,2));
console.log(JSON.stringify(records.filter(x=>!x.file.startsWith('chunks')),null,2));
