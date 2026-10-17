#!/usr/bin/env python3
"""Read-only inventory of a saved Blender scene for the V387 skinning gate.

Run inside Blender:
  blender --background candidate.blend --python tools/probe_blend_skinning_v387.py -- --output report.json
The script does not alter or save the input scene.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import bpy

TOOLS_DIR = str(Path(__file__).resolve().parent)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)
from audit_blender_skinning_v387 import audit_mesh_skinning


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    scene = bpy.context.scene
    scene_meshes = [obj for obj in scene.objects if obj.type == "MESH"]
    rigs = []
    for rig in (obj for obj in scene.objects if obj.type == "ARMATURE"):
        linked = [
            obj for obj in scene_meshes if any(
                modifier.type == "ARMATURE" and modifier.object == rig
                for modifier in obj.modifiers
            )
        ]
        rigs.append({
            "name": rig.name,
            "bone_count": len(rig.data.bones),
            "bones": [bone.name for bone in rig.data.bones],
            "linked_meshes": [audit_mesh_skinning(mesh, rig) for mesh in linked],
            "linked_mesh_count": len(linked),
        })

    all_meshes = []
    for obj in scene_meshes:
        shape_keys = obj.data.shape_keys
        armature_modifiers = [
            modifier.object.name if modifier.object else None
            for modifier in obj.modifiers if modifier.type == "ARMATURE"
        ]
        all_meshes.append({
            "object": obj.name,
            "vertex_count": len(obj.data.vertices),
            "polygon_count": len(obj.data.polygons),
            "armature_modifiers": armature_modifiers,
            "vertex_group_count": len(obj.vertex_groups),
            "shape_key_count": len(shape_keys.key_blocks) - 1 if shape_keys else 0,
            "shape_key_names": [key.name for key in list(shape_keys.key_blocks)[1:]] if shape_keys else [],
            "has_shape_keys": bool(shape_keys and len(shape_keys.key_blocks) > 1),
            "modifiers": [{"name": modifier.name, "type": modifier.type} for modifier in obj.modifiers],
        })

    all_morph_names = sorted({name for item in all_meshes for name in item["shape_key_names"]})
    report = {
        "status": "SCENE_SKINNING_PROBE_COMPLETE",
        "blender_version": bpy.app.version_string,
        "blend_file": bpy.data.filepath,
        "scene_name": scene.name,
        "scene_mesh_count": len(scene_meshes),
        "scene_armature_count": len(rigs),
        "armatures_with_linked_meshes": sum(1 for rig in rigs if rig["linked_mesh_count"]),
        "armatures": rigs,
        "scene_shape_key_mesh_count": sum(1 for item in all_meshes if item["has_shape_keys"]),
        "scene_shape_key_names": all_morph_names,
        "all_scene_meshes": all_meshes,
        "read_only": True,
        "note": "Inventory only. A passing report does not prove exported GLB deformation; the next gate is skinned export plus pose tests.",
    }
    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("V387_SCENE_SKINNING_PROBE=" + str(out))
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
