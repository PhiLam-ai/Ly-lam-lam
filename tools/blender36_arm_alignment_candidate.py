import bpy
import hashlib
import json
import os
import sys
import traceback
from mathutils import Vector

def args_after_dashdash():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

def parse_args():
    args = args_after_dashdash()
    out = "artifacts/arm-alignment-candidate"
    for i, arg in enumerate(args[:-1]):
        if arg == "--output-dir":
            out = args[i + 1]
    return os.path.abspath(out)

def bounds(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return [[min(p[i] for p in pts), max(p[i] for p in pts)] for i in range(3)]

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def aim(cam, target):
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()

def main():
    out = parse_args()
    os.makedirs(out, exist_ok=True)
    source = os.path.abspath("lam-default.glb")
    if not os.path.isfile(source):
        raise FileNotFoundError(source)
    source_hash = sha256(source)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=source)
    meshes = {o.name.lower(): o for o in bpy.context.scene.objects if o.type == "MESH"}

    # Candidate-only validation: never silently export a no-op correction.
    # Discover names conservatively; require at least one recognized bilateral pair.
    pairs = [
        "upper_arm", "shoulder", "shoulder_cap", "elbow", "elbow_cap",
        "forearm", "wrist", "hand", "palm", "thumb",
        "index", "middle", "ring", "little"
    ]
    changes = []
    moved_count = 0
    for part in pairs:
        left_name, right_name = "left_" + part, "right_" + part
        left, right = meshes.get(left_name), meshes.get(right_name)
        if left is None or right is None:
            changes.append({"part": part, "status": "SKIP_MISSING_PAIR"})
            continue
        rb = bounds(right)
        lb = bounds(left)
        right_center = [(v[0] + v[1]) / 2 for v in rb]
        left_center = [(v[0] + v[1]) / 2 for v in lb]
        target = [-right_center[0], right_center[1], right_center[2]]
        delta = [target[i] - left_center[i] for i in range(3)]
        delta_length = sum(v * v for v in delta) ** 0.5
        if delta_length < 1e-5:
            changes.append({
                "part": part, "left_object": left.name, "right_reference": right.name,
                "translation_delta": delta, "status": "ALREADY_ALIGNED"
            })
            continue
        left.matrix_world.translation += Vector(delta)
        moved_count += 1
        changes.append({
            "part": part, "left_object": left.name, "right_reference": right.name,
            "left_center_before": left_center, "target_mirrored_center": target,
            "translation_delta": delta, "status": "MOVED"
        })

    found_pairs = sum(1 for item in changes if item["status"] in {"MOVED", "ALREADY_ALIGNED"})
    if found_pairs == 0:
        available = sorted(meshes.keys())
        raise RuntimeError(
            "No recognized bilateral arm/hand mesh pairs found; refusing to export a no-op candidate. "
            "Available mesh names: " + ", ".join(available)
        )
    if moved_count == 0:
        raise RuntimeError(
            "Recognized bilateral pairs exist, but no mesh required a measurable correction; "
            "refusing to label this as a corrected candidate."
        )

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("LamCandidateWorld")
    scene.world.color = (0.055, 0.055, 0.055)
    all_meshes = list(meshes.values())
    all_bounds = [bounds(o) for o in all_meshes]
    mins = [min(b[i][0] for b in all_bounds) for i in range(3)]
    maxs = [max(b[i][1] for b in all_bounds) for i in range(3)]
    center = [(mins[i] + maxs[i]) / 2 for i in range(3)]
    size = [maxs[i] - mins[i] for i in range(3)]
    distance = max(size) * 2.8
    camdata = bpy.data.cameras.new("CandidateFrontCamera")
    cam = bpy.data.objects.new("CandidateFrontCamera", camdata)
    scene.collection.objects.link(cam)
    cam.location = (center[0], center[1] - distance, center[2])
    aim(cam, center)
    camdata.type = "ORTHO"
    camdata.ortho_scale = max(size) * 1.28
    scene.camera = cam
    scene.render.filepath = os.path.join(out, "arm-alignment-candidate-front.png")
    bpy.ops.render.render(write_still=True)

    glb = os.path.join(out, "lam-arm-alignment-candidate.glb")
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.context.scene.objects:
        if obj.type in {"MESH", "ARMATURE"}:
            obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes.get("torso", all_meshes[0])
    bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", use_selection=True)
    report = {
        "status": "CANDIDATE_EXPORTED_NOT_APPROVED",
        "recognized_pair_count": found_pairs,
        "moved_pair_count": moved_count,
        "purpose": "Experimental mirrored-position correction of arm and hand components only; not a finished avatar.",
        "source_file": os.path.basename(source),
        "source_sha256_before": source_hash,
        "source_sha256_after": sha256(source),
        "source_unchanged": source_hash == sha256(source),
        "changes": changes,
        "candidate_glb": os.path.basename(glb),
        "candidate_bytes": os.path.getsize(glb),
        "render": "arm-alignment-candidate-front.png",
        "warning": "This translates separate meshes only. It does not weld geometry or create natural anatomy; visual review is mandatory."
    }
    with open(os.path.join(out, "arm-alignment-candidate-report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("ARM_ALIGNMENT_CANDIDATE=" + json.dumps(report, ensure_ascii=False))
    assert report["source_unchanged"], "Source GLB was modified unexpectedly"
    assert os.path.getsize(glb) > 1024, "Candidate GLB export failed"

if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
