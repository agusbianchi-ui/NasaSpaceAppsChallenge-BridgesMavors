import bpy,json,math
from pathlib import Path
from mathutils import Vector
root=Path(r'D:/Nasa SpaceApps Challenge - Bridges Mavors');out=root/'output-visual'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for p in sorted(out.glob('ez_lod0_*.glb')):bpy.ops.import_scene.gltf(filepath=str(p))
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
world=scene.world;world.use_nodes=True;world.node_tree.nodes.get('Background').inputs[0].default_value=(.10,.13,.17,1);world.node_tree.nodes.get('Background').inputs[1].default_value=.35
bpy.ops.object.light_add(type='SUN',location=(0,0,10000));sun=bpy.context.object;sun.rotation_euler=(math.radians(55),math.radians(-20),math.radians(-30));sun.data.energy=2;sun.data.angle=.12
bpy.ops.object.camera_add(location=(130000,-180000,145000));cam=bpy.context.object;scene.camera=cam
cam.rotation_euler=(Vector((0,0,6500))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=245000;cam.data.clip_end=1000000
scene.view_settings.view_transform='Standard'
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=1400;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
bpy.ops.wm.save_as_mainfile(filepath=str(out/'mars-visual-3x.blend'))
scene.render.filepath=str(out/'preview-overview.png');bpy.ops.render.render(write_still=True)
cam.location=(55000,-75000,42000);target=Vector((15000,35000,6500));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=85000
scene.render.filepath=str(out/'preview-detail.png');bpy.ops.render.render(write_still=True)

