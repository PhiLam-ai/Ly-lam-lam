#!/usr/bin/env python3
"""V331: build a coherent human-topology Lam candidate with MPFB, real asset materials,
a game-engine rig, a light idle action and 12 composite facial morphs.

This is an experimental candidate. It never edits the production GLB.
"""
import argparse
import hashlib
import json
import math
import os
import shutil
import sys
import traceback
import zipfile
from pathlib import Path

import bpy
from mathutils import Vector

EXPECTED_MORPHS = [
    "smile", "blink_left", "blink_right", "mouth_open", "jaw_open", "jaw_hinge",
    "brow_raise", "cheek_raise", "lip_press", "lip_fv", "lip_round", "tongue_tip",
]

MORPH_SOURCES = {
    "smile": [("mouthSmileLeft", 0.72), ("mouthSmileRight", 0.72)],
    "blink_left": [("eyeBlinkLeft", 0.98)],
    "blink_right": [("eyeBlinkRight", 0.98)],
    "mouth_open": [
        ("jawOpen", 0.48), ("mouthLowerDownLeft", 0.32), ("mouthLowerDownRight", 0.32),
    ],
    "jaw_open": [("jawOpen", 0.90)],
    "jaw_hinge": [("jawForward", 0.52), ("jawOpen", 0.25)],
    "brow_raise": [
        ("browInnerUp", 0.72), ("browOuterUpLeft", 0.30), ("browOuterUpRight", 0.30),
    ],
    "cheek_raise": [("cheekSquintLeft", 0.62), ("cheekSquintRight", 0.62)],
    "lip_press": [("mouthPressLeft", 0.75), ("mouthPressRight", 0.75)],
    "lip_fv": [
        ("f_v_18", 0.80), ("mouthLowerDownLeft", 0.18), ("mouthLowerDownRight", 0.18),
    ],
    "lip_round": [("mouthFunnel", 0.72), ("mouthPucker", 0.28)],
    "tongue_tip": [("tongueOut", 0.80)],
}

ARKIT_NAMES = {
    "browDownLeft", "browDownRight", "browInnerUp", "browOuterUpLeft", "browOuterUpRight",
    "cheekPuff", "cheekSquintLeft", "cheekSquintRight", "eyeBlinkLeft", "eyeBlinkRight",
    "eyeLookDownLeft", "eyeLookDownRight", "eyeLookInLeft", "eyeLookInRight", "eyeLookOutLeft",
    "eyeLookOutRight", "eyeLookUpLeft", "eyeLookUpRight", "eyeSquintLeft", "eyeSquintRight",
    "eyeWideLeft", "eyeWideRight", "jawForward", "jawLeft", "jawOpen", "jawRight",
    "mouthClose", "mouthDimpleLeft", "mouthDimpleRight", "mouthFrownLeft", "mouthFrownRight",
    "mouthFunnel", "mouthLeft", "mouthLowerDownLeft", "mouthLowerDownRight", "mouthPressLeft",
    "mouthPressRight", "mouthPucker", "mouthRight", "mouthRollLower", "mouthRollUpper",
    "mouthShrugLower", "mouthShrugUpper", "mouthSmileLeft", "mouthSmileRight",
    "mouthStretchLeft", "mouthStretchRight", "mouthUpperUpLeft", "mouthUpperUpRight",
    "noseSneerLeft", "noseSneerRight", "tongueOut",
}
VISEME_NAMES = {
    "aa_02", "aa_ah_ax_01", "ao_03", "aw_09", "ay_11", "d_t_n_19", "er_05",
    "ey_eh_uh_04", "f_v_18", "h_12", "k_g_ng_20", "l_14", "ow_08", "oy_10",
    "p_b_m_21", "r_13", "sh_ch_jh_zh_16", "sil_00", "s_z_15", "th_dh_17",
    "w_uw_07", "y_iy_ih_ix_06",
}
SOURCE_NAMES = ARKIT_NAMES | VISEME_NAMES


def parse_args():
    raw = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--mpfb-src", required=True)
    parser.add_argument("--system-pack", required=True)
    parser.add_argument("--face-pack", required=True)
    parser.add_argument("--viseme-pack", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args(raw)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_install_pack(archive, asset_service, location_service):
    archive = str(Path(archive).resolve())
    if not os.path.isfile(archive):
        raise FileNotFoundError("Missing MakeHuman asset pack: " + archive)
    check = asset_service.check_asset_pack_zip(archive)
    if check not in (None, "STRUCTURE", "MACOS"):
        raise RuntimeError("MPFB rejected asset pack " + os.path.basename(archive) + ": " + str(check))
    target = location_service.get_user_data()
    os.makedirs(target, exist_ok=True)
    error = asset_service.fix_and_extract_asset_pack_zip(archive, target)
    if error:
        raise RuntimeError("MPFB failed to extract " + os.path.basename(archive) + ": " + str(error))
    asset_service.rescan_pack_metadata()
    asset_service.update_all_asset_lists()
    asset_service.rescan_pack_metadata()
    return {
        "file": os.path.basename(archive),
        "bytes": os.path.getsize(archive),
        "sha256": sha256(archive),
        "preflight": check or "OK",
        "target": target,
    }


def find_asset(asset_service, subdir, candidates):
    for candidate in candidates:
        path = asset_service.find_asset_absolute_path(candidate, asset_subdir=subdir)
        if path and os.path.isfile(path):
            return str(path)
    roots = asset_service.get_asset_roots(subdir)
    suffix = {"skins": ".mhmat"}.get(subdir, ".mhclo")
    files = []
    for root in roots:
        p = Path(root)
        if p.exists():
            files.extend(p.rglob("*" + suffix))
    lower = subdir.lower()
    if subdir == "skins":
        matches = [p for p in files if "young_asian_female" in str(p).lower()]
        if not matches:
            matches = [p for p in files if "young_caucasian_female" in str(p).lower()]
    elif subdir == "hair":
        matches = [p for p in files if "long" in p.name.lower()]
    elif subdir == "clothes":
        matches = [p for p in files if "female" in str(p).lower() and ("casual" in str(p).lower() or "suit" in str(p).lower())]
    elif subdir == "eyes":
        matches = [p for p in files if "high" in p.name.lower()] or [p for p in files if "low" in p.name.lower()]
    else:
        matches = []
    if matches:
        return str(sorted(matches, key=lambda p: (len(str(p)), str(p).lower()))[0])
    return None


def all_descendants(root):
    result = []
    seen = set()
    stack = [root]
    while stack:
        obj = stack.pop()
        if obj is None or obj.name in seen:
            continue
        seen.add(obj.name)
        result.append(obj)
        stack.extend(list(obj.children))
    return result


def world_bounds(objects):
    points = []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in objects:
        if obj.type != "MESH":
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            for vertex in mesh.vertices:
                points.append(evaluated.matrix_world @ vertex.co)
        finally:
            evaluated.to_mesh_clear()
    if not points:
        raise RuntimeError("No evaluated character mesh vertices to measure")
    lows = [min(v[i] for v in points) for i in range(3)]
    highs = [max(v[i] for v in points) for i in range(3)]
    return {
        "min": [round(float(v), 6) for v in lows],
        "max": [round(float(v), 6) for v in highs],
        "size": [round(float(highs[i] - lows[i]), 6) for i in range(3)],
    }


def source_key_name(obj, source_name):
    keys = getattr(getattr(obj.data, "shape_keys", None), "key_blocks", None)
    if not keys:
        return None
    names = [key.name for key in keys]
    candidates = [
        source_name,
        "!ex-" + source_name,
        "!msv-" + source_name,
        "viseme_" + source_name,
    ]
    for candidate in candidates:
        if candidate in names:
            return candidate
    # Different MPFB pack revisions can carry a prefix. Match a unique suffix only.
    matches = [name for name in names if name.lower().endswith(source_name.lower())]
    if len(matches) == 1:
        return matches[0]
    return None


def make_composite_morphs(objects):
    report = {}
    for obj in objects:
        if obj.type != "MESH":
            continue
        key_data = obj.data.shape_keys
        if key_data is None or not key_data.key_blocks:
            continue
        keys = key_data.key_blocks
        source_lookup = {}
        for sources in MORPH_SOURCES.values():
            for source_name, _weight in sources:
                if source_name not in source_lookup:
                    source_lookup[source_name] = source_key_name(obj, source_name)
        built = []
        for target_name, sources in MORPH_SOURCES.items():
            resolved = [(source_lookup.get(name), weight, name) for name, weight in sources if source_lookup.get(name)]
            if not resolved:
                continue
            # Every output key must be a delta from neutral. Clear all prior weights first.
            for block in keys:
                if block.name != "Basis":
                    block.value = 0.0
            for actual_name, weight, _source in resolved:
                keys[actual_name].value = float(weight)
            new_key = obj.shape_key_add(name=target_name, from_mix=True)
            new_key.value = 0.0
            for block in obj.data.shape_keys.key_blocks:
                if block.name != "Basis":
                    block.value = 0.0
            built.append(target_name)
        # Leave only the 12 runtime-facing morphs plus any unrelated non-face keys.
        removable = []
        for block in list(obj.data.shape_keys.key_blocks)[1:]:
            name = block.name
            if name in EXPECTED_MORPHS:
                continue
            if name in SOURCE_NAMES or name.startswith("!ex-") or name.startswith("!msv-"):
                removable.append(block)
        for block in removable:
            try:
                obj.shape_key_remove(block)
            except Exception:
                pass
        report[obj.name] = {
            "vertices": len(obj.data.vertices),
            "composite_morphs": [name for name in EXPECTED_MORPHS if obj.data.shape_keys and obj.data.shape_keys.key_blocks.get(name)],
            "source_keys_available": sorted(source for source, actual in source_lookup.items() if actual),
            "missing_sources": sorted(source for source, actual in source_lookup.items() if actual is None),
        }
    return report


def style_materials(basemesh, hair_objects, clothing_objects):
    # Preserve the source texture maps while nudging shader settings toward natural skin.
    skin_materials = []
    all_skin_materials = list(basemesh.data.materials)
    for material in all_skin_materials:
        if material is None:
            continue
        material.use_nodes = True
        changed = False
        for node in material.node_tree.nodes:
            if node.type != "BSDF_PRINCIPLED":
                continue
            inputs = node.inputs
            if "Roughness" in inputs:
                inputs["Roughness"].default_value = 0.42
            if "Metallic" in inputs:
                inputs["Metallic"].default_value = 0.0
            if "Subsurface Weight" in inputs:
                inputs["Subsurface Weight"].default_value = 0.055
            elif "Subsurface" in inputs:
                inputs["Subsurface"].default_value = 0.055
            if "Specular IOR Level" in inputs:
                inputs["Specular IOR Level"].default_value = 0.28
            changed = True
        if changed:
            material.diffuse_color = (0.76, 0.48, 0.36, 1.0)
            skin_materials.append(material.name)
    for obj in hair_objects:
        if obj.type != "MESH":
            continue
        for material in obj.data.materials:
            if not material:
                continue
            material.use_nodes = True
            for node in material.node_tree.nodes:
                if node.type == "BSDF_PRINCIPLED":
                    inputs = node.inputs
                    if "Roughness" in inputs:
                        inputs["Roughness"].default_value = 0.52
                    # A dark warm multiplier preserves map variation while giving Lam black hair.
                    if "Base Color" in inputs and not inputs["Base Color"].is_linked:
                        inputs["Base Color"].default_value = (0.105, 0.072, 0.052, 1.0)
            material.diffuse_color = (0.105, 0.072, 0.052, 1.0)
    for obj in clothing_objects:
        if obj.type != "MESH":
            continue
        for material in obj.data.materials:
            if not material:
                continue
            material.use_nodes = True
            for node in material.node_tree.nodes:
                if node.type == "BSDF_PRINCIPLED":
                    inputs = node.inputs
                    if "Roughness" in inputs:
                        inputs["Roughness"].default_value = 0.58
                    if "Metallic" in inputs:
                        inputs["Metallic"].default_value = 0.0
    # Smooth the existing human topology. No sphere/capsule substitute geometry is added.
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and obj.name != "V331_StudioFloor":
            for polygon in obj.data.polygons:
                polygon.use_smooth = True
    return skin_materials


def add_idle_animation(rig, scene):
    if not rig or rig.type != "ARMATURE":
        raise RuntimeError("MPFB did not create a skeletal armature")
    names = [bone.name for bone in rig.pose.bones]
    def find_bone(keys):
        for key in keys:
            for bone in rig.pose.bones:
                if bone.name.lower() == key:
                    return bone
        for key in keys:
            for bone in rig.pose.bones:
                if key in bone.name.lower():
                    return bone
        return None
    root = find_bone(["root", "pelvis"])
    chest = find_bone(["spine02", "spine2", "spine01", "spine1", "spine"])
    if root is None:
        root = rig.pose.bones[0] if rig.pose.bones else None
    if root is None:
        raise RuntimeError("MPFB rig has no pose bones")
    # Reset pose before creating a deterministic low-amplitude breathing/sway clip.
    for bone in rig.pose.bones:
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = (0.0, 0.0, 0.0)
    rig.animation_data_clear()
    action = bpy.data.actions.new("Lam_Idle_GentleSway")
    rig.animation_data_create()
    rig.animation_data.action = action
    scene.frame_start = 1
    scene.frame_end = 49
    poses = [
        (1, 0.0), (13, 0.012), (25, 0.0), (37, -0.012), (49, 0.0),
    ]
    for frame, yaw in poses:
        scene.frame_set(frame)
        root.rotation_euler[2] = yaw
        root.keyframe_insert(data_path="rotation_euler", frame=frame, group=root.name)
        if chest:
            chest.rotation_euler[0] = 0.0 if frame in (1, 25, 49) else (0.006 if frame == 13 else -0.006)
            chest.keyframe_insert(data_path="rotation_euler", frame=frame, group=chest.name)
    scene.frame_set(1)
    return {
        "name": action.name,
        "root_bone": root.name,
        "chest_bone": chest.name if chest else None,
        "bone_count": len(names),
        "bone_names": names,
    }


def setup_studio(scene, bounds):
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1300
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.resolution_percentage = 100
    scene.render.image_settings.color_depth = "8"
    scene.render.filepath = ""
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("V331StudioWorld")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.16, 0.19, 0.23, 1.0)
        bg.inputs["Strength"].default_value = 0.32

    def area_light(name, location, target, power, color, size):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = power
        data.color = color
        data.shape = "DISK"
        data.size = size
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = location
        obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
        return obj

    subject = (0.0, 0.0, 0.83)
    area_light("V331_Key_Softbox", (-2.8, -3.3, 3.2), subject, 720.0, (1.0, 0.83, 0.72), 2.8)
    area_light("V331_Fill_Softbox", (2.6, -2.2, 1.8), subject, 320.0, (0.70, 0.82, 1.0), 2.4)
    area_light("V331_Rim_Softbox", (0.8, 1.8, 2.8), subject, 900.0, (0.78, 0.86, 1.0), 2.0)
    area_light("V331_Top_Softbox", (0.0, -0.5, 3.8), subject, 220.0, (1.0, 0.91, 0.82), 2.0)

    floor_mat = bpy.data.materials.new("V331_MatteStudioFloor")
    floor_mat.diffuse_color = (0.055, 0.07, 0.09, 1.0)
    floor_mat.use_nodes = True
    p = next((n for n in floor_mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if p:
        p.inputs["Base Color"].default_value = (0.055, 0.07, 0.09, 1.0)
        p.inputs["Roughness"].default_value = 0.88
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, -0.006))
    floor = bpy.context.object
    floor.name = "V331_StudioFloor"
    floor.data.materials.append(floor_mat)

    center_z = bounds["size"][2] * 0.50
    front_y = min(bounds["min"][1] - 3.4, -3.3)
    def create_camera(name, location, target, lens=52, ortho=None):
        data = bpy.data.cameras.new(name)
        camera = bpy.data.objects.new(name, data)
        scene.collection.objects.link(camera)
        camera.location = location
        camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
        if ortho is not None:
            data.type = "ORTHO"
            data.ortho_scale = ortho
        else:
            data.type = "PERSP"
            data.lens = lens
        return camera

    cameras = {
        "front": create_camera("V331_Camera_Front", (0.0, front_y, center_z), (0, 0, center_z), ortho=1.92),
        "three_quarter": create_camera("V331_Camera_ThreeQuarter", (2.0, front_y * 0.88, center_z), (0, 0, center_z), ortho=2.04),
        "side": create_camera("V331_Camera_Side", (abs(front_y), 0.0, center_z), (0, 0, center_z), ortho=1.92),
    }
    # Face close-up uses a perspective lens to retain natural facial proportions.
    cameras["face_closeup"] = create_camera(
        "V331_Camera_FaceCloseup", (0.0, front_y * 0.54, min(1.46, bounds["size"][2] * 0.91)),
        (0.0, 0.0, min(1.42, bounds["size"][2] * 0.87)), lens=75,
    )
    return cameras, floor


def render_evidence(scene, cameras, output_dir, character_bounds):
    images = []
    for label, camera in cameras.items():
        scene.camera = camera
        if label == "face_closeup":
            scene.render.resolution_x = 1000
            scene.render.resolution_y = 1000
        else:
            scene.render.resolution_x = 1000
            scene.render.resolution_y = 1300
        path = os.path.join(output_dir, "v331-" + label.replace("_", "-") + ".png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        if not os.path.isfile(path) or os.path.getsize(path) < 10000:
            raise RuntimeError("Expected render was not written: " + path)
        images.append({"file": os.path.basename(path), "bytes": os.path.getsize(path)})
    return images


def parse_glb_json(path):
    import struct
    data = Path(path).read_bytes()
    if len(data) < 20:
        raise RuntimeError("Output GLB is too small")
    magic, version, total_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or total_length != len(data):
        raise RuntimeError("Output GLB header failed validation")
    length, kind = struct.unpack_from("<II", data, 12)
    if kind != 0x4E4F534A or 20 + length > len(data):
        raise RuntimeError("Output GLB JSON chunk is invalid")
    return json.loads(data[20:20 + length].decode("utf-8").rstrip("\x00 \t\r\n"))


def main():
    args = parse_args()
    output = os.path.abspath(args.output_dir)
    os.makedirs(output, exist_ok=True)
    mpfb_src = os.path.abspath(args.mpfb_src)
    if not os.path.isdir(os.path.join(mpfb_src, "mpfb")):
        raise FileNotFoundError("MPFB source package was not found under " + mpfb_src)
    sys.path.insert(0, mpfb_src)
    import mpfb
    mpfb.register()

    from mpfb.services import AssetService, HumanService, LocationService, TargetService, FaceService, ExportService, ObjectService

    pack_reports = []
    for archive in (args.system_pack, args.face_pack, args.viseme_pack):
        pack_reports.append(safe_install_pack(archive, AssetService, LocationService))
    # Refresh all three source libraries after pack installation.
    AssetService.update_all_asset_lists()
    AssetService.rescan_pack_metadata()
    pack_names = AssetService.get_pack_names()
    if "makehuman_system_assets" not in pack_names:
        raise RuntimeError("The modern MakeHuman system asset pack is not installed")
    for subdir, filename in (
        ("skins", "young_asian_female.mhmat"),
        ("hair", "long01.mhclo"),
        ("clothes", "female_casualsuit01.mhclo"),
    ):
        if AssetService.find_asset_absolute_path(filename, asset_subdir=subdir) is None:
            raise RuntimeError("Required human asset missing after pack install: " + subdir + "/" + filename)

    # Create a coherent female human mesh from MPFB's anatomical basemesh and shape targets.
    macro = TargetService.get_default_macro_info_dict()
    macro["gender"] = 0.08
    macro["age"] = 0.49
    macro["muscle"] = 0.54
    macro["weight"] = 0.56
    macro["proportions"] = 0.50
    macro["height"] = 0.50
    macro["cupsize"] = 0.46
    macro["firmness"] = 0.64
    macro["race"] = {"asian": 0.92, "caucasian": 0.08, "african": 0.0}
    basemesh = HumanService.create_human(
        mask_helpers=True,
        detailed_helpers=True,
        extra_vertex_groups=True,
        feet_on_ground=True,
        scale=0.1,
        macro_detail_dict=macro,
    )
    TargetService.bake_targets(basemesh)
    bpy.context.view_layer.update()
    first_bounds = world_bounds([basemesh])
    height = first_bounds["size"][2]
    if height <= 0.3:
        raise RuntimeError("MPFB base human returned an implausible height: " + repr(first_bounds))
    scale_factor = 1.60 / height
    basemesh.scale = (basemesh.scale.x * scale_factor, basemesh.scale.y * scale_factor, basemesh.scale.z * scale_factor)
    bpy.context.view_layer.update()
    # Preserve feet-on-ground after uniform scale.
    scaled_bounds = world_bounds([basemesh])
    basemesh.location.z -= scaled_bounds["min"][2]
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    basemesh.select_set(True)
    bpy.context.view_layer.objects.active = basemesh
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.context.view_layer.update()

    skin_path = find_asset(AssetService, "skins", [
        "young_asian_female.mhmat",
        "young_caucasian_female.mhmat",
    ])
    if not skin_path:
        raise RuntimeError("Could not find a natural female skin material in the installed assets")
    HumanService.set_character_skin(skin_path, basemesh, skin_type="GAMEENGINE")

    rig = HumanService.add_builtin_rig(basemesh, "game_engine")
    if rig is None or rig.type != "ARMATURE":
        raise RuntimeError("MPFB failed to create the game-engine armature")

    assets_added = []
    hair_objects = []
    clothing_objects = []
    optional_assets = [
        ("eyes", ["high-poly.mhclo", "low-poly.mhclo"], "Eyes", False),
        ("eyebrows", ["eyebrow001.mhclo"], "Eyebrows", False),
        ("eyelashes", ["eyelashes01.mhclo"], "Eyelashes", False),
        ("teeth", ["teeth_base.mhclo"], "Teeth", False),
        ("tongue", ["tongue01.mhclo"], "Tongue", False),
        ("hair", ["long01.mhclo"], "Hair", True),
        ("clothes", ["female_casualsuit01.mhclo"], "Clothes", True),
    ]
    for subdir, candidates, asset_type, required in optional_assets:
        asset_path = find_asset(AssetService, subdir, candidates)
        if asset_path is None:
            if required:
                raise RuntimeError("Could not find required " + asset_type + " asset from MPFB pack: " + repr(candidates))
            assets_added.append({"type": asset_type, "status": "SKIPPED_OPTIONAL", "candidates": candidates})
            continue
        obj = HumanService.add_mhclo_asset(
            asset_path,
            basemesh,
            asset_type=asset_type,
            material_type="GAMEENGINE",
            subdiv_levels=1,
            set_up_rigging=True,
            interpolate_weights=True,
            import_subrig=True,
            import_weights=True,
        )
        if obj is not None:
            if asset_type == "Hair":
                hair_objects.append(obj)
            if asset_type == "Clothes":
                clothing_objects.append(obj)
        assets_added.append({"type": asset_type, "file": asset_path, "name": obj.name if obj else None, "status": "ADDED"})

    # Add source facial targets, transfer them to mapped child meshes, then build the
    # compact set expected by the Lam viewer. The full source targets are removed afterward.
    FaceService.load_targets(basemesh, load_microsoft_visemes=True, load_meta_visemes=False, load_arkit_faceunits=True)
    FaceService.interpolate_targets(basemesh)
    character_root = basemesh.parent if basemesh.parent else basemesh
    character_objects = all_descendants(character_root)
    composite_report = make_composite_morphs(character_objects)
    base_morphs = composite_report.get(basemesh.name, {}).get("composite_morphs", [])
    if base_morphs != EXPECTED_MORPHS:
        raise RuntimeError(
            "The base human is missing required composite morphs. found=" + repr(base_morphs)
            + "; source key inventory=" + repr(composite_report.get(basemesh.name, {}))
        )

    skin_materials = style_materials(basemesh, hair_objects, clothing_objects)
    idle_report = add_idle_animation(rig, bpy.context.scene)

    # Evidence images use studio lighting. The studio floor, lights and cameras are not
    # selected for GLB export.
    bpy.context.view_layer.update()
    character_bounds = world_bounds(character_objects)
    if abs(character_bounds["size"][2] - 1.60) > 0.06:
        raise RuntimeError("Character height outside 1.60 m target after rig/assets: " + repr(character_bounds))
    cameras, floor = setup_studio(bpy.context.scene, character_bounds)
    renders = render_evidence(bpy.context.scene, cameras, output, character_bounds)
    bpy.context.scene.frame_set(1)

    glb_path = os.path.join(output, "lam-v331-real-human-candidate.glb")
    bpy.ops.object.select_all(action="DESELECT")
    for obj in character_objects:
        if obj.name in bpy.data.objects and obj.type in {"MESH", "ARMATURE"}:
            obj.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.gltf(
        filepath=glb_path,
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
    gltf = parse_glb_json(glb_path)
    node_names = [node.get("name", "") for node in gltf.get("nodes", [])]
    animation_names = [anim.get("name", "") for anim in gltf.get("animations", [])]
    skin_count = len(gltf.get("skins", []))
    mesh_count = len(gltf.get("meshes", []))
    source_morph_names = set()
    for mesh in gltf.get("meshes", []):
        extras = mesh.get("extras", {})
        source_morph_names.update(extras.get("targetNames", []))
    missing_morphs = sorted(set(EXPECTED_MORPHS) - source_morph_names)
    texture_count = len(gltf.get("images", []))
    material_count = len(gltf.get("materials", []))
    if skin_count < 1:
        raise RuntimeError("The exported GLB does not contain a skeletal skin")
    if not set(EXPECTED_MORPHS).issubset(source_morph_names):
        raise RuntimeError("The exported GLB is missing morph targets: " + repr(missing_morphs))
    if not texture_count or not material_count:
        raise RuntimeError("The exported GLB unexpectedly has no textures/materials")
    if "Lam_Idle_GentleSway" not in animation_names:
        raise RuntimeError("The exported GLB is missing Lam_Idle_GentleSway animation")

    report = {
        "status": "EXPERIMENTAL_V331_REAL_HUMAN_TOPOLOGY_CANDIDATE_NOT_APPROVED",
        "version": "V331",
        "purpose": "Real human-topology candidate built with MPFB/MakeHuman asset packs; candidate only, not yet photorealism-approved.",
        "blender_version": bpy.app.version_string,
        "mpfb_version": list(getattr(mpfb, "VERSION", ())),
        "mpfb_user_data": LocationService.get_user_data(),
        "asset_packs": pack_reports,
        "installed_pack_names": pack_names,
        "skin_asset": skin_path,
        "height_before_scale_m": round(height, 6),
        "height_scale_factor": round(scale_factor, 6),
        "character_bounds_m": character_bounds,
        "rig": idle_report,
        "assets_added": assets_added,
        "skin_materials": skin_materials,
        "mesh_count_gltf": mesh_count,
        "node_count_gltf": len(node_names),
        "skin_count_gltf": skin_count,
        "texture_count_gltf": texture_count,
        "material_count_gltf": material_count,
        "animation_names_gltf": animation_names,
        "morph_names_gltf": sorted(source_morph_names),
        "missing_expected_morphs": missing_morphs,
        "composite_morph_diagnostics": composite_report,
        "glb_file": os.path.basename(glb_path),
        "glb_bytes": os.path.getsize(glb_path),
        "glb_sha256": sha256(glb_path),
        "renders": renders,
        "warnings": [
            "V331 uses a real human-topology base mesh rather than procedural sphere/capsule facial anatomy.",
            "The model remains a candidate: photorealism requires human visual comparison against Phi's reference.",
            "The included idle clip is intentionally subtle and skeletal; it is a technical animation, not a complete motion library.",
            "Voice/chat integration is outside this avatar candidate build.",
        ],
    }
    report_path = os.path.join(output, "lam-v331-candidate-report.json")
    Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Save an editable Blender scene alongside the exported GLB and visual evidence.
    scene_path = os.path.join(output, "lam-v331-real-human-candidate.blend")
    bpy.ops.wm.save_as_mainfile(filepath=scene_path)
    print("V331_REAL_HUMAN_CANDIDATE=" + json.dumps(report, ensure_ascii=False))
    if os.path.getsize(glb_path) < 1_000_000:
        raise RuntimeError("V331 GLB is unexpectedly small for a textured human character")
    if os.path.getsize(glb_path) > 200_000_000:
        raise RuntimeError("V331 GLB is too large for an initial mobile candidate: " + str(os.path.getsize(glb_path)))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
