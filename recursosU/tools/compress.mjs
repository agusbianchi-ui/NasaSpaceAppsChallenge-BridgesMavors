import fs from 'node:fs';import path from 'node:path';
import {NodeIO} from '@gltf-transform/core';import {EXTMeshoptCompression} from '@gltf-transform/extensions';import {MeshoptEncoder,MeshoptDecoder} from 'meshoptimizer';import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
await MeshoptEncoder.ready;await MeshoptDecoder.ready;
const io=new NodeIO().registerExtensions([EXTMeshoptCompression]).registerDependencies({'meshopt.encoder':MeshoptEncoder,'meshopt.decoder':MeshoptDecoder});
const dir=path.resolve('../output');fs.mkdirSync(path.join(dir,'meshopt'),{recursive:true});let records=[];
for(const item of JSON.parse(fs.readFileSync(path.join(dir,'manifest.json')))){
 const doc=await io.read(path.join(dir,item.file));const before=doc.getRoot().listMeshes()[0].listPrimitives()[0].getAttribute('POSITION').getArray().slice();
 doc.createExtension(EXTMeshoptCompression).setRequired(true).setEncoderOptions({method:EXTMeshoptCompression.EncoderMethod.QUANTIZE});
 const dest=path.join(dir,'meshopt',item.file);await io.write(dest,doc);const decoded=await io.read(dest);const after=decoded.getRoot().listMeshes()[0].listPrimitives()[0].getAttribute('POSITION').getArray();
 if(before.length!==after.length||before.some((v,i)=>v!==after[i]))throw Error('Position changed');
 const b=fs.readFileSync(dest);await new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).parseAsync(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),'');
 records.push({...item,file:'meshopt/'+item.file,bytes:b.length,position_error_m:0,threeLoaded:true});
}
fs.writeFileSync(path.join(dir,'manifest-meshopt.json'),JSON.stringify(records,null,2));console.log('Lossless compression verified',records.length);
