import bpy
import json
import os
import sys
import traceback
from mathutils import Vector

def args_after_dashdash():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

def main():
    args = args_after_dashdash()
    source = os.path.abspath("lam-default.glb")
    out = os.path.abspath("artifacts/geometry-gap-audit")
    for i, arg in enumerate(args[:-1]):
        if arg == "--input": source = os.path.abspath(args[i + 1])
        elif arg == "--output-dir": out = os.path.abspath(args[i + 1])
    os.makedirs(out, exist_ok=True)
    if not os.path.isfile(source):
        raise FileNotFoundError(source)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=source)
    meshes = {o.name.lower(): o for o in bpy.context.scene.objects if o.type == "MESH"}

    def bounds(obj):
        pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        return [[min(p[i] for p in pts), max(p[i] for p in pts)] for i in range(3)]

    parts = {name: bounds(obj) for name, obj in meshes.items()}
    # These are diagnostic pairs only. AABB separation is a screening signal,
    # not proof of a real surface gap; geometry can overlap without being welded.
    pairs = [
        ("torso", "abdomen"), ("abdomen", "waist"), ("waist", "pelvis"),
        ("pelvis", "left_hip"), ("pelvis", "right_hip"),
        ("left_hip", "left_thigh"), ("right_hip", "right_thigh"),
        ("left_thigh", "left_knee"), ("right_thigh", "right_knee"),
        ("left_knee", "left_shin"), ("right_knee", "right_shin"),
        ("left_shin", "left_calf"), ("right_shin", "right_calf"),
        ("left_calf", "left_ankle"), ("right_calf", "right_ankle"),
        ("left_ankle", "left_foot"), ("right_ankle", "right_foot"),
        ("torso", "left_shoulder"), ("torso", "right_shoulder"),
        ("left_shoulder", "left_upper_arm"), ("right_shoulder", "right_upper_arm"),
        ("left_upper_arm", "left_elbow"), ("right_upper_arm", "right_elbow"),
        ("left_elbow", "left_forearm"), ("right_elbow", "right_forearm"),
        ("left_forearm", "left_wrist"), ("right_forearm", "right_wrist"),
        ("left_wrist", "left_hand"), ("right_wrist", "right_hand"),
        ("neck", "head")
    ]
    checks = []
    for a, b in pairs:
        if a not in parts or b not in parts:
            checks.append({"a": a, "b": b, "status": "MISSING_MESH"})
            continue
        ba, bb = parts[a], parts[b]
        axis = []
        for i, label in enumerate(("x", "y", "z")):
            gap = max(0.0, bb[i][0] - ba[i][1], ba[i][0] - bb[i][1])
            axis.append({"axis": label, "a_max": ba[i][1], "b_min": bb[i][0],
                         "interval_separation": gap})
        # Minimum Euclidean separation between AABBs (0 means boxes overlap).
        distance = sum(item["interval_separation"] ** 2 for item in axis) ** 0.5
        checks.append({"a": a, "b": b, "status": "MEASURED",
                       "a_bounds_world": ba, "b_bounds_world": bb,
                       "aabb_distance": distance, "axis_separation": axis})
    report = {
        "status": "DIAGNOSTIC_ONLY",
        "source_file": os.path.basename(source),
        "object_count": len(list(bpy.context.scene.objects)),
        "mesh_count": len(meshes),
        "shape_key_meshes": {name: [k.name for k in obj.data.shape_keys.key_blocks]
                             for name, obj in meshes.items() if obj.data.shape_keys},
        "pairs": checks,
        "interpretation": "AABB distance is only a screening metric. Zero means bounding boxes touch/overlap, not that surfaces are connected. Nonzero may indicate separation but requires visual review."
    }
    path = os.path.join(out, "geometry-gap-audit.json")
    with open(path, "w", encoding="utf-8") as f: json.dump(report, f, ensure_ascii=False, indent=2)
    with open(os.path.join(out, "geometry-gap-audit.txt"), "w", encoding="utf-8") as f:
        f.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("GEOMETRY_GAP_AUDIT=" + json.dumps(report, ensure_ascii=False))
    assert len(meshes) > 0, "No mesh objects imported"
    assert all(item["status"] != "MISSING_MESH" for item in checks), "Required diagnostic mesh missing"

if __name__ == "__main__":
    try: main()
    except Exception:
        traceback.print_exc()
        raise
