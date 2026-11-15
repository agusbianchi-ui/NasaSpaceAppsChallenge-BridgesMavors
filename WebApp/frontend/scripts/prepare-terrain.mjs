import { readFile, mkdir, copyFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'../../..');
const source=path.join(root,'output-stage1');
const target=path.resolve(import.meta.dirname,'../public/terrain');
const manifest=JSON.parse(await readFile(path.join(source,'manifest.json'),'utf8'));
await mkdir(path.join(target,'chunks'),{recursive:true});
for(const item of manifest.assets.filter(a=>a.file.startsWith('chunks/'))){
 const data=await readFile(path.join(source,item.file));
 if(createHash('sha256').update(data).digest('hex')!==item.sha256)throw Error(`Hash mismatch: ${item.file}`);
 await copyFile(path.join(source,item.file),path.join(target,item.file));
}
await copyFile(path.join(source,'manifest.json'),path.join(target,'manifest.json'));
console.log('Prepared 44 verified stage 1 terrain chunks.');

const visual=path.join(root,'output-stage3');
for(const file of ['terrain_metadata.json','visual_elevation.bin','valid_mask.bin']) await copyFile(path.join(visual,file),path.join(target,file));
await copyFile(path.join(root,'ruta_marte_preliminar.json'),path.join(target,'preliminary-route.json'));
