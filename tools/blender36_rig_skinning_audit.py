import bpy
import json
import os
import sys
import traceback

def args_after_dashdash():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

def parse_args():
    args = args_after_dashdash()
    cfg = {"input": "lam-default.glb", "output_dir": "artifacts/rig-skinning-audit"}
    i = 0
    while i < len(args):
        if args[i] == "--input" and i + 1 < len(args):
            cfg["input"] = args[i + 1]; i += 2
        elif args[i] == "--output-dir" and i + 1 < len(args):
            cfg["output_dir"] = args[i + 1]; i += 2
        else:
            i += 1
    return cfg

def main():
    cfg = parse_args()
    source = os.path.abspath(cfg["input"])
    out = os.path.abspath(cfg["output_dir"])
    os.makedirs(out, exist_ok=True)
    if not os.path.isfile(source):
        raise FileNotFoundError("Missing input GLB: " + source)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=source)
    objects = list(bpy.context.scene.objects)
    meshes = [o for o in objects if o.type == "MESH"]
    armatures = [o for o in objects if o.type == "ARMATURE"]
    armature_names = {o.name for o in armatures}
    mesh_reports = []
    for obj in meshes:
        armature_modifiers = [
            m for m in obj.modifiers
            if m.type == "ARMATURE" and m.object and m.object.name in armature_names
        ]
        weighted_vertices = 0
        total_weight_entries = 0
        for vertex in obj.data.vertices:
            weights = [g.weight for g in vertex.groups if g.weight > 0.001]
            if weights:
                weighted_vertices += 1
                total_weight_entries += len(weights)
        mesh_reports.append({
            "name": obj.name,
            "vertex_count": len(obj.data.vertices),
            "vertex_group_count": len(obj.vertex_groups),
            "armature_modifier_targets": [m.object.name for m in armature_modifiers],
            "weighted_vertex_count": weighted_vertices,
            "weighted_vertex_ratio": round(weighted_vertices / max(1, len(obj.data.vertices)), 6),
            "weight_entries_above_0_001": total_weight_entries,
            "shape_key_count": max(0, len(obj.data.shape_keys.key_blocks) - 1) if obj.data.shape_keys else 0,
            "shape_key_names": [k.name for k in obj.data.shape_keys.key_blocks if k.name != "Basis"] if obj.data.shape_keys else [],
        })
    weighted_meshes = [m for m in mesh_reports if m["weighted_vertex_count"] > 0 and m["armature_modifier_targets"]]
    bone_count = sum(len(a.data.bones) for a in armatures)
    action_names = sorted(a.name for a in bpy.data.actions)
    findings = []
    if not armatures:
        findings.append("NO_ARMATURE")
    if bone_count == 0:
        findings.append("NO_SKELETON_BONES")
    if not weighted_meshes:
        findings.append("NO_SKINNED_MESH_WITH_ARMATURE_MODIFIER_AND_WEIGHTS")
    status = "BLOCKED" if findings else "RIG_PRESENT_REQUIRES_POSE_VALIDATION"
    report = {
        "status": status,
        "purpose": "Structural diagnostic only. A present armature and weights do not prove good deformation; pose tests and visual review remain mandatory.",
        "input_file": os.path.basename(source),
        "object_count": len(objects),
        "mesh_count": len(meshes),
        "armature_count": len(armatures),
        "armatures": [{"name": a.name, "bone_count": len(a.data.bones), "bones": [b.name for b in a.data.bones]} for a in armatures],
        "total_bone_count": bone_count,
        "skinned_mesh_count": len(weighted_meshes),
        "mesh_reports": mesh_reports,
        "animation_action_names": action_names,
        "findings": findings,
        "approval": "NOT_APPROVED_BY_STRUCTURAL_AUDIT",
    }
    path = os.path.join(out, "rig-skinning-audit.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(os.path.join(out, "rig-skinning-audit.txt"), "w", encoding="utf-8") as f:
        f.write("RIG / SKINNING STRUCTURAL AUDIT\n")
        f.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("RIG_SKINNING_AUDIT=" + json.dumps(report, ensure_ascii=False))
    # This is an informative gate at first: preserve baseline CI while making missing rigging visible.
    # It intentionally does not claim that a blocked asset is acceptable.
if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
