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
import os
import struct
import sys
import tempfile
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


def select_baked_visual_meshes(scene):
    """Select V386's final baked visual meshes, excluding hidden editable source meshes."""
    meshes = [
        obj for obj in scene.objects
        if obj.type == "MESH" and obj.name.startswith("V386_Baked_")
    ]
    if not meshes:
        raise RuntimeError("No V386_Baked_ visual meshes found in the source scene")
    return sorted(meshes, key=lambda obj: obj.name)


def has_positive_bone_weights(mesh_obj, rig):
    bone_names = set(rig.data.bones.keys())
    bone_group_indices = {group.index for group in mesh_obj.vertex_groups if group.name in bone_names}
    if not bone_group_indices:
        return False
    return any(
        assignment.group in bone_group_indices and assignment.weight > 0.0
        for vertex in mesh_obj.data.vertices for assignment in vertex.groups
    )


def rigid_bone_for_baked_mesh(mesh_name, rig):
    """Documented rigid attachment policy for V386's static wardrobe/face accessories."""
    name = mesh_name.lower()
    if "faceframe" in name or "forelock" in name or "temple" in name:
        candidate = "head"
    elif "necklace" in name or "pendant" in name:
        candidate = "neck_01"
    elif "anklecover_left" in name:
        candidate = "foot_l"
    elif "anklecover_right" in name:
        candidate = "foot_r"
    elif "armholebinding" in name:
        candidate = "spine_03"
    elif any(token in name for token in ("beltstrap", "buckle", "waistgappatch", "cargopocket")):
        candidate = "pelvis"
    else:
        candidate = "spine_03"
    if rig.data.bones.get(candidate) is None:
        raise RuntimeError(f"Rigid mesh {mesh_name!r} maps to missing attachment bone {candidate!r}")
    return candidate


def create_temporary_export_copies(scene, rig, source_meshes, normalize_weights, visual_source="rigged"):
    """Create isolated export copies; source scene objects/data are never edited."""
    temp_objects = []
    export_rig = rig.copy()
    export_rig.data = rig.data.copy()
    export_rig.name = f"{rig.name}.V387_EXPORT_TEMP"
    scene.collection.objects.link(export_rig)
    temp_objects.append(export_rig)

    export_meshes = []
    deformable_meshes = []
    mesh_policies = []
    bone_names = set(export_rig.data.bones.keys())

    for source in source_meshes:
        duplicate = source.copy()
        duplicate.data = source.data.copy()
        duplicate.name = f"{source.name}.V387_EXPORT_TEMP"
        scene.collection.objects.link(duplicate)
        temp_objects.append(duplicate)
        source_world = source.matrix_world.copy()

        if visual_source == "baked-v386":
            has_weights = has_positive_bone_weights(duplicate, export_rig)
            # Baked V386 geometry is already in world-space at identity. Add a new
            # armature modifier only to meshes carrying real bone weights.
            duplicate.parent = None
            duplicate.parent_type = "OBJECT"
            duplicate.matrix_world = source_world
            if has_weights:
                modifier = duplicate.modifiers.new(name="V387_Armature", type="ARMATURE")
                modifier.object = export_rig
                duplicate.parent = export_rig
                duplicate.parent_type = "OBJECT"
                duplicate.matrix_parent_inverse = export_rig.matrix_world.inverted()
                duplicate.matrix_world = source_world
                if normalize_weights:
                    normalize_bone_weights(duplicate, export_rig)
                deformable_meshes.append(duplicate)
                mesh_policies.append({
                    "source_object": source.name,
                    "export_object": duplicate.name,
                    "policy": "skinned_deformable_mesh",
                    "attachment_bone": None,
                    "armature_modifier": modifier.name,
                })
            else:
                bone = rigid_bone_for_baked_mesh(source.name, export_rig)
                duplicate.parent = export_rig
                duplicate.parent_type = "BONE"
                duplicate.parent_bone = bone
                duplicate.matrix_parent_inverse.identity()
                duplicate.matrix_world = source_world
                mesh_policies.append({
                    "source_object": source.name,
                    "export_object": duplicate.name,
                    "policy": "rigid_bone_attachment",
                    "attachment_bone": bone,
                    "armature_modifier": None,
                })
        else:
            duplicate.parent = export_rig
            duplicate.parent_type = "OBJECT"
            duplicate.matrix_parent_inverse = export_rig.matrix_world.inverted()
            duplicate.matrix_world = source_world
            for modifier in duplicate.modifiers:
                if modifier.type == "ARMATURE" and modifier.object == rig:
                    modifier.object = export_rig
            deformable_meshes.append(duplicate)
            if normalize_weights:
                normalize_bone_weights(duplicate, export_rig)
            mesh_policies.append({
                "source_object": source.name,
                "export_object": duplicate.name,
                "policy": "existing_rigged_mesh",
                "attachment_bone": None,
                "armature_modifier": next((
                    modifier.name for modifier in duplicate.modifiers
                    if modifier.type == "ARMATURE" and modifier.object == export_rig
                ), None),
            })
        export_meshes.append(duplicate)

    if not deformable_meshes:
        raise RuntimeError("No deformable meshes with positive real-bone weights found for export")
    return export_rig, export_meshes, deformable_meshes, temp_objects, mesh_policies


def extract_embedded_image_from_glb(glb_path, preferred_name):
    """Return embedded PNG/JPEG bytes for a named image in an existing GLB."""
    data = Path(glb_path).read_bytes()
    if len(data) < 20:
        raise RuntimeError(f"Texture source GLB is too small: {glb_path}")
    magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or declared_length != len(data):
        raise RuntimeError(f"Texture source GLB header is invalid: {glb_path}")
    offset = 12
    gltf = None
    binary = None
    while offset + 8 <= len(data):
        length, chunk_type = struct.unpack_from("<I4s", data, offset)
        offset += 8
        payload = data[offset:offset + length]
        if len(payload) != length:
            raise RuntimeError("Texture source GLB contains a truncated chunk")
        offset += length
        if chunk_type == b"JSON":
            gltf = json.loads(payload.decode("utf-8").rstrip(" \\t\\r\\n\\0"))
        elif chunk_type == b"BIN\\0":
            binary = payload
    if gltf is None or binary is None:
        raise RuntimeError("Texture source GLB must contain JSON and BIN chunks")
    images = gltf.get("images", [])
    matches = [image for image in images if preferred_name.lower() in image.get("name", "").lower()]
    if not matches:
        raise RuntimeError(f"Could not find embedded image {preferred_name!r} in {glb_path}")
    image = matches[0]
    view_index = image.get("bufferView")
    if not isinstance(view_index, int) or not 0 <= view_index < len(gltf.get("bufferViews", [])):
        raise RuntimeError(f"Embedded image {image.get('name')} has no valid bufferView")
    view = gltf["bufferViews"][view_index]
    start = int(view.get("byteOffset", 0))
    length = int(view.get("byteLength", 0))
    payload = binary[start:start + length]
    if len(payload) != length or length == 0:
        raise RuntimeError(f"Embedded image {image.get('name')} payload is empty or truncated")
    mime = image.get("mimeType", "image/png")
    extension = ".jpg" if mime == "image/jpeg" else ".png"
    return payload, mime, image.get("name", preferred_name), extension


def restore_baked_skin_material(export_meshes, texture_source_glb):
    """Restore the embedded V386 skin diffuse image on a copied material only."""
    source_glb = Path(texture_source_glb).expanduser().resolve()
    if not source_glb.exists():
        raise RuntimeError(f"Skin texture source GLB does not exist: {source_glb}")
    payload, mime, image_name, extension = extract_embedded_image_from_glb(
        source_glb, "young_lightskinned_female_diffuse3"
    )
    handle = tempfile.NamedTemporaryFile(prefix="v387-skin-", suffix=extension, delete=False)
    temp_path = Path(handle.name)
    try:
        handle.write(payload)
        handle.close()
        image = bpy.data.images.load(str(temp_path), check_existing=False)
        image.name = "V387_RestoredSkinDiffuse"
        image.colorspace_settings.name = "sRGB"

        body = next((obj for obj in export_meshes if obj.name == "V386_Baked_Human.V387_EXPORT_TEMP"), None)
        if body is None:
            bpy.data.images.remove(image)
            raise RuntimeError("Cannot restore skin texture: baked base human mesh is missing")

        material = bpy.data.materials.new("V387_GltfCompatibleSkin_Restored")
        material.use_nodes = True
        tree = material.node_tree
        tree.nodes.clear()
        output = tree.nodes.new("ShaderNodeOutputMaterial")
        output.location = (420, 40)
        principled = tree.nodes.new("ShaderNodeBsdfPrincipled")
        principled.location = (120, 40)
        principled.inputs["Roughness"].default_value = 0.48
        if "Metallic" in principled.inputs:
            principled.inputs["Metallic"].default_value = 0.0
        if "Specular IOR Level" in principled.inputs:
            principled.inputs["Specular IOR Level"].default_value = 0.28
        if "Subsurface Weight" in principled.inputs:
            principled.inputs["Subsurface Weight"].default_value = 0.025
        uv_node = tree.nodes.new("ShaderNodeUVMap")
        uv_node.uv_map = "UVMap"
        uv_node.location = (-600, 40)
        texture = tree.nodes.new("ShaderNodeTexImage")
        texture.image = image
        texture.interpolation = "Linear"
        texture.extension = "REPEAT"
        texture.location = (-340, 40)
        texture.label = "V386 skin diffuse restored from embedded GLB"
        tree.links.new(uv_node.outputs["UV"], texture.inputs["Vector"])
        tree.links.new(texture.outputs["Color"], principled.inputs["Base Color"])
        tree.links.new(principled.outputs["BSDF"], output.inputs["Surface"])
        material.diffuse_color = (0.76, 0.48, 0.36, 1.0)

        body.data.materials.clear()
        body.data.materials.append(material)
        return {
            "status": "SKIN_TEXTURE_RESTORED_ON_EXPORT_COPY",
            "source_glb": str(source_glb),
            "source_image_name": image_name,
            "mime_type": mime,
            "bytes": len(payload),
            "uv_map": "UVMap",
            "material_name": material.name,
            "temporary_image": image,
            "temporary_material": material,
            "temporary_file": str(temp_path),
        }
    except Exception:
        try:
            handle.close()
        except Exception:
            pass
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise


def cleanup_temporary_skin_material(report):
    if not report:
        return
    material = report.get("temporary_material")
    image = report.get("temporary_image")
    if material is not None and material.users == 0:
        bpy.data.materials.remove(material)
    if image is not None and image.users == 0:
        bpy.data.images.remove(image)
    temp_file = report.get("temporary_file")
    if temp_file:
        try:
            Path(temp_file).unlink(missing_ok=True)
        except Exception:
            pass


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


def rename_glb_animation(output_path, old_name, new_name):
    """Rename one glTF animation in a GLB JSON chunk without changing source Blender data."""
    if not old_name or old_name == new_name:
        return {"renamed": False, "old_name": old_name, "new_name": new_name, "reason": "no temporary action rename needed"}
    data = output_path.read_bytes()
    if len(data) < 20:
        raise RuntimeError("Cannot rename animation: exported GLB is too small")
    magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or declared_length != len(data):
        raise RuntimeError("Cannot rename animation: invalid GLB header")
    chunks = []
    offset = 12
    json_index = None
    while offset + 8 <= len(data):
        length, chunk_type = struct.unpack_from("<I4s", data, offset)
        offset += 8
        chunk = data[offset:offset + length]
        if len(chunk) != length:
            raise RuntimeError("Cannot rename animation: truncated GLB chunk")
        offset += length
        if chunk_type == b"JSON":
            gltf = json.loads(chunk.decode("utf-8").rstrip(" \\t\\r\\n\\0"))
            json_index = len(chunks)
            chunks.append([chunk_type, gltf])
        else:
            chunks.append([chunk_type, chunk])
    if json_index is None:
        raise RuntimeError("Cannot rename animation: GLB JSON chunk missing")
    gltf = chunks[json_index][1]
    matches = [animation for animation in gltf.get("animations", []) if animation.get("name") == old_name]
    if not matches:
        return {"renamed": False, "old_name": old_name, "new_name": new_name,
                "reason": "matching animation name not found", "available_names": [a.get("name", "") for a in gltf.get("animations", [])]}
    matches[0]["name"] = new_name
    chunks[json_index][1] = gltf

    encoded_chunks = []
    for chunk_type, chunk in chunks:
        if chunk_type == b"JSON":
            payload = json.dumps(chunk, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            payload += b" " * ((-len(payload)) % 4)
        else:
            payload = chunk
        encoded_chunks.append(struct.pack("<I4s", len(payload), chunk_type) + payload)
    body = b"".join(encoded_chunks)
    output_path.write_bytes(struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body)
    return {"renamed": True, "old_name": old_name, "new_name": new_name,
            "animation_count": len(gltf.get("animations", [])),
            "animation_names": [animation.get("name", "") for animation in gltf.get("animations", [])]}


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
    parser.add_argument("--visual-source", choices=("rigged", "baked-v386"), default="rigged",
                        help="Export original rigged meshes or V386's final baked visual meshes with experimental skin restoration")
    parser.add_argument("--texture-source-glb", type=Path,
                        help="GLB containing embedded V386 skin texture; defaults to the source .blend sibling GLB")
    parser.add_argument("--allow-incomplete-morphs", action="store_true",
                        help="Do not require all 12 Lam facial morph names in the exported GLB")
    return parser.parse_args(argv)


def main():
    args = parse_args()
    scene = bpy.context.scene
    rig, linked_meshes = choose_rig(scene, args.rig_name)
    source_audit = audit_character_skinning(linked_meshes, rig)

    if args.visual_source == "baked-v386":
        source_meshes = select_baked_visual_meshes(scene)
    else:
        source_meshes = linked_meshes

    source_failures = [
        mesh["object"] for mesh in source_audit["meshes"]
        if not mesh["has_intended_armature_modifier"]
        or mesh["vertex_count"] == 0
        or mesh["zero_weight_vertex_count"] > 0
        or (mesh["non_normalized_weighted_vertex_count"] > 0
            and not args.normalize_bone_weights_on_export_copy)
    ]
    if args.visual_source == "rigged" and source_failures:
        raise RuntimeError("Source skinning audit failed; refusing export: " + json.dumps({
            "failed_meshes": source_failures,
            "normalization_requested": args.normalize_bone_weights_on_export_copy,
            "audit": source_audit,
        }, ensure_ascii=False))

    output = Path(args.output).expanduser().resolve()
    if output.exists() and not args.overwrite:
        raise RuntimeError(f"Output already exists; choose a new path or pass --overwrite: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    export_rig, export_meshes, deformable_meshes, temp_objects, mesh_policies = create_temporary_export_copies(
        scene, rig, source_meshes, args.normalize_bone_weights_on_export_copy, args.visual_source
    )
    temporary_action_report = rename_temporary_rig_action(export_rig, args.animation_name)
    skin_texture_report = None
    if args.visual_source == "baked-v386":
        texture_source_glb = args.texture_source_glb or Path(bpy.data.filepath).with_suffix(".glb")
        skin_texture_report = restore_baked_skin_material(export_meshes, texture_source_glb)
    try:
        export_audit = audit_character_skinning(deformable_meshes, export_rig)
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

        expected_body_name = (
            "V386_Baked_Human.V387_EXPORT_TEMP"
            if args.visual_source == "baked-v386"
            else "Human.V387_EXPORT_TEMP"
        )
        body_copy = next((obj for obj in deformable_meshes if obj.name == expected_body_name), None)
        if body_copy is None:
            raise RuntimeError(f"Cannot run pose deformation probe: expected body mesh copy {expected_body_name!r} is missing")
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
        cleanup_temporary_skin_material(skin_texture_report)

    glb_animation_rename_report = rename_glb_animation(
        output,
        temporary_action_report.get("export_action"),
        args.animation_name,
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
        "visual_source": args.visual_source,
        "rig_name": rig.name,
        "rig_bone_count": len(rig.data.bones),
        "source_mesh_count": len(source_meshes),
        "source_rigged_mesh_count": len(linked_meshes),
        "deformable_mesh_count": len(deformable_meshes),
        "rigid_accessory_count": len(export_meshes) - len(deformable_meshes),
        "mesh_export_policies": mesh_policies,
        "skin_texture_restoration": {
            key: value for key, value in (skin_texture_report or {}).items()
            if key not in ("temporary_image", "temporary_material", "temporary_file")
        },
        "source_skinning_audit": source_audit,
        "export_copy_skinning_audit": export_audit,
        "pose_deformation_probe": pose_deformation_report,
        "temporary_action_rename": temporary_action_report,
        "glb_animation_rename": glb_animation_rename_report,
        "gltf_animation_names": [animation.get("name", "") for animation in gltf.get("animations", [])],
        "bone_weights_normalized_on_temporary_copies": args.normalize_bone_weights_on_export_copy,
        "gltf_skin_count": len(gltf.get("skins", [])),
        "gltf_skinned_node_count": sum(1 for node in gltf.get("nodes", []) if "skin" in node and "mesh" in node),
        "gltf_animation_count": len(gltf.get("animations", [])),
        "gltf_mesh_count": len(gltf.get("meshes", [])),
        "gltf_morph_names": sorted({
            name for mesh in gltf.get("meshes", [])
            for name in mesh.get("extras", {}).get("targetNames", [])
        }),
        "note": "Structural and Blender pose-deformation gates only. Browser runtime and visual quality review remain required.",
    }
    report_path = output.with_suffix(".skinning-report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("V387_SKINNED_EXPORT_REPORT=" + str(report_path))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
