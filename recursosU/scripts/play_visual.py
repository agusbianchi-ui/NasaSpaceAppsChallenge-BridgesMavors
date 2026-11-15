import bpy,math
from mathutils import Vector
path=r'D:/Nasa SpaceApps Challenge - Bridges Mavors/output-visual/mars-visual-3x.blend'
with bpy.data.libraries.load(path,link=False) as (source,target):target.scenes=[source.scenes[0]]
scene=target.scenes[0];scene.name='Marte - HRSC 250m - Color orbital - Relieve 3x'
bpy.context.window.scene=scene
pivot=bpy.data.objects.new('Vista giratoria - no exportar',None);scene.collection.objects.link(pivot);pivot.location=(0,0,6500)
cam=scene.camera;cam.parent=pivot;cam.location-=pivot.location
scene.frame_start=1;scene.frame_end=360;scene.render.fps=24
pivot.rotation_euler.z=0;pivot.keyframe_insert(data_path='rotation_euler',frame=1)
pivot.rotation_euler.z=2*math.pi;pivot.keyframe_insert(data_path='rotation_euler',frame=361)
try:
 for curve in pivot.animation_data.action.fcurves:
  for point in curve.keyframe_points:point.interpolation='LINEAR'
except AttributeError:pass
scene.frame_set(1)
for area in bpy.context.screen.areas:
 if area.type=='VIEW_3D':
  space=area.spaces.active;space.clip_start=100;space.clip_end=1000000
  space.overlay.show_overlays=False;space.shading.type='MATERIAL'
  space.region_3d.view_perspective='CAMERA';space.region_3d.view_camera_zoom=0
# Save only this scene and its dependencies, leaving unrelated live scenes intact.
bpy.data.libraries.write(r'D:/Nasa SpaceApps Challenge - Bridges Mavors/output-visual/mars-visual-playback.blend',{scene})
if not bpy.context.screen.is_animation_playing:bpy.ops.screen.animation_play()
print('Playing:',scene.name,'frames',scene.frame_start,scene.frame_end)
