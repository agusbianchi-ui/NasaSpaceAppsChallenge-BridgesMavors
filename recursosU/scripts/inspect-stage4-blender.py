import bpy, json
from pathlib import Path

scene = bpy.context.scene
record = {
    "file": bpy.data.filepath,
    "scene": scene.name,
    "unit_system": scene.unit_settings.system,
    "scale_length": scene.unit_settings.scale_length,
    "objects": [
        {
            "name": o.name,
            "type": o.type,
            "matrix_world": [list(row) for row in o.matrix_world],
        }
        for o in scene.objects
    ],
}
Path(
    "D:/Nasa SpaceApps Challenge - Bridges Mavors/output-stage4/blender-inventory.json"
).write_text(json.dumps(record, indent=2))
