import fs from 'node:fs';
import path from 'node:path';
import validator from 'gltf-validator';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {Box3} from 'three';
const dir=path.resolve('../output');const manifest=JSON.parse(fs.readFileSync(path.join(dir,'manifest.json')));let reports=[];
for(const item of manifest){
 const b=fs.readFileSync(path.join(dir,item.file));const report=await validator.validateBytes(new Uint8Array(b),{uri:item.file});
 const model=await new GLTFLoader().parseAsync(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),'');const box=new Box3().setFromObject(model.scene);
 if(report.issues.numErrors)throw Error(item.file+JSON.stringify(report.issues));
 reports.push({file:item.file,issues:report.issues,bounds:[box.min.toArray(),box.max.toArray()],threeLoaded:true});
}
fs.writeFileSync(path.join(dir,'validation-glb.json'),JSON.stringify(reports,null,2));console.log('Validated and loaded in Three.js:',reports.length);
