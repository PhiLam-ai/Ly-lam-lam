#!/usr/bin/env python3
"""V387 Blender-side skinning audit helpers.

Import from the Blender candidate builder before export. This module audits source
mesh weights and rig links; it does not export or modify production assets.
"""
from __future__ import annotations


def audit_mesh_skinning(obj, rig, tolerance=0.02):
    """Return a JSON-serializable report for one Blender mesh and the intended rig."""
    bone_names = set(rig.data.bones.keys()) if rig and rig.type == "ARMATURE" else set()
    group_names = {group.index: group.name for group in obj.vertex_groups}
    valid_group_indices = {index for index, name in group_names.items() if name in bone_names}
    invalid_positive_groups = set()
    weighted = 0
    zero_weight = 0
    non_normalized = 0
    min_sum = None
    max_sum = None
    for vertex in obj.data.vertices:
        total = 0.0
        for assignment in vertex.groups:
            name = group_names.get(assignment.group)
            if assignment.weight <= 0.0:
                continue
            if assignment.group in valid_group_indices:
                total += assignment.weight
            else:
                invalid_positive_groups.add(name or f"group-index-{assignment.group}")
        if total <= 1e-8:
            zero_weight += 1
        else:
            weighted += 1
            min_sum = total if min_sum is None else min(min_sum, total)
            max_sum = total if max_sum is None else max(max_sum, total)
            if abs(total - 1.0) > tolerance:
                non_normalized += 1
    modifiers = [
        modifier for modifier in obj.modifiers
        if modifier.type == "ARMATURE" and modifier.object == rig
    ]
    is_mesh = obj.type == "MESH"
    vertex_count = len(obj.data.vertices) if is_mesh else 0
    return {
        "object": obj.name,
        "vertex_count": vertex_count,
        "bone_count": len(bone_names),
        "intended_rig": rig.name if rig else None,
        "armature_modifier_count_for_intended_rig": len(modifiers),
        "has_intended_armature_modifier": bool(modifiers),
        "valid_bone_group_count": len(valid_group_indices),
        "weighted_vertex_count": weighted,
        "zero_weight_vertex_count": zero_weight,
        "non_normalized_weighted_vertex_count": non_normalized,
        "weight_sum_min": min_sum,
        "weight_sum_max": max_sum,
        "positive_weights_on_nonbone_groups": sorted(invalid_positive_groups),
        "passes_strict_deformable_mesh_gate": bool(
            is_mesh and rig and rig.type == "ARMATURE" and modifiers
            and vertex_count > 0 and zero_weight == 0 and non_normalized == 0
            and not invalid_positive_groups
        ),
        "note": "Strict gate is for deformable body meshes; rigid accessories need an explicit documented exception.",
    }


def audit_character_skinning(mesh_objects, rig, strict_body_tokens=("human", "body", "basemesh", "skin")):
    """Audit mesh collection and flag body-like meshes that cannot be safely exported skinned."""
    reports = [audit_mesh_skinning(obj, rig) for obj in mesh_objects if obj.type == "MESH"]
    body_reports = [
        report for report in reports
        if any(token in report["object"].lower() for token in strict_body_tokens)
    ]
    failures = [
        report["object"] for report in body_reports
        if not report["passes_strict_deformable_mesh_gate"]
    ]
    return {
        "rig_name": rig.name if rig else None,
        "rig_bone_count": len(rig.data.bones) if rig and rig.type == "ARMATURE" else 0,
        "mesh_count": len(reports),
        "body_mesh_count": len(body_reports),
        "body_meshes_failing_strict_gate": failures,
        "passes_strict_body_gate": bool(body_reports) and not failures,
        "meshes": reports,
    }
