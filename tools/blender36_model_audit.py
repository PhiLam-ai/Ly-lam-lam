import bpy
import hashlib
import json
import math
import os
import sys
import traceback
from mathutils import Vector

def args_after_dashdash():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

def parse_args():
    args = args_after_dashdash()
    result = {"input": "lam-default.glb", "output_dir": "artifacts/model-audit"}
    i = 0
    while i < len(args):
        if args[i] == "--input" and i + 1 < len(args):
            result["input"] = args[i + 1]; i += 2
        elif args[i] == "--output-dir" and i + 1 < len(args):
            result["output_dir"] = args[i + 1]; i += 2
        else:
            i += 1
    return result

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def bounds_for(objects):
    points = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            points.append(obj.matrix_world @ Vector(corner))
    if not points:
        return None
    mins = [min(p[i] for p in points) for i in range(3)]
    maxs = [max(p[i] for p in points) for i in range(3)]
    return {"min": mins, "max": maxs, "size": [maxs[i] - mins[i] for i in range(3)]}

def aim_camera(camera, target):
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()

def make_camera(name, location, target, ortho_scale):
    data = bpy.data.cameras.new(name)
    camera = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = location
    aim_camera(camera, target)
    data.type = "ORTHO"
    data.ortho_scale = ortho_scale
    data.lens = 50
    return camera

def render_view(scene, camera, path):
    scene.camera = camera
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

def main():
    cfg = parse_args()
    source = os.path.abspath(cfg["input"])
    out = os.path.abspath(cfg["output_dir"])
    os.makedirs(out, exist_ok=True)
    if not os.path.isfile(source):
        raise FileNotFoundError("Missing source GLB: " + source)
    original_sha = sha256(source)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=source)
    imported = list(bpy.context.scene.objects)
    meshes = [o for o in imported if o.type == "MESH"]
    if not meshes:
        raise RuntimeError("GLB imported but contains no mesh objects")
    bounds = bounds_for(meshes)
    if not bounds:
        raise RuntimeError("Could not calculate mesh bounds")
    size = bounds["size"]
    center = [(bounds["min"][i] + bounds["max"][i]) / 2.0 for i in range(3)]
    max_dim = max(size)
    if not math.isfinite(max_dim) or max_dim <= 0:
        raise RuntimeError("Invalid mesh bounds: " + repr(bounds))

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.display.shading.show_specular_highlight = True
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("LamAuditWorld")
    scene.world.color = (0.055, 0.055, 0.055)

    distance = max_dim * 2.8
    ortho = max(size[0], size[2], size[1]) * 1.28
    # glTF convention usually presents the character toward -Y in Blender after import.
    views = [
        ("front", (center[0], center[1] - distance, center[2])),
        ("side", (center[0] + distance, center[1], center[2])),
        ("three-quarter", (center[0] + distance * 0.72, center[1] - distance * 0.72, center[2])),
    ]
    cameras = []
    for label, loc in views:
        cam = make_camera("AuditCamera_" + label, loc, center, ortho)
        cameras.append(cam)
        render_view(scene, cam, os.path.join(out, "lam-default-" + label + ".png"))

    # Export a round-trip copy, never touching the repository source.
    bpy.ops.object.select_all(action="DESELECT")
    for obj in imported:
        if obj.type in {"MESH", "ARMATURE"}:
            obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    roundtrip = os.path.join(out, "lam-default-roundtrip.glb")
    bpy.ops.export_scene.gltf(filepath=roundtrip, export_format="GLB", use_selection=True)
    if not os.path.isfile(roundtrip) or os.path.getsize(roundtrip) < 1024:
        raise RuntimeError("Round-trip GLB export missing or unexpectedly small")

    # Per-part diagnostics: preserve each mesh's world-space bounds to identify detached body parts.
    mesh_parts = []
    for obj in sorted(meshes, key=lambda item: item.name.lower()):
        part_bounds = bounds_for([obj])
        mesh_parts.append({
            "name": obj.name,
            "vertices": len(obj.data.vertices),
            "polygons": len(obj.data.polygons),
            "bounds": part_bounds,
            "materials": sorted({m.name for m in obj.data.materials if m}),
            "has_shape_keys": bool(obj.data.shape_keys),
            "shape_keys": [key.name for key in obj.data.shape_keys.key_blocks if key.name != "Basis"] if obj.data.shape_keys else [],
        })
    with open(os.path.join(out, "mesh-part-diagnostics.json"), "w", encoding="utf-8") as f:
        json.dump(mesh_parts, f, ensure_ascii=False, indent=2)
    with open(os.path.join(out, "mesh-part-diagnostics.txt"), "w", encoding="utf-8") as f:
        f.write("MESH PART DIAGNOSTICS — world-space bounds per source mesh\\n")
        f.write(json.dumps(mesh_parts, ensure_ascii=False, indent=2) + "\\n")

    material_names = sorted({m.name for o in meshes for m in o.data.materials if m})
    morph_names = sorted({key.name for o in meshes if o.data.shape_keys for key in o.data.shape_keys.key_blocks if key.name != "Basis"})
    animation_names = sorted({a.name for a in bpy.data.actions})
    textures = [im.name for im in bpy.data.images if im.source == "FILE" or im.packed_file]
    report = {
        "status": "PASS",
        "purpose": "Real source GLB import, multi-angle preview renders, and round-trip export. PASS is technical only, not an artistic quality approval.",
        "blender_version": bpy.app.version_string,
        "source_file": os.path.basename(source),
        "source_bytes": os.path.getsize(source),
        "source_sha256_before": original_sha,
        "source_sha256_after": sha256(source),
        "source_unchanged": original_sha == sha256(source),
        "object_count": len(imported),
        "mesh_count": len(meshes),
        "vertex_count": sum(len(o.data.vertices) for o in meshes),
        "polygon_count": sum(len(o.data.polygons) for o in meshes),
        "bounds": bounds,
        "material_names": material_names,
        "texture_image_count": len(textures),
        "texture_images": textures,
        "morph_names": morph_names,
        "animation_action_names": animation_names,
        "render_files": [os.path.basename(os.path.join(out, "lam-default-" + label + ".png")) for label, _ in views],
        "roundtrip_glb": os.path.basename(roundtrip),
        "roundtrip_bytes": os.path.getsize(roundtrip),
        "roundtrip_sha256": sha256(roundtrip),
    }
    report_path = os.path.join(out, "blender36-model-audit.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(os.path.join(out, "blender36-model-audit.txt"), "w", encoding="utf-8") as f:
        f.write("BLENDER 3.6 REAL MODEL AUDIT\n")
        f.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("BLENDER36_MODEL_AUDIT=" + json.dumps(report, ensure_ascii=False))
    if not report["source_unchanged"] or len(meshes) == 0:
        raise RuntimeError("Model audit integrity check failed")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
