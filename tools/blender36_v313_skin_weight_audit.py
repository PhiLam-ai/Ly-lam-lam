import bpy
import json
import math
import os
import sys
from mathutils import Vector

def args_after_dashdash():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

def main():
    args = args_after_dashdash()
    source = os.path.abspath("lam-default.glb")
    out_dir = os.path.abspath("artifacts/v313-skin-weight-audit")
    for i, arg in enumerate(args[:-1]):
        if arg == "--input": source = os.path.abspath(args[i + 1])
        elif arg == "--output-dir": out_dir = os.path.abspath(args[i + 1])
    os.makedirs(out_dir, exist_ok=True)
    if not os.path.isfile(source):
        raise FileNotFoundError(source)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=source)
    arms = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
    arm = arms[0] if arms else None
    bone_names = {b.name for b in arm.data.bones} if arm else set()
    report = {"status": "DIAGNOSTIC_ONLY", "source": os.path.basename(source),
              "armature": arm.name if arm else None,
              "bone_count": len(bone_names), "meshes": []}
    for obj in [o for o in bpy.context.scene.objects if o.type == "MESH"]:
        group_names = {g.index: g.name for g in obj.vertex_groups}
        weighted_vertices = 0
        total_weighted_memberships = 0
        weight_by_group = {}
        min_w = [math.inf, math.inf, math.inf]
        max_w = [-math.inf, -math.inf, -math.inf]
        unweighted = 0
        for v in obj.data.vertices:
            memberships = [(group_names.get(g.group, "?"), float(g.weight))
                           for g in v.groups if g.weight > 1e-6]
            if not memberships:
                unweighted += 1
            else:
                weighted_vertices += 1
                total_weighted_memberships += len(memberships)
            for name, weight in memberships:
                weight_by_group[name] = weight_by_group.get(name, 0.0) + weight
                co = obj.matrix_world @ v.co
                for axis in range(3):
                    min_w[axis] = min(min_w[axis], float(co[axis]))
                    max_w[axis] = max(max_w[axis], float(co[axis]))
        weight_total = sum(weight_by_group.values())
        ranked = sorted(weight_by_group.items(), key=lambda kv: kv[1], reverse=True)
        mods = [{"name": m.name, "target": m.object.name if m.object else None,
                 "use_vertex_groups": m.use_vertex_groups,
                 "use_bone_envelopes": m.use_bone_envelopes}
                for m in obj.modifiers if m.type == "ARMATURE"]
        report["meshes"].append({
            "name": obj.name, "vertices": len(obj.data.vertices),
            "world_bounds_min": [float(x) for x in obj.bound_box[0]] if False else
                [float(min((obj.matrix_world @ Vector(c))[i] for c in obj.bound_box)) for i in range(3)],
            "world_bounds_max":
                [float(max((obj.matrix_world @ Vector(c))[i] for c in obj.bound_box)) for i in range(3)],
            "vertex_groups": len(obj.vertex_groups), "armature_modifiers": mods,
            "weighted_vertex_count": weighted_vertices, "unweighted_vertex_count": unweighted,
            "weighted_vertex_ratio": round(weighted_vertices / len(obj.data.vertices), 5) if obj.data.vertices else 0,
            "average_memberships_per_weighted_vertex": round(total_weighted_memberships / weighted_vertices, 3) if weighted_vertices else 0,
            "weight_totals_top12": [{"group": n, "total_weight": round(w, 4), "matches_bone": n in bone_names}
                                    for n, w in ranked[:12]],
            "group_names_missing_matching_bone": sorted(n for n, w in ranked if n not in bone_names and w > 1e-6),
            "has_shape_keys": bool(obj.data.shape_keys),
            "shape_keys": [k.name for k in obj.data.shape_keys.key_blocks] if obj.data.shape_keys else []
        })
    path = os.path.join(out_dir, "v313-skin-weight-audit.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("V313_SKIN_WEIGHT_AUDIT=DIAGNOSTIC_ONLY")
    print(json.dumps({"armature": report["armature"], "bone_count": report["bone_count"],
                      "mesh_count": len(report["meshes"]),
                      "unweighted_meshes": [m["name"] for m in report["meshes"] if m["unweighted_vertex_count"] > 0],
                      "meshes_without_armature_modifier": [m["name"] for m in report["meshes"] if not m["armature_modifiers"]],
                      "groups_missing_bones": {m["name"]: m["group_names_missing_matching_bone"] for m in report["meshes"] if m["group_names_missing_matching_bone"]}}, ensure_ascii=False))
if __name__ == "__main__":
    main()
