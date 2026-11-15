"""Isolated Blender process: equivalent cameras, lights and render settings."""
import bpy,math,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output-stage1'
results=[]
for label,file in [('original',ROOT/'MapaMarteN.glb'),('optimized',OUT/'terrain-joined-decoded.glb')]:
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.gltf(filepath=str(file))
 scene=bpy.context.scene
 # Auxiliary animation has no mesh and is excluded from the static comparison.
 for ob in list(scene.objects):
  if ob.type!='MESH':bpy.data.objects.remove(ob,do_unlink=True)
 world=bpy.data.worlds.new('ComparisonWorld');scene.world=world;world.use_nodes=True;bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.10,.13,.17,1);bg.inputs[1].default_value=.35
 bpy.ops.object.light_add(type='SUN');sun=bpy.context.object;sun.rotation_euler=(math.radians(55),math.radians(-20),math.radians(-30));sun.data.energy=2;sun.data.angle=.12
 bpy.ops.object.camera_add();cam=bpy.context.object;scene.camera=cam;cam.data.type='ORTHO';cam.data.clip_end=1000000;cam.data.clip_start=10
 scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True;scene.cycles.seed=0;scene.view_settings.view_transform='Standard';scene.render.resolution_x=1100;scene.render.resolution_y=850;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
 for view,position,target,scale in [('overview',(130000,-180000,145000),(0,0,6500),245000),('detail',(55000,-75000,42000),(15000,35000,6500),50000)]:
  cam.location=position;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale;scene.render.filepath=str(OUT/f'{label}-{view}.png');bpy.ops.render.render(write_still=True)
  results.append({'model':label,'view':view,'camera_blender':position,'target':target,'orthographic_scale':scale})
(OUT/'render-settings.json').write_text(json.dumps(results,indent=2),encoding='utf8')
