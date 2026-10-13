import bpy
import json
import os
import sys
import traceback
from mathutils import Vector

def output_dir_from_args():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = os.getcwd()
    for i, arg in enumerate(args[:-1]):
        if arg == "--output-dir":
            out = args[i + 1]
    os.makedirs(out, exist_ok=True)
    return out

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)

def material(name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    return mat

def add_uv_sphere(name, location, scale, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=20, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    for face in obj.data.polygons:
        face.use_smooth = True
    return obj

def main():
    out = output_dir_from_args()
    clear_scene()

    skin = material("SmokeTest_Skin", (0.68, 0.42, 0.30))
    cloth = material("SmokeTest_Cloth", (0.08, 0.22, 0.42))
    hair = material("SmokeTest_Hair", (0.035, 0.025, 0.02))
    floor_mat = material("SmokeTest_Floor", (0.18, 0.19, 0.22))

    # This is a diagnostic placeholder only; it is NOT the production Lam avatar.
    add_uv_sphere("Test_Torso", (0, 0, 2.15), (0.48, 0.30, 0.72), cloth)
    add_uv_sphere("Test_Pelvis", (0, 0, 1.55), (0.45, 0.29, 0.32), cloth)
    add_uv_sphere("Test_Head", (0, 0, 3.10), (0.30, 0.28, 0.38), skin)
    add_uv_sphere("Test_Hair_Cap", (0, 0.035, 3.34), (0.32, 0.29, 0.25), hair)
    for side in (-1, 1):
        add_uv_sphere("Test_Leg", (side * 0.20, 0, 0.82), (0.18, 0.20, 0.62), skin)
        add_uv_sphere("Test_Foot", (side * 0.20, -0.10, 0.18), (0.18, 0.32, 0.12), cloth)
        add_uv_sphere("Test_Arm", (side * 0.53, 0, 2.22), (0.15, 0.17, 0.56), skin)

    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, 0.02))
    floor = bpy.context.object
    floor.name = "Test_Floor"
    floor.data.materials.append(floor_mat)

    bpy.ops.object.camera_add(location=(5.5, -9.0, 3.0))
    camera = bpy.context.object
    camera.name = "SmokeTest_Camera"
    direction = Vector((0, 0, 1.75)) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 4.2
    bpy.context.scene.camera = camera

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.render.resolution_x = 800
    scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = os.path.join(out, "blender36-smoke-test.png")
    scene.world.color = (0.06, 0.06, 0.06)

    bpy.ops.render.render(write_still=True)

    # Export only mesh objects; diagnostic camera/floor are not needed in the GLB.
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and obj.name != "Test_Floor":
            obj.select_set(True)
    bpy.context.view_layer.objects.active = next(
        (o for o in bpy.context.scene.objects if o.name == "Test_Torso"), None
    )
    glb_path = os.path.join(out, "blender36-smoke-test.glb")
    bpy.ops.export_scene.gltf(filepath=glb_path, export_format="GLB", use_selection=True)

    report = {
        "status": "PASS",
        "purpose": "Blender 3.6 CI smoke test only; not a production avatar quality test.",
        "blender_version": bpy.app.version_string,
        "scene_object_count": len(bpy.context.scene.objects),
        "mesh_count": sum(1 for o in bpy.context.scene.objects if o.type == "MESH"),
        "render_png": os.path.basename(scene.render.filepath),
        "glb": os.path.basename(glb_path),
        "render_exists": os.path.isfile(scene.render.filepath),
        "glb_exists": os.path.isfile(glb_path),
        "glb_bytes": os.path.getsize(glb_path) if os.path.isfile(glb_path) else 0,
    }
    report["status"] = "PASS" if report["render_exists"] and report["glb_exists"] and report["glb_bytes"] > 20_000 else "FAIL"
    with open(os.path.join(out, "blender36-smoke-report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("BLENDER36_SMOKE_REPORT=" + json.dumps(report, ensure_ascii=False))
    if report["status"] != "PASS":
        raise RuntimeError("Blender 3.6 smoke test failed; inspect report and logs.")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
