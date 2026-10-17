#!/usr/bin/env python3
"""Experimental V387 rig-preserving GLB exporter.

Run inside Blender after a scene builder has created the source character:
  blender --background scene.blend --python tools/export_skinned_glb_v387.py -- \
    --rig-name "Armature" --output "/tmp/lam-v387-skinned.glb"

This deliberately exports only meshes linked to the requested armature through an
Armature modifier. It does not bake evaluated geometry, change the production GLB,
or silently fall back to unskinned export. Rigid accessories need a separately
documented inclusion policy.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy

TOOLS_DIR = str(Path(__file__).resolve().parent)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from audit_blender_skinning_v387 import audit_character_skinning
from validate_gltf_skinning_v387 import read_glb, validate


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--rig-name", required=True, help="Exact Blender armature object name")
    parser.add_argument("--output", required=True, help="Destination GLB path")
    parser.add_argument("--allow-incomplete-morphs", action="store_true",
                        help="Do not require all 12 Lam facial morph names in the exported GLB")
    return parser.parse_args(argv)


def main():
    args = parse_args()
    rig = bpy.data.objects.get(args.rig_name)
    if rig is None or rig.type != "ARMATURE":
        raise RuntimeError(f"Requested rig {args.rig_name!r} is missing or is not an ARMATURE")

    linked_meshes = [
        obj for obj in bpy.context.scene.objects
        if obj.type == "MESH" and any(
            modifier.type == "ARMATURE" and modifier.object == rig
            for modifier in obj.modifiers
        )
    ]
    if not linked_meshes:
        raise RuntimeError(f"No scene meshes have an Armature modifier targeting {rig.name!r}")

    audit = audit_character_skinning(linked_meshes, rig)
    failing = [
        mesh["object"] for mesh in audit["meshes"]
        if not mesh["has_intended_armature_modifier"]
        or mesh["vertex_count"] == 0
        or mesh["zero_weight_vertex_count"] > 0
        or mesh["non_normalized_weighted_vertex_count"] > 0
        or mesh["positive_weights_on_nonbone_groups"]
    ]
    if failing:
        raise RuntimeError("Strict source skinning audit failed; refusing export: " + json.dumps({
            "failed_meshes": failing,
            "audit": audit,
        }, ensure_ascii=False))

    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in linked_meshes:
        obj.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig

    bpy.ops.export_scene.gltf(
        filepath=str(output),
        export_format="GLB",
        use_selection=True,
        export_animations=True,
        export_skins=True,
        export_morph=True,
        export_morph_normal=False,
        export_apply=False,
        export_cameras=False,
        export_lights=False,
    )

    gltf = read_glb(output)
    errors = validate(gltf)
    if args.allow_incomplete_morphs:
        errors = [error for error in errors if "Missing expected facial morph names" not in error]
    if errors:
        raise RuntimeError("Exported GLB failed structural skinning validation: " + json.dumps(errors))
    report = {
        "status": "STRUCTURAL_SKINNING_GATE_PASSED",
        "output": str(output),
        "bytes": output.stat().st_size,
        "rig_name": rig.name,
        "rig_bone_count": len(rig.data.bones),
        "source_mesh_count": len(linked_meshes),
        "source_skinning_audit": audit,
        "gltf_skin_count": len(gltf.get("skins", [])),
        "gltf_skinned_node_count": sum(1 for node in gltf.get("nodes", []) if "skin" in node and "mesh" in node),
        "gltf_animation_count": len(gltf.get("animations", [])),
        "gltf_mesh_count": len(gltf.get("meshes", [])),
        "gltf_morph_names": sorted({
            name for mesh in gltf.get("meshes", [])
            for name in mesh.get("extras", {}).get("targetNames", [])
        }),
        "note": "Structural gate only. Pose-deformation renders, browser runtime tests, visual quality review, and accessory integration remain required.",
    }
    report_path = output.with_suffix(".skinning-report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("V387_SKINNED_EXPORT_REPORT=" + str(report_path))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
