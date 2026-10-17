#!/usr/bin/env python3
"""Experimental V387 rig-preserving GLB exporter.

Run inside Blender after a scene builder has created the source character:
  blender --background scene.blend --python tools/export_skinned_glb_v387.py -- \
    --output "/tmp/lam-v387-skinned.glb"
If the scene has multiple eligible armatures, pass --rig-name with the exact object name.

The exporter creates temporary copies of the rig and linked meshes, exports those copies,
then removes them. Source scene objects, weights and data are never edited or saved.
Existing output files are protected unless --overwrite is explicitly supplied.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy

TOOLS_DIR = str(Path(__file__).resolve().parent)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from audit_blender_skinning_v387 import audit_character_skinning
from validate_gltf_skinning_v387 import read_glb, validate


def linked_meshes_for_rig(scene, rig):
    return [
        obj for obj in scene.objects
        if obj.type == "MESH" and any(
            modifier.type == "ARMATURE" and modifier.object == rig
            for modifier in obj.modifiers
        )
    ]


def choose_rig(scene, requested_name=None):
    """Choose an explicitly named rig or the sole eligible rig; never guess on ties."""
    if requested_name:
        rig = bpy.data.objects.get(requested_name)
        if rig is None or rig.type != "ARMATURE":
            raise RuntimeError(f"Requested rig {requested_name!r} is missing or is not an ARMATURE")
        linked = linked_meshes_for_rig(scene, rig)
        if not linked:
            raise RuntimeError(f"No scene meshes have an Armature modifier targeting {rig.name!r}")
        return rig, linked

    candidates = [
        (rig, linked_meshes_for_rig(scene, rig))
        for rig in scene.objects if rig.type == "ARMATURE"
    ]
    candidates = [(rig, linked) for rig, linked in candidates if linked]
    if not candidates:
        raise RuntimeError("No armature in the active scene has linked deformable mesh objects")
    if len(candidates) != 1:
        summary = [{"rig": rig.name, "linked_meshes": [obj.name for obj in linked]}
                   for rig, linked in candidates]
        raise RuntimeError(
            "Multiple eligible armatures found; pass --rig-name explicitly: "
            + json.dumps(summary, ensure_ascii=False)
        )
    return candidates[0]


def rename_temporary_rig_action(rig, requested_name="Lam_Idle_GentleSway"):
    """Rename a copied action for the preview runtime without touching the source action."""
    animation_data = rig.animation_data
    if not animation_data or not animation_data.action:
        return {"source_action": None, "export_action": None, "renamed": False}
    source_name = animation_data.action.name
    action_copy = animation_data.action.copy()
    action_copy.name = requested_name
    animation_data.action = action_copy
    return {"source_action": source_name, "export_action": action_copy.name, "renamed": True}


def normalize_bone_weights(mesh_obj, rig):
    """Normalize only weights whose vertex-group names match real bones on the rig."""
    bone_names = set(rig.data.bones.keys())
    bone_groups = [group for group in mesh_obj.vertex_groups if group.name in bone_names]
    if not bone_groups:
        raise RuntimeError(f"{mesh_obj.name}: no vertex groups match bones on {rig.name}")
    group_by_index = {group.index: group for group in bone_groups}
    for vertex in mesh_obj.data.vertices:
        assignments = [
            (group_by_index[assignment.group], assignment.weight)
            for assignment in vertex.groups if assignment.group in group_by_index
        ]
        total = sum(weight for _, weight in assignments if weight > 0.0)
        if total <= 1e-8:
            raise RuntimeError(
                f"{mesh_obj.name}: vertex {vertex.index} has no positive weight for a real rig bone"
            )
        for group, weight in assignments:
            if weight > 0.0:
                group.add([vertex.index], weight / total, "REPLACE")


def create_temporary_export_copies(scene, rig, linked_meshes, normalize_weights):
    """Duplicate rig and mesh datablocks for export-only edits; caller must clean up."""
    temp_objects = []
    export_rig = rig.copy()
    export_rig.data = rig.data.copy()
    export_rig.name = f"{rig.name}.V387_EXPORT_TEMP"
    scene.collection.objects.link(export_rig)
    temp_objects.append(export_rig)

    export_meshes = []
    for source in linked_meshes:
        duplicate = source.copy()
        duplicate.data = source.data.copy()
        duplicate.name = f"{source.name}.V387_EXPORT_TEMP"
        scene.collection.objects.link(duplicate)
        temp_objects.append(duplicate)
        # The glTF exporter reliably binds a skin when each deforming mesh is
        # parented to the same exported armature. Preserve world transform while
        # establishing that relationship on temporary copies only.
        source_world = source.matrix_world.copy()
        duplicate.parent = export_rig
        duplicate.matrix_parent_inverse = export_rig.matrix_world.inverted()
        duplicate.matrix_world = source_world
        for modifier in duplicate.modifiers:
            if modifier.type == "ARMATURE" and modifier.object == rig:
                modifier.object = export_rig
        if normalize_weights:
            normalize_bone_weights(duplicate, export_rig)
        export_meshes.append(duplicate)
    return export_rig, export_meshes, temp_objects


def cleanup_temporary_copies(objects):
    """Remove temporary objects and orphaned copied data without touching source data."""
    for obj in reversed(objects):
        data = obj.data if obj.type in {"MESH", "ARMATURE"} else None
        bpy.data.objects.remove(obj, do_unlink=True)
        if data is not None and data.users == 0:
            if data.__class__.__name__ == "Mesh":
                bpy.data.meshes.remove(data)
            elif data.__class__.__name__ == "Armature":
                bpy.data.armatures.remove(data)


def probe_pose_deformation(mesh_obj, rig, bone_names=("upperarm_l", "thigh_l", "head"), angle_degrees=30.0):
    """Measure evaluated mesh movement under deterministic single-bone rotations."""
    missing = [name for name in bone_names if rig.pose.bones.get(name) is None]
    if missing:
        raise RuntimeError(f"Pose deformation probe cannot find expected bones: {missing}")

    depsgraph = bpy.context.evaluated_depsgraph_get()
    bpy.context.view_layer.update()
    evaluated = mesh_obj.evaluated_get(depsgraph)
    base_mesh = evaluated.to_mesh()
    try:
        baseline = [vertex.co.copy() for vertex in base_mesh.vertices]
    finally:
        evaluated.to_mesh_clear()

    results = []
    angle = math.radians(angle_degrees)
    for bone_name in bone_names:
        pose_bone = rig.pose.bones[bone_name]
        original_mode = pose_bone.rotation_mode
        original_euler = pose_bone.rotation_euler.copy()
        best = {"bone": bone_name, "axis": None, "max_displacement": 0.0, "moved_vertex_count": 0}
        try:
            pose_bone.rotation_mode = "XYZ"
            neutral_euler = pose_bone.rotation_euler.copy()
            for axis in range(3):
                pose_bone.rotation_euler = neutral_euler
                pose_bone.rotation_euler[axis] = neutral_euler[axis] + angle
                bpy.context.view_layer.update()
                depsgraph = bpy.context.evaluated_depsgraph_get()
                evaluated = mesh_obj.evaluated_get(depsgraph)
                posed_mesh = evaluated.to_mesh()
                try:
                    if len(posed_mesh.vertices) != len(baseline):
                        raise RuntimeError(f"{mesh_obj.name}: evaluated vertex count changed during pose probe")
                    displacements = [
                        (vertex.co - baseline[index]).length
                        for index, vertex in enumerate(posed_mesh.vertices)
                    ]
                finally:
                    evaluated.to_mesh_clear()
                moved = sum(distance > 1e-5 for distance in displacements)
                maximum = max(displacements, default=0.0)
                if maximum > best["max_displacement"]:
                    best = {
                        "bone": bone_name,
                        "axis": "XYZ"[axis],
                        "max_displacement": maximum,
                        "moved_vertex_count": moved,
                    }
        finally:
            pose_bone.rotation_euler = original_euler
            pose_bone.rotation_mode = original_mode
            bpy.context.view_layer.update()
        results.append(best)

    failures = [item for item in results if item["max_displacement"] <= 1e-5 or item["moved_vertex_count"] == 0]
    if failures:
        raise RuntimeError("Source pose deformation probe failed: " + json.dumps({
            "mesh": mesh_obj.name, "results": results, "failures": failures,
        }, ensure_ascii=False))
    return {
        "status": "POSE_DEFORMATION_PROBE_PASSED",
        "mesh": mesh_obj.name,
        "angle_degrees": angle_degrees,
        "tests": results,
        "note": "Measured on Blender evaluated geometry before GLB export; browser playback and rendered pose review remain separate gates.",
    }


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--rig-name", help="Exact Blender armature object name; required only when scene has multiple eligible rigs")
    parser.add_argument("--output", required=True, help="Destination GLB path")
    parser.add_argument("--overwrite", action="store_true", help="Allow replacing an existing file at the exact output path")
    parser.add_argument("--normalize-bone-weights-on-export-copy", action="store_true",
                        help="Normalize only real-bone weights on temporary copies; source scene is not modified")
    parser.add_argument("--animation-name", default="Lam_Idle_GentleSway",
                        help="Name assigned to a copied active rig action for preview runtime compatibility")
    parser.add_argument("--allow-incomplete-morphs", action="store_true",
                        help="Do not require all 12 Lam facial morph names in the exported GLB")
    return parser.parse_args(argv)


def main():
    args = parse_args()
    scene = bpy.context.scene
    rig, linked_meshes = choose_rig(scene, args.rig_name)

    source_audit = audit_character_skinning(linked_meshes, rig)
    source_failures = [
        mesh["object"] for mesh in source_audit["meshes"]
        if not mesh["has_intended_armature_modifier"]
        or mesh["vertex_count"] == 0
        or mesh["zero_weight_vertex_count"] > 0
        or (mesh["non_normalized_weighted_vertex_count"] > 0
            and not args.normalize_bone_weights_on_export_copy)
    ]
    if source_failures:
        raise RuntimeError("Source skinning audit failed; refusing export: " + json.dumps({
            "failed_meshes": source_failures,
            "normalization_requested": args.normalize_bone_weights_on_export_copy,
            "audit": source_audit,
        }, ensure_ascii=False))

    output = Path(args.output).expanduser().resolve()
    if output.exists() and not args.overwrite:
        raise RuntimeError(f"Output already exists; choose a new path or pass --overwrite: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    export_rig, export_meshes, temp_objects = create_temporary_export_copies(
        scene, rig, linked_meshes, args.normalize_bone_weights_on_export_copy
    )
    temporary_action_report = rename_temporary_rig_action(export_rig, args.animation_name)
    try:
        export_audit = audit_character_skinning(export_meshes, export_rig)
        failing = [
            mesh["object"] for mesh in export_audit["meshes"]
            if not mesh["has_intended_armature_modifier"]
            or mesh["vertex_count"] == 0
            or mesh["zero_weight_vertex_count"] > 0
            or mesh["non_normalized_weighted_vertex_count"] > 0
        ]
        if failing:
            raise RuntimeError("Temporary export-copy audit failed: " + json.dumps({
                "failed_meshes": failing, "audit": export_audit,
            }, ensure_ascii=False))

        body_copy = next((obj for obj in export_meshes if obj.name == "Human.V387_EXPORT_TEMP"), None)
        if body_copy is None:
            raise RuntimeError("Cannot run pose deformation probe: expected Human body mesh copy is missing")
        pose_deformation_report = probe_pose_deformation(body_copy, export_rig)

        bpy.ops.object.select_all(action="DESELECT")
        for obj in export_meshes:
            obj.select_set(True)
        export_rig.select_set(True)
        bpy.context.view_layer.objects.active = export_rig

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
    finally:
        cleanup_temporary_copies(temp_objects)

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
        "source_skinning_audit": source_audit,
        "export_copy_skinning_audit": export_audit,
        "pose_deformation_probe": pose_deformation_report,
        "temporary_action_rename": temporary_action_report,
        "bone_weights_normalized_on_temporary_copies": args.normalize_bone_weights_on_export_copy,
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
