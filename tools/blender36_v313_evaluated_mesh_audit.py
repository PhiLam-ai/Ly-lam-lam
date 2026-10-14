import bpy
import hashlib
import json
import math
import os
import sys

EXPECTED_MORPHS = {
    "smile", "blink_left", "blink_right", "mouth_open", "jaw_open", "jaw_hinge",
    "brow_raise", "cheek_raise", "lip_press", "lip_fv", "lip_round", "tongue_tip"
}
CRITICAL_PAIRS = [
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
    ("pelvis", "waist"), ("waist", "abdomen"), ("abdomen", "torso"),
    ("torso", "neck"), ("neck", "head"),
]

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
        "min": [round(x, 6) for x in lo],
        "max": [round(x, 6) for x in hi],
        "size": [round(hi[i] - lo[i], 6) for i in range(3)],
        "center": [round((lo[i] + hi[i]) / 2, 6) for i in range(3)],
    }

def gap_between(a, b):
    if not a or not b:
        return None
    axis_gaps = []
    for i, axis in enumerate(("x", "y", "z")):
        gap = max(0.0, a["min"][i] - b["max"][i], b["min"][i] - a["max"][i])
        axis_gaps.append({"axis": axis, "gap": round(gap, 6)})
    distance = math.sqrt(sum(item["gap"] ** 2 for item in axis_gaps))
    return {
        "aabb_gap": round(distance, 6),
        "axis_gaps": axis_gaps,
        "interpretation": "AABB overlap/touch is only a screening result, not proof that surfaces are welded or visually continuous.",
    }

def main():
    args = args_after_dashdash()
    source = os.path.abspath("lam-default.glb")
    out_dir = os.path.abspath("artifacts/v313-evaluated-mesh-audit")
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
    scene.frame_set(0)
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()

    meshes = {}
    morph_names = set()
    rows = []
    for obj in [o for o in scene.objects if o.type == "MESH"]:
        raw_points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
        raw_bounds = bounds(raw_points)
        obj_eval = obj.evaluated_get(depsgraph)
        evaluated_mesh = obj_eval.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
        try:
            evaluated_points = [obj_eval.matrix_world @ vertex.co for vertex in evaluated_mesh.vertices]
            evaluated_bounds = bounds(evaluated_points)
        finally:
            obj_eval.to_mesh_clear()

        displacement = []
        if raw_points and len(raw_points) == len(evaluated_points):
            displacement = [(evaluated_points[i] - raw_points[i]).length for i in range(len(raw_points))]
        shape_keys = list(obj.data.shape_keys.key_blocks.keys()) if obj.data.shape_keys else []
        morph_names.update(name for name in shape_keys if name != "Basis")
        groups = {group.index: group.name for group in obj.vertex_groups}
        weight_sum = {}
        for vertex in obj.data.vertices:
            for membership in vertex.groups:
                name = groups.get(membership.group, "UNKNOWN")
                weight_sum[name] = weight_sum.get(name, 0.0) + float(membership.weight)
        dominant = sorted(weight_sum.items(), key=lambda pair: pair[1], reverse=True)[:3]
        row = {
            "mesh": obj.name,
            "parent": obj.parent.name if obj.parent else None,
            "vertex_count": len(obj.data.vertices),
            "raw_object_space_bounds": raw_bounds,
            "evaluated_world_space_bounds": evaluated_bounds,
            "evaluated_vertex_count": len(evaluated_points),
            "deformation_vs_raw": {
                "max_vertex_displacement": round(max(displacement), 6) if displacement else None,
                "mean_vertex_displacement": round(sum(displacement) / len(displacement), 6) if displacement else None,
            },
            "armature_modifiers": [
                {
                    "name": mod.name,
                    "target": mod.object.name if mod.object else None,
                    "enabled": bool(mod.show_viewport),
                    "use_vertex_groups": bool(mod.use_vertex_groups),
                }
                for mod in obj.modifiers if mod.type == "ARMATURE"
            ],
            "shape_keys": shape_keys,
            "dominant_weight_groups": [
                {"bone_group": name, "weight_sum": round(value, 6)} for name, value in dominant
            ],
        }
        rows.append(row)
        meshes[obj.name] = row

    pair_rows = []
    for a_name, b_name in CRITICAL_PAIRS:
        a, b = meshes.get(a_name), meshes.get(b_name)
        pair_rows.append({
            "a": a_name,
            "b": b_name,
            "status": "MEASURED" if a and b else "MISSING_MESH",
            "raw_bounds_gap": gap_between(
                a.get("raw_object_space_bounds") if a else None,
                b.get("raw_object_space_bounds") if b else None,
            ),
            "evaluated_bounds_gap": gap_between(
                a.get("evaluated_world_space_bounds") if a else None,
                b.get("evaluated_world_space_bounds") if b else None,
            ),
        })

    final_hash = sha256(source)
    report = {
        "status": "DIAGNOSTIC_ONLY_NO_MESH_OR_WEIGHT_CHANGES",
        "source_file": os.path.basename(source),
        "source_sha256_before": original_hash,
        "source_sha256_after": final_hash,
        "source_unchanged": original_hash == final_hash,
        "blender_version": bpy.app.version_string,
        "mesh_count": len(rows),
        "armature_count": sum(1 for o in scene.objects if o.type == "ARMATURE"),
        "expected_morphs": sorted(EXPECTED_MORPHS),
        "found_expected_morphs": sorted(EXPECTED_MORPHS & morph_names),
        "missing_expected_morphs": sorted(EXPECTED_MORPHS - morph_names),
        "method": (
            "Compare undeformed object-space bounds against evaluated world-space bounds after Blender's "
            "dependency graph applies current modifiers, including armature deformation. AABB gaps screen "
            "for disconnections but do not prove surface continuity. This script makes no model edits."
        ),
        "mesh_diagnostics": sorted(rows, key=lambda row: row["mesh"]),
        "critical_adjacency_pairs": pair_rows,
        "largest_evaluated_gaps": sorted(
            [r for r in pair_rows if r["evaluated_bounds_gap"]],
            key=lambda r: r["evaluated_bounds_gap"]["aabb_gap"],
            reverse=True,
        )[:15],
    }
    out = os.path.join(out_dir, "v313-evaluated-mesh-audit.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("V313_EVALUATED_MESH_AUDIT=DIAGNOSTIC_ONLY")
    print(json.dumps({
        "source_sha256": final_hash,
        "source_unchanged": report["source_unchanged"],
        "mesh_count": report["mesh_count"],
        "armature_count": report["armature_count"],
        "missing_morphs": report["missing_expected_morphs"],
        "largest_evaluated_gaps": report["largest_evaluated_gaps"][:8],
        "report": out,
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
