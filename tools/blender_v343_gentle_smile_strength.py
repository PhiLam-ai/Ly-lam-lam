#!/usr/bin/env python3
"""V343: build a coherent human-topology Lam candidate with MPFB, real asset materials,
a game-engine rig, a light idle action and 12 composite facial morphs.

This is an experimental candidate. It never edits the production GLB.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import types
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


def _linear_quantile(values, q):
    """Deterministic interpolated quantile for small geometry audit arrays."""
    values = sorted(float(value) for value in values)
    if not values:
        raise ValueError("Cannot compute a quantile for an empty collection")
    position = max(0.0, min(1.0, float(q))) * (len(values) - 1)
    lower = int(math.floor(position))
    upper = min(lower + 1, len(values) - 1)
    fraction = position - lower
    return values[lower] * (1.0 - fraction) + values[upper] * fraction


def _world_mesh_points(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
    try:
        matrix = evaluated.matrix_world.copy()
        return [matrix @ vertex.co for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


def body_profile_audit(basemesh, clothing_objects):
    """Measure visible neutral-surface cross-sections before changing proportions.

    The base skin mesh may be masked by clothing in thigh regions, so garment
    vertices are sampled for dressed torso/hip/leg bands. Arm outliers are
    restricted with a central-body x window. Measurements are comparative
    geometry diagnostics rather than anatomical/likeness claims.
    """
    body_points = _world_mesh_points(basemesh)
    garment_points = []
    garment_sources = []
    for obj in clothing_objects:
        if obj.type == "MESH":
            garment_points.extend(_world_mesh_points(obj))
            garment_sources.append(obj.name)
    if len(body_points) < 100:
        raise RuntimeError("Too few base-mesh vertices for V343 morphometric audit")
    z_min = min(point.z for point in body_points)
    z_max = max(point.z for point in body_points)
    height = z_max - z_min
    if height <= 0:
        raise RuntimeError("Invalid base-mesh height in V343 morphometric audit")

    # z bands are fractions of measured human height. For upper body, sample
    # both skin and clothing around the central torso; lower bands use clothing
    # because MakeHuman hides the skin topology under garments.
    bands = {
        "head":        (0.82, 0.985, "skin", None),
        "neck":        (0.755, 0.835, "skin", 0.20),
        "shoulders":   (0.715, 0.795, "both", 0.30),
        "upper_torso": (0.635, 0.735, "both", 0.23),
        "waist":       (0.535, 0.625, "both", 0.22),
        "hips":        (0.425, 0.545, "clothing", 0.28),
        "upper_thigh": (0.315, 0.435, "clothing", 0.27),
        "mid_thigh":   (0.225, 0.335, "clothing", 0.23),
    }
    regions = {}
    for name, (low_fraction, high_fraction, source, x_limit) in bands.items():
        z_low = z_min + height * low_fraction
        z_high = z_min + height * high_fraction
        candidates = body_points if source == "skin" else garment_points if source == "clothing" else body_points + garment_points
        slab = [point for point in candidates if z_low <= point.z <= z_high]
        if x_limit is not None:
            slab = [point for point in slab if abs(point.x) <= x_limit]
        if len(slab) < 20:
            regions[name] = {
                "status": "INSUFFICIENT_VERTICES",
                "vertex_count": len(slab),
                "source": source,
                "central_x_limit_m": x_limit,
                "z_band_m": [round(z_low, 5), round(z_high, 5)],
            }
            continue
        abs_x = [abs(point.x) for point in slab]
        y_values = [point.y for point in slab]
        regions[name] = {
            "status": "MEASURED",
            "vertex_count": len(slab),
            "source": source,
            "central_x_limit_m": x_limit,
            "z_band_m": [round(z_low, 5), round(z_high, 5)],
            "robust_width_x_m": round(2.0 * _linear_quantile(abs_x, 0.85), 5),
            "robust_depth_y_m": round(
                _linear_quantile(y_values, 0.95) - _linear_quantile(y_values, 0.05), 5
            ),
        }
    return {
        "method": "neutral world-space height bands; region-specific skin/garment sources; central x filtering; width=2*P85(abs(x)); depth=P95(y)-P05(y)",
        "measurement_warning": "Comparative dressed-mesh metrics only; not a replacement for visual review or a likeness check.",
        "vertex_count": len(body_points),
        "garment_vertex_count": len(garment_points),
        "garment_objects": garment_sources,
        "height_m": round(height, 5),
        "regions": regions,
    }


def _smooth_band_weight(z, center, half_width):
    """Cubic smooth envelope that reaches zero at each band edge."""
    if half_width <= 0:
        return 0.0
    value = 1.0 - abs((float(z) - center) / half_width)
    if value <= 0.0:
        return 0.0
    value = min(1.0, value)
    return value * value * (3.0 - 2.0 * value)


def _central_x_weight(x, inner_radius, outer_radius):
    """Fade body adjustment to zero outside the central torso/leg silhouette."""
    radius = abs(float(x))
    if radius <= inner_radius:
        return 1.0
    if radius >= outer_radius:
        return 0.0
    value = (outer_radius - radius) / (outer_radius - inner_radius)
    return value * value * (3.0 - 2.0 * value)


def apply_targeted_body_shape_adjustment(basemesh, clothing_objects):
    """Apply a smooth lower-body adjustment while keeping arms outside the x range.

    Operates before facial targets are loaded and applies the same transform to
    body skin and clothing. A central-x falloff prevents arm vertices at a
    matching height from being widened by the lower-body profile.
    """
    targets = [("body", basemesh)] + [("clothing", obj) for obj in clothing_objects if obj.type == "MESH"]
    if not clothing_objects:
        raise RuntimeError("V343 requires clothing geometry to keep the dressed silhouette continuous")

    adjusted = []
    for role, obj in targets:
        if obj.type != "MESH":
            continue
        matrix = obj.matrix_world.copy()
        inverse = matrix.inverted()
        edited_vertices = 0

        def transform_point(local_co):
            point = matrix @ local_co
            z = float(point.z)
            hip = _smooth_band_weight(z, center=0.79, half_width=0.17)
            upper_thigh = _smooth_band_weight(z, center=0.60, half_width=0.16)
            mid_thigh = _smooth_band_weight(z, center=0.45, half_width=0.14)
            hip_gate = _central_x_weight(point.x, 0.22, 0.30)
            upper_gate = _central_x_weight(point.x, 0.21, 0.29)
            mid_gate = _central_x_weight(point.x, 0.20, 0.28)

            hip_effect = hip * hip_gate
            upper_thigh_effect = upper_thigh * upper_gate
            mid_thigh_effect = mid_thigh * mid_gate
            x_scale = 1.0 + (0.10 * hip_effect) + (0.08 * upper_thigh_effect) + (0.06 * mid_thigh_effect)

            # The camera looks from negative Y; positive Y is the back side.
            # Only the gated central hip band receives posterior projection.
            posterior = max(0.0, min(1.0, (float(point.y) + 0.08) / 0.16))
            rear_shift = 0.025 * hip_effect * posterior
            shaped = Vector((float(point.x) * x_scale, float(point.y) + rear_shift, float(point.z)))
            return inverse @ shaped

        shape_keys = getattr(obj.data, "shape_keys", None)
        if shape_keys is not None and len(shape_keys.key_blocks):
            # Apply the same spatial rule to every key block so existing targets
            # remain aligned. At this stage no facial target pack has been loaded.
            for key_block in shape_keys.key_blocks:
                for point in key_block.data:
                    point.co = transform_point(point.co.copy())
                    edited_vertices += 1
        else:
            for vertex in obj.data.vertices:
                vertex.co = transform_point(vertex.co.copy())
                edited_vertices += 1
        obj.data.update()
        adjusted.append({
            "role": role,
            "object": obj.name,
            "edited_coordinate_count": edited_vertices,
            "has_shape_keys": bool(shape_keys and len(shape_keys.key_blocks)),
        })

    bpy.context.view_layer.update()
    return {
        "status": "APPLIED",
        "zones": {
            "hips": {
                "center_z_m": 0.79, "half_width_m": 0.17, "max_lateral_scale": 1.10,
                "central_x_falloff_m": [0.22, 0.30],
            },
            "upper_thigh": {
                "center_z_m": 0.60, "half_width_m": 0.16, "max_lateral_scale": 1.08,
                "central_x_falloff_m": [0.21, 0.29],
            },
            "mid_thigh": {
                "center_z_m": 0.45, "half_width_m": 0.14, "max_lateral_scale": 1.06,
                "central_x_falloff_m": [0.20, 0.28],
            },
            "posterior_hip_projection": {"max_shift_m": 0.025, "side": "positive_y/back", "x_gated": True},
        },
        "scope": "base body and clothing meshes; central-x falloff protects arms; hair, face accessories, textures, morph recipes and animation logic unchanged",
        "edited_meshes": adjusted,
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


def apply_default_smile_base_pose(character_objects, strength=0.12):
    """Bake a small fraction of the existing smile shape into the neutral pose.

    The same offset is added to Basis and every non-smile key. The smile target
    itself is deliberately left unchanged, so the dedicated smile control still
    ends at the original full-smile target instead of becoming overdriven.
    This changes no topology and keeps other morph deltas relative to Basis.
    """
    strength = max(0.0, min(0.25, float(strength)))
    audits = []
    total_vertices = 0
    for obj in character_objects:
        if obj.type != "MESH":
            continue
        shape_keys = getattr(obj.data, "shape_keys", None)
        if shape_keys is None or not shape_keys.key_blocks:
            continue
        keys = shape_keys.key_blocks
        basis = keys.get("Basis")
        smile = keys.get("smile")
        if basis is None or smile is None:
            continue
        if len(basis.data) != len(smile.data):
            raise RuntimeError("V343 Basis/smile vertex count mismatch on " + obj.name)
        deltas = [
            smile.data[index].co.copy() - basis.data[index].co.copy()
            for index in range(len(basis.data))
        ]
        max_delta = max((delta.length for delta in deltas), default=0.0)
        if max_delta <= 1e-8:
            audits.append({
                "object": obj.name,
                "status": "SKIPPED_ZERO_DELTA",
                "vertices": len(basis.data),
                "max_delta_m": max_delta,
            })
            continue
        # Shift Basis and all alternate targets except the smile endpoint by the
        # same delta. Their relative morph offsets are preserved; the smile target
        # remains at its original full expression.
        changed_keys = []
        for key_block in keys:
            if key_block.name == "smile":
                continue
            for index, delta in enumerate(deltas):
                key_block.data[index].co += delta * strength
            changed_keys.append(key_block.name)
        obj.data.update()
        audits.append({
            "object": obj.name,
            "status": "APPLIED",
            "vertices": len(basis.data),
            "max_delta_m": round(float(max_delta), 8),
            "max_neutral_displacement_m": round(float(max_delta * strength), 8),
            "strength": strength,
            "changed_key_blocks": changed_keys,
            "smile_endpoint_preserved": True,
        })
        total_vertices += len(basis.data)
    if total_vertices == 0:
        raise RuntimeError("V343 could not apply a gentle smile base pose to any face mesh with a smile morph")
    return {
        "status": "APPLIED",
        "expression": "gentle_smile",
        "strength": strength,
        "method": "Bake a restrained fraction of the existing smile delta into Basis and all non-smile shape keys; leave smile endpoint unchanged.",
        "total_vertices_adjusted": total_vertices,
        "objects": audits,
        "safety_note": "All 12 named morph controls are retained; smile endpoint and all non-smile morph deltas relative to the new Basis are preserved.",
    }


def find_hair_diffuse_image(hair_objects):
    scored = []
    for obj in hair_objects:
        for material in getattr(obj.data, "materials", []):
            if not material or not material.use_nodes or not material.node_tree:
                continue
            for node in material.node_tree.nodes:
                if node.type != "TEX_IMAGE" or not getattr(node, "image", None):
                    continue
                image = node.image
                name = image.name.lower()
                if "normal" in name or "specular" in name or "roughness" in name or "alpha" in node.name.lower():
                    continue
                score = 0
                if "long01_diffuse" in name:
                    score += 100
                elif "diffuse" in name:
                    score += 40
                if image.channels >= 4:
                    score += 10
                if image.size[0] >= 1024 and image.size[1] >= 1024:
                    score += 5
                if score:
                    scored.append((score, image, obj))
    if not scored:
        raise RuntimeError("V343 cannot find the long01 hair diffuse image")
    scored.sort(key=lambda row: (-row[0], row[1].name.lower()))
    return scored[0][1], scored[0][2]


def make_darkened_hair_image(source_image):
    """Reduce highlights baked into the source diffuse while preserving alpha."""
    import numpy as np

    width, height = int(source_image.size[0]), int(source_image.size[1])
    channels = int(source_image.channels)
    if width < 128 or height < 128 or channels < 3:
        raise RuntimeError("V343 hair diffuse image has unexpected dimensions/channels")
    raw = np.empty(len(source_image.pixels), dtype=np.float32)
    source_image.pixels.foreach_get(raw)
    source_pixels = raw.reshape((-1, channels))
    rgb = source_pixels[:, :3]
    source_rgb_mean_linear = float(np.mean(rgb))
    # Texture luminance is used to compress only the bright baked highlight
    # bands. The alpha channel is deliberately left byte-for-byte unchanged.
    luminance = (0.2126 * rgb[:, 0]) + (0.7152 * rgb[:, 1]) + (0.0722 * rgb[:, 2])
    t = np.clip((luminance - 0.18) / (0.72 - 0.18), 0.0, 1.0)
    smooth = t * t * (3.0 - 2.0 * t)
    scale = 0.74 - (0.34 * smooth)
    rgb[:, 0] *= scale * 0.94
    rgb[:, 1] *= scale * 0.80
    rgb[:, 2] *= scale * 0.78
    np.clip(rgb, 0.0, 1.0, out=rgb)

    output_image = source_image.copy()
    output_image.name = "V343_HairDiffuse_Darkened"
    output_image.pixels.foreach_set(raw)
    output_image.update()
    output_image["v343_source_image"] = source_image.name
    output_image["v343_processing"] = "luminance-weighted highlight compression; RGB darkened and warmed; alpha preserved"
    try:
        output_image.pack()
    except Exception:
        # Blender will still include generated image pixels in the saved scene/export;
        # record the non-packed condition so it is visible in the artifact audit.
        pass
    return output_image, {
        "source_image_name": source_image.name,
        "image_name": output_image.name,
        "width": width,
        "height": height,
        "channels": channels,
        "source_rgb_mean_linear": source_rgb_mean_linear,
        "processed_rgb_mean_linear": float(np.mean(rgb)),
        "alpha_preserved": channels >= 4,
        "processing": "highlight scale 0.74 at dark values to 0.40 at bright values; red x0.94, green x0.80, blue x0.78; original alpha unchanged",
    }


def make_gltf_compatible_hair_material(image, uv_map_name):
    """Use a single processed diffuse texture and explicit UV/alpha links."""
    material = bpy.data.materials.new("V343_GltfCompatibleHair")
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    output.location = (420, 40)
    principled = tree.nodes.new("ShaderNodeBsdfPrincipled")
    principled.location = (120, 40)
    principled.inputs["Roughness"].default_value = 0.86
    if "Metallic" in principled.inputs:
        principled.inputs["Metallic"].default_value = 0.0
    if "Specular IOR Level" in principled.inputs:
        principled.inputs["Specular IOR Level"].default_value = 0.12
    if "Coat Weight" in principled.inputs:
        principled.inputs["Coat Weight"].default_value = 0.0
    uv_node = tree.nodes.new("ShaderNodeUVMap")
    uv_node.uv_map = uv_map_name
    uv_node.location = (-600, 40)
    texture = tree.nodes.new("ShaderNodeTexImage")
    texture.image = image
    texture.interpolation = "Linear"
    texture.extension = "REPEAT"
    texture.location = (-340, 40)
    texture.label = "V343 darkened hair diffuse — explicit UV map"
    tree.links.new(uv_node.outputs["UV"], texture.inputs["Vector"])
    tree.links.new(texture.outputs["Color"], principled.inputs["Base Color"])
    alpha_enabled = bool(getattr(image, "channels", 3) >= 4)
    if alpha_enabled and "Alpha" in principled.inputs:
        tree.links.new(texture.outputs["Alpha"], principled.inputs["Alpha"])
        if hasattr(material, "surface_render_method"):
            try:
                material.surface_render_method = "BLENDED"
            except Exception:
                pass
    tree.links.new(principled.outputs["BSDF"], output.inputs["Surface"])
    material.diffuse_color = (0.075, 0.035, 0.025, 1.0)
    return material, alpha_enabled


def prepare_hair_materials(hair_objects):
    source_image, source_obj = find_hair_diffuse_image(hair_objects)
    dark_image, image_audit = make_darkened_hair_image(source_image)
    audits = []
    for obj in hair_objects:
        if obj.type != "MESH":
            continue
        uv_name = get_active_uv_name(obj)
        if not uv_name:
            raise RuntimeError("V343 hair object has no active UV map: " + obj.name)
        uv_audit = activate_uv_layer(obj, uv_name)
        material, alpha_enabled = make_gltf_compatible_hair_material(dark_image, uv_name)
        obj.data.materials.clear()
        obj.data.materials.append(material)
        audits.append({
            "source_object": obj.name,
            "source_image_name": source_image.name,
            "image_name": dark_image.name,
            "uv_map_name": uv_name,
            "alpha_enabled": alpha_enabled,
            "roughness": 0.86,
            "specular_ior_level": 0.12,
            "source_uv_audit": uv_audit,
            "material_name": material.name,
        })
    return {
        "image": image_audit,
        "hair_objects": audits,
        "material_node_graph": ["UVMap -> Image Texture Vector", "Image Texture Color -> Principled Base Color", "Image Texture Alpha -> Principled Alpha", "Principled BSDF -> Material Output"],
        "note": "This intentionally changes only hair diffuse processing/material; body silhouette, face accessories, skin, clothing, morphs and animation remain unchanged.",
    }


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
    # V343 replaces the source hair material after this helper with an explicit
    # darkened RGBA texture + UVMap material; no unsupported tint node survives.
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
        if obj.type == "MESH" and obj.name != "V343_StudioFloor":
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
        scene.world = bpy.data.worlds.new("V343StudioWorld")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.16, 0.19, 0.23, 1.0)
        bg.inputs["Strength"].default_value = 0.20

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
    area_light("V343_Key_Softbox", (-2.8, -3.3, 3.2), subject, 300.0, (1.0, 0.83, 0.72), 2.8)
    area_light("V343_Fill_Softbox", (2.6, -2.2, 1.8), subject, 150.0, (0.70, 0.82, 1.0), 2.4)
    area_light("V343_Rim_Softbox", (0.8, 1.8, 2.8), subject, 240.0, (0.78, 0.86, 1.0), 2.0)
    area_light("V343_Top_Softbox", (0.0, -0.5, 3.8), subject, 90.0, (1.0, 0.91, 0.82), 2.0)

    floor_mat = bpy.data.materials.new("V343_MatteStudioFloor")
    floor_mat.diffuse_color = (0.055, 0.07, 0.09, 1.0)
    floor_mat.use_nodes = True
    p = next((n for n in floor_mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if p:
        p.inputs["Base Color"].default_value = (0.055, 0.07, 0.09, 1.0)
        p.inputs["Roughness"].default_value = 0.88
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, -0.006))
    floor = bpy.context.object
    floor.name = "V343_StudioFloor"
    floor.data.materials.append(floor_mat)
    # Do not let a bright ground plane obscure most of the avatar evidence frame.
    floor.hide_render = True

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
        "front": create_camera("V343_Camera_Front", (0.0, front_y, center_z), (0, 0, center_z), ortho=2.15),
        "three_quarter": create_camera("V343_Camera_ThreeQuarter", (2.0, front_y * 0.88, center_z), (0, 0, center_z), ortho=2.28),
        "side": create_camera("V343_Camera_Side", (abs(front_y), 0.0, center_z), (0, 0, center_z), ortho=1.92),
    }
    # Face close-up uses a perspective lens to retain natural facial proportions.
    cameras["face_closeup"] = create_camera(
        "V343_Camera_FaceCloseup", (0.0, front_y * 0.54, min(1.46, bounds["size"][2] * 0.91)),
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
        path = os.path.join(output_dir, "v343-" + label.replace("_", "-") + ".png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        if not os.path.isfile(path) or os.path.getsize(path) < 10000:
            raise RuntimeError("Expected render was not written: " + path)
        images.append({"file": os.path.basename(path), "bytes": os.path.getsize(path)})
    return images



def evaluated_world_mesh(obj, depsgraph):
    """Return an evaluated mesh copy with rig deformation baked into world-space vertices."""
    evaluated = obj.evaluated_get(depsgraph)
    evaluated_mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
    try:
        world_matrix = evaluated.matrix_world.copy()
        world_vertices = [world_matrix @ vertex.co for vertex in evaluated_mesh.vertices]
        mesh_copy = evaluated_mesh.copy()
    finally:
        evaluated.to_mesh_clear()
    # Store all vertices in a shared world coordinate frame so the web file carries no
    # original object-space or inverse-bind transform that could deform the avatar.
    for vertex, world_co in zip(mesh_copy.vertices, world_vertices):
        vertex.co = world_co
    mesh_copy.update()
    return mesh_copy, world_vertices


def add_baked_root_idle_animation(root, scene):
    """Animate a common root node; body geometry remains baked and unskinned."""
    # Preserve the source-rig action for inspection, but give it a distinct name so the
    # exported web clip is exactly Lam_Idle_GentleSway (not Blender's .001 duplicate).
    source_action = bpy.data.actions.get("Lam_Idle_GentleSway")
    if source_action is not None:
        source_action.name = "Lam_SourceRig_GentleSway_Diagnostic"
    root.rotation_mode = "XYZ"
    root.animation_data_clear()
    action = bpy.data.actions.new("Lam_Idle_GentleSway")
    root.animation_data_create()
    root.animation_data.action = action
    scene.frame_start = 1
    scene.frame_end = 49
    poses = [(1, 0.0), (13, 0.008), (25, 0.0), (37, -0.008), (49, 0.0)]
    for frame, yaw in poses:
        scene.frame_set(frame)
        root.rotation_euler = (0.0, 0.0, yaw)
        root.keyframe_insert(data_path="rotation_euler", frame=frame, group="Lam_Idle_GentleSway")
    scene.frame_set(1)
    return {
        "name": action.name,
        "target_node": root.name,
        "type": "common-root subtle sway; geometry stays baked and unskinned",
        "keyframes": len(poses),
    }


def bake_character_to_morph_meshes(character_objects, scene):
    """Bake neutral geometry, while isolating optional face accessory meshes from the web GLB."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    baked_objects = []
    mesh_reports = []
    excluded_face_accessories = []
    # The skin diffuse map already includes eyes, brows and lips. In the prior test these
    # separate accessory meshes aligned in Blender but rendered as red/black patches in WebGL.
    # Excluding them isolates the material/UV cause without editing the source human.
    excluded_suffixes = ()
    for source in character_objects:
        if source.type != "MESH":
            continue
        suffix = source.name.rsplit(".", 1)[-1].lower()
        if suffix in excluded_suffixes:
            excluded_face_accessories.append({
                "source_object": source.name,
                "suffix": suffix,
                "excluded_from_web_glb": True,
                "reason": "V343 isolate facial accessory material/UV artifacts; skin base texture remains.",
            })
            continue
        source_keys = source.data.shape_keys.key_blocks if source.data.shape_keys else []
        available_morphs = [
            name for name in EXPECTED_MORPHS
            if source.data.shape_keys and source.data.shape_keys.key_blocks.get(name)
        ]
        for block in source_keys:
            if block.name != "Basis":
                block.value = 0.0
        depsgraph.update()
        neutral_mesh, neutral_world_vertices = evaluated_world_mesh(source, depsgraph)
        if not neutral_mesh.vertices or len(neutral_world_vertices) != len(neutral_mesh.vertices):
            bpy.data.meshes.remove(neutral_mesh)
            raise RuntimeError("Invalid neutral evaluated mesh while baking: " + source.name)
        neutral_mesh.name = "V343_Baked_" + source.data.name
        baked = bpy.data.objects.new("V343_Baked_" + source.name, neutral_mesh)
        scene.collection.objects.link(baked)

        basis = None
        if baked.data.shape_keys:
            key_blocks = baked.data.shape_keys.key_blocks
            basis = key_blocks[0]
            for old_key in list(key_blocks)[1:]:
                baked.shape_key_remove(old_key)
            for index, co in enumerate(neutral_world_vertices):
                basis.data[index].co = co
        elif available_morphs:
            basis = baked.shape_key_add(name="Basis", from_mix=False)
            if len(basis.data) != len(neutral_world_vertices):
                raise RuntimeError("Baked Basis vertex count mismatch: " + source.name)
            for index, co in enumerate(neutral_world_vertices):
                basis.data[index].co = co

        if available_morphs:
            if basis is None:
                raise RuntimeError("Could not initialize morph Basis for " + source.name)
            for morph_name in available_morphs:
                for block in source_keys:
                    if block.name != "Basis":
                        block.value = 0.0
                source.data.shape_keys.key_blocks[morph_name].value = 1.0
                depsgraph.update()
                target_mesh, target_world_vertices = evaluated_world_mesh(source, depsgraph)
                try:
                    if len(target_world_vertices) != len(neutral_world_vertices):
                        raise RuntimeError("Morph vertex count changed while baking " + source.name + "/" + morph_name)
                    target = baked.shape_key_add(name=morph_name, from_mix=False)
                    target.slider_min = 0.0
                    target.slider_max = 1.0
                    if len(target.data) != len(target_world_vertices):
                        raise RuntimeError("Output morph vertex count mismatch: " + source.name + "/" + morph_name)
                    for index, co in enumerate(target_world_vertices):
                        target.data[index].co = co
                    target.value = 0.0
                finally:
                    bpy.data.meshes.remove(target_mesh)

            for block in source_keys:
                if block.name != "Basis":
                    block.value = 0.0
            depsgraph.update()

        # Coordinates are already world-space, so each baked object and the root start at identity.
        baked.matrix_world.identity()
        baked_objects.append(baked)
        mesh_reports.append({
            "source_object": source.name,
            "baked_object": baked.name,
            "vertex_count": len(neutral_world_vertices),
            "morphs": available_morphs,
            "material_slots": len(baked.data.materials),
            "world_space_geometry": True,
        })

    if not baked_objects:
        raise RuntimeError("No character meshes were available for baked export")

    root = bpy.data.objects.new("Lam_CharacterRoot_V343", None)
    root.empty_display_type = "PLAIN_AXES"
    root.location = (0.0, 0.0, 0.0)
    root.rotation_mode = "XYZ"
    scene.collection.objects.link(root)
    for baked in baked_objects:
        baked.parent = root
        baked.matrix_parent_inverse = root.matrix_world.inverted()
        baked.matrix_world.identity()

    # Original rigged source is kept in the editable .blend but excluded from visual output.
    for source in character_objects:
        if source.name in bpy.data.objects:
            source.hide_render = True
            source.hide_set(True)

    idle_report = add_baked_root_idle_animation(root, scene)
    scene.frame_set(1)
    bpy.context.view_layer.update()
    if len(baked_objects) != len(mesh_reports):
        raise RuntimeError("Baked mesh/report count mismatch")
    return baked_objects, root, idle_report, mesh_reports, excluded_face_accessories


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



def extract_glb_embedded_image_bytes(glb_path, gltf, image_index):
    """Extract a GLB image payload through JSON bufferView metadata."""
    import struct

    blob = Path(glb_path).read_bytes()
    if len(blob) < 20:
        raise RuntimeError("GLB too small for embedded image audit")
    magic, version, total_length = struct.unpack_from("<4sII", blob, 0)
    if magic != b"glTF" or version != 2 or total_length != len(blob):
        raise RuntimeError("GLB header invalid during embedded hair image audit")
    json_length, json_kind = struct.unpack_from("<I4s", blob, 12)
    if json_kind != b"JSON":
        raise RuntimeError("GLB JSON chunk missing during hair image audit")
    binary_chunk_offset = 20 + json_length
    binary_length, binary_kind = struct.unpack_from("<I4s", blob, binary_chunk_offset)
    if binary_kind != b"BIN\x00":
        raise RuntimeError("GLB binary chunk missing during hair image audit")
    binary_payload = blob[binary_chunk_offset + 8:binary_chunk_offset + 8 + binary_length]
    image_entry = gltf.get("images", [])[image_index]
    if "bufferView" not in image_entry:
        raise RuntimeError("Hair image is not embedded in the GLB bufferView")
    view = gltf.get("bufferViews", [])[image_entry["bufferView"]]
    start = int(view.get("byteOffset", 0))
    length = int(view["byteLength"])
    payload = binary_payload[start:start + length]
    if len(payload) != length:
        raise RuntimeError("Truncated image payload while auditing GLB hair image")
    return payload, image_entry.get("mimeType", "image/png"), image_entry.get("name", "")


def mean_rgb_linear_from_png_bytes(payload, output_dir):
    """Decode embedded PNG via Blender's image loader and return its mean RGB."""
    import numpy as np

    temp_path = os.path.join(output_dir, ".v343-embedded-hair-check.png")
    Path(temp_path).write_bytes(payload)
    loaded = None
    try:
        loaded = bpy.data.images.load(temp_path, check_existing=False)
        raw = np.empty(len(loaded.pixels), dtype=np.float32)
        loaded.pixels.foreach_get(raw)
        pixels = raw.reshape((-1, int(loaded.channels)))
        return float(np.mean(pixels[:, :3])), float(np.mean(pixels[:, 3])) if loaded.channels >= 4 else 1.0
    finally:
        if loaded is not None:
            bpy.data.images.remove(loaded)
        try:
            os.remove(temp_path)
        except FileNotFoundError:
            pass


def get_active_uv_name(obj):
    layers = getattr(getattr(obj, "data", None), "uv_layers", None)
    if not layers or len(layers) == 0:
        return None
    active = getattr(layers, "active", None)
    if active is not None:
        return active.name
    return layers[0].name


def inspect_uv_layers(obj):
    layers = getattr(getattr(obj, "data", None), "uv_layers", None)
    if not layers:
        return []
    active_name = get_active_uv_name(obj)
    result = []
    for layer in layers:
        result.append({
            "name": layer.name,
            "active": layer.name == active_name,
            "active_render": bool(getattr(layer, "active_render", False)),
        })
    return result


def skin_material_node_audit(obj, skin_image=None):
    audit = {
        "object": obj.name,
        "uv_layers": inspect_uv_layers(obj),
        "materials": [],
    }
    for material in getattr(obj.data, "materials", []):
        if not material:
            continue
        item = {"material": material.name, "use_nodes": bool(material.use_nodes), "image_nodes": []}
        if material.use_nodes and material.node_tree:
            tree = material.node_tree
            for node in tree.nodes:
                if node.type != "TEX_IMAGE" or not getattr(node, "image", None):
                    continue
                vec = node.inputs.get("Vector") if hasattr(node, "inputs") else None
                sources = []
                if vec is not None:
                    for link in vec.links:
                        from_node = link.from_node
                        sources.append({
                            "node": from_node.name,
                            "type": from_node.type,
                            "socket": link.from_socket.name,
                            "uv_map": getattr(from_node, "uv_map", None),
                        })
                item["image_nodes"].append({
                    "node": node.name,
                    "image": node.image.name,
                    "chosen_skin_image": bool(skin_image and node.image == skin_image),
                    "vector_sources": sources,
                })
        audit["materials"].append(item)
    return audit


def find_skin_diffuse_image(basemesh):
    scored = []
    for material in getattr(basemesh.data, "materials", []):
        if not material or not material.use_nodes or not material.node_tree:
            continue
        for node in material.node_tree.nodes:
            if node.type != "TEX_IMAGE" or not getattr(node, "image", None):
                continue
            name = node.image.name.lower()
            score = 0
            if "young_lightskinned_female_diffuse3" in name:
                score = 100
            elif "lightskinned" in name and "diffuse" in name and "female" in name:
                score = 80
            elif "skin" in name and "diffuse" in name:
                score = 50
            if score:
                scored.append((score, node.image))
    if not scored:
        # Audit fallback: a base-body diffuse image is preferred over normal/specular maps.
        for material in getattr(basemesh.data, "materials", []):
            if not material or not material.use_nodes or not material.node_tree:
                continue
            for node in material.node_tree.nodes:
                if node.type != "TEX_IMAGE" or not getattr(node, "image", None):
                    continue
                name = node.image.name.lower()
                if "diffuse" in name and ("female" in name or "skin" in name):
                    scored.append((10, node.image))
    if not scored:
        raise RuntimeError("Cannot find a skin diffuse image in the base human's material nodes")
    scored.sort(key=lambda row: (-row[0], row[1].name.lower()))
    return scored[0][1]


def resolve_skin_uv_name(basemesh, skin_image, audit):
    """Use the UV map explicitly feeding the source skin diffuse texture when present."""
    candidates = []
    for material in getattr(basemesh.data, "materials", []):
        if not material or not material.use_nodes or not material.node_tree:
            continue
        for node in material.node_tree.nodes:
            if node.type != "TEX_IMAGE" or getattr(node, "image", None) != skin_image:
                continue
            vec = node.inputs.get("Vector")
            if vec is None:
                continue
            for link in vec.links:
                from_node = link.from_node
                if from_node.type == "UVMAP" and getattr(from_node, "uv_map", ""):
                    candidates.append(from_node.uv_map)
    layers = getattr(basemesh.data, "uv_layers", None)
    if not layers or len(layers) == 0:
        raise RuntimeError("Base human has no UV map for the skin diffuse texture")
    available = {layer.name for layer in layers}
    for name in candidates:
        if name in available:
            return name, "explicit_uv_map_node"
    active_name = get_active_uv_name(basemesh)
    if active_name in available:
        return active_name, "active_uv_layer_fallback"
    return layers[0].name, "first_uv_layer_fallback"


def activate_uv_layer(obj, name):
    layers = getattr(getattr(obj, "data", None), "uv_layers", None)
    if not layers or len(layers) == 0:
        raise RuntimeError("Cannot activate a skin UV layer on " + obj.name)
    names = [layer.name for layer in layers]
    if name not in names:
        raise RuntimeError("Skin UV map " + repr(name) + " missing on " + obj.name + ": " + repr(names))
    selected_index = names.index(name)
    # Set active and active-render so glTF TEXCOORD_0 corresponds to the source skin mapping.
    for index, layer in enumerate(layers):
        try:
            layer.active_render = (index == selected_index)
        except Exception:
            pass
    try:
        layers.active_index = selected_index
    except Exception:
        pass
    return {
        "object": obj.name,
        "selected_uv_map": name,
        "uv_layers_after": inspect_uv_layers(obj),
    }


def make_gltf_compatible_skin_material(image, uv_map_name):
    """Create one explicit base-color image + UVMap node, avoiding ambiguous multi-image graphs."""
    material = bpy.data.materials.new("V343_GltfCompatibleSkin")
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
    uv_node.uv_map = uv_map_name
    uv_node.location = (-600, 40)
    texture = tree.nodes.new("ShaderNodeTexImage")
    texture.image = image
    texture.interpolation = "Linear"
    texture.extension = "REPEAT"
    texture.location = (-340, 40)
    texture.label = "V343 skin diffuse — explicit UV map"
    tree.links.new(uv_node.outputs["UV"], texture.inputs["Vector"])
    tree.links.new(texture.outputs["Color"], principled.inputs["Base Color"])
    tree.links.new(principled.outputs["BSDF"], output.inputs["Surface"])
    material.diffuse_color = (0.76, 0.48, 0.36, 1.0)
    return material



def find_face_accessory_diffuse_image(source_obj, suffix):
    tokens = {
        "eyebrow001": ("eyebrow001",),
        "eyelashes01": ("eyelashes01",),
        "high-poly": ("brown_eye", "eyeball", "eye"),
        "teeth_base": ("teeth",),
        "tongue01": ("tongue01_diffuse", "tongue01", "tongue"),
    }.get(suffix, (suffix,))
    scored = []
    for material in getattr(source_obj.data, "materials", []):
        if not material or not material.use_nodes or not material.node_tree:
            continue
        for node in material.node_tree.nodes:
            if node.type != "TEX_IMAGE" or not getattr(node, "image", None):
                continue
            name = node.image.name.lower()
            score = 0
            if any(token in name for token in tokens):
                score = 100
            if "normal" in name or "specular" in name or "roughness" in name:
                score -= 80
            if "alpha" in node.name.lower() and score > 0:
                score -= 5
            if score > 0:
                scored.append((score, node.image))
    if not scored:
        raise RuntimeError("Could not find a diffuse image for face accessory " + source_obj.name)
    # Same file can appear in diffuse and alpha nodes; choose the matching image once.
    scored.sort(key=lambda row: (-row[0], row[1].name.lower()))
    return scored[0][1]


def make_gltf_compatible_accessory_material(suffix, image, uv_map_name):
    """Use one image and explicit UV map; preserve RGBA for translucent brow/lash cards."""
    material = bpy.data.materials.new("V343_GltfCompatibleAccessory_" + suffix)
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    output.location = (420, 40)
    principled = tree.nodes.new("ShaderNodeBsdfPrincipled")
    principled.location = (120, 40)
    principled.inputs["Roughness"].default_value = 0.6
    if "Metallic" in principled.inputs:
        principled.inputs["Metallic"].default_value = 0.0
    uv_node = tree.nodes.new("ShaderNodeUVMap")
    uv_node.uv_map = uv_map_name
    uv_node.location = (-600, 40)
    texture = tree.nodes.new("ShaderNodeTexImage")
    texture.image = image
    texture.interpolation = "Linear"
    texture.extension = "REPEAT"
    texture.location = (-340, 40)
    texture.label = "V343 accessory texture — explicit UV map"
    tree.links.new(uv_node.outputs["UV"], texture.inputs["Vector"])
    tree.links.new(texture.outputs["Color"], principled.inputs["Base Color"])
    alpha_enabled = bool(getattr(image, "channels", 3) >= 4)
    if alpha_enabled and "Alpha" in principled.inputs:
        tree.links.new(texture.outputs["Alpha"], principled.inputs["Alpha"])
        # Blender 4.2+ exposes the transparency mode as surface_render_method.
        if hasattr(material, "surface_render_method"):
            try:
                material.surface_render_method = "BLENDED"
            except Exception:
                pass
    tree.links.new(principled.outputs["BSDF"], output.inputs["Surface"])
    material.diffuse_color = (0.15, 0.12, 0.1, 1.0)
    return material, alpha_enabled


def restore_face_accessory_materials(character_objects, baked_objects, baked_mesh_report):
    suffixes = {"eyebrow001", "eyelashes01", "high-poly", "teeth_base", "tongue01"}
    source_by_name = {obj.name: obj for obj in character_objects}
    baked_by_name = {obj.name: obj for obj in baked_objects}
    report = []
    for row in baked_mesh_report:
        source_name = row["source_object"]
        suffix = source_name.rsplit(".", 1)[-1].lower()
        if suffix not in suffixes:
            continue
        source_obj = source_by_name.get(source_name)
        baked_obj = baked_by_name.get(row["baked_object"])
        if source_obj is None or baked_obj is None:
            raise RuntimeError("Could not map source/baked accessory pair: " + repr(row))
        image = find_face_accessory_diffuse_image(source_obj, suffix)
        uv_name = get_active_uv_name(source_obj)
        if not uv_name:
            raise RuntimeError("No UV map on face accessory " + source_name)
        source_uv_audit = activate_uv_layer(source_obj, uv_name)
        baked_uv_audit = activate_uv_layer(baked_obj, uv_name)
        material, alpha_enabled = make_gltf_compatible_accessory_material(suffix, image, uv_name)
        baked_obj.data.materials.clear()
        baked_obj.data.materials.append(material)
        report.append({
            "source_object": source_name,
            "baked_object": baked_obj.name,
            "suffix": suffix,
            "image_name": image.name,
            "image_channels": int(image.channels),
            "alpha_enabled": alpha_enabled,
            "uv_map_name": uv_name,
            "source_uv_audit": source_uv_audit,
            "baked_uv_audit": baked_uv_audit,
            "export_material": material.name,
        })
    found = {item["suffix"] for item in report}
    if found != suffixes:
        raise RuntimeError("V343 did not restore every expected face accessory. Found " + repr(sorted(found)))
    return report


def main():
    args = parse_args()
    output = os.path.abspath(args.output_dir)
    os.makedirs(output, exist_ok=True)

    # --factory-startup begins with a visible Cube, Camera and Light. The Cube was
    # occluding the lower half of the evidence renders even though it was not exported.
    removed_startup_objects = []
    for obj in list(bpy.context.scene.objects):
        if obj.name in {"Cube", "Camera", "Light"}:
            removed_startup_objects.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)
    bpy.context.view_layer.update()
    if any(name in bpy.data.objects for name in ("Cube", "Camera", "Light")):
        raise RuntimeError("Factory-startup objects remain in the scene: " + repr(removed_startup_objects))

    mpfb_src = os.path.abspath(args.mpfb_src)
    if not os.path.isdir(os.path.join(mpfb_src, "mpfb")):
        raise FileNotFoundError("MPFB source package was not found under " + mpfb_src)
    # Enable MPFB through Blender's own extension/add-on manager. This ensures
    # AddonPreferences is registered and appears in bpy.context.preferences.addons
    # before MPFB services read preferences during import.
    extension_name = "bl_ext.user_default.mpfb"
    if extension_name not in bpy.context.preferences.addons:
        result = bpy.ops.preferences.addon_enable(module=extension_name)
        if "FINISHED" not in result or extension_name not in bpy.context.preferences.addons:
            raise RuntimeError(
                "Blender could not enable the installed MPFB extension. "
                "Ensure it exists in the configured user extension repository. "
                "Operator result: " + repr(result)
            )
    mpfb = importlib.import_module(extension_name)
    from bl_ext.user_default.mpfb.services import AssetService, HumanService, LocationService, TargetService, FaceService, ExportService, ObjectService

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

    # V343 targeted silhouette experiment: shape the skin and garment together before adding face morphs.
    body_shape_adjustment = apply_targeted_body_shape_adjustment(basemesh, clothing_objects)

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

    default_face_pose = apply_default_smile_base_pose(character_objects, strength=0.22)
    skin_materials = style_materials(basemesh, hair_objects, clothing_objects)
    hair_material_audit = prepare_hair_materials(hair_objects)

    skin_image = find_skin_diffuse_image(basemesh)
    skin_node_audit_before = skin_material_node_audit(basemesh, skin_image)
    skin_uv_name, skin_uv_resolution = resolve_skin_uv_name(basemesh, skin_image, skin_node_audit_before)
    skin_uv_activation_source = activate_uv_layer(basemesh, skin_uv_name)
    bpy.context.view_layer.update()
    idle_report = add_idle_animation(rig, bpy.context.scene)

    # Evidence images use studio lighting. The studio floor, lights and cameras are not
    # selected for GLB export.
    bpy.context.view_layer.update()
    character_bounds = world_bounds(character_objects)
    if abs(character_bounds["size"][2] - 1.60) > 0.06:
        raise RuntimeError("Character height outside 1.60 m target after rig/assets: " + repr(character_bounds))
    morphometric_audit = body_profile_audit(basemesh, clothing_objects)
    cameras, floor = setup_studio(bpy.context.scene, character_bounds)
    # Remove the temporary floor mesh entirely; the candidate evidence must not contain
    # a ground-plane line that masks the lower body in an orthographic camera.
    if floor is not None and floor.name in bpy.data.objects:
        bpy.data.objects.remove(floor, do_unlink=True)
    renders = render_evidence(bpy.context.scene, cameras, output, character_bounds)
    bpy.context.scene.frame_set(1)

    # Keep the rigged source for audit, but export evaluated rest-pose meshes so that
    # the browser does not apply an inconsistent inverse-bind matrix. Face morphs survive.
    baked_objects, character_root, baked_idle_report, baked_mesh_report, excluded_face_accessories = bake_character_to_morph_meshes(
        character_objects, bpy.context.scene
    )
    base_baked = next((obj for obj in baked_objects if obj.name.endswith("_Human")), None)
    if base_baked is None:
        raise RuntimeError("Cannot find baked base human mesh to receive glTF-compatible skin material")
    skin_uv_activation_baked = activate_uv_layer(base_baked, skin_uv_name)
    gltf_skin_material = make_gltf_compatible_skin_material(skin_image, skin_uv_name)
    base_baked.data.materials.clear()
    base_baked.data.materials.append(gltf_skin_material)
    skin_node_audit_after = skin_material_node_audit(basemesh, skin_image)
    face_accessory_material_audits = restore_face_accessory_materials(
        character_objects, baked_objects, baked_mesh_report
    )
    glb_path = os.path.join(output, "lam-v343-gltf-materials-full-face-candidate.glb")
    bpy.ops.object.select_all(action="DESELECT")
    for obj in baked_objects:
        obj.select_set(True)
    character_root.select_set(True)
    bpy.context.view_layer.objects.active = character_root
    bpy.ops.export_scene.gltf(
        filepath=glb_path,
        export_format="GLB",
        use_selection=True,
        export_animations=True,
        export_skins=False,
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
    gltf_hair_materials = [
        material for material in gltf.get("materials", [])
        if material.get("name") == "V343_GltfCompatibleHair"
    ]
    if len(gltf_hair_materials) != 1:
        raise RuntimeError("V343 expected exactly one explicit glTF hair material")
    gltf_hair_material = gltf_hair_materials[0]
    gltf_hair_pbr = gltf_hair_material.get("pbrMetallicRoughness", {})
    hair_texture_index = gltf_hair_pbr.get("baseColorTexture", {}).get("index")
    gltf_hair_textures = gltf.get("textures", [])
    gltf_hair_images = gltf.get("images", [])
    texture_row = gltf_hair_textures[hair_texture_index] if hair_texture_index is not None and hair_texture_index < len(gltf_hair_textures) else {}
    hair_image_source_index = texture_row.get("source")
    hair_image_name = gltf_hair_images[hair_image_source_index].get("name", "") if hair_image_source_index is not None and hair_image_source_index < len(gltf_hair_images) else ""
    if hair_image_source_index is None or hair_image_source_index >= len(gltf_hair_images):
        raise RuntimeError("V343 glTF hair texture has no valid embedded image source")
    hair_png_payload, hair_mime_type, embedded_image_label = extract_glb_embedded_image_bytes(
        glb_path, gltf, hair_image_source_index
    )
    if hair_mime_type != "image/png":
        raise RuntimeError("V343 expected embedded PNG hair texture, got " + repr(hair_mime_type))
    embedded_rgb_mean, embedded_alpha_mean = mean_rgb_linear_from_png_bytes(hair_png_payload, output)
    source_rgb_mean = float(hair_material_audit["image"]["source_rgb_mean_linear"])
    processed_rgb_mean = float(hair_material_audit["image"]["processed_rgb_mean_linear"])
    embedded_darkening_verified = embedded_rgb_mean < source_rgb_mean * 0.90
    if not embedded_darkening_verified:
        raise RuntimeError(
            "V343 embedded hair texture is not sufficiently darker than source: "
            + repr({"source_rgb_mean": source_rgb_mean, "embedded_rgb_mean": embedded_rgb_mean})
        )
    if abs(embedded_rgb_mean - processed_rgb_mean) > 0.06:
        raise RuntimeError(
            "V343 embedded hair image pixels do not match the processed source: "
            + repr({"processed_rgb_mean": processed_rgb_mean, "embedded_rgb_mean": embedded_rgb_mean})
        )
    if float(gltf_hair_pbr.get("roughnessFactor", 0.0)) < 0.80:
        raise RuntimeError("V343 hair roughness was not preserved in glTF")
    gltf_hair_material_audit = {
        "name": gltf_hair_material.get("name"),
        "roughness_factor": gltf_hair_pbr.get("roughnessFactor"),
        "alpha_mode": gltf_hair_material.get("alphaMode", "OPAQUE"),
        "base_color_texture_index": hair_texture_index,
        "base_color_image_name": hair_image_name,
        "embedded_image_label": embedded_image_label,
        "embedded_mime_type": hair_mime_type,
        "embedded_rgb_mean_linear": embedded_rgb_mean,
        "embedded_alpha_mean": embedded_alpha_mean,
        "source_rgb_mean_linear": source_rgb_mean,
        "processed_rgb_mean_linear": processed_rgb_mean,
        "embedded_darkening_verified": embedded_darkening_verified,
    }
    if skin_count != 0:
        raise RuntimeError("V343 must export baked geometry without a skin; found " + str(skin_count))
    if not set(EXPECTED_MORPHS).issubset(source_morph_names):
        raise RuntimeError("The exported GLB is missing morph targets: " + repr(missing_morphs))
    if not texture_count or not material_count:
        raise RuntimeError("The exported GLB unexpectedly has no textures/materials")
    if "Lam_Idle_GentleSway" not in animation_names:
        raise RuntimeError("The exported GLB is missing Lam_Idle_GentleSway animation")

    mpfb_repo = Path(mpfb_src).resolve().parent
    mpfb_commit_result = subprocess.run(
        ["git", "-C", str(mpfb_repo), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    )
    mpfb_source_commit = mpfb_commit_result.stdout.strip()

    report = {
        "status": "EXPERIMENTAL_V343_GLTFSKIN_FACE_ACCESSORY_CANDIDATE_NOT_APPROVED",
        "mpfb_source_commit": mpfb_source_commit,
        "version": "V343",
        "purpose": "V343 preserves the V340 body silhouette and tests a luminance-compressed hair diffuse texture with glTF-compatible alpha, UVs, roughness and specular settings.",
        "blender_version": bpy.app.version_string,
        "mpfb_version": list(getattr(mpfb, "VERSION", ())),
        "mpfb_user_data": LocationService.get_user_data(),
        "asset_packs": pack_reports,
        "installed_pack_names": pack_names,
        "skin_asset": skin_path,
        "removed_factory_startup_objects": removed_startup_objects,
        "height_before_scale_m": round(height, 6),
        "height_scale_factor": round(scale_factor, 6),
        "macro_parameters": {
            "gender": macro["gender"],
            "age": macro["age"],
            "muscle": macro["muscle"],
            "weight": macro["weight"],
            "proportions": macro["proportions"],
            "height": macro["height"],
            "cupsize": macro["cupsize"],
            "firmness": macro["firmness"],
            "race": macro["race"],
        },
        "character_bounds_m": character_bounds,
        "morphometric_audit": morphometric_audit,
        "body_shape_adjustment": body_shape_adjustment,
        "source_rig_diagnostic_only": idle_report,
        "idle_animation": baked_idle_report,
        "body_skinning": "Baked neutral evaluated mesh; exported skin_count must be zero; twelve face morphs retained.",
        "baked_mesh_diagnostics": baked_mesh_report,
        "excluded_face_accessories": excluded_face_accessories,
        "face_accessory_material_audits": face_accessory_material_audits,
        "skin_uv_diagnostic": {
            "image_name": skin_image.name,
            "uv_map_name": skin_uv_name,
            "uv_map_resolution": skin_uv_resolution,
            "uv_activation_source": skin_uv_activation_source,
            "baked_uv_activation": skin_uv_activation_baked,
            "source_material_nodes": skin_node_audit_before,
            "source_material_nodes_after_render": skin_node_audit_after,
            "export_material": {
                "name": gltf_skin_material.name,
                "image": skin_image.name,
                "uv_map": skin_uv_name,
                "node_graph": ["UVMap -> Image Texture Vector", "Image Texture Color -> Principled BSDF Base Color", "Principled BSDF -> Material Output"],
            },
        },
        "assets_added": assets_added,
        "skin_materials": skin_materials,
        "hair_material_audit": hair_material_audit,
        "default_face_pose": default_face_pose,
        "gltf_hair_material_audit": gltf_hair_material_audit,
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
            "V343 removes Blender factory-startup Cube/Camera/Light before rendering.",
            "V343 preserves the glTF-compatible skin material and restores all five eye/brow/lash/teeth/tongue meshes with explicit UVMap nodes and simplified materials.",
            "V343 uses evaluated.matrix_world when baking evaluated mesh positions.",
            "V343 uses a real human-topology base mesh rather than procedural sphere/capsule facial anatomy.",
            "The model remains a candidate: photorealism requires human visual comparison against Phi's reference.",
            "The included idle clip is intentionally subtle and skeletal; it is a technical animation, not a complete motion library.",
            "Voice/chat integration is outside this avatar candidate build.",
        ],
    }
    report_path = os.path.join(output, "lam-v343-candidate-report.json")
    Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Save an editable Blender scene alongside the exported GLB and visual evidence.
    scene_path = os.path.join(output, "lam-v343-gltf-materials-full-face-candidate.blend")
    bpy.ops.wm.save_as_mainfile(filepath=scene_path)
    print("V343_REAL_HUMAN_CANDIDATE=" + json.dumps(report, ensure_ascii=False))
    if os.path.getsize(glb_path) < 1_000_000:
        raise RuntimeError("V343 GLB is unexpectedly small for a textured human character")
    if os.path.getsize(glb_path) > 200_000_000:
        raise RuntimeError("V343 GLB is too large for an initial mobile candidate: " + str(os.path.getsize(glb_path)))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
