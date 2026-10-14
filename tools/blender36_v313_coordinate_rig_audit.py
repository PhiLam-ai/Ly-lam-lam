import bpy
import hashlib
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
    out_dir = os.path.abspath("artifacts/v313-coordinate-audit")
    for i, arg in enumerate(args[:-1]):
        if arg == "--input": source = os.path.abspath(args[i + 1])
        elif arg == "--output-dir": out_dir = os.path.abspath(args[i + 1])
    os.makedirs(out_dir, exist_ok=True)
    if not os.path.isfile(source):
        raise FileNotFoundError(source)
    digest = hashlib.sha256(open(source, "rb").read()).hexdigest()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=source)
    objects = list(bpy.context.scene.objects)
    armatures = [o for o in objects if o.type == "ARMATURE"]
    report_meshes = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        mins = [min(p[i] for p in points) for i in range(3)] if points else [None]*3
        maxs = [max(p[i] for p in points) for i in range(3)] if points else [None]*3
        shape_keys = obj.data.shape_keys.key_blocks if obj.data.shape_keys else []
        finite = all(math.isfinite(float(v)) for vert in obj.data.vertices for v in vert.co)
        armature_modifiers = []
        for mod in obj.modifiers:
            if mod.type == "ARMATURE":
                armature_modifiers.append({
                    "name": mod.name,
                    "object": mod.object.name if mod.object else None,
                    "use_vertex_groups": mod.use_vertex_groups,
                    "use_bone_envelopes": mod.use_bone_envelopes
                })
        groups = [g.name for g in obj.vertex_groups]
        report_meshes.append({
            "name": obj.name,
            "parent": obj.parent.name if obj.parent else None,
            "parent_type": obj.parent_type,
            "parent_bone": obj.parent_bone,
            "matrix_world": [list(row) for row in obj.matrix_world],
            "bounds_world_min": mins,
            "bounds_world_max": maxs,
            "bounds_world_size": [maxs[i]-mins[i] for i in range(3)],
            "vertex_count": len(obj.data.vertices),
            "polygon_count": len(obj.data.polygons),
            "vertex_groups_count": len(groups),
            "vertex_groups": groups,
            "armature_modifiers": armature_modifiers,
            "shape_key_count": len(shape_keys),
            "shape_keys": [k.name for k in shape_keys],
            "finite_local_vertex_coordinates": finite,
            "dimensions": list(obj.dimensions),
            "location": list(obj.location),
            "rotation_euler": list(obj.rotation_euler),
            "scale": list(obj.scale)
        })
    armature_report = []
    for arm in armatures:
        armature_report.append({
            "name": arm.name,
            "parent": arm.parent.name if arm.parent else None,
            "location": list(arm.location),
            "rotation_euler": list(arm.rotation_euler),
            "scale": list(arm.scale),
            "bone_count": len(arm.data.bones),
            "bones": [{"name": b.name, "parent": b.parent.name if b.parent else None,
                       "head_local": list(b.head_local), "tail_local": list(b.tail_local)}
                      for b in arm.data.bones]
        })
    expected = ["smile","blink_left","blink_right","mouth_open","jaw_open","jaw_hinge",
                "brow_raise","cheek_raise","lip_press","lip_fv","lip_round","tongue_tip"]
    all_keys = sorted({name for mesh in report_meshes for name in mesh["shape_keys"]})
    report = {
        "status": "DIAGNOSTIC_ONLY",
        "source": os.path.basename(source),
        "source_sha256": digest,
        "mesh_count": len(report_meshes),
        "armature_count": len(armature_report),
        "armatures": armature_report,
        "meshes": report_meshes,
        "expected_morph_names": expected,
        "found_expected_morph_names": [name for name in expected if name in all_keys],
        "missing_expected_morph_names": [name for name in expected if name not in all_keys],
        "all_shape_key_names": all_keys,
        "all_vertex_coordinates_finite": all(m["finite_local_vertex_coordinates"] for m in report_meshes),
        "interpretation": "Diagnostic only. World bounds and local vertex coordinates do not prove bind-pose correctness. Do not auto-translate or rotate meshes from these bounds alone."
    }
    target = os.path.join(out_dir, "v313-coordinate-rig-audit.json")
    with open(target, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("V313_COORDINATE_RIG_AUDIT=" + json.dumps({
        "status": report["status"], "source_sha256": digest,
        "mesh_count": len(report_meshes), "armature_count": len(armature_report),
        "morphs_found": len(report["found_expected_morph_names"]),
        "morphs_missing": report["missing_expected_morph_names"],
        "all_vertex_coordinates_finite": report["all_vertex_coordinates_finite"],
        "report": target
    }, ensure_ascii=False))
    if not report_meshes:
        raise RuntimeError("No mesh objects imported from GLB")
    if not report["all_vertex_coordinates_finite"]:
        raise RuntimeError("Non-finite vertex coordinate detected")
    if len(report["found_expected_morph_names"]) != len(expected):
        raise RuntimeError("Expected morph names are missing; see diagnostic JSON")
    # The audit succeeds only as a structural gate; visual continuity remains a separate gate.
    print("V313_COORDINATE_RIG_AUDIT_GATE=PASS_STRUCTURAL_ONLY")

if __name__ == "__main__":
    main()
