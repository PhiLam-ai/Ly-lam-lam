import bpy
import hashlib
import json
import os
import sys
from mathutils import Matrix, Vector

def args_after_dashdash():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def bounds(points):
    if not points:
        return None
    lo = [min(float(p[i]) for p in points) for i in range(3)]
    hi = [max(float(p[i]) for p in points) for i in range(3)]
    return {
        "min": [round(v, 6) for v in lo],
        "max": [round(v, 6) for v in hi],
        "size": [round(hi[i] - lo[i], 6) for i in range(3)],
        "center": [round((lo[i] + hi[i]) / 2, 6) for i in range(3)],
    }

def make_camera(scene, name, location, target, ortho_scale):
    data = bpy.data.cameras.new(name)
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    data.type = "ORTHO"
    data.ortho_scale = ortho_scale
    return obj

def render(scene, camera, path):
    scene.camera = camera
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

def main():
    args = args_after_dashdash()
    source = os.path.abspath("lam-default.glb")
    out_dir = os.path.abspath("artifacts/v313-unskinned-diagnostic")
    for i, arg in enumerate(args[:-1]):
        if arg == "--input":
            source = os.path.abspath(args[i + 1])
        elif arg == "--output-dir":
            out_dir = os.path.abspath(args[i + 1])
    os.makedirs(out_dir, exist_ok=True)
    if not os.path.isfile(source):
        raise FileNotFoundError(source)
    original_hash = sha256(source)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=source)
    scene = bpy.context.scene
    meshes = [obj for obj in scene.objects if obj.type == "MESH"]
    armatures = [obj for obj in scene.objects if obj.type == "ARMATURE"]
    morph_names = set()
    original_points = []
    for obj in meshes:
        if obj.data.shape_keys:
            morph_names.update(k.name for k in obj.data.shape_keys.key_blocks if k.name != "Basis")
        # Record imported static vertex positions before disabling skin deformation.
        original_points.extend([obj.matrix_world @ vertex.co for vertex in obj.data.vertices])

    # Detach mesh transforms in world space, then remove armature deformation only.
    # Mesh vertex coordinates and any shape keys remain intact; source GLB is read-only.
    for obj in meshes:
        world = obj.matrix_world.copy()
        for mod in list(obj.modifiers):
            if mod.type == "ARMATURE":
                obj.modifiers.remove(mod)
        obj.parent = None
        obj.matrix_world = world

    for rig in armatures:
        bpy.data.objects.remove(rig, do_unlink=True)

    bpy.context.view_layer.update()
    raw_points = [obj.matrix_world @ vertex.co for obj in meshes for vertex in obj.data.vertices]
    raw_bounds = bounds(raw_points)
    if not raw_bounds or raw_bounds["size"][2] <= 0:
        raise RuntimeError("Cannot calculate non-zero source geometry bounds.")

    scale_factor = 1.60 / raw_bounds["size"][2]
    center = raw_bounds["center"]
    offset = Vector((-center[0] * scale_factor, -center[1] * scale_factor, -raw_bounds["min"][2] * scale_factor))
    scale_matrix = Matrix.Diagonal((scale_factor, scale_factor, scale_factor, 1.0))
    translation = Matrix.Translation(offset)

    for obj in meshes:
        obj.matrix_world = translation @ scale_matrix @ obj.matrix_world

    bpy.context.view_layer.update()
    normalized_points = [obj.matrix_world @ vertex.co for obj in meshes for vertex in obj.data.vertices]
    normalized_bounds = bounds(normalized_points)

    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("V313UnskinnedAuditWorld")
    scene.world.color = (0.045, 0.045, 0.045)

    target = (0, 0, 0.80)
    # Source facial parts are offset toward +Y in the imported Blender scene.
    dist = 3.8
    camera_front = make_camera(scene, "UnskinnedFrontDiagnostic", (0, dist, 0.8), target, 2.0)
    render(scene, camera_front, os.path.join(out_dir, "unskinned-front.png"))
    camera_three_quarter = make_camera(scene, "UnskinnedThreeQuarterDiagnostic", (dist * 0.65, dist * 0.75, 0.8), target, 2.0)
    render(scene, camera_three_quarter, os.path.join(out_dir, "unskinned-three-quarter.png"))
    camera_side = make_camera(scene, "UnskinnedSideDiagnostic", (dist, 0, 0.8), target, 2.0)
    render(scene, camera_side, os.path.join(out_dir, "unskinned-side.png"))

    # Export a static-skinning diagnostic candidate, not a production avatar.
    # Shape keys stay on the mesh; skeleton/rig animation is intentionally removed.
    glb = os.path.join(out_dir, "lam-unskinned-normalized-diagnostic.glb")
    bpy.ops.object.select_all(action="DESELECT")
    for obj in meshes:
        obj.select_set(True)
    if meshes:
        bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", use_selection=True)

    final_hash = sha256(source)
    report = {
        "status": "DIAGNOSTIC_ONLY_NOT_APPROVED",
        "purpose": "Test whether the current avatar fragmentation is caused by armature skinning or by base mesh placement.",
        "source_file": os.path.basename(source),
        "source_sha256_before": original_hash,
        "source_sha256_after": final_hash,
        "source_unchanged": original_hash == final_hash,
        "blender_version": bpy.app.version_string,
        "mesh_count": len(meshes),
        "removed_armature_count": len(armatures),
        "found_morph_names": sorted(morph_names),
        "morph_count": len(morph_names),
        "bounds_before_skinning_disable": bounds(original_points),
        "bounds_after_skinning_disable_before_normalization": raw_bounds,
        "normalization_factor": round(scale_factor, 8),
        "bounds_after_normalization": normalized_bounds,
        "render_files": ["unskinned-front.png", "unskinned-three-quarter.png", "unskinned-side.png"],
        "candidate_glb": os.path.basename(glb),
        "candidate_bytes": os.path.getsize(glb),
        "warnings": [
            "Armature and skin deformation removed intentionally; this candidate cannot be promoted as the final animated avatar.",
            "All edits are in-memory diagnostics and do not modify the source GLB.",
            "Bounds are a geometric normalization check, not a claim that joints, surfaces, proportions, or appearance are correct."
        ]
    }
    with open(os.path.join(out_dir, "v313-unskinned-diagnostic.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("V313_UNSKINNED_DIAGNOSTIC=" + json.dumps(report, ensure_ascii=False))
    assert report["source_unchanged"] is True
    assert report["mesh_count"] == 85
    assert report["morph_count"] >= 12
    assert abs(normalized_bounds["size"][2] - 1.6) < 0.02
    assert os.path.getsize(glb) > 1024

if __name__ == "__main__":
    main()
