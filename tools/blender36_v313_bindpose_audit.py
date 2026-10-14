import bpy
import json
import math
import os
import sys
from mathutils import Vector

def args_after_dashdash():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

def point_segment_distance(point, a, b):
    ab = b - a
    denom = ab.length_squared
    if denom <= 1e-12:
        return (point - a).length
    t = max(0.0, min(1.0, (point - a).dot(ab) / denom))
    return (point - (a + t * ab)).length

def main():
    args = args_after_dashdash()
    source = os.path.abspath("lam-default.glb")
    out_dir = os.path.abspath("artifacts/v313-bindpose-audit")
    for i, arg in enumerate(args[:-1]):
        if arg == "--input": source = os.path.abspath(args[i + 1])
        elif arg == "--output-dir": out_dir = os.path.abspath(args[i + 1])
    os.makedirs(out_dir, exist_ok=True)
    if not os.path.isfile(source):
        raise FileNotFoundError(source)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=source)
    arms = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
    if not arms:
        raise RuntimeError("No armature found")
    arm = arms[0]
    bones = {}
    for bone in arm.data.bones:
        bones[bone.name] = {
            "head": arm.matrix_world @ bone.head_local,
            "tail": arm.matrix_world @ bone.tail_local,
        }
    group_stats = {}
    mesh_bounds = []
    for obj in [o for o in bpy.context.scene.objects if o.type == "MESH"]:
        corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        mesh_bounds.append({
            "mesh": obj.name,
            "min": [min(p[i] for p in corners) for i in range(3)],
            "max": [max(p[i] for p in corners) for i in range(3)],
        })
        groups = {g.index: g.name for g in obj.vertex_groups}
        accum = {}
        for vert in obj.data.vertices:
            p = obj.matrix_world @ vert.co
            for membership in vert.groups:
                name = groups.get(membership.group)
                w = float(membership.weight)
                if name not in bones or w <= 1e-6:
                    continue
                row = accum.setdefault(name, {"weight": 0.0, "sum": Vector((0,0,0)), "count": 0})
                row["weight"] += w
                row["sum"] += p * w
                row["count"] += 1
        for name, row in accum.items():
            centroid = row["sum"] / row["weight"]
            dist = point_segment_distance(centroid, bones[name]["head"], bones[name]["tail"])
            s = group_stats.setdefault(name, {"weight": 0.0, "weighted_centroid_sum": Vector((0,0,0)), "memberships": 0})
            s["weight"] += row["weight"]
            s["weighted_centroid_sum"] += centroid * row["weight"]
            s["memberships"] += row["count"]
    results = []
    for name, row in group_stats.items():
        centroid = row["weighted_centroid_sum"] / row["weight"]
        results.append({
            "bone": name,
            "weighted_vertex_memberships": row["memberships"],
            "weighted_centroid_world": [round(float(x), 5) for x in centroid],
            "distance_centroid_to_bone_segment": round(float(point_segment_distance(centroid, bones[name]["head"], bones[name]["tail"])), 5),
            "bone_head_world": [round(float(x), 5) for x in bones[name]["head"]],
            "bone_tail_world": [round(float(x), 5) for x in bones[name]["tail"]],
        })
    results.sort(key=lambda x: x["distance_centroid_to_bone_segment"], reverse=True)
    report = {
        "status": "DIAGNOSTIC_ONLY_NOT_AUTOCORRECTED",
        "source": os.path.basename(source),
        "armature": arm.name,
        "bone_count": len(bones),
        "mesh_count": len(mesh_bounds),
        "method": "For each bone group, compare the weighted centroid of its assigned vertices with the bone segment in imported world space. This is a heuristic only; multi-part meshes and morphs can legitimately shift centroids. No transforms or weights are changed.",
        "mesh_world_bounds": mesh_bounds,
        "bone_group_spatial_checks": results,
        "largest_centroid_segment_distances": results[:20],
    }
    path = os.path.join(out_dir, "v313-bindpose-audit.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("V313_BINDPOSE_AUDIT=DIAGNOSTIC_ONLY")
    print(json.dumps({"mesh_count": len(mesh_bounds), "bone_count": len(bones),
                      "groups_checked": len(results),
                      "largest_distances": results[:8]}, ensure_ascii=False))
if __name__ == "__main__":
    main()
