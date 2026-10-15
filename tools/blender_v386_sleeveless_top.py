#!/usr/bin/env python3
"""V386: build a coherent human-topology Lam candidate with MPFB, real asset materials,
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


def _make_surface_casters(objects):
    """Build world-transform-aware BVHs for projecting wardrobe details."""
    from mathutils.bvhtree import BVHTree

    depsgraph = bpy.context.evaluated_depsgraph_get()
    casters = []
    for obj in objects:
        if obj is None or obj.type != "MESH":
            continue
        evaluated = obj.evaluated_get(depsgraph)
        bvh = BVHTree.FromObject(obj, depsgraph, deform=True, cage=False, epsilon=0.0)
        if bvh is None:
            continue
        casters.append({
            "object": obj,
            "bvh": bvh,
            "matrix": evaluated.matrix_world.copy(),
            "inverse": evaluated.matrix_world.inverted(),
        })
    return casters


def _surface_hit(casters, world_origin, world_direction, max_distance=3.0):
    """Return the closest ray hit transformed into world coordinates."""
    world_origin = Vector(world_origin)
    world_direction = Vector(world_direction).normalized()
    best = None
    for caster in casters:
        inverse = caster["inverse"]
        matrix = caster["matrix"]
        local_origin = inverse @ world_origin
        local_direction = inverse.to_3x3() @ world_direction
        if local_direction.length <= 1e-10:
            continue
        local_direction.normalize()
        location, normal, face_index, _local_distance = caster["bvh"].ray_cast(
            local_origin, local_direction, max_distance
        )
        if location is None or normal is None:
            continue
        world_location = matrix @ location
        distance = (world_location - world_origin).dot(world_direction)
        if distance < -1e-5 or distance > max_distance:
            continue
        normal_matrix = matrix.to_3x3().inverted().transposed()
        world_normal = normal_matrix @ normal
        if world_normal.length <= 1e-10:
            continue
        world_normal.normalize()
        if best is None or distance < best["distance_m"]:
            best = {
                "location": world_location,
                "normal": world_normal,
                "distance_m": float(distance),
                "face_index": int(face_index),
                "source_object": caster["object"].name,
            }
    return best


def _surface_hit_outermost(casters, world_origin, world_direction, max_distance=2.0):
    """From a centerline origin, choose the outermost hit across body and clothes.

    This differs from _surface_hit (nearest from origin): waist belt samples
    begin inside the character and travel outward, so the furthest first-hit
    among the body and clothing objects represents the visible outer surface.
    """
    world_origin = Vector(world_origin)
    world_direction = Vector(world_direction).normalized()
    best = None
    for caster in casters:
        inverse = caster["inverse"]
        matrix = caster["matrix"]
        local_origin = inverse @ world_origin
        local_direction = inverse.to_3x3() @ world_direction
        if local_direction.length <= 1e-10:
            continue
        local_direction.normalize()
        location, normal, face_index, _local_distance = caster["bvh"].ray_cast(
            local_origin, local_direction, max_distance
        )
        if location is None or normal is None:
            continue
        world_location = matrix @ location
        distance = (world_location - world_origin).dot(world_direction)
        if distance < -1e-5 or distance > max_distance:
            continue
        normal_matrix = matrix.to_3x3().inverted().transposed()
        world_normal = normal_matrix @ normal
        if world_normal.length <= 1e-10:
            continue
        world_normal.normalize()
        if best is None or distance > best["distance_m"]:
            best = {
                "location": world_location,
                "normal": world_normal,
                "distance_m": float(distance),
                "face_index": int(face_index),
                "source_object": caster["object"].name,
            }
    return best



def _make_solid_material(name, color, metallic=0.0, roughness=0.8, specular=0.2):
    material = bpy.data.materials.new(name)
    material.diffuse_color = tuple(color)
    material.use_nodes = True
    principled = next((node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"), None)
    if principled:
        inputs = principled.inputs
        inputs["Base Color"].default_value = tuple(color)
        inputs["Metallic"].default_value = float(metallic)
        inputs["Roughness"].default_value = float(roughness)
        if "Specular IOR Level" in inputs:
            inputs["Specular IOR Level"].default_value = float(specular)
    return material


def _create_mesh_object(scene, name, vertices, faces, material, smooth=False):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.validate(verbose=False)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    if material:
        obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = bool(smooth)
    return obj


def _create_box_object(scene, name, center, size, material):
    cx, cy, cz = [float(value) for value in center]
    sx, sy, sz = [float(value) for value in size]
    verts = [
        (cx-sx/2, cy-sy/2, cz-sz/2), (cx+sx/2, cy-sy/2, cz-sz/2),
        (cx+sx/2, cy-sy/2, cz+sz/2), (cx-sx/2, cy-sy/2, cz+sz/2),
        (cx-sx/2, cy+sy/2, cz-sz/2), (cx+sx/2, cy+sy/2, cz-sz/2),
        (cx+sx/2, cy+sy/2, cz+sz/2), (cx-sx/2, cy+sy/2, cz+sz/2),
    ]
    faces = [
        (0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1),
        (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0),
    ]
    return _create_mesh_object(scene, name, verts, faces, material, smooth=False)


def _create_rectangular_buckle(scene, center, material):
    """Build a true 3D rectangular metal buckle ring with an open center."""
    cx, cy, cz = [float(value) for value in center]
    outer_w, outer_h = 0.043, 0.027
    inner_w, inner_h = 0.033, 0.017
    depth = 0.0032
    y_front = cy - depth / 2
    y_back = cy + depth / 2

    def loop(width, height, y):
        return [
            (cx-width/2, y, cz-height/2),
            (cx+width/2, y, cz-height/2),
            (cx+width/2, y, cz+height/2),
            (cx-width/2, y, cz+height/2),
        ]

    outer_front = loop(outer_w, outer_h, y_front)
    inner_front = loop(inner_w, inner_h, y_front)
    outer_back = loop(outer_w, outer_h, y_back)
    inner_back = loop(inner_w, inner_h, y_back)
    verts = outer_front + inner_front + outer_back + inner_back
    faces = []
    for index in range(4):
        nxt = (index + 1) % 4
        # Front/back ring faces, then outer and inner walls.
        faces.append((index, nxt, 4+nxt, 4+index))
        faces.append((8+index, 12+index, 12+nxt, 8+nxt))
        faces.append((index, 8+index, 8+nxt, nxt))
        faces.append((4+index, 4+nxt, 12+nxt, 12+index))
    return _create_mesh_object(scene, "V386_Wardrobe_BuckleFrame", verts, faces, material, smooth=False)


def _create_surface_panel(scene, name, surface_casters, center_x, center_z, width, height,
                          material, columns=6, rows=7, front_offset=0.0030, thickness=0.0014):
    """Build a small front-facing cargo panel conformed to the existing trouser surface."""
    hits = []
    missing = []
    for row in range(rows + 1):
        z = center_z + height/2 - height * row / rows
        for column in range(columns + 1):
            x = center_x - width/2 + width * column / columns
            hit = _surface_hit(
                surface_casters,
                Vector((x, -0.70, z)),
                Vector((0.0, 1.0, 0.0)),
                max_distance=2.0,
            )
            if hit is None:
                hits.append(None)
                missing.append({"x_m": round(x, 5), "z_m": round(z, 5)})
            else:
                hits.append(hit)
    expected = (rows + 1) * (columns + 1)
    valid_count = expected - len(missing)
    if valid_count < int(expected * 0.92):
        raise RuntimeError(
            "V386 cargo panel cannot be projected onto garment surface: "
            + repr({"name": name, "valid_hits": valid_count, "expected": expected, "missing": missing[:12]})
        )
    # A few boundary samples can miss at a sharply tapered seam. Fill only those
    # from the nearest valid grid neighbor and record the count in the audit.
    valid_indices = [i for i, hit in enumerate(hits) if hit is not None]
    for i, hit in enumerate(hits):
        if hit is not None:
            continue
        row, column = divmod(i, columns + 1)
        nearest = min(
            valid_indices,
            key=lambda j: abs(divmod(j, columns + 1)[0]-row) + abs(divmod(j, columns + 1)[1]-column),
        )
        hits[i] = hits[nearest]

    vertices = []
    for hit in hits:
        loc = hit["location"]
        normal = hit["normal"]
        vertices.append(tuple(loc + normal * front_offset))
    front_count = len(vertices)
    for hit in hits:
        loc = hit["location"]
        normal = hit["normal"]
        vertices.append(tuple(loc + normal * (front_offset - thickness)))

    faces = []
    stride = columns + 1
    for row in range(rows):
        for column in range(columns):
            a = row * stride + column
            b = a + 1
            d = (row + 1) * stride + column
            c = d + 1
            # The camera looks from -Y; this order orients the front toward it.
            faces.append((a, d, c, b))
            faces.append((front_count+b, front_count+c, front_count+d, front_count+a))
    # Side walls only around the outer panel boundary. Interior grid cells
    # share edges and must not receive duplicate coplanar walls.
    for row in range(rows):
        left_top = row * stride
        left_bottom = (row + 1) * stride
        right_top = row * stride + columns
        right_bottom = (row + 1) * stride + columns
        faces.append((left_top, front_count+left_top, front_count+left_bottom, left_bottom))
        faces.append((right_top, right_bottom, front_count+right_bottom, front_count+right_top))
    for column in range(columns):
        a = column
        b = a + 1
        faces.append((a, b, front_count+b, front_count+a))
        a = rows * stride + column
        b = a + 1
        faces.append((a, front_count+a, front_count+b, b))
    obj = _create_mesh_object(scene, name, vertices, faces, material, smooth=False)
    return obj, {
        "object": obj.name,
        "vertex_count": len(vertices),
        "polygon_count": len(faces),
        "ray_samples_expected": expected,
        "ray_samples_hit": valid_count,
        "ray_samples_filled": len(missing),
        "hit_fraction": round(valid_count / expected, 5),
        "center_x_m": round(float(center_x), 5),
        "center_z_m": round(float(center_z), 5),
        "size_x_m": round(float(width), 5),
        "size_z_m": round(float(height), 5),
        "front_offset_m": round(float(front_offset), 5),
        "surface_object_names": sorted({hit["source_object"] for hit in hits}),
    }


def create_wardrobe_details(scene, basemesh, clothing_objects):
    """Add a black belt, silver rectangular buckle, and mirrored cargo pockets.

    Geometry only: projects to existing body/trouser surfaces, retains V367 colors,
    and does not alter the face, hair, body proportions, morph definitions or clothing textures.
    """
    bpy.context.view_layer.update()
    all_casters = _make_surface_casters([basemesh] + list(clothing_objects))
    outfit_objects = [obj for obj in clothing_objects if "female_sportsuit01" in obj.name.lower()]
    if len(outfit_objects) != 1:
        raise RuntimeError("V386 needs exactly one sportsuit garment mesh for cargo-pocket projection")
    trouser_casters = _make_surface_casters(outfit_objects)

    belt_material = _make_solid_material("V386_MatteBlackBelt", (0.012, 0.011, 0.013, 1.0), 0.0, 0.78, 0.15)
    pocket_material = _make_solid_material("V386_CargoPocketCharcoal", (0.055, 0.058, 0.062, 1.0), 0.0, 0.90, 0.15)
    flap_material = _make_solid_material("V386_CargoFlapCharcoal", (0.080, 0.083, 0.088, 1.0), 0.0, 0.88, 0.16)
    buckle_material = _make_solid_material("V386_BuckleSilver", (0.52, 0.55, 0.60, 1.0), 0.78, 0.28, 0.42)
    stitch_material = _make_solid_material("V386_BucklePinSilver", (0.30, 0.33, 0.38, 1.0), 0.72, 0.32, 0.38)

    # Search from the character centerline outward and select the outermost
    # surface hit among skin and outfit. The T-pose arms cannot be chosen first
    # from an outside-in ray, and the visible abdomen/clothing surface is used.
    sample_count = 64
    belt_height = 0.040
    half_belt_height = belt_height / 2.0
    candidate_centers = [round(0.780 + index * 0.005, 5) for index in range(23)]
    belt_candidate_audit = []
    eligible_belt_rings = []
    allowed_belt_sources = {basemesh.name, outfit_objects[0].name}

    for candidate_center_z in candidate_centers:
        candidate_bottom_z = round(candidate_center_z - half_belt_height, 5)
        candidate_top_z = round(candidate_center_z + half_belt_height, 5)
        candidate_bottom, candidate_top = [], []
        candidate_missing = []
        for index in range(sample_count):
            theta = (2.0 * math.pi * index) / sample_count
            radial_x, radial_y = math.cos(theta), math.sin(theta)
            center_origin_bottom = Vector((0.0, 0.0, candidate_bottom_z))
            center_origin_top = Vector((0.0, 0.0, candidate_top_z))
            radial_direction = Vector((radial_x, radial_y, 0.0))
            bottom_hit = _surface_hit_outermost(
                all_casters, center_origin_bottom, radial_direction, max_distance=0.65
            )
            top_hit = _surface_hit_outermost(
                all_casters, center_origin_top, radial_direction, max_distance=0.65
            )
            if bottom_hit is None or top_hit is None:
                candidate_missing.append(index)
            candidate_bottom.append(bottom_hit)
            candidate_top.append(top_hit)

        valid_pairs = sample_count - len(candidate_missing)
        all_hits = [hit for hit in candidate_bottom + candidate_top if hit is not None]
        hit_sources = sorted({hit["source_object"] for hit in all_hits})
        max_abs_x = max((abs(float(hit["location"].x)) for hit in all_hits), default=0.0)
        is_eligible = (
            valid_pairs >= 60
            and bool(hit_sources)
            and set(hit_sources).issubset(allowed_belt_sources)
            and max_abs_x <= 0.30
        )
        belt_candidate_audit.append({
            "center_z_m": candidate_center_z,
            "bottom_z_m": candidate_bottom_z,
            "top_z_m": candidate_top_z,
            "valid_pairs": valid_pairs,
            "missing_samples": len(candidate_missing),
            "source_names": hit_sources,
            "max_abs_x_m": round(float(max_abs_x), 5),
            "eligible": is_eligible,
        })
        if is_eligible:
            eligible_belt_rings.append({
                "center_z": candidate_center_z,
                "bottom_z": candidate_bottom_z,
                "top_z": candidate_top_z,
                "bottom_hits": candidate_bottom,
                "top_hits": candidate_top,
                "missing": candidate_missing,
                "valid_pairs": valid_pairs,
                "source_names": hit_sources,
                "max_abs_x": max_abs_x,
            })

    if not eligible_belt_rings:
        raise RuntimeError("V386 could not find an outward-visible waistband ring within width bounds: " + repr({
            "candidate_centers_m": candidate_centers,
            "belt_candidate_audit": belt_candidate_audit,
            "allowed_belt_sources": sorted(allowed_belt_sources),
        }))

    # Use the highest level where skin/garment outer surfaces form a complete
    # ring. Its front edge sits on the visible abdomen surface instead of behind it.
    selected_ring = eligible_belt_rings[-1]
    belt_center_z = selected_ring["center_z"]
    belt_bottom_z = selected_ring["bottom_z"]
    belt_top_z = selected_ring["top_z"]
    belt_samples_bottom = selected_ring["bottom_hits"]
    belt_samples_top = selected_ring["top_hits"]
    missing_belt_hits = selected_ring["missing"]
    valid_belt_hits = selected_ring["valid_pairs"]
    belt_hit_sources = selected_ring["source_names"]
    belt_hit_max_abs_x = selected_ring["max_abs_x"]

    belt_vertices = []
    for bottom_hit, top_hit in zip(belt_samples_bottom, belt_samples_top):
        if bottom_hit is None:
            bottom_hit = min(
                (hit for hit in belt_samples_bottom if hit is not None),
                key=lambda hit: abs(hit["location"].z - belt_bottom_z),
            )
        if top_hit is None:
            top_hit = min(
                (hit for hit in belt_samples_top if hit is not None),
                key=lambda hit: abs(hit["location"].z - belt_top_z),
            )
        belt_vertices.extend([
            tuple(bottom_hit["location"] + bottom_hit["normal"] * 0.0022),
            tuple(top_hit["location"] + top_hit["normal"] * 0.0022),
            tuple(bottom_hit["location"] + bottom_hit["normal"] * 0.0005),
            tuple(top_hit["location"] + top_hit["normal"] * 0.0005),
        ])
    belt_faces = []
    for index in range(sample_count):
        next_index = (index + 1) % sample_count
        b0, t0, bi0, ti0 = [4 * index + k for k in range(4)]
        b1, t1, bi1, ti1 = [4 * next_index + k for k in range(4)]
        belt_faces.extend([
            (b0, b1, t1, t0), (bi1, bi0, ti0, ti1),
            (t0, t1, ti1, ti0), (b1, b0, bi0, bi1),
            (b0, t0, ti0, bi0),
        ])
    belt_obj = _create_mesh_object(scene, "V386_Wardrobe_BeltStrap", belt_vertices, belt_faces, belt_material, smooth=True)

    # Cover only the two small skin-colored gaps below the belt, rather than
    # wrapping the entire waist in a second band. These tiny panels follow the
    # visible outermost skin/trouser surface and tuck their top edge under the belt.
    waist_gap_patch_material = _make_solid_material(
        "V386_WaistGapPatchCharcoal", (0.045, 0.047, 0.052, 1.0), 0.0, 0.90, 0.12
    )
    waist_gap_patch_objects = []
    waist_gap_patch_reports = []
    patch_center_z = round(belt_bottom_z - 0.010, 5)
    patch_width = 0.029
    patch_height = 0.022
    for side_name, side_sign in (("Left", -1.0), ("Right", 1.0)):
        panel, panel_audit = _create_surface_panel(
            scene, "V386_WaistGapPatch_" + side_name,
            all_casters,
            side_sign * 0.135, patch_center_z, patch_width, patch_height,
            waist_gap_patch_material,
            columns=4, rows=3, front_offset=0.0026, thickness=0.0012,
        )
        source_names = set(panel_audit["surface_object_names"])
        if not source_names or not source_names.issubset(allowed_belt_sources):
            raise RuntimeError("V386 waist-gap patch hit an unexpected surface: " + repr({
                "side": side_name, "surface_sources": sorted(source_names),
                "allowed": sorted(allowed_belt_sources),
            }))
        if panel_audit["hit_fraction"] < 0.92:
            raise RuntimeError("V386 waist-gap patch did not sufficiently conform: " + repr(panel_audit))
        waist_gap_patch_objects.append(panel)
        waist_gap_patch_reports.append({
            "side": side_name,
            **panel_audit,
            "allowed_source_names": sorted(allowed_belt_sources),
            "material": waist_gap_patch_material.name,
            "belt_lower_edge_z_m": round(float(belt_bottom_z), 5),
            "patch_top_z_m": round(float(patch_center_z + patch_height / 2.0), 5),
            "top_tucks_under_belt": (patch_center_z + patch_height / 2.0) < belt_bottom_z + 0.002,
        })

    waist_gap_patch_audit = {
        "status": "APPLIED",
        "purpose": "Two local surface-conformed charcoal patches cover the small skin-colored triangles below the belt; no circumferential waistband bridge is added.",
        "patch_count": len(waist_gap_patch_objects),
        "center_z_m": patch_center_z,
        "size_x_m": patch_width,
        "size_z_m": patch_height,
        "surface_method": "front-facing ray grid to outermost visible body/trouser surface",
        "patches": waist_gap_patch_reports,
        "material": waist_gap_patch_material.name,
        "scope": "two local front/side waist-gap patches only; belt center, belt width, buckle, body, textures and trouser geometry unchanged",
    }

    # Buckle uses the same outward-visible surface and z as the selected belt ring.
    buckle_hit = _surface_hit_outermost(
        all_casters,
        Vector((0.0, 0.0, belt_center_z)),
        Vector((0.0, -1.0, 0.0)),
        max_distance=0.65,
    )
    if buckle_hit is None or buckle_hit["source_object"] not in allowed_belt_sources:
        raise RuntimeError("V386 could not locate the visible front waist surface at selected belt height: " + repr({
            "belt_center_z_m": belt_center_z,
            "allowed_sources": sorted(allowed_belt_sources),
            "actual_source": buckle_hit["source_object"] if buckle_hit else None,
        }))
    buckle_center = Vector((0.0, buckle_hit["location"].y - 0.0035, belt_center_z))
    buckle_frame = _create_rectangular_buckle(scene, buckle_center, buckle_material)
    buckle_pin = _create_box_object(
        scene, "V386_Wardrobe_BucklePin",
        (0.0, buckle_center.y - 0.0019, belt_center_z),
        (0.017, 0.0014, 0.0020), stitch_material,
    )

    pocket_reports = []
    pocket_objects = []
    pocket_center_x = 0.118
    pocket_center_z = 0.600
    pocket_width = 0.086
    pocket_height = 0.105
    for side, sign in (("Left", -1.0), ("Right", 1.0)):
        center_x = sign * pocket_center_x
        panel, panel_audit = _create_surface_panel(
            scene, "V386_CargoPocket_" + side + "_Panel", trouser_casters,
            center_x, pocket_center_z, pocket_width, pocket_height,
            pocket_material, columns=6, rows=7, front_offset=0.0030, thickness=0.0015,
        )
        flap, flap_audit = _create_surface_panel(
            scene, "V386_CargoPocket_" + side + "_Flap", trouser_casters,
            center_x, pocket_center_z + pocket_height/2 - 0.009, pocket_width * 0.96, 0.027,
            flap_material, columns=6, rows=2, front_offset=0.0050, thickness=0.0017,
        )
        # A small dark-silver snap makes the flap closure readable without bright ornament.
        snap_hit = _surface_hit(
            trouser_casters,
            Vector((center_x, -0.70, pocket_center_z + pocket_height/2 - 0.021)),
            Vector((0.0, 1.0, 0.0)),
            max_distance=2.0,
        )
        snap_obj = None
        if snap_hit:
            snap_obj = _create_box_object(
                scene, "V386_CargoPocket_" + side + "_Snap",
                (center_x, snap_hit["location"].y - 0.0060, pocket_center_z + pocket_height/2 - 0.021),
                (0.006, 0.0018, 0.006), stitch_material,
            )
            pocket_objects.append(snap_obj)
        pocket_objects.extend([panel, flap])
        pocket_reports.append({
            "side": side.lower(),
            "panel": panel_audit,
            "flap": flap_audit,
            "snap_object": snap_obj.name if snap_obj else None,
        })

    # The remaining pale ankle patches sit below the old cuff start. Keep the cuff height
    # at 12 cm but shift it down to bridge that strip and overlap the sneaker collar,
    # while ray-conforming to the visible garment/shoe surface.
    cuff_material = _make_solid_material(
        "V386_AnkleCuffCharcoal", (0.035, 0.037, 0.040, 1.0), 0.0, 0.90, 0.13
    )
    cuff_z_bottom = 0.125
    cuff_z_top = 0.245
    cuff_height = cuff_z_top - cuff_z_bottom
    cuff_sample_count = 64
    body_matrix = basemesh.matrix_world.copy()
    body_world_points = [body_matrix @ vertex.co for vertex in basemesh.data.vertices]
    allowed_cuff_sources = {basemesh.name, outfit_objects[0].name} | {obj.name for obj in clothing_objects if "shoes06" in obj.name.lower()}

    def estimate_leg_centerline(side_sign, target_z):
        expected_x = side_sign * 0.14
        nearby = [
            point for point in body_world_points
            if abs(point.z - target_z) <= 0.025
            and abs(point.x - expected_x) <= 0.085
        ]
        if len(nearby) < 12:
            raise RuntimeError("V386 cannot estimate lower-leg centerline: " + repr({
                "side_sign": side_sign, "target_z_m": target_z, "vertices": len(nearby),
            }))
        x_values = sorted(point.x for point in nearby)
        center_x = float(x_values[len(x_values) // 2])
        y_values = [float(point.y) for point in nearby]
        center_y = (min(y_values) + max(y_values)) / 2.0
        return center_x, center_y, len(nearby)

    ankle_cuff_objects = []
    ankle_cuff_reports = []
    for side_name, side_sign in (("Left", -1.0), ("Right", 1.0)):
        bottom_center = estimate_leg_centerline(side_sign, cuff_z_bottom)
        top_center = estimate_leg_centerline(side_sign, cuff_z_top)
        bottom_hits, top_hits, missing_indices = [], [], []
        for index in range(cuff_sample_count):
            theta = (2.0 * math.pi * index) / cuff_sample_count
            radial_x, radial_y = math.cos(theta), math.sin(theta)
            radial_direction = Vector((radial_x, radial_y, 0.0))
            bottom_hit = _surface_hit_outermost(
                all_casters,
                Vector((bottom_center[0], bottom_center[1], cuff_z_bottom)),
                radial_direction,
                max_distance=0.16,
            )
            top_hit = _surface_hit_outermost(
                all_casters,
                Vector((top_center[0], top_center[1], cuff_z_top)),
                radial_direction,
                max_distance=0.16,
            )
            if bottom_hit is None or top_hit is None:
                missing_indices.append(index)
            bottom_hits.append(bottom_hit)
            top_hits.append(top_hit)

        valid_pairs = cuff_sample_count - len(missing_indices)
        if valid_pairs < 60:
            raise RuntimeError("V386 ankle cuff cannot follow the leg surface: " + repr({
                "side": side_name, "valid_pairs": valid_pairs,
                "missing_samples": len(missing_indices),
                "z_range_m": [cuff_z_bottom, cuff_z_top],
            }))
        all_hits = [hit for hit in bottom_hits + top_hits if hit is not None]
        cuff_sources = sorted({hit["source_object"] for hit in all_hits})
        if not cuff_sources or not set(cuff_sources).issubset(allowed_cuff_sources):
            raise RuntimeError("V386 ankle cuff hit an unexpected object: " + repr({
                "side": side_name, "sources": cuff_sources,
                "allowed": sorted(allowed_cuff_sources),
            }))
        max_radius = max(
            (
                math.sqrt(
                    (hit["location"].x - center[0]) ** 2
                    + (hit["location"].y - center[1]) ** 2
                )
                for hits, center in ((bottom_hits, bottom_center), (top_hits, top_center))
                for hit in hits if hit is not None
            ),
            default=0.0,
        )
        if max_radius > 0.13:
            raise RuntimeError("V386 ankle cuff radius exceeded its lower-leg guard: " + repr({
                "side": side_name, "max_radius_m": max_radius, "limit_m": 0.13,
                "sources": cuff_sources,
            }))

        for index, hit in enumerate(bottom_hits):
            if hit is None:
                bottom_hits[index] = min(
                    (candidate for candidate in bottom_hits if candidate is not None),
                    key=lambda candidate: candidate["location"].x,
                )
        for index, hit in enumerate(top_hits):
            if hit is None:
                top_hits[index] = min(
                    (candidate for candidate in top_hits if candidate is not None),
                    key=lambda candidate: candidate["location"].x,
                )
        cuff_vertices = []
        for bottom_hit, top_hit in zip(bottom_hits, top_hits):
            cuff_vertices.extend([
                tuple(bottom_hit["location"] + bottom_hit["normal"] * 0.0022),
                tuple(top_hit["location"] + top_hit["normal"] * 0.0022),
                tuple(bottom_hit["location"] + bottom_hit["normal"] * 0.0005),
                tuple(top_hit["location"] + top_hit["normal"] * 0.0005),
            ])
        cuff_faces = []
        for index in range(cuff_sample_count):
            next_index = (index + 1) % cuff_sample_count
            b0, t0, bi0, ti0 = [4 * index + k for k in range(4)]
            b1, t1, bi1, ti1 = [4 * next_index + k for k in range(4)]
            cuff_faces.extend([
                (b0, b1, t1, t0), (bi1, bi0, ti0, ti1),
                (t0, t1, ti1, ti0), (b1, b0, bi0, bi1),
                (b0, t0, ti0, bi0),
            ])
        cuff_obj = _create_mesh_object(
            scene, "V386_AnkleCover_" + side_name, cuff_vertices, cuff_faces, cuff_material, smooth=True
        )
        ankle_cuff_objects.append(cuff_obj)
        ankle_cuff_reports.append({
            "side": side_name,
            "object": cuff_obj.name,
            "z_range_m": [cuff_z_bottom, cuff_z_top],
            "height_m": round(cuff_height, 5),
            "sample_count": cuff_sample_count,
            "surface_hits": valid_pairs,
            "missing_samples": len(missing_indices),
            "surface_source_names": cuff_sources,
            "centerline_bottom_m": [round(bottom_center[0], 5), round(bottom_center[1], 5)],
            "centerline_top_m": [round(top_center[0], 5), round(top_center[1], 5)],
            "max_radial_extent_m": round(float(max_radius), 5),
            "radial_extent_guard_m": 0.13,
            "centerline_estimate_vertices": [bottom_center[2], top_center[2]],
            "material": cuff_material.name,
        })

    ankle_patch_cover_audit = {
        "status": "APPLIED",
        "working_hypothesis": "The embedded sportsuit pants texture is uniformly charcoal in the affected UV regions; pale shin marks appear to be skin/clothing overlap or coverage gaps rather than painted bright texture patches.",
        "treatment": "Two 12 cm surface-conformed charcoal lower-leg cuffs are shifted downward to z 0.125–0.245 m, covering the pale ankle strip and meeting the sneaker collar. Source ray hits still determine the outer surface; body mesh and skin material remain unchanged.",
        "z_range_m": [cuff_z_bottom, cuff_z_top],
        "cuff_count": len(ankle_cuff_objects),
        "cuffs": ankle_cuff_reports,
    }

    detail_objects = [belt_obj, buckle_frame, buckle_pin] + waist_gap_patch_objects + pocket_objects + ankle_cuff_objects
    bpy.context.view_layer.update()
    return detail_objects, {
        "status": "APPLIED",
        "reference_name": "Bảng giới thiệu nhân vật Lý Lâm Lam.png",
        "reference_sha256": "0be925c095166289727c597690b57ed31d23fcbf0a77f7f517d1928098f3c575",
        "scope": "V386 preserves the V373 ankle cuffs and existing belt/pockets, adding two small surface-conformed trouser-charcoal patches at the skin-colored gaps below the belt; face, hair, body mesh, skin texture, belt dimensions, morphs and animation remain unchanged",
        "belt": {
            "object": belt_obj.name,
            "sample_count": sample_count,
            "surface_hits": valid_belt_hits,
            "missing_samples": len(missing_belt_hits),
            "surface_source_names": belt_hit_sources,
            "max_abs_x_m": round(float(belt_hit_max_abs_x), 5),
            "source_mesh_method": "body_and_garment_outermost",
            "allowed_source_names": sorted(allowed_belt_sources),
            "sampling_method": "centerline origin, outward radial rays, outermost visible hit among skin and clothing",
            "wide_hit_guard_m": 0.30,
            "center_z_m": round(float(belt_center_z), 5),
            "candidate_search_count": len(belt_candidate_audit),
            "eligible_ring_centers_m": [ring["center_z"] for ring in eligible_belt_rings],
            "candidate_audit": belt_candidate_audit,
            "z_range_m": [belt_bottom_z, belt_top_z],
            "strap_height_m": round(belt_top_z - belt_bottom_z, 5),
            "material": belt_material.name,
        },
        "waist_gap_patch_audit": waist_gap_patch_audit,
        "buckle": {
            "frame_object": buckle_frame.name,
            "pin_object": buckle_pin.name,
            "front_surface_hit": True,
            "center_z_m": round(float(belt_center_z), 5),
            "surface_source": buckle_hit["source_object"],
            "frame_size_m": [0.043, 0.027],
            "material": buckle_material.name,
        },
        "cargo_pockets": pocket_reports,
        "ankle_patch_cover_audit": ankle_patch_cover_audit,
        "objects_added": [obj.name for obj in detail_objects],
        "visual_warning": "First-pass flat conformed pocket panels only; assess whether they read as cargo pockets and remain attached in front/side renders.",
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
    profile_points = body_points + garment_points
    if len(body_points) < 100 or len(profile_points) < 100:
        raise RuntimeError("Too few body/clothing vertices for V386 dressed-profile audit")
    # Wardrobe/mask helpers can hide lower-body skin vertices. Use the union of
    # base skin plus clothing/shoes for z bounds, otherwise thigh bands drift
    # upward when the exposed skin mesh ends at the shorts/trouser hem.
    z_min = min(point.z for point in profile_points)
    z_max = max(point.z for point in profile_points)
    height = z_max - z_min
    if height <= 0:
        raise RuntimeError("Invalid dressed-character height in V386 morphometric audit")

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
        actual_source = source
        slab = [point for point in candidates if z_low <= point.z <= z_high]
        if x_limit is not None:
            slab = [point for point in slab if abs(point.x) <= x_limit]
        # The V386 outfit is a different garment asset; if a crop hem leaves a
        # height band uncovered, measure the visible body there instead of
        # falsely failing due to absent clothing vertices.
        if len(slab) < 20 and source == "clothing":
            candidates = body_points + garment_points
            slab = [point for point in candidates if z_low <= point.z <= z_high]
            if x_limit is not None:
                slab = [point for point in slab if abs(point.x) <= x_limit]
            actual_source = "skin_or_clothing_fallback"
        if len(slab) < 20:
            regions[name] = {
                "status": "INSUFFICIENT_VERTICES",
                "vertex_count": len(slab),
                "source": actual_source,
                "central_x_limit_m": x_limit,
                "z_band_m": [round(z_low, 5), round(z_high, 5)],
            }
            continue
        abs_x = [abs(point.x) for point in slab]
        y_values = [point.y for point in slab]
        regions[name] = {
            "status": "MEASURED",
            "vertex_count": len(slab),
            "source": actual_source,
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
        "height_method": "union of body skin plus wardrobe/shoe mesh world-space bounds; needed because garment masks hide portions of lower-body skin",
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
        raise RuntimeError("V386 requires clothing geometry to keep the dressed silhouette continuous")

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



def _v386_smooth_unit(value):
    """Cubic smoothstep for a clamped 0..1 weight."""
    value = max(0.0, min(1.0, float(value)))
    return value * value * (3.0 - 2.0 * value)



def remove_short_sleeve_components(clothing_objects):
    """Trim integrated short sleeves with a measured band and conservative validation.

    The MPFB sportsuit shirt and sleeves are a single connected shell, so the
    sleeve surfaces are cut directly. The builder accepts the result only when
    the remaining upper-shirt region and trouser region are both present, the
    upper outline measurably narrows, both sides receive comparable cuts, and
    mesh-count arithmetic is consistent. No unrelated disconnected region is
    deleted speculatively.
    """
    import bmesh

    outfits = [
        obj for obj in clothing_objects
        if obj.type == "MESH" and "female_sportsuit01" in obj.name.lower()
    ]
    if len(outfits) != 1:
        raise RuntimeError("V386 requires exactly one Human.female_sportsuit01 mesh: " + repr([o.name for o in outfits]))
    obj = outfits[0]
    shape_keys = getattr(obj.data, "shape_keys", None)
    if shape_keys is not None and len(shape_keys.key_blocks):
        raise RuntimeError("V386 sleeve trim refuses to edit a garment mesh with shape keys")

    mesh = obj.data
    matrix = obj.matrix_world.copy()
    vertex_count_before = len(mesh.vertices)
    face_count_before = len(mesh.polygons)

    def world_point(index):
        point = matrix @ mesh.vertices[index].co
        return (float(point.x), float(point.y), float(point.z))

    def connected_components(current_mesh):
        adjacency = [set() for _ in current_mesh.vertices]
        for polygon in current_mesh.polygons:
            ids = list(polygon.vertices)
            for a, b in zip(ids, ids[1:] + ids[:1]):
                adjacency[a].add(b)
                adjacency[b].add(a)

        visited = set()
        result = []
        for seed in range(len(current_mesh.vertices)):
            if seed in visited or not adjacency[seed]:
                continue
            stack = [seed]
            visited.add(seed)
            indices = []
            while stack:
                current = stack.pop()
                indices.append(current)
                for neighbor in adjacency[current]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        stack.append(neighbor)

            index_set = set(indices)
            points = [world_point(index) for index in indices]
            min_x = min(point[0] for point in points)
            max_x = max(point[0] for point in points)
            min_y = min(point[1] for point in points)
            max_y = max(point[1] for point in points)
            min_z = min(point[2] for point in points)
            max_z = max(point[2] for point in points)
            face_count = sum(
                1 for polygon in current_mesh.polygons
                if all(index in index_set for index in polygon.vertices)
            )
            result.append({
                "component_index": len(result),
                "vertex_count": len(indices),
                "face_count": face_count,
                "bounds_world_m": {
                    "min": [round(min_x, 6), round(min_y, 6), round(min_z, 6)],
                    "max": [round(max_x, 6), round(max_y, 6), round(max_z, 6)],
                },
                "max_abs_x_m": round(max(abs(min_x), abs(max_x)), 6),
                "height_m": round(max_z - min_z, 6),
            })
        return result

    components_before = connected_components(mesh)
    cut_profile = [
        # Carry the fabric farther over the upper arm near the underarm opening,
        # then taper the shoulder tip instead of leaving an outward-pointing flap.
        (1.095, 0.210),
        (1.115, 0.210),
        (1.135, 0.215),
        (1.165, 0.215),
        (1.200, 0.220),
        (1.235, 0.220),
        (1.265, 0.225),
        (1.290, 0.235),
        (1.310, 0.240),
        (1.325, 0.240),
        (1.340, 0.225),
        (1.355, 0.195),
        (1.370, 0.165),
        (1.380, 0.145),
    ]

    def lateral_limit(z_value):
        if z_value < cut_profile[0][0] or z_value > cut_profile[-1][0]:
            return None
        for (z0, x0), (z1, x1) in zip(cut_profile, cut_profile[1:]):
            if z0 <= z_value <= z1:
                fraction = (z_value - z0) / (z1 - z0)
                return x0 + (x1 - x0) * fraction
        return None

    cut_face_indices = set()
    cut_face_counts = {"left": 0, "right": 0}
    cut_vertex_indices = {"left": set(), "right": set()}
    cut_points_by_side = {"left": [], "right": []}
    for polygon in mesh.polygons:
        points = [world_point(index) for index in polygon.vertices]
        center_x = sum(point[0] for point in points) / len(points)
        side = "left" if center_x < 0 else "right"
        # A triangle is trimmed if any corner protrudes beyond the measured
        # envelope. Centroid-only selection leaves long shoulder triangles
        # outside the cut and causes visible flaps after the sleeve surface is removed.
        outside_envelope = False
        for point in points:
            limit = lateral_limit(point[2])
            if limit is None:
                continue
            if (side == "left" and -point[0] > limit) or (side == "right" and point[0] > limit):
                outside_envelope = True
                break
        if outside_envelope:
            cut_face_indices.add(polygon.index)
            cut_face_counts[side] += 1
            cut_vertex_indices[side].update(polygon.vertices)
            cut_points_by_side[side].extend(points)

    cut_face_count = len(cut_face_indices)
    if not 60 <= cut_face_count <= 450:
        raise RuntimeError(
            "V386 sleeve trim rejected: face count outside conservative safety bounds: "
            + repr({"cut_face_count": cut_face_count, "side_counts": cut_face_counts})
        )
    if min(cut_face_counts.values()) < 25:
        raise RuntimeError("V386 sleeve trim did not select both lateral sides: " + repr(cut_face_counts))
    if abs(cut_face_counts["left"] - cut_face_counts["right"]) > max(cut_face_counts.values()) * 0.40:
        raise RuntimeError("V386 sleeve trim is too asymmetric to trust: " + repr(cut_face_counts))

    cut_bounds = {
        "min": [round(min(point[i] for point in cut_points_by_side["left"] + cut_points_by_side["right"]), 6) for i in range(3)],
        "max": [round(max(point[i] for point in cut_points_by_side["left"] + cut_points_by_side["right"]), 6) for i in range(3)],
    }
    cut_region_audit = {
        "method": "smooth lateral face-centroid envelope; integrated shirt-sleeve surface trim",
        "profile_world_xz_m": [[z, x] for z, x in cut_profile],
        "face_count": cut_face_count,
        "side_face_counts": cut_face_counts,
        "side_touched_vertex_counts": {side: len(indices) for side, indices in cut_vertex_indices.items()},
        "touched_vertex_count_total": len(cut_vertex_indices["left"] | cut_vertex_indices["right"]),
        "bounds_world_m": cut_bounds,
    }

    # Remove only faces inside the explicitly measured lateral trim envelope.
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bm.faces.ensure_lookup_table()
        bm.faces.index_update()
        target_faces = [face for face in bm.faces if face.index in cut_face_indices]
        if len(target_faces) != cut_face_count:
            raise RuntimeError("V386 BMesh face indices do not align with the measured sleeve trim")
        bmesh.ops.delete(bm, geom=target_faces, context="FACES")
        loose_edges = [edge for edge in bm.edges if not edge.link_faces]
        if loose_edges:
            bmesh.ops.delete(bm, geom=loose_edges, context="EDGES")
        loose_verts = [vertex for vertex in bm.verts if not vertex.link_edges]
        if loose_verts:
            bmesh.ops.delete(bm, geom=loose_verts, context="VERTS")
        bm.to_mesh(mesh)
    finally:
        bm.free()
    mesh.update()
    bpy.context.view_layer.update()

    # Widen the retained upper armhole edge itself. A face-centroid/vertex trim
    # leaves a coarse topology edge too far inward; a small smooth edge offset
    # gives the sleeveless shoulder panel enough overlap to cover the arm-cap
    # without filling the armhole or adding a detached sleeve.
    boundary_edge_counts = {}
    for polygon in mesh.polygons:
        ids = list(polygon.vertices)
        for edge_a, edge_b in zip(ids, ids[1:] + ids[:1]):
            edge_key = (edge_a, edge_b) if edge_a < edge_b else (edge_b, edge_a)
            boundary_edge_counts[edge_key] = boundary_edge_counts.get(edge_key, 0) + 1

    shoulder_boundary_vertex_indices = set()
    for (edge_a, edge_b), face_count in boundary_edge_counts.items():
        if face_count != 1:
            continue
        for vertex_index in (edge_a, edge_b):
            point = world_point(vertex_index)
            point_z = point[2]
            limit = lateral_limit(point_z)
            if limit is None or not (1.12 < point_z < 1.34):
                continue
            absolute_x = abs(point[0])
            if not (0.10 < absolute_x < 0.255):
                continue
            if abs(absolute_x - limit) > 0.095:
                continue
            shoulder_boundary_vertex_indices.add(vertex_index)

    if len(shoulder_boundary_vertex_indices) < 20:
        raise RuntimeError("V386 could not find enough retained shoulder-edge vertices to overlap the arm cap: " + repr({
            "candidate_boundary_vertex_count": len(shoulder_boundary_vertex_indices),
        }))

    def smooth_unit(value):
        value = min(1.0, max(0.0, float(value)))
        return value * value * (3.0 - 2.0 * value)

    inverse_matrix = matrix.inverted()
    shoulder_edge_offsets = []
    max_abs_x_before_overlap = max(abs(world_point(index)[0]) for index in range(len(mesh.vertices)))
    for vertex_index in shoulder_boundary_vertex_indices:
        point = world_point(vertex_index)
        point_z = point[2]
        rise = smooth_unit((point_z - 1.12) / (1.18 - 1.12))
        fall = smooth_unit((1.34 - point_z) / (1.34 - 1.26))
        weight = rise * fall
        # A22 visual candidate: modest local overlap; require front/side visual review before promotion.
        # Keep the taper localized; the former 30 mm trial made the shoulder cap look too broad.
        delta_x = 0.022 * weight
        if delta_x < 0.002:
            continue
        side_sign = 1.0 if point[0] >= 0.0 else -1.0
        widened_point = Vector((point[0] + side_sign * delta_x, point[1], point[2]))
        mesh.vertices[vertex_index].co = inverse_matrix @ widened_point
        shoulder_edge_offsets.append(delta_x)

    if len(shoulder_edge_offsets) < 12:
        raise RuntimeError("V386 shoulder edge overlap moved too few vertices to be reliable: " + repr({
            "candidate_boundary_vertex_count": len(shoulder_boundary_vertex_indices),
            "moved_vertex_count": len(shoulder_edge_offsets),
        }))
    mesh.update()
    bpy.context.view_layer.update()
    max_abs_x_after_overlap = max(abs(world_point(index)[0]) for index in range(len(mesh.vertices)))
    shoulder_edge_overlap_audit = {
        "status": "APPLIED",
        "method": "smooth localized 22 mm maximum outward offset on the retained upper armhole boundary; tapered at underarm and shoulder-top ends",
        "candidate_boundary_vertex_count": len(shoulder_boundary_vertex_indices),
        "moved_vertex_count": len(shoulder_edge_offsets),
        "max_offset_m": round(max(shoulder_edge_offsets), 6),
        "mean_offset_m": round(sum(shoulder_edge_offsets) / len(shoulder_edge_offsets), 6),
        "max_abs_x_before_m": round(max_abs_x_before_overlap, 6),
        "max_abs_x_after_m": round(max_abs_x_after_overlap, 6),
        "preserved": "underarm opening remains open; no detached sleeve or solid armhole cap added",
        "visual_warning": "Inspect the widened upper edge from front/side/three-quarter views for cloth stretching before approval.",
    }

    removed_vertex_count = vertex_count_before - len(mesh.vertices)
    removed_face_count = face_count_before - len(mesh.polygons)
    components_after = connected_components(mesh)
    if removed_face_count != cut_face_count:
        raise RuntimeError("V386 sleeve trim face-count accounting failed: " + repr({
            "removed_face_count": removed_face_count,
            "selected_cut_face_count": cut_face_count,
        }))
    if removed_vertex_count < 80 or removed_vertex_count > 500:
        raise RuntimeError("V386 sleeve trim removed an unexpected number of vertices: " + str(removed_vertex_count))
    if len(components_before) != 2 or len(components_after) != 2:
        raise RuntimeError("V386 must retain exactly the expected shirt and trouser regions: " + repr({
            "components_before": components_before,
            "components_after": components_after,
        }))

    upper_candidates = [
        component for component in components_after
        if component["bounds_world_m"]["min"][2] > 1.0
    ]
    lower_candidates = [
        component for component in components_after
        if component["bounds_world_m"]["max"][2] < 1.0
    ]
    if len(upper_candidates) != 1 or len(lower_candidates) != 1:
        raise RuntimeError("V386 cannot uniquely identify retained shirt and trouser regions: " + repr(components_after))
    shirt_after = upper_candidates[0]
    pants_after = lower_candidates[0]
    shirt_before = next(
        (component for component in components_before if component["bounds_world_m"]["min"][2] > 1.0),
        None,
    )
    if shirt_before is None:
        raise RuntimeError("V386 could not identify the original upper-shirt region")
    if shirt_after["vertex_count"] < 450 or shirt_after["face_count"] < 400:
        raise RuntimeError("V386 remaining shirt torso is unexpectedly small: " + repr(shirt_after))
    if pants_after["vertex_count"] < 500 or pants_after["face_count"] < 500:
        raise RuntimeError("V386 trouser region appears damaged by sleeve trim: " + repr(pants_after))
    if shirt_after["max_abs_x_m"] > shirt_before["max_abs_x_m"] - 0.015:
        raise RuntimeError("V386 lateral trim did not narrow the upper garment by the required 15 mm: " + repr({
            "shirt_before": shirt_before, "shirt_after": shirt_after,
        }))

    # Add a very narrow, fabric-colored binding on the exposed armhole edges.
    # This softens the hard, single-sided cut without filling the armhole or
    # changing the skin, shoulder pose, shirt silhouette or trouser geometry.
    edge_face_counts = {}
    for polygon in mesh.polygons:
        ids = list(polygon.vertices)
        for a, b in zip(ids, ids[1:] + ids[:1]):
            key = (a, b) if a < b else (b, a)
            edge_face_counts[key] = edge_face_counts.get(key, 0) + 1

    boundary_graph = {}
    selected_boundary_edges = []
    for (a, b), face_count in edge_face_counts.items():
        if face_count != 1:
            continue
        point_a = world_point(a)
        point_b = world_point(b)
        mid_x = (point_a[0] + point_b[0]) / 2.0
        mid_z = (point_a[2] + point_b[2]) / 2.0
        limit = lateral_limit(mid_z)
        if limit is None or not (1.08 < mid_z < 1.39):
            continue
        if not (0.10 < abs(mid_x) < 0.30):
            continue
        if abs(abs(mid_x) - limit) > 0.07:
            continue
        selected_boundary_edges.append((a, b))
        boundary_graph.setdefault(a, set()).add(b)
        boundary_graph.setdefault(b, set()).add(a)

    # The native shirt mesh is relatively coarse around the cut. Smooth only
    # vertices along the exposed armhole boundary chain, not the shirt body,
    # so the silhouette loses the small triangular teeth introduced by face
    # trimming. Curve binding is generated afterward from this same smoothed edge.
    boundary_smoothing_iterations = 4
    boundary_smoothing_factor = 0.40
    boundary_vertex_indices = sorted(boundary_graph)
    boundary_original_positions = {
        index: Vector(world_point(index)) for index in boundary_vertex_indices
    }
    boundary_smoothed_positions = {
        index: point.copy() for index, point in boundary_original_positions.items()
    }

    def mean_boundary_roughness(positions):
        residuals = []
        for vertex_index in boundary_vertex_indices:
            neighbor_indices = sorted(boundary_graph[vertex_index])
            if len(neighbor_indices) < 2:
                continue
            neighbor_mean = sum(
                (positions[neighbor] for neighbor in neighbor_indices),
                Vector((0.0, 0.0, 0.0)),
            ) / len(neighbor_indices)
            residuals.append(float((positions[vertex_index] - neighbor_mean).length))
        return sum(residuals) / len(residuals) if residuals else 0.0

    roughness_before_m = mean_boundary_roughness(boundary_original_positions)
    for _ in range(boundary_smoothing_iterations):
        next_positions = {}
        for index in boundary_vertex_indices:
            neighbors = sorted(boundary_graph[index])
            current = boundary_smoothed_positions[index]
            if len(neighbors) < 2:
                next_positions[index] = current.copy()
                continue
            neighbor_mean = sum(
                (boundary_smoothed_positions[neighbor] for neighbor in neighbors),
                Vector((0.0, 0.0, 0.0)),
            ) / len(neighbors)
            next_positions[index] = current.lerp(neighbor_mean, boundary_smoothing_factor)
        boundary_smoothed_positions = next_positions

    smoothing_displacements = []
    inverse_matrix_for_edge_smoothing = matrix.inverted()
    for index in boundary_vertex_indices:
        before_point = boundary_original_positions[index]
        after_point = boundary_smoothed_positions[index]
        displacement = float((after_point - before_point).length)
        smoothing_displacements.append(displacement)
        mesh.vertices[index].co = inverse_matrix_for_edge_smoothing @ after_point
    mesh.update()
    bpy.context.view_layer.update()
    roughness_after_m = mean_boundary_roughness(boundary_smoothed_positions)
    roughness_reduction_fraction = (
        (roughness_before_m - roughness_after_m) / roughness_before_m
        if roughness_before_m > 1e-12 else 0.0
    )
    boundary_smoothing_audit = {
        "status": "APPLIED",
        "method": "two-pass boundary-chain Laplacian relaxation; interior shirt vertices remain unchanged",
        "vertex_count": len(boundary_vertex_indices),
        "iterations": boundary_smoothing_iterations,
        "relaxation_factor": boundary_smoothing_factor,
        "mean_roughness_before_m": round(roughness_before_m, 7),
        "mean_roughness_after_m": round(roughness_after_m, 7),
        "roughness_reduction_fraction": round(roughness_reduction_fraction, 6),
        "mean_displacement_m": round(sum(smoothing_displacements) / len(smoothing_displacements), 6) if smoothing_displacements else 0.0,
        "max_displacement_m": round(max(smoothing_displacements), 6) if smoothing_displacements else 0.0,
        "preserved": "only exposed armhole boundary vertices are smoothed; shirt interior, torso and trousers are untouched",
    }
    if len(boundary_vertex_indices) < 40:
        raise RuntimeError("V386 armhole boundary smoothing found too few vertices: " + repr(boundary_smoothing_audit))
    if not smoothing_displacements or max(smoothing_displacements) > 0.035:
        raise RuntimeError("V386 armhole boundary smoothing exceeded its 35 mm safety limit: " + repr(boundary_smoothing_audit))
    if roughness_before_m <= 1e-12 or roughness_reduction_fraction < 0.15:
        raise RuntimeError("V386 armhole boundary smoothing did not reduce boundary roughness by at least 15%: " + repr(boundary_smoothing_audit))

    remaining_vertices = set(boundary_graph)
    binding_chains = []
    while remaining_vertices:
        seed = remaining_vertices.pop()
        component = {seed}
        stack = [seed]
        while stack:
            current = stack.pop()
            for neighbor in boundary_graph[current]:
                if neighbor in remaining_vertices:
                    remaining_vertices.remove(neighbor)
                    component.add(neighbor)
                    stack.append(neighbor)
        if len(component) < 20:
            continue

        endpoints = sorted(vertex for vertex in component if len(boundary_graph[vertex] & component) == 1)
        start_vertex = endpoints[0] if endpoints else min(component)
        ordered = [start_vertex]
        visited_vertices = {start_vertex}
        previous = None
        current = start_vertex
        closed = False
        while True:
            options = sorted(
                neighbor for neighbor in (boundary_graph[current] & component)
                if neighbor != previous and (neighbor not in visited_vertices or neighbor == start_vertex)
            )
            if not options:
                break
            next_vertex = options[0]
            if next_vertex == start_vertex:
                closed = True
                break
            ordered.append(next_vertex)
            visited_vertices.add(next_vertex)
            previous, current = current, next_vertex
            if len(ordered) > len(component) + 2:
                raise RuntimeError("V386 armhole binding path ordering exceeded component size")
        if len(ordered) >= 20:
            binding_chains.append({"vertices": ordered, "closed": closed})

    for chain in binding_chains:
        mean_x = sum(world_point(index)[0] for index in chain["vertices"]) / len(chain["vertices"])
        chain["side"] = "left" if mean_x < 0 else "right"
    chain_sides = {chain["side"] for chain in binding_chains}
    if len(binding_chains) < 2 or chain_sides != {"left", "right"}:
        raise RuntimeError("V386 could not trace a substantial armhole boundary on both sides: " + repr({
            "selected_boundary_edge_count": len(selected_boundary_edges),
            "binding_chain_sizes": [len(chain["vertices"]) for chain in binding_chains],
            "binding_chain_sides": [chain["side"] for chain in binding_chains],
        }))

    binding_curve = bpy.data.curves.new("V386_ArmholeBindingCurve", type="CURVE")
    binding_curve.dimensions = "3D"
    binding_curve.resolution_u = 2
    binding_curve.bevel_depth = 0.00125
    binding_curve.bevel_resolution = 3
    binding_curve.fill_mode = "FULL"
    for chain in binding_chains:
        points = chain["vertices"]
        spline = binding_curve.splines.new(type="POLY")
        spline.points.add(len(points) - 1)
        for point_index, vertex_index in enumerate(points):
            co = mesh.vertices[vertex_index].co
            spline.points[point_index].co = (float(co.x), float(co.y), float(co.z), 1.0)
        spline.use_cyclic_u = bool(chain["closed"])

    binding_obj = bpy.data.objects.new("V386_ArmholeBinding", binding_curve)
    bpy.context.scene.collection.objects.link(binding_obj)
    binding_obj.parent = obj
    binding_obj.location = (0.0, 0.0, 0.0)
    binding_obj.rotation_euler = (0.0, 0.0, 0.0)
    binding_obj.scale = (1.0, 1.0, 1.0)
    binding_material = _make_solid_material(
        "V386_DarkTeal_ArmholeBinding",
        (0.006, 0.020, 0.017, 1.0),
        metallic=0.0,
        roughness=0.72,
        specular=0.16,
    )
    binding_curve.materials.append(binding_material)

    for selected in list(bpy.context.selected_objects):
        selected.select_set(False)
    binding_obj.select_set(True)
    bpy.context.view_layer.objects.active = binding_obj
    conversion_result = bpy.ops.object.convert(target="MESH")
    if "FINISHED" not in conversion_result:
        raise RuntimeError("V386 failed to convert the armhole binding into exportable mesh geometry")
    binding_obj = bpy.context.view_layer.objects.active
    binding_obj.name = "V386_ArmholeBinding"
    binding_obj.data.name = "V386_ArmholeBinding_Mesh"
    if binding_obj.parent is not obj:
        binding_obj.parent = obj
    if len(binding_obj.data.vertices) < 100 or len(binding_obj.data.polygons) < 100:
        raise RuntimeError("V386 armhole binding mesh is unexpectedly small: " + repr({
            "vertices": len(binding_obj.data.vertices), "faces": len(binding_obj.data.polygons),
        }))
    clothing_objects.append(binding_obj)
    armhole_binding_audit = {
        "status": "APPLIED",
        "object": binding_obj.name,
        "material": binding_material.name,
        "method": "bevelled left/right polyline chains sampled from exposed armhole boundary edges; 1.25 mm radius",
        "selected_boundary_edge_count": len(selected_boundary_edges),
        "chain_count": len(binding_chains),
        "chain_vertex_counts": [len(chain["vertices"]) for chain in binding_chains],
        "chain_sides": [chain["side"] for chain in binding_chains],
        "binding_mesh_vertex_count": len(binding_obj.data.vertices),
        "binding_mesh_face_count": len(binding_obj.data.polygons),
        "visual_warning": "Confirm the narrow binding follows the visible cut edge and does not appear as floating trim in front, side and three-quarter views.",
    }

    removed_components = []
    for side in ("left", "right"):
        points = cut_points_by_side[side]
        removed_components.append({
            "side": side,
            "region_kind": "trimmed_surface_patch_not_detached_component",
            "classified_as_sleeve": True,
            "face_count": cut_face_counts[side],
            "touched_vertex_count": len(cut_vertex_indices[side]),
            "bounds_world_m": {
                "min": [round(min(point[i] for point in points), 6) for i in range(3)],
                "max": [round(max(point[i] for point in points), 6) for i in range(3)],
            },
            "max_abs_x_m": round(max(abs(point[0]) for point in points), 6),
        })

    return {
        "status": "APPLIED",
        "object": obj.name,
        "method": "measured lateral sleeve surface trim; retain validated shirt torso and trouser regions",
        "component_count_before": len(components_before),
        "component_count_after_cut": len(components_after),
        "component_count_after_expected": len(components_after),
        "component_count_after": len(components_after),
        "components_before": components_before,
        "components_after_cut": components_after,
        "removed_components": removed_components,
        "removed_component_count": 2,
        "cut_region_audit": cut_region_audit,
        "cut_face_count": cut_face_count,
        "removed_vertex_count": removed_vertex_count,
        "removed_face_count": removed_face_count,
        "vertex_count_before": vertex_count_before,
        "vertex_count_after": len(mesh.vertices),
        "face_count_before": face_count_before,
        "face_count_after": len(mesh.polygons),
        "shirt_region_before": shirt_before,
        "shirt_region_after": shirt_after,
        "trouser_region_after": pants_after,
        "shoulder_edge_overlap_audit": shoulder_edge_overlap_audit,
        "armhole_boundary_smoothing_audit": boundary_smoothing_audit,
        "armhole_binding_audit": armhole_binding_audit,
        "preserved": [
            "body skin and both arm meshes",
            "retained central sleeveless shirt torso/shoulder region",
            "lower-body trouser mesh and trouser geometry",
            "face, eyes/iris, hair, necklace, belt/pockets and ankle details",
            "12 facial morphs and Lam_Idle_GentleSway",
        ],
        "visual_warning": "Inspect armholes, shoulder edges and shirt coverage in front, side and three-quarter renders before visual approval.",
    }

def apply_relaxed_arm_pose(basemesh, clothing_objects):
    """Relax the A-pose about a higher shoulder pivot with a continuous arm-cap blend.

    The earlier pivot (z=1.14 m) sat below much of the upper-arm cap, so rotating
    the arm down could push the skin away from the sleeveless shoulder edge.
    This variant raises the pivot and brings the lateral fade inward while
    keeping x<=0.18 m and z<=0.60 m exactly protected. It is an experimental
    candidate; inspect the shoulder/armhole in front, side and three-quarter views.
    """
    targets = [("body", basemesh)]
    upper_garments = [
        obj for obj in clothing_objects
        if obj.type == "MESH" and "sportsuit01" in obj.name.lower()
    ]
    if not upper_garments:
        raise RuntimeError("V386 could not find Human.female_sportsuit01 to keep the sleeve/arm surface aligned")
    targets.extend(("upper_clothing", obj) for obj in upper_garments)

    pivot_abs_x = 0.205
    pivot_z = 1.23
    max_angle_deg = 22.0
    lateral_inner_m = 0.18
    lateral_outer_m = 0.34
    # Continue the smooth inward/downward arm rotation through the upper-arm
    # cap. The previous fade stopped at z=1.13 m, leaving the shoulder head
    # static above the shirt armhole and exposing a sharp triangular skin patch.
    vertical_start_z_m = 1.42
    vertical_full_z_m = 1.15
    lower_cutoff_z_m = 0.60
    lower_full_z_m = 0.78

    def point_weight(point):
        lateral = _v386_smooth_unit(
            (abs(float(point.x)) - lateral_inner_m) / (lateral_outer_m - lateral_inner_m)
        )
        z = float(point.z)
        upper_vertical = _v386_smooth_unit(
            (vertical_start_z_m - z) / (vertical_start_z_m - vertical_full_z_m)
        )
        lower_vertical = _v386_smooth_unit(
            (z - lower_cutoff_z_m) / (lower_full_z_m - lower_cutoff_z_m)
        )
        return lateral * upper_vertical * lower_vertical

    def transform_world_point(point):
        weight = point_weight(point)
        if weight <= 0.0:
            return point.copy(), weight
        side = 1.0 if point.x >= 0.0 else -1.0
        dx = abs(float(point.x)) - pivot_abs_x
        dz = float(point.z) - pivot_z
        angle = -math.radians(max_angle_deg) * weight
        c = math.cos(angle)
        sn = math.sin(angle)
        # Rotate the distal arm vector about the shoulder pivot in the X-Z plane.
        # Negative angle swings the hands toward the body and down, preserving the
        # vector length for fully weighted points.
        new_x_abs = pivot_abs_x + c * dx - sn * dz
        new_z = pivot_z + sn * dx + c * dz
        return Vector((side * new_x_abs, float(point.y), new_z)), weight

    per_mesh = []
    selected_before_x = []
    selected_after_x = []
    selected_lateral_reductions = []
    selected_vertical_drops = []
    selected_displacements = []
    shoulder_cap_displacements = []
    shoulder_cap_vertical_drops = []
    shoulder_cap_lateral_changes = []
    shoulder_cap_candidate_count = 0
    protected_torso_displacements = []
    protected_lower_body_displacements = []
    protected_torso_count = 0
    protected_lower_body_count = 0
    selected_count = 0

    for role, obj in targets:
        if obj.type != "MESH":
            continue
        matrix = obj.matrix_world.copy()
        inverse = matrix.inverted()
        shape_keys = getattr(obj.data, "shape_keys", None)
        key_blocks = list(shape_keys.key_blocks) if shape_keys and shape_keys.key_blocks else []
        basis = next((key for key in key_blocks if key.name == "Basis"), None)
        measure_block = basis if basis is not None else (key_blocks[0] if key_blocks else None)

        mesh_before_x, mesh_after_x, mesh_lateral, mesh_drop, mesh_disp = [], [], [], [], []
        mesh_torso_guard_disp = []
        mesh_lower_guard_disp = []
        mesh_torso_guard_count = 0
        mesh_lower_guard_count = 0
        # Measure from Basis (or the first available key block / raw vertices), but transform every key block
        # by the same spatial rule so any existing keys remain aligned.
        for block in (key_blocks if key_blocks else [None]):
            points = block.data if block is not None else obj.data.vertices
            is_measure_block = (block is measure_block) if key_blocks else (block is None)
            for vertex in points:
                original = matrix @ vertex.co
                transformed, weight = transform_world_point(original)
                if is_measure_block:
                    displacement = float((transformed - original).length)
                    abs_x = abs(float(original.x))
                    z_world = float(original.z)
                    if role == "body" and 0.22 <= abs_x <= 0.31 and 1.10 <= z_world <= 1.31:
                        shoulder_cap_candidate_count += 1
                        if weight > 0.01:
                            shoulder_cap_displacements.append(displacement)
                            shoulder_cap_vertical_drops.append(z_world - float(transformed.z))
                            shoulder_cap_lateral_changes.append(abs_x - abs(float(transformed.x)))
                    if abs(float(original.x)) <= lateral_inner_m + 1e-9:
                        mesh_torso_guard_disp.append(displacement)
                        mesh_torso_guard_count += 1
                    if float(original.z) <= lower_cutoff_z_m + 1e-9:
                        mesh_lower_guard_disp.append(displacement)
                        mesh_lower_guard_count += 1
                    if weight >= 0.50:
                        new_abs_x = abs(float(transformed.x))
                        old_abs_x = abs(float(original.x))
                        lateral_delta = old_abs_x - new_abs_x
                        vertical_drop = float(original.z) - float(transformed.z)
                        mesh_before_x.append(old_abs_x)
                        mesh_after_x.append(new_abs_x)
                        mesh_lateral.append(lateral_delta)
                        mesh_drop.append(vertical_drop)
                        mesh_disp.append(displacement)
                vertex.co = inverse @ transformed
        obj.data.update()

        if mesh_before_x:
            selected_before_x.extend(mesh_before_x)
            selected_after_x.extend(mesh_after_x)
            selected_lateral_reductions.extend(mesh_lateral)
            selected_vertical_drops.extend(mesh_drop)
            selected_displacements.extend(mesh_disp)
            selected_count += len(mesh_before_x)
        protected_torso_displacements.extend(mesh_torso_guard_disp)
        protected_lower_body_displacements.extend(mesh_lower_guard_disp)
        protected_torso_count += mesh_torso_guard_count
        protected_lower_body_count += mesh_lower_guard_count
        per_mesh.append({
            "role": role,
            "object": obj.name,
            "mesh_vertex_count": len(obj.data.vertices),
            "weighted_vertex_count": len(mesh_before_x),
            "protected_torso_vertex_count": mesh_torso_guard_count,
            "protected_torso_max_displacement_m": round(max(mesh_torso_guard_disp), 9) if mesh_torso_guard_disp else 0.0,
            "protected_lower_body_vertex_count": mesh_lower_guard_count,
            "protected_lower_body_max_displacement_m": round(max(mesh_lower_guard_disp), 9) if mesh_lower_guard_disp else 0.0,
            "max_abs_x_before_m": round(max(mesh_before_x), 6) if mesh_before_x else None,
            "max_abs_x_after_m": round(max(mesh_after_x), 6) if mesh_after_x else None,
            "mean_lateral_reduction_m": round(sum(mesh_lateral) / len(mesh_lateral), 6) if mesh_lateral else None,
            "mean_vertical_drop_m": round(sum(mesh_drop) / len(mesh_drop), 6) if mesh_drop else None,
            "max_vertex_displacement_m": round(max(mesh_disp), 6) if mesh_disp else None,
        })

    bpy.context.view_layer.update()
    if selected_count < 25:
        raise RuntimeError("V386 arm-pose gate found too few weighted body/sleeve vertices: " + repr(per_mesh))
    lateral_gain = sum(selected_lateral_reductions) / selected_count
    vertical_drop = sum(selected_vertical_drops) / selected_count
    max_before = max(selected_before_x)
    max_after = max(selected_after_x)
    max_displacement = max(selected_displacements)
    torso_guard_max_displacement = max(protected_torso_displacements, default=0.0)
    lower_body_guard_max_displacement = max(protected_lower_body_displacements, default=0.0)
    if protected_torso_count < 25 or protected_lower_body_count < 25:
        raise RuntimeError("V386 could not establish enough protected torso/lower-body vertices: " + repr({
            "protected_torso_count": protected_torso_count,
            "protected_lower_body_count": protected_lower_body_count,
        }))
    if torso_guard_max_displacement > 1e-7:
        raise RuntimeError("V386 unexpectedly moved vertices inside the torso x-guard: " + repr(torso_guard_max_displacement))
    if lower_body_guard_max_displacement > 1e-7:
        raise RuntimeError("V386 unexpectedly moved vertices below the lower-body z-guard: " + repr(lower_body_guard_max_displacement))
    if max_before - max_after < 0.06:
        raise RuntimeError("V386 arm-pose gate did not reduce lateral spread enough: " + repr({
            "max_before": max_before, "max_after": max_after, "per_mesh": per_mesh
        }))
    if lateral_gain < 0.025 or vertical_drop < 0.015:
        raise RuntimeError("V386 arm-pose change fell below the intended measurable range: " + repr({
            "mean_lateral_reduction_m": lateral_gain, "mean_vertical_drop_m": vertical_drop,
            "per_mesh": per_mesh
        }))
    if max_displacement > 0.30:
        raise RuntimeError("V386 arm-pose displacement exceeded the 0.30 m safety ceiling: " + repr(max_displacement))

    return {
        "status": "APPLIED",
        "scope": "base skin and female_sportsuit01 upper-clothing mesh only; smooth distal arm rotation before facial target load",
        "pivot_world_m": {"abs_x": pivot_abs_x, "z": pivot_z},
        "rotation": {
            "max_inward_downward_degrees": max_angle_deg,
            "lateral_fade_m": [lateral_inner_m, lateral_outer_m],
            "upper_vertical_fade_z_m": [vertical_start_z_m, vertical_full_z_m],
            "lower_body_cutoff_z_m": lower_cutoff_z_m,
            "lower_vertical_fade_z_m": [lower_cutoff_z_m, lower_full_z_m],
            "interpolation": "product of cubic smoothstep lateral, upper-vertical and lower-vertical gates",
        },
        "weighted_vertex_count": selected_count,
        "shoulder_cap_audit": {
            "status": "APPLIED" if shoulder_cap_displacements else "NO_WEIGHTED_VERTICES",
            "object": "Human",
            "zone_abs_x_m": [0.22, 0.31],
            "zone_z_m": [1.10, 1.31],
            "candidate_vertex_count": shoulder_cap_candidate_count,
            "transformed_vertex_count": len(shoulder_cap_displacements),
            "mean_displacement_m": round(sum(shoulder_cap_displacements) / len(shoulder_cap_displacements), 6) if shoulder_cap_displacements else 0.0,
            "mean_downward_shift_m": round(sum(shoulder_cap_vertical_drops) / len(shoulder_cap_vertical_drops), 6) if shoulder_cap_vertical_drops else 0.0,
            "mean_inward_lateral_change_m": round(sum(shoulder_cap_lateral_changes) / len(shoulder_cap_lateral_changes), 6) if shoulder_cap_lateral_changes else 0.0,
            "max_displacement_m": round(max(shoulder_cap_displacements), 6) if shoulder_cap_displacements else 0.0,
        },
        "max_abs_x_before_m": round(max_before, 6),
        "max_abs_x_after_m": round(max_after, 6),
        "mean_lateral_reduction_m": round(lateral_gain, 6),
        "mean_vertical_drop_m": round(vertical_drop, 6),
        "max_vertex_displacement_m": round(max_displacement, 6),
        "protected_torso_vertex_count": protected_torso_count,
        "protected_torso_max_displacement_m": round(torso_guard_max_displacement, 9),
        "protected_lower_body_vertex_count": protected_lower_body_count,
        "protected_lower_body_max_displacement_m": round(lower_body_guard_max_displacement, 9),
        "per_mesh": per_mesh,
        "preserved": [
            "head and facial profile; eyes, iris texture, hair and necklace",
            "waist/hip/thigh shaping and waist-gap/ankle details",
            "12 composite facial morph names and idle animation are built after this pose adjustment",
            "shoes are excluded from the arm deformation",
        ],
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
    strength = max(0.0, min(0.45, float(strength)))
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
            raise RuntimeError("V386 Basis/smile vertex count mismatch on " + obj.name)
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
        raise RuntimeError("V386 could not apply a gentle smile base pose to any face mesh with a smile morph")
    return {
        "status": "APPLIED",
        "expression": "gentle_smile",
        "strength": strength,
        "method": "Bake a restrained fraction of the existing smile delta into Basis and all non-smile shape keys; leave smile endpoint unchanged.",
        "total_vertices_adjusted": total_vertices,
        "objects": audits,
        "safety_note": "All 12 named morph controls are retained; smile endpoint and all non-smile morph deltas relative to the new Basis are preserved.",
    }


def create_necklace_accessory(scene, basemesh, clothing_objects):
    """Refine the silver necklace chain/pendant junction with a measured 3D contact check.

    Chain surface samples and V364 styling remain unchanged; only the middle
    chain control point's Y depth is corrected so the chain tube intersects the
    outer pendant torus. Head/hair/face/body, clothing, morphs and animation are
    otherwise untouched.
    """
    silver = bpy.data.materials.new("V386_SilverNecklace")
    silver.use_nodes = True
    tree = silver.node_tree
    tree.nodes.clear()
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    output.location = (360, 40)
    principled = tree.nodes.new("ShaderNodeBsdfPrincipled")
    principled.location = (80, 40)
    principled.inputs["Base Color"].default_value = (0.62, 0.66, 0.72, 1.0)
    principled.inputs["Metallic"].default_value = 0.82
    principled.inputs["Roughness"].default_value = 0.23
    if "Specular IOR Level" in principled.inputs:
        principled.inputs["Specular IOR Level"].default_value = 0.48
    tree.links.new(principled.outputs["BSDF"], output.inputs["Surface"])
    silver.diffuse_color = (0.62, 0.66, 0.72, 1.0)

    def sample_front_y(x, z):
        sample_objects = [obj for obj in clothing_objects if obj.type == "MESH"] + [basemesh]
        for x_radius, z_radius in ((0.018, 0.018), (0.032, 0.028), (0.055, 0.040), (0.08, 0.06)):
            ys = []
            for obj in sample_objects:
                matrix = obj.matrix_world.copy()
                for vertex in obj.data.vertices:
                    point = matrix @ vertex.co
                    if abs(float(point.x) - x) <= x_radius and abs(float(point.z) - z) <= z_radius:
                        ys.append(float(point.y))
            if ys:
                return min(ys), {
                    "x_m": round(x, 5),
                    "z_m": round(z, 5),
                    "sampled_front_y_m": round(min(ys), 5),
                    "sample_count": len(ys),
                    "x_radius_m": x_radius,
                    "z_radius_m": z_radius,
                }
        raise RuntimeError("V386 could not sample a front surface for necklace point " + repr((x, z)))

    # V386 keeps the V364 chain path and material, but corrects the depth
    # at the single chain/pendant junction. The rest of the chain remains 3.5 mm
    # in front of the sampled surface. At the nadir, the chain centerline moves
    # to the forward tangent plane of the pendant's outer torus so their tube
    # cross-sections intersect in 3D instead of only overlapping in front view.
    pendant_center_z_m = 1.283
    pendant_surface_y, pendant_sample = sample_front_y(0.0, pendant_center_z_m)
    pendant_center_y = pendant_surface_y - 0.0035
    outer_ring_major_radius_m = 0.0085
    outer_ring_minor_radius_m = 0.0009
    ring_centerline_top_y_m = pendant_center_y
    ring_centerline_top_z_m = pendant_center_z_m + outer_ring_major_radius_m
    ring_forward_surface_y_m = pendant_center_y - outer_ring_minor_radius_m

    chain_xz = [
        (-0.055, 1.326),
        (-0.040, 1.307),
        (-0.020, 1.296),
        (0.000, 1.293),
        (0.020, 1.296),
        (0.040, 1.307),
        (0.055, 1.326),
    ]
    chain_points = []
    surface_samples = []
    chain_surface_offset_m = 0.0035
    chain_bevel_depth_m = 0.0010
    junction_index = None
    for index, (x, z) in enumerate(chain_xz):
        surface_y, sample = sample_front_y(x, z)
        nominal_chain_y_m = surface_y - chain_surface_offset_m
        chain_y_m = nominal_chain_y_m
        if abs(x) < 1e-9 and abs(z - 1.293) < 1e-6:
            junction_index = index
            chain_y_m = ring_forward_surface_y_m
        chain_points.append((x, chain_y_m, z))
        sample["nominal_chain_y_m"] = round(nominal_chain_y_m, 5)
        sample["junction_depth_adjustment_m"] = round(chain_y_m - nominal_chain_y_m, 5)
        sample["chain_y_m"] = round(chain_y_m, 5)
        surface_samples.append(sample)
    if junction_index is None:
        raise RuntimeError("V386 could not locate the necklace chain nadir control point")

    center_x, center_y, center_z = chain_points[junction_index]
    depth_delta_m = abs(center_y - ring_centerline_top_y_m)
    vertical_delta_m = abs(center_z - ring_centerline_top_z_m)
    centerline_distance_m = math.sqrt(depth_delta_m ** 2 + vertical_delta_m ** 2)
    combined_tube_radii_m = chain_bevel_depth_m + outer_ring_minor_radius_m
    contact_margin_m = combined_tube_radii_m - centerline_distance_m
    chain_junction_audit = {
        "status": "PASS_CONTACT_GEOMETRY" if contact_margin_m > 0 else "FAIL_NO_CONTACT",
        "control_point_index": junction_index,
        "chain_centerline_xyz_m": [round(center_x, 5), round(center_y, 5), round(center_z, 5)],
        "nominal_chain_centerline_y_m": round(surface_samples[junction_index]["nominal_chain_y_m"], 5),
        "chain_centerline_y_m": round(center_y, 5),
        "ring_centerline_top_xyz_m": [0.0, round(ring_centerline_top_y_m, 5), round(ring_centerline_top_z_m, 5)],
        "ring_forward_surface_y_m": round(ring_forward_surface_y_m, 5),
        "junction_depth_adjustment_m": round(center_y - surface_samples[junction_index]["nominal_chain_y_m"], 5),
        "depth_delta_to_ring_centerline_m": round(depth_delta_m, 7),
        "vertical_delta_to_ring_centerline_m": round(vertical_delta_m, 7),
        "centerline_distance_m": round(centerline_distance_m, 7),
        "combined_tube_radii_m": round(combined_tube_radii_m, 7),
        "contact_margin_m": round(contact_margin_m, 7),
        "surface_to_chain_offsets_m": [round(item["sampled_front_y_m"] - item["chain_y_m"], 5) for item in surface_samples],
        "method": "Place the center chain control point on the forward tangent plane of the outer pendant torus; centerline distance must be smaller than the sum of tube radii.",
    }
    if chain_junction_audit["status"] != "PASS_CONTACT_GEOMETRY":
        raise RuntimeError("V386 necklace chain does not physically intersect the pendant ring: " + repr(chain_junction_audit))
    curve = bpy.data.curves.new("V386_SilverNecklaceChainCurve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 16
    curve.bevel_depth = chain_bevel_depth_m
    curve.bevel_resolution = 4
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(chain_points) - 1)
    for point, coordinate in zip(spline.bezier_points, chain_points):
        point.co = coordinate
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    chain_obj = bpy.data.objects.new("V386_NecklaceChain", curve)
    scene.collection.objects.link(chain_obj)
    chain_obj.data.materials.append(silver)

    # Curves do not export as glTF geometry in the configured baker; convert the
    # visible beveled chain to a mesh so it is retained in the baked GLB.
    bpy.ops.object.select_all(action="DESELECT")
    chain_obj.select_set(True)
    bpy.context.view_layer.objects.active = chain_obj
    bpy.ops.object.convert(target="MESH")
    chain_obj = bpy.context.object
    chain_obj.name = "V386_NecklaceChain"
    if len(chain_obj.data.materials) == 0:
        chain_obj.data.materials.append(silver)
    for polygon in chain_obj.data.polygons:
        polygon.use_smooth = True

    pendant_location = (0.0, pendant_center_y, pendant_center_z_m)
    components = []

    # Circular outer ring, facing the camera (camera/front is the negative Y axis).
    bpy.ops.mesh.primitive_torus_add(
        major_segments=48,
        minor_segments=12,
        major_radius=0.0085,
        minor_radius=0.0009,
        location=pendant_location,
        rotation=(math.radians(90.0), 0.0, 0.0),
    )
    outer_ring = bpy.context.object
    outer_ring.name = "V386_PendantOuterRing"
    outer_ring.data.materials.append(silver)
    components.append(outer_ring)

    # A fine inner concentric ring and a small oval center motif mirror the
    # reference medallion without introducing a heavy/chunky pendant.
    bpy.ops.mesh.primitive_torus_add(
        major_segments=40,
        minor_segments=10,
        major_radius=0.0045,
        minor_radius=0.00045,
        location=(0.0, pendant_center_y - 0.0007, pendant_center_z_m),
        rotation=(math.radians(90.0), 0.0, 0.0),
    )
    inner_ring = bpy.context.object
    inner_ring.name = "V386_PendantInnerRing"
    inner_ring.data.materials.append(silver)
    components.append(inner_ring)

    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=16,
        ring_count=12,
        radius=1.0,
        location=(0.0, pendant_center_y - 0.00135, pendant_center_z_m),
    )
    center_motif = bpy.context.object
    center_motif.name = "V386_PendantCenterMotif"
    center_motif.scale = (0.00125, 0.00055, 0.0023)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    center_motif.data.materials.append(silver)
    components.append(center_motif)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in components:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = outer_ring
    bpy.ops.object.join()
    pendant_obj = bpy.context.object
    pendant_obj.name = "V386_NecklacePendant"
    # Explicitly collapse the joined assembly to one predictable material slot.
    pendant_obj.data.materials.clear()
    pendant_obj.data.materials.append(silver)
    for polygon in pendant_obj.data.polygons:
        polygon.material_index = 0
        polygon.use_smooth = True

    objects = [chain_obj, pendant_obj]
    audits = []
    for obj in objects:
        audits.append({
            "object": obj.name,
            "type": obj.type,
            "vertex_count": len(obj.data.vertices) if obj.type == "MESH" else 0,
            "polygon_count": len(obj.data.polygons) if obj.type == "MESH" else 0,
            "material_names": [material.name for material in obj.data.materials if material],
            "world_bounds_m": world_bounds([obj]),
        })
    return objects, {
        "status": "APPLIED",
        "style": "fine silver chain with a circular open pendant, concentric inner ring and restrained center motif guided by the saved Lam reference",
        "material": {
            "name": silver.name,
            "base_color_rgba": [0.62, 0.66, 0.72, 1.0],
            "metallic": 0.82,
            "roughness": 0.23,
            "specular_ior_level": 0.48,
        },
        "chain_bevel_depth_m": chain_bevel_depth_m,
        "objects": audits,
        "pendant_geometry": {
            "design": "open circular outer ring + concentric inner ring + small oval center motif, joined into one mesh",
            "outer_major_radius_m": 0.0085,
            "outer_minor_radius_m": 0.0009,
            "inner_major_radius_m": 0.0045,
            "inner_minor_radius_m": 0.00045,
            "center_motif_scale_m": [0.00125, 0.00055, 0.0023],
            "joined_mesh": True,
            "component_count": 3,
            "orientation": "X-Z plane facing the camera/front (-Y)",
        },
        "chain_surface_samples": surface_samples,
        "chain_junction_audit": chain_junction_audit,
        "pendant_surface_sample": {
            **pendant_sample,
            "pendant_center_y_m": round(pendant_location[1], 5),
            "pendant_center_z_m": round(pendant_location[2], 5),
        },
        "scope": "necklace material and pendant/chain geometry only; no changes to body, clothes, face, hair, eye materials, morph targets or idle animation",
        "placement_revision": {
            "baseline_version": "V364",
            "vertical_offset_m": 0.0,
            "baseline_chain_z_m": [1.283, 1.288, 1.302, 1.326],
            "candidate_chain_z_m": [1.293, 1.296, 1.307, 1.326],
            "pendant_center_z_m": pendant_center_z_m,
            "reason": "Keep necklace attachment surface and pendant center stable, thin the chain, and raise only the chain nadir to meet the top of the circular ring."
        },
    }


def create_face_framing_hair_strands(scene, basemesh, hair_objects):
    """Add restrained, tapered hair wisps guided by the saved Lam character sheet.

    These are separate solid-color meshes so the existing V341 diffuse hair UVs,
    texture alpha and source hair geometry remain untouched. World coordinates
    follow the current baked character convention: negative Y is the front.
    """
    import bmesh
    from mathutils import Vector

    # Sample the actual front surfaces by ray-casting through the scene's
    # current head and hair meshes at each intended strand (x,z) control point.
    # World front is negative Y; the first front-facing hit is the smallest Y.
    depsgraph = bpy.context.evaluated_depsgraph_get()

    def raycast_surface_y(obj, x, z):
        if obj is None or obj.type != "MESH":
            return None
        evaluated = obj.evaluated_get(depsgraph)
        matrix = evaluated.matrix_world.copy()
        inverse = matrix.inverted()
        world_origin = Vector((float(x), -2.0, float(z)))
        world_direction = Vector((0.0, 1.0, 0.0))
        local_origin = inverse @ world_origin
        local_direction = (inverse.to_3x3() @ world_direction).normalized()
        try:
            hit, local_location, _normal, _face_index = evaluated.ray_cast(
                local_origin, local_direction, distance=10.0
            )
        except TypeError:
            hit, local_location, _normal, _face_index = evaluated.ray_cast(
                local_origin, local_direction
            )
        if not hit:
            return None
        world_location = matrix @ local_location
        return float(world_location.y)

    surface_sources = [obj for obj in hair_objects if obj.type == "MESH"] + [basemesh]
    if not any(obj.type == "MESH" for obj in surface_sources):
        raise RuntimeError("V386 has no head/hair meshes for surface-aware strand placement")

    surface_offset_m = 0.0012

    def align_section_to_surface(x, old_y, z):
        hits = []
        for surface_obj in surface_sources:
            hit_y = raycast_surface_y(surface_obj, x, z)
            if hit_y is not None:
                hits.append({"object": surface_obj.name, "surface_y_m": hit_y})
        if not hits:
            raise RuntimeError(
                "V386 could not sample head/hair surface for face-frame point "
                + repr({"x_m": x, "z_m": z})
            )
        frontmost = min(hits, key=lambda item: item["surface_y_m"])
        surface_y = float(frontmost["surface_y_m"])
        aligned_y = surface_y - surface_offset_m
        return aligned_y, {
            "x_m": round(float(x), 6),
            "z_m": round(float(z), 6),
            "source_y_m": round(float(old_y), 6),
            "surface_object": frontmost["object"],
            "surface_y_m": round(surface_y, 6),
            "aligned_y_m": round(aligned_y, 6),
            "surface_offset_m": round(surface_offset_m, 6),
            "delta_y_m": round(aligned_y - float(old_y), 6),
            "hit_object_count": len(hits),
            "hits": [
                {"object": item["object"], "surface_y_m": round(item["surface_y_m"], 6)}
                for item in hits
            ],
        }

    material_name = "V386_FaceFrameStrandMaterial"
    material = bpy.data.materials.get(material_name)
    if material is None:
        material = bpy.data.materials.new(material_name)
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    output.location = (360, 30)
    principled = tree.nodes.new("ShaderNodeBsdfPrincipled")
    principled.location = (80, 30)
    principled.inputs["Base Color"].default_value = (0.030, 0.0110, 0.0060, 1.0)
    principled.inputs["Roughness"].default_value = 0.80
    if "Metallic" in principled.inputs:
        principled.inputs["Metallic"].default_value = 0.0
    if "Specular IOR Level" in principled.inputs:
        principled.inputs["Specular IOR Level"].default_value = 0.11
    if "Coat Weight" in principled.inputs:
        principled.inputs["Coat Weight"].default_value = 0.0
    tree.links.new(principled.outputs["BSDF"], output.inputs["Surface"])
    material.diffuse_color = (0.030, 0.0110, 0.0060, 1.0)

    # Each section is (x, y, z, half_width_x, half_depth_y) in world metres.
    # Strands taper at both ends and stay outside the eye aperture/brow line.
    specs = [
        {
            "name": "V386_FaceFrame_LeftTemple",
            "role": "left_temple_lock",
            "sections": [
                (-0.047, -0.108, 1.560, 0.0010, 0.0008),
                (-0.058, -0.119, 1.538, 0.0038, 0.0018),
                (-0.073, -0.130, 1.508, 0.0050, 0.0028),
                (-0.082, -0.135, 1.475, 0.0048, 0.0028),
                (-0.079, -0.127, 1.442, 0.0034, 0.0020),
                (-0.068, -0.116, 1.415, 0.0008, 0.0007),
            ],
        },
        {
            "name": "V386_FaceFrame_RightTemple",
            "role": "right_temple_lock",
            "sections": [
                (0.045, -0.108, 1.559, 0.0010, 0.0008),
                (0.057, -0.119, 1.537, 0.0038, 0.0018),
                (0.073, -0.131, 1.506, 0.0050, 0.0028),
                (0.081, -0.136, 1.473, 0.0046, 0.0027),
                (0.077, -0.128, 1.441, 0.0032, 0.0019),
                (0.066, -0.116, 1.416, 0.0008, 0.0007),
            ],
        },
        {
            "name": "V386_FaceFrame_LeftForelock",
            "role": "left_forelock_wisp",
            "sections": [
                (-0.010, -0.103, 1.565, 0.0007, 0.0007),
                (-0.018, -0.116, 1.553, 0.0025, 0.0014),
                (-0.032, -0.127, 1.539, 0.0022, 0.0013),
                (-0.044, -0.131, 1.522, 0.0017, 0.0010),
                (-0.052, -0.128, 1.511, 0.0004, 0.0004),
            ],
        },
        {
            "name": "V386_FaceFrame_RightForelock",
            "role": "right_forelock_wisp",
            "sections": [
                (0.012, -0.103, 1.565, 0.0007, 0.0007),
                (0.022, -0.116, 1.552, 0.0024, 0.0014),
                (0.036, -0.127, 1.537, 0.0020, 0.0012),
                (0.046, -0.131, 1.521, 0.0015, 0.0009),
                (0.052, -0.128, 1.509, 0.0004, 0.0004),
            ],
        },
        {
            "name": "V386_FaceFrame_LeftFine",
            "role": "left_fine_strand",
            "sections": [
                (-0.055, -0.110, 1.548, 0.0005, 0.0005),
                (-0.067, -0.124, 1.528, 0.0018, 0.0010),
                (-0.079, -0.137, 1.503, 0.0017, 0.0010),
                (-0.081, -0.137, 1.482, 0.0012, 0.0007),
                (-0.075, -0.128, 1.464, 0.0003, 0.0003),
            ],
        },
        {
            "name": "V386_FaceFrame_RightFine",
            "role": "right_fine_strand",
            "sections": [
                (0.054, -0.110, 1.548, 0.0005, 0.0005),
                (0.066, -0.124, 1.527, 0.0018, 0.0010),
                (0.078, -0.138, 1.501, 0.0016, 0.0009),
                (0.080, -0.138, 1.481, 0.0011, 0.0007),
                (0.073, -0.128, 1.463, 0.0003, 0.0003),
            ],
        },
    ]

    objects = []
    audits = []
    sides = 8
    radius_scale_x = 0.70
    radius_scale_y = 0.72
    total_alignment_sections = 0
    max_abs_y_shift_m = 0.0
    for spec in specs:
        source_sections = spec["sections"]
        sections = []
        section_alignment = []
        for x, y, z, radius_x, radius_y in source_sections:
            aligned_y, alignment = align_section_to_surface(x, y, z)
            sections.append((x, aligned_y, z, radius_x, radius_y))
            section_alignment.append(alignment)
            total_alignment_sections += 1
            max_abs_y_shift_m = max(max_abs_y_shift_m, abs(alignment["delta_y_m"]))
        vertices = []
        faces = []
        for x, y, z, radius_x, radius_y in sections:
            for side in range(sides):
                angle = (2.0 * math.pi * side) / sides
                vertices.append((
                    float(x) + (float(radius_x) * radius_scale_x) * math.cos(angle),
                    float(y) + (float(radius_y) * radius_scale_y) * math.sin(angle),
                    float(z),
                ))
        for ring in range(len(sections) - 1):
            top = ring * sides
            bottom = (ring + 1) * sides
            for side in range(sides):
                next_side = (side + 1) % sides
                faces.append((
                    top + side,
                    bottom + side,
                    bottom + next_side,
                    top + next_side,
                ))
        faces.append(tuple(range(sides - 1, -1, -1)))
        last = (len(sections) - 1) * sides
        faces.append(tuple(last + side for side in range(sides)))

        mesh = bpy.data.meshes.new(spec["name"] + "_Mesh")
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(mesh)
        bm.free()
        for polygon in mesh.polygons:
            polygon.use_smooth = True
        mesh.materials.append(material)
        obj = bpy.data.objects.new(spec["name"], mesh)
        scene.collection.objects.link(obj)
        objects.append(obj)
        audits.append({
            "name": obj.name,
            "role": spec["role"],
            "section_count": len(sections),
            "vertex_count": len(mesh.vertices),
            "face_count": len(mesh.polygons),
            "z_min_m": round(min(point[2] for point in sections), 5),
            "z_max_m": round(max(point[2] for point in sections), 5),
            "max_half_width_source_m": round(max(point[3] for point in sections), 5),
            "max_half_depth_source_m": round(max(point[4] for point in sections), 5),
            "max_half_width_m": round(max(point[3] for point in sections) * radius_scale_x, 5),
            "max_half_depth_m": round(max(point[4] for point in sections) * radius_scale_y, 5),
            "material_name": material.name,
            "uv_required": False,
            "surface_alignment": section_alignment,
        })

    return objects, {
        "status": "APPLIED",
        "reference": "Bảng giới thiệu nhân vật Lý Lâm Lam.png",
        "surface_alignment": {
            "status": "APPLIED",
            "method": "Ray-cast from the camera-facing side through the base head mesh and original hair mesh at every strand control point; place centerline 1.2 mm in front of the frontmost hit.",
            "surface_offset_m": surface_offset_m,
            "control_point_count": total_alignment_sections,
            "max_abs_centerline_y_shift_m": round(max_abs_y_shift_m, 6),
            "all_points_sampled": total_alignment_sections == sum(len(spec["sections"]) for spec in specs),
            "note": "Only Y depth is adapted to sampled surface positions; X/Z centerline paths, V362 radius scales, strand material, head/face/body and original hair texture stay unchanged."
        },
        "reference_dimensions_px": [1214, 1295],
        "reference_sha256": "0be925c095166289727c597690b57ed31d23fcbf0a77f7f517d1928098f3c575",
        "strand_count": len(objects),
        "material_name": material.name,
        "material_settings": {
            "base_color_linear_rgba": [0.030, 0.0110, 0.0060, 1.0],
            "radius_scale_x": radius_scale_x,
            "radius_scale_y": radius_scale_y,
            "roughness": 0.80,
            "metallic": 0.0,
            "specular_ior_level": 0.11,
            "coat_weight": 0.0,
        },
        "geometry_method": "six tapered, smooth solid-color strand meshes; x half-width scaled to 70%, y half-depth scaled to 72%; same centerline paths, warmer dark-brown material; eight-sided rings; no source hair UVs or textures changed",
        "scope": "refines only the six added forehead/temple strands by reducing width/depth and warming their dark-brown material; original hair, face, eyes, iris pixels, necklace, body silhouette, facial profile, smile and morph recipes remain unchanged",
        "strands": audits,
        "gltf_expected_nodes": ["V386_Baked_" + item["name"] for item in audits],
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
        raise RuntimeError("V386 cannot find the long01 hair diffuse image")
    scored.sort(key=lambda row: (-row[0], row[1].name.lower()))
    return scored[0][1], scored[0][2]


def make_darkened_hair_image(source_image):
    """Reduce highlights baked into the source diffuse while preserving alpha."""
    import numpy as np

    width, height = int(source_image.size[0]), int(source_image.size[1])
    channels = int(source_image.channels)
    if width < 128 or height < 128 or channels < 3:
        raise RuntimeError("V386 hair diffuse image has unexpected dimensions/channels")
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
    output_image.name = "V386_HairDiffuse_Darkened"
    output_image.pixels.foreach_set(raw)
    output_image.update()
    output_image["v386_source_image"] = source_image.name
    output_image["v386_processing"] = "luminance-weighted highlight compression; RGB darkened and warmed; alpha preserved"
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
    material = bpy.data.materials.new("V386_GltfCompatibleHair")
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
    texture.label = "V386 darkened hair diffuse — explicit UV map"
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
            raise RuntimeError("V386 hair object has no active UV map: " + obj.name)
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


def _rgb_to_hsv_array(rgb, np):
    """Vectorized HSV conversion for linear RGB arrays in [0,1]."""
    r = rgb[:, 0]
    g = rgb[:, 1]
    b = rgb[:, 2]
    maximum = np.max(rgb, axis=1)
    minimum = np.min(rgb, axis=1)
    delta = maximum - minimum
    hue = np.zeros_like(maximum)
    nonzero = delta > 1e-8
    red_max = nonzero & (maximum == r)
    green_max = nonzero & (maximum == g)
    blue_max = nonzero & (maximum == b)
    hue[red_max] = ((g[red_max] - b[red_max]) / delta[red_max]) % 6.0
    hue[green_max] = ((b[green_max] - r[green_max]) / delta[green_max]) + 2.0
    hue[blue_max] = ((r[blue_max] - g[blue_max]) / delta[blue_max]) + 4.0
    hue = hue / 6.0
    saturation = np.zeros_like(maximum)
    nonblack = maximum > 1e-8
    saturation[nonblack] = delta[nonblack] / maximum[nonblack]
    return hue, saturation, maximum


def find_wardrobe_diffuse_image(obj, role):
    scored = []
    for material in getattr(obj.data, "materials", []):
        if not material or not material.use_nodes or not material.node_tree:
            continue
        for node in material.node_tree.nodes:
            if node.type != "TEX_IMAGE" or not getattr(node, "image", None):
                continue
            image = node.image
            name = image.name.lower()
            node_name = node.name.lower()
            if any(token in name or token in node_name for token in ("normal", "roughness", "metallic", "specular", "opacity", "alpha")):
                continue
            score = 10
            if "diffuse" in name or "albedo" in name or "basecolor" in name or "base_color" in name:
                score += 50
            if role == "sportsuit" and "sportsuit" in name:
                score += 60
            if role == "shoes" and "shoe" in name:
                score += 60
            if "diffuse" in node_name or "color" in node_name:
                score += 8
            if int(getattr(image, "channels", 3)) >= 3 and image.size[0] >= 128 and image.size[1] >= 128:
                score += 5
            scored.append((score, image))
    if not scored:
        raise RuntimeError("V386 could not find a diffuse/albedo texture for wardrobe object " + obj.name)
    scored.sort(key=lambda row: (-row[0], row[1].name.lower()))
    return scored[0][1]


def process_wardrobe_texture(source_image, role):
    """Recolor blue sportswear to dark teal and blue shoe panels to light neutral gray.

    Alpha is preserved. The sportsuit's existing dark fabric regions stay charcoal;
    its bright neutral stripe/patch pixels are darkened so the leggings read as
    charcoal rather than having distracting white edge marks.
    """
    import numpy as np

    width, height = int(source_image.size[0]), int(source_image.size[1])
    channels = int(source_image.channels)
    if width < 64 or height < 64 or channels < 3:
        raise RuntimeError("V386 unexpected wardrobe texture dimensions/channels: " + repr((width, height, channels)))
    raw = np.empty(len(source_image.pixels), dtype=np.float32)
    source_image.pixels.foreach_get(raw)
    source_pixels = raw.reshape((-1, channels))
    pixels = source_pixels.copy()
    rgb = pixels[:, :3]
    source_rgb_mean = float(np.mean(rgb))
    hue, saturation, value = _rgb_to_hsv_array(rgb, np)

    if channels >= 4:
        alpha = source_pixels[:, 3].copy()
        source_alpha_mean = float(np.mean(alpha))
        visible = alpha > 0.08
    else:
        alpha = None
        source_alpha_mean = 1.0
        visible = np.ones(len(rgb), dtype=bool)

    blue_mask = visible & (hue >= 0.53) & (hue <= 0.78) & (saturation >= 0.18) & (value >= 0.035)
    orange_mask = visible & (((hue >= 0.015) & (hue <= 0.14)) | (hue >= 0.94)) & (saturation >= 0.30) & (value >= 0.08)
    neutral_bright_mask = visible & (saturation <= 0.16) & (value >= 0.58)

    counts = {
        "blue_pixels_detected": int(np.count_nonzero(blue_mask)),
        "warm_orange_pixels_detected": int(np.count_nonzero(orange_mask)),
        "neutral_bright_pixels_detected": int(np.count_nonzero(neutral_bright_mask)),
    }
    if role == "sportsuit":
        if counts["blue_pixels_detected"] < 100:
            raise RuntimeError("V386 expected blue sportsuit texture regions to recolor: " + repr(counts))
        # Dark teal with preserved fabric shading. The low red channel and green-led
        # teal hue intentionally replace the blue base while retaining knit shading.
        shade = np.clip(0.52 + 0.64 * value[blue_mask], 0.48, 0.92)
        rgb[blue_mask, 0] = 0.010 * shade
        rgb[blue_mask, 1] = 0.105 * shade
        rgb[blue_mask, 2] = 0.091 * shade

        # Desaturate and darken orange trim into a restrained deep-teal seam.
        if counts["warm_orange_pixels_detected"]:
            seam_shade = np.clip(0.40 + 0.42 * value[orange_mask], 0.35, 0.72)
            rgb[orange_mask, 0] = 0.009 * seam_shade
            rgb[orange_mask, 1] = 0.060 * seam_shade
            rgb[orange_mask, 2] = 0.050 * seam_shade

        # Turn high-value neutral stripe/patch areas into subtle charcoal seam detail.
        # This avoids bright white bars on the leggings and visible pale ankle patches.
        darken_neutral = neutral_bright_mask & ~blue_mask & ~orange_mask
        if counts["neutral_bright_pixels_detected"]:
            neutral_value = np.clip(0.045 + 0.045 * value[darken_neutral], 0.035, 0.11)
            rgb[darken_neutral, 0] = neutral_value
            rgb[darken_neutral, 1] = neutral_value
            rgb[darken_neutral, 2] = neutral_value
        counts["blue_pixels_recolored"] = counts["blue_pixels_detected"]
        counts["orange_pixels_muted"] = counts["warm_orange_pixels_detected"]
        counts["bright_neutral_pixels_darkened"] = int(np.count_nonzero(darken_neutral))
        processing = "blue fabric -> dark teal; orange piping -> muted deep teal; bright neutral trouser/ankle patches -> charcoal; alpha unchanged"
    elif role == "shoes":
        if counts["blue_pixels_detected"] < 100:
            raise RuntimeError("V386 expected blue shoe texture regions to recolor: " + repr(counts))
        # Blue panels become neutral sneaker gray; keep dark shadows and sole pixels
        # untouched for shoe shape/detail.
        gray_value = np.clip(0.30 + 0.56 * value[blue_mask], 0.36, 0.88)
        rgb[blue_mask, 0] = gray_value
        rgb[blue_mask, 1] = gray_value * 0.99
        rgb[blue_mask, 2] = gray_value * 0.96
        counts["blue_pixels_recolored_to_gray"] = counts["blue_pixels_detected"]
        processing = "blue shoe panels -> neutral white/gray; dark sole/detail and alpha unchanged"
    else:
        raise ValueError("Unsupported V386 wardrobe role: " + role)

    np.clip(rgb, 0.0, 1.0, out=rgb)
    alpha_preserved = True
    if alpha is not None:
        alpha_preserved = bool(np.array_equal(pixels[:, 3], alpha))
        if not alpha_preserved:
            raise RuntimeError("V386 alpha channel changed while recoloring " + role)

    image_copy = source_image.copy()
    image_copy.name = "V386_" + ("SportsuitDarkTeal" if role == "sportsuit" else "SneakerNeutralGray")
    image_copy.pixels.foreach_set(pixels.reshape(-1))
    image_copy.update()
    image_copy["v386_source_image"] = source_image.name
    image_copy["v386_role"] = role
    image_copy["v386_processing"] = processing
    try:
        image_copy.pack()
    except Exception:
        pass
    return image_copy, {
        "role": role,
        "source_image_name": source_image.name,
        "processed_image_name": image_copy.name,
        "width": width,
        "height": height,
        "channels": channels,
        "alpha_preserved": alpha_preserved,
        "source_rgb_mean_linear": source_rgb_mean,
        "processed_rgb_mean_linear": float(np.mean(rgb)),
        "source_alpha_mean": source_alpha_mean,
        "processed_alpha_mean": float(np.mean(pixels[:, 3])) if channels >= 4 else 1.0,
        "pixel_counts": counts,
        "processing": processing,
    }


def make_gltf_compatible_wardrobe_material(role, image, uv_map_name):
    material = bpy.data.materials.new("V386_GltfWardrobe_" + role)
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    output.location = (420, 40)
    principled = tree.nodes.new("ShaderNodeBsdfPrincipled")
    principled.location = (120, 40)
    principled.inputs["Roughness"].default_value = 0.78
    if "Metallic" in principled.inputs:
        principled.inputs["Metallic"].default_value = 0.0
    if "Specular IOR Level" in principled.inputs:
        principled.inputs["Specular IOR Level"].default_value = 0.20
    uv_node = tree.nodes.new("ShaderNodeUVMap")
    uv_node.uv_map = uv_map_name
    uv_node.location = (-600, 40)
    texture = tree.nodes.new("ShaderNodeTexImage")
    texture.image = image
    texture.interpolation = "Linear"
    texture.extension = "REPEAT"
    texture.location = (-340, 40)
    texture.label = "V386 processed wardrobe diffuse — explicit UV"
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
    material.diffuse_color = (0.03, 0.13, 0.12, 1.0) if role == "sportsuit" else (0.63, 0.64, 0.65, 1.0)
    return material, alpha_enabled


def prepare_reference_wardrobe_colors(clothing_objects):
    role_tokens = {
        "sportsuit": ("female_sportsuit01",),
        "shoes": ("shoes06",),
    }
    report = {
        "status": "APPLIED",
        "reference_targets": {
            "top": "dark teal cropped athletic top",
            "bottom": "dark charcoal trousers with bright stripes/ankle patches muted",
            "footwear": "neutral white/gray sneakers",
        },
        "scope": "processed source diffuse textures and glTF-compatible materials for sportsuit and shoes only; no wardrobe geometry change",
        "materials": [],
    }
    found = set()
    for obj in clothing_objects:
        if obj.type != "MESH":
            continue
        name = obj.name.lower()
        role = next((candidate for candidate, tokens in role_tokens.items() if any(token in name for token in tokens)), None)
        if role is None:
            continue
        source_image = find_wardrobe_diffuse_image(obj, role)
        uv_name = get_active_uv_name(obj)
        if not uv_name:
            raise RuntimeError("V386 wardrobe object has no active UV map: " + obj.name)
        uv_audit = activate_uv_layer(obj, uv_name)
        image_copy, image_audit = process_wardrobe_texture(source_image, role)
        material, alpha_enabled = make_gltf_compatible_wardrobe_material(role, image_copy, uv_name)
        obj.data.materials.clear()
        obj.data.materials.append(material)
        report["materials"].append({
            "object": obj.name,
            "role": role,
            "source_uv_audit": uv_audit,
            "image_audit": image_audit,
            "material_name": material.name,
            "uv_map_name": uv_name,
            "alpha_enabled": alpha_enabled,
            "roughness": 0.78,
            "specular_ior_level": 0.20,
        })
        found.add(role)
    if found != {"sportsuit", "shoes"}:
        raise RuntimeError("V386 did not recolor both required wardrobe meshes: " + repr(sorted(found)))
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
    # V386 replaces the source hair material after this helper with an explicit
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
        if obj.type == "MESH" and obj.name != "V386_StudioFloor":
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


def _face_profile_measurements(points):
    """Measure frontal cheek/jaw/chin widths with one fixed neutral-profile method."""
    bands = {
        "cheeks": (1.39, 1.465),
        "jaw": (1.33, 1.405),
        "chin": (1.30, 1.35),
    }
    result = {}
    for name, (z_low, z_high) in bands.items():
        slab = [
            point for point in points
            if z_low <= point.z <= z_high and point.y <= -0.055 and abs(point.x) <= 0.12
        ]
        if len(slab) < 20:
            result[name] = {
                "status": "INSUFFICIENT_VERTICES",
                "vertex_count": len(slab),
                "z_band_m": [z_low, z_high],
            }
            continue
        width = 2.0 * _linear_quantile([abs(point.x) for point in slab], 0.85)
        result[name] = {
            "status": "MEASURED",
            "vertex_count": len(slab),
            "z_band_m": [z_low, z_high],
            "robust_frontal_width_x_m": round(float(width), 6),
        }
    return result


def apply_armhole_skin_tuck(basemesh):
    """Narrow only the exposed upper-arm skin cap near the armhole by at most 12 mm.

    The shirt width is intentionally kept at the visually-tested A22 value.
    A localized, smooth inward shift of the skin directly beneath the armhole
    helps the arm cap sit behind the retained shirt edge without adding a broad
    shoulder flap or moving the central torso, face, hair, clothing or trousers.
    """
    obj = basemesh
    if obj.type != "MESH":
        raise RuntimeError("V386 armhole skin tuck requires the base Human mesh")
    shape_keys = getattr(obj.data, "shape_keys", None)
    if shape_keys is not None and len(shape_keys.key_blocks):
        raise RuntimeError("V386 armhole skin tuck refuses to edit a body mesh with shape keys")

    matrix = obj.matrix_world.copy()
    inverse = matrix.inverted()
    max_inward_shift_m = 0.012
    lateral_inner_m = 0.16
    lateral_outer_m = 0.30
    vertical_start_z_m = 1.18
    vertical_full_z_m = 1.24
    vertical_full_end_z_m = 1.29
    vertical_end_z_m = 1.34

    selected_shifts = []
    selected_before_x = []
    selected_after_x = []
    protected_torso_displacements = []
    protected_lower_body_displacements = []
    protected_torso_count = 0
    protected_lower_body_count = 0
    candidate_vertex_count = 0

    for vertex in obj.data.vertices:
        original = matrix @ vertex.co
        abs_x = abs(float(original.x))
        z = float(original.z)

        lateral_weight = _v386_smooth_unit(
            (abs_x - lateral_inner_m) / (lateral_outer_m - lateral_inner_m)
        )
        rise_weight = _v386_smooth_unit(
            (z - vertical_start_z_m) / (vertical_full_z_m - vertical_start_z_m)
        )
        fall_weight = _v386_smooth_unit(
            (vertical_end_z_m - z) / (vertical_end_z_m - vertical_full_end_z_m)
        )
        weight = lateral_weight * rise_weight * fall_weight

        if lateral_inner_m < abs_x < lateral_outer_m and vertical_start_z_m < z < vertical_end_z_m:
            candidate_vertex_count += 1

        if abs_x <= lateral_inner_m + 1e-9:
            protected_torso_displacements.append(0.0)
            protected_torso_count += 1
        if z <= 1.16 + 1e-9:
            protected_lower_body_displacements.append(0.0)
            protected_lower_body_count += 1

        if weight <= 0.01:
            continue
        shift = max_inward_shift_m * weight
        new_abs_x = max(0.0, abs_x - shift)
        side_sign = 1.0 if float(original.x) >= 0.0 else -1.0
        transformed = Vector((side_sign * new_abs_x, float(original.y), float(original.z)))
        displacement = float((transformed - original).length)
        vertex.co = inverse @ transformed

        selected_shifts.append(shift)
        selected_before_x.append(abs_x)
        selected_after_x.append(new_abs_x)

    obj.data.update()
    bpy.context.view_layer.update()

    moved_count = len(selected_shifts)
    mean_shift = sum(selected_shifts) / moved_count if moved_count else 0.0
    max_shift = max(selected_shifts) if selected_shifts else 0.0
    mean_lateral_reduction = (
        sum(a - b for a, b in zip(selected_before_x, selected_after_x)) / moved_count
        if moved_count else 0.0
    )

    audit = {
        "status": "APPLIED" if moved_count >= 25 else "INSUFFICIENT_SKIN_CAP_VERTICES",
        "object": obj.name,
        "scope": "base skin vertices in the lateral upper-arm/armhole transition only",
        "zone_abs_x_m": [lateral_inner_m, lateral_outer_m],
        "zone_z_m": [vertical_start_z_m, vertical_end_z_m],
        "vertical_full_weight_z_m": [vertical_full_z_m, vertical_full_end_z_m],
        "candidate_vertex_count": candidate_vertex_count,
        "moved_vertex_count": moved_count,
        "max_inward_shift_m": max_inward_shift_m,
        "mean_inward_shift_m": round(mean_shift, 6),
        "mean_lateral_reduction_m": round(mean_lateral_reduction, 6),
        "max_vertex_displacement_m": round(max_shift, 6),
        "protected_torso_vertex_count": protected_torso_count,
        "protected_torso_max_displacement_m": max(protected_torso_displacements, default=0.0),
        "protected_lower_body_vertex_count": protected_lower_body_count,
        "protected_lower_body_max_displacement_m": max(protected_lower_body_displacements, default=0.0),
        "preserved": [
            "central torso x<=0.16 m",
            "lower body z<=1.16 m",
            "upper head/face/hair and all clothing geometry",
            "12 facial morph controls are loaded after this bounded skin adjustment",
        ],
    }
    if candidate_vertex_count < 30 or moved_count < 25:
        raise RuntimeError("V386 armhole skin tuck affected too few upper-arm cap vertices: " + repr(audit))
    if not (0.004 <= mean_shift <= 0.012) or max_shift > 0.0120001:
        raise RuntimeError("V386 armhole skin tuck moved skin outside the intended 4-12 mm range: " + repr(audit))
    if protected_torso_count < 25 or protected_lower_body_count < 25:
        raise RuntimeError("V386 armhole skin tuck could not establish protected torso/lower-body vertices: " + repr(audit))
    if max(protected_torso_displacements, default=0.0) > 1e-7 or max(protected_lower_body_displacements, default=0.0) > 1e-7:
        raise RuntimeError("V386 armhole skin tuck unexpectedly moved a protected region: " + repr(audit))
    return audit


def apply_face_profile_refinement(basemesh):
    """Subtly fuller cheek and tapered lower jaw on the skin face only.

    Uses soft z envelopes and a front-facing gate so the back of the skull,
    ears, hair, eyes, clothes and the V358 iris/material treatment are untouched.
    Runs before facial shape targets load, so the 12 morph controls are generated
    from the refined geometry rather than being broken by a post-morph edit.
    """
    if basemesh.type != "MESH":
        raise RuntimeError("V386 face refinement requires the base skin mesh")

    matrix = basemesh.matrix_world.copy()
    inverse = matrix.inverted()
    shape_keys = getattr(basemesh.data, "shape_keys", None)
    key_blocks = list(shape_keys.key_blocks) if shape_keys and shape_keys.key_blocks else []
    basis = next((key for key in key_blocks if key.name == "Basis"), None)
    basis_points = [
        matrix @ point.co
        for point in (basis.data if basis is not None else basemesh.data.vertices)
    ]
    before_metrics = _face_profile_measurements(basis_points)
    if any(row.get("status") != "MEASURED" for row in before_metrics.values()):
        raise RuntimeError("V386 could not establish all baseline face-width measurements: " + repr(before_metrics))

    def transform_point(local_co):
        point = matrix @ local_co
        z = float(point.z)
        x = float(point.x)
        y = float(point.y)

        # Camera/front side is negative Y. Fade the adjustment out before the
        # profile wraps around the head; do not alter the back of the skull.
        front_raw = max(0.0, min(1.0, (-y - 0.035) / 0.065))
        front_gate = front_raw * front_raw * (3.0 - 2.0 * front_raw)
        central_gate = _central_x_weight(x, 0.065, 0.12)

        cheek = _smooth_band_weight(z, center=1.43, half_width=0.038)
        jaw = _smooth_band_weight(z, center=1.37, half_width=0.055)
        chin = _smooth_band_weight(z, center=1.32, half_width=0.026)
        influence = front_gate * central_gate
        x_scale = 1.0 + (0.035 * cheek * influence) - (0.080 * jaw * influence) - (0.040 * chin * influence)

        shaped = Vector((x * x_scale, y, z))
        displacement = (shaped - point).length
        return inverse @ shaped, float(displacement)

    edited_coordinates = 0
    max_displacement = 0.0
    if key_blocks:
        for key_block in key_blocks:
            for point in key_block.data:
                new_co, delta = transform_point(point.co.copy())
                point.co = new_co
                edited_coordinates += 1
                max_displacement = max(max_displacement, delta)
    else:
        for vertex in basemesh.data.vertices:
            new_co, delta = transform_point(vertex.co.copy())
            vertex.co = new_co
            edited_coordinates += 1
            max_displacement = max(max_displacement, delta)

    basemesh.data.update()
    bpy.context.view_layer.update()
    final_matrix = basemesh.matrix_world.copy()
    basis_after = next(
        (key for key in basemesh.data.shape_keys.key_blocks if key.name == "Basis"),
        None,
    ) if basemesh.data.shape_keys else None
    after_points = [
        final_matrix @ point.co
        for point in (basis_after.data if basis_after is not None else basemesh.data.vertices)
    ]
    after_metrics = _face_profile_measurements(after_points)

    for region, before in before_metrics.items():
        after = after_metrics[region]
        if before["status"] != "MEASURED" or after["status"] != "MEASURED":
            raise RuntimeError("V386 face profile measurement failed after adjustment: " + repr({region: [before, after]}))

    cheek_gain = (
        after_metrics["cheeks"]["robust_frontal_width_x_m"]
        / before_metrics["cheeks"]["robust_frontal_width_x_m"]
    ) - 1.0
    jaw_reduction = 1.0 - (
        after_metrics["jaw"]["robust_frontal_width_x_m"]
        / before_metrics["jaw"]["robust_frontal_width_x_m"]
    )
    chin_reduction = 1.0 - (
        after_metrics["chin"]["robust_frontal_width_x_m"]
        / before_metrics["chin"]["robust_frontal_width_x_m"]
    )
    if not (0.0 < cheek_gain < 0.05 and 0.005 < jaw_reduction < 0.08 and 0.002 < chin_reduction < 0.05):
        raise RuntimeError("V386 facial profile change did not stay within the intended subtle ranges: " + repr({
            "cheek_gain": cheek_gain,
            "jaw_reduction": jaw_reduction,
            "chin_reduction": chin_reduction,
            "before": before_metrics,
            "after": after_metrics,
        }))
    if max_displacement <= 0.0005 or max_displacement > 0.006:
        raise RuntimeError("V386 face displacement fell outside the safe 0.5–6 mm range: " + repr(max_displacement))

    return {
        "status": "APPLIED",
        "baseline_version": "V359",
        "scope": "stronger but bounded base skin facial profile; frontal cheek/jaw/chin bands",
        "zones": {
            "cheeks": {"center_z_m": 1.43, "half_width_m": 0.038, "max_lateral_scale": 1.0350},
            "jaw": {"center_z_m": 1.37, "half_width_m": 0.055, "max_lateral_scale": 0.920},
            "chin": {"center_z_m": 1.32, "half_width_m": 0.026, "max_lateral_scale": 0.9600},
            "front_falloff_y_m": [-0.035, -0.100],
            "central_x_falloff_m": [0.065, 0.12],
        },
        "edited_coordinate_count": edited_coordinates,
        "max_vertex_displacement_m": round(max_displacement, 7),
        "before_metrics": before_metrics,
        "after_metrics": after_metrics,
        "measured_changes": {
            "cheek_width_gain_fraction": round(float(cheek_gain), 6),
            "jaw_width_reduction_fraction": round(float(jaw_reduction), 6),
            "chin_width_reduction_fraction": round(float(chin_reduction), 6),
        },
        "preserved": [
            "V358 iris pixel treatment, alpha and UVs",
            "eye geometry/materials and eye accessory meshes",
            "hair, necklace, clothing and V340 lower-body silhouette",
            "all 12 facial morph names and idle animation, generated after this geometry refinement",
        ],
    }


def audit_eye_geometry(character_objects, basemesh):
    """Measure existing eye-mesh bounds and add a tight evidence target; never edits geometry."""
    candidates = [
        obj for obj in character_objects
        if obj.type == "MESH" and obj.name.rsplit(".", 1)[-1].lower() == "high-poly"
    ]
    if len(candidates) != 1:
        raise RuntimeError("V386 expected one high-poly eye mesh; found " + repr([obj.name for obj in candidates]))
    eye_obj = candidates[0]
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = eye_obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
    try:
        matrix = evaluated.matrix_world.copy()
        points = [matrix @ vertex.co for vertex in mesh.vertices]
        adjacency = [set() for _ in points]
        for edge in mesh.edges:
            a, b = int(edge.vertices[0]), int(edge.vertices[1])
            adjacency[a].add(b)
            adjacency[b].add(a)
    finally:
        evaluated.to_mesh_clear()
    if len(points) < 100:
        raise RuntimeError("V386 eye mesh is unexpectedly sparse: " + str(len(points)))

    minimum = [min(float(p[i]) for p in points) for i in range(3)]
    maximum = [max(float(p[i]) for p in points) for i in range(3)]
    size = [maximum[i] - minimum[i] for i in range(3)]
    center = [(minimum[i] + maximum[i]) * 0.5 for i in range(3)]

    # Connected components are diagnostic only: some versions ship the two eyeballs
    # as separate islands, while others join them into one component.
    unseen = set(range(len(points)))
    components = []
    while unseen:
        root = next(iter(unseen))
        stack = [root]
        unseen.remove(root)
        indices = []
        while stack:
            current = stack.pop()
            indices.append(current)
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    stack.append(neighbor)
        if len(indices) < 20:
            continue
        comp_points = [points[i] for i in indices]
        comp_min = [min(float(p[k]) for p in comp_points) for k in range(3)]
        comp_max = [max(float(p[k]) for p in comp_points) for k in range(3)]
        comp_center = [(comp_min[k] + comp_max[k]) * 0.5 for k in range(3)]
        components.append({
            "vertex_count": len(indices),
            "min_m": [round(v, 6) for v in comp_min],
            "max_m": [round(v, 6) for v in comp_max],
            "size_m": [round(comp_max[k] - comp_min[k], 6) for k in range(3)],
            "center_m": [round(v, 6) for v in comp_center],
        })
    components.sort(key=lambda row: row["center_m"][0])

    body_points = _world_mesh_points(basemesh)
    body_z_min = min(float(p.z) for p in body_points)
    body_z_max = max(float(p.z) for p in body_points)
    body_height = body_z_max - body_z_min
    head_slab = [
        p for p in body_points
        if body_z_min + body_height * 0.82 <= p.z <= body_z_min + body_height * 0.985
    ]
    if len(head_slab) < 100:
        raise RuntimeError("V386 cannot find enough base-mesh head vertices for comparison")
    head_width = max(float(p.x) for p in head_slab) - min(float(p.x) for p in head_slab)
    eye_span_to_head_width = size[0] / head_width if head_width > 1e-8 else 0.0
    if size[0] <= 0 or size[1] <= 0 or size[2] <= 0 or head_width <= 0:
        raise RuntimeError("V386 measured invalid eye/head bounds")

    return {
        "status": "MEASURED_ONLY",
        "geometry_changed": False,
        "eye_object": eye_obj.name,
        "vertex_count": len(points),
        "connected_component_count_ge20_vertices": len(components),
        "components": components,
        "eye_bounds_min_m": [round(v, 6) for v in minimum],
        "eye_bounds_max_m": [round(v, 6) for v in maximum],
        "eye_bounds_size_m": [round(v, 6) for v in size],
        "eye_center_m": [round(v, 6) for v in center],
        "eye_front_surface_y_m": round(minimum[1], 6),
        "head_band_z_range_m": [
            round(body_z_min + body_height * 0.82, 6),
            round(body_z_min + body_height * 0.985, 6),
        ],
        "head_band_vertex_count": len(head_slab),
        "head_band_width_x_m": round(head_width, 6),
        "eye_pair_span_to_head_band_width_ratio": round(eye_span_to_head_width, 6),
        "method_warning": "This is a bounding-box ratio, not a clinical anatomy standard or a likeness score. Use the tight render and the approved reference for visual judgement.",
    }


def setup_studio(scene, bounds, eye_geometry=None, necklace_audit=None):
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
        scene.world = bpy.data.worlds.new("V386StudioWorld")
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
    area_light("V386_Key_Softbox", (-2.8, -3.3, 3.2), subject, 300.0, (1.0, 0.83, 0.72), 2.8)
    area_light("V386_Fill_Softbox", (2.6, -2.2, 1.8), subject, 150.0, (0.70, 0.82, 1.0), 2.4)
    area_light("V386_Rim_Softbox", (0.8, 1.8, 2.8), subject, 240.0, (0.78, 0.86, 1.0), 2.0)
    area_light("V386_Top_Softbox", (0.0, -0.5, 3.8), subject, 90.0, (1.0, 0.91, 0.82), 2.0)

    floor_mat = bpy.data.materials.new("V386_MatteStudioFloor")
    floor_mat.diffuse_color = (0.055, 0.07, 0.09, 1.0)
    floor_mat.use_nodes = True
    p = next((n for n in floor_mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if p:
        p.inputs["Base Color"].default_value = (0.055, 0.07, 0.09, 1.0)
        p.inputs["Roughness"].default_value = 0.88
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, -0.006))
    floor = bpy.context.object
    floor.name = "V386_StudioFloor"
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
        "front": create_camera("V386_Camera_Front", (0.0, front_y, center_z), (0, 0, center_z), ortho=2.15),
        "three_quarter": create_camera("V386_Camera_ThreeQuarter", (2.0, front_y * 0.88, center_z), (0, 0, center_z), ortho=2.28),
        "side": create_camera("V386_Camera_Side", (abs(front_y), 0.0, center_z), (0, 0, center_z), ortho=1.92),
    }
    # Face close-up uses a perspective lens to retain natural facial proportions.
    cameras["face_closeup"] = create_camera(
        "V386_Camera_FaceCloseup", (0.0, front_y * 0.54, min(1.46, bounds["size"][2] * 0.91)),
        (0.0, 0.0, min(1.42, bounds["size"][2] * 0.87)), lens=75,
    )
    if eye_geometry is not None:
        eye_center = eye_geometry["eye_center_m"]
        eye_front_y = eye_geometry["eye_front_surface_y_m"]
        cameras["eye_closeup"] = create_camera(
            "V386_Camera_EyeCloseup",
            (eye_center[0], eye_front_y - 0.42, eye_center[2]),
            tuple(eye_center),
            lens=75,
        )
    if necklace_audit is not None:
        pendant = necklace_audit.get("pendant_surface_sample", {})
        necklace_y = float(pendant.get("pendant_center_y_m", -0.2))
        necklace_z = float(pendant.get("pendant_center_z_m", 1.283))
        cameras["necklace_closeup"] = create_camera(
            "V386_Camera_NecklaceCloseup",
            (0.0, necklace_y - 0.62, necklace_z + 0.105),
            (0.0, necklace_y, necklace_z + 0.018),
            lens=90,
        )
    return cameras, floor


def render_evidence(scene, cameras, output_dir, character_bounds):
    images = []
    for label, camera in cameras.items():
        scene.camera = camera
        if label == "face_closeup":
            scene.render.resolution_x = 1000
            scene.render.resolution_y = 1000
        elif label == "eye_closeup":
            scene.render.resolution_x = 1000
            scene.render.resolution_y = 700
        elif label == "necklace_closeup":
            scene.render.resolution_x = 1000
            scene.render.resolution_y = 1000
        else:
            scene.render.resolution_x = 1000
            scene.render.resolution_y = 1300
        path = os.path.join(output_dir, "v386-" + label.replace("_", "-") + ".png")
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
                "reason": "V386 isolate facial accessory material/UV artifacts; skin base texture remains.",
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
        neutral_mesh.name = "V386_Baked_" + source.data.name
        baked = bpy.data.objects.new("V386_Baked_" + source.name, neutral_mesh)
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

    root = bpy.data.objects.new("Lam_CharacterRoot_V386", None)
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

    temp_path = os.path.join(output_dir, ".v386-embedded-hair-check.png")
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
    material = bpy.data.materials.new("V386_GltfCompatibleSkin")
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
    texture.label = "V386 skin diffuse — explicit UV map"
    tree.links.new(uv_node.outputs["UV"], texture.inputs["Vector"])
    tree.links.new(texture.outputs["Color"], principled.inputs["Base Color"])
    tree.links.new(principled.outputs["BSDF"], output.inputs["Surface"])
    material.diffuse_color = (0.76, 0.48, 0.36, 1.0)
    return material



def build_iris_annulus_mask(width, height):
    """Mask only the two iris annuli in the 1024x1024 brown_eye atlas.

    Blender image pixels are traversed bottom-up. The calibrated centres below
    correspond to the visible upper-right and lower-left iris circles in the
    existing atlas. Pupil cores and surrounding sclera are feathered out.
    """
    import numpy as np

    if width < 512 or height < 512:
        raise RuntimeError("V386 expected a brown_eye atlas at least 512x512")
    sx = width / 1024.0
    sy = height / 1024.0
    scale = min(sx, sy)
    yy, xx = np.indices((height, width), dtype=np.float32)
    # Atlas preview coordinates converted from top-left to Blender bottom-up rows.
    centers = [
        (726.0 * sx, (1023.0 - 305.0) * sy),
        (292.0 * sx, (1023.0 - 728.0) * sy),
    ]

    def smoothstep(edge0, edge1, value):
        t = np.clip((value - edge0) / (edge1 - edge0), 0.0, 1.0)
        return t * t * (3.0 - 2.0 * t)

    mask = np.zeros((height, width), dtype=np.float32)
    for cx, cy in centers:
        radius = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        inner = smoothstep(37.0 * scale, 47.0 * scale, radius)
        outer = 1.0 - smoothstep(101.0 * scale, 117.0 * scale, radius)
        mask = np.maximum(mask, inner * outer)
    return mask, centers, scale


def make_warm_brown_iris_texture(source_image):
    """Move only iris RGB gently toward chestnut brown; preserve pupil, sclera, alpha and UVs."""
    import hashlib
    import numpy as np

    width, height = int(source_image.size[0]), int(source_image.size[1])
    channels = int(source_image.channels)
    if width < 512 or height < 512 or channels != 4:
        raise RuntimeError(
            "V386 expected an RGBA brown_eye texture at least 512x512; got "
            + repr({"size": [width, height], "channels": channels})
        )
    source_flat = np.empty(len(source_image.pixels), dtype=np.float32)
    source_image.pixels.foreach_get(source_flat)
    source_pixels = source_flat.reshape((height, width, channels))
    source_rgb = source_pixels[:, :, :3].copy()
    source_alpha = source_pixels[:, :, 3].copy()
    source_alpha_mean = float(np.mean(source_alpha))
    mask, centers, scale = build_iris_annulus_mask(width, height)
    coverage = float(np.mean(mask))
    if not (0.02 <= coverage <= 0.10):
        raise RuntimeError("V386 iris mask coverage outside expected range: " + repr(coverage))

    # Target is a muted warm chestnut in linear RGB. A bounded 30% mix keeps
    # the fibre texture/highlights while reducing the overly red/orange cast.
    target = np.asarray([0.13, 0.075, 0.03], dtype=np.float32)
    blend = (mask * 0.30)[:, :, None]
    processed_rgb = source_rgb + (target[None, None, :] - source_rgb) * blend
    np.clip(processed_rgb, 0.0, 1.0, out=processed_rgb)

    processed_pixels = np.empty_like(source_pixels)
    processed_pixels[:, :, :3] = processed_rgb
    processed_pixels[:, :, 3] = source_alpha

    # Copy the datablock so the original brown_eye image and its other users
    # are untouched. Preserve alpha values exactly and retain the original UV map.
    processed_image = source_image.copy()
    processed_image.name = "V386_WarmBrownIris"
    processed_image.pixels.foreach_set(processed_pixels.reshape(-1))
    processed_image.update()
    processed_image["v386_source_image_name"] = source_image.name
    processed_image["v386_adjustment"] = "30% linear-RGB blend toward muted chestnut inside two feathered iris annuli only; alpha unchanged"
    try:
        processed_image.pack()
    except Exception:
        pass

    # Verify the source datablock was not mutated while making the new image.
    source_after = np.empty(len(source_image.pixels), dtype=np.float32)
    source_image.pixels.foreach_get(source_after)
    if not np.array_equal(source_after, source_flat):
        raise RuntimeError("V386 modified the original brown_eye image while creating its derivative")

    source_iris = np.sum(source_rgb * mask[:, :, None], axis=(0, 1)) / max(float(mask.sum()), 1e-8)
    processed_iris = np.sum(processed_rgb * mask[:, :, None], axis=(0, 1)) / max(float(mask.sum()), 1e-8)
    source_global = np.mean(source_rgb, axis=(0, 1))
    processed_global = np.mean(processed_rgb, axis=(0, 1))
    outside = mask <= 1e-7
    outside_change = np.abs(processed_rgb - source_rgb)[outside] if np.any(outside) else np.zeros(1, dtype=np.float32)
    source_alpha_digest = hashlib.sha256(source_alpha.astype(np.float32).tobytes()).hexdigest()
    processed_alpha_digest = hashlib.sha256(processed_pixels[:, :, 3].astype(np.float32).tobytes()).hexdigest()
    alpha_preserved = np.array_equal(source_alpha, processed_pixels[:, :, 3])
    if not alpha_preserved or source_alpha_digest != processed_alpha_digest:
        raise RuntimeError("V386 did not preserve the brown_eye alpha channel exactly")

    def ratios(rgb):
        red = max(float(rgb[0]), 1e-8)
        return {"green_to_red": float(rgb[1]) / red, "blue_to_red": float(rgb[2]) / red}

    source_ratios = ratios(source_iris)
    processed_ratios = ratios(processed_iris)
    if processed_ratios["green_to_red"] <= source_ratios["green_to_red"] * 1.20:
        raise RuntimeError("V386 warm-brown transformation did not produce the expected warm-brown green/red shift: " + repr({
            "source": source_ratios, "processed": processed_ratios
        }))
    if processed_ratios["blue_to_red"] <= source_ratios["blue_to_red"] * 1.50:
        raise RuntimeError("V386 blue/red balance did not move toward warm brown: " + repr({
            "source": source_ratios, "processed": processed_ratios
        }))

    return processed_image, {
        "status": "APPLIED",
        "source_image_name": source_image.name,
        "processed_image_name": processed_image.name,
        "width": width,
        "height": height,
        "channels": channels,
        "mask_coverage": coverage,
        "iris_centers_blender_pixel_xy": [[round(x, 3), round(y, 3)] for x, y in centers],
        "feather_radii_reference_pixels": {"inner_fade": [37, 47], "outer_fade": [101, 117]},
        "scale_reference": scale,
        "target_linear_rgb": target.tolist(),
        "blend_strength": 0.30,
        "source_iris_mean_rgb_linear": source_iris.tolist(),
        "processed_iris_mean_rgb_linear": processed_iris.tolist(),
        "source_iris_channel_ratios": source_ratios,
        "processed_iris_channel_ratios": processed_ratios,
        "source_global_mean_rgb_linear": source_global.tolist(),
        "processed_global_mean_rgb_linear": processed_global.tolist(),
        "outside_mask_max_rgb_delta": float(np.max(outside_change)) if outside_change.size else 0.0,
        "alpha_preserved": alpha_preserved,
        "source_alpha_mean": source_alpha_mean,
        "source_alpha_sha256_float32": source_alpha_digest,
        "processed_alpha_sha256_float32": processed_alpha_digest,
        "source_datablock_unchanged": True,
        "scope": "iris annuli only; pupil cores, sclera, alpha channel and UV layout unchanged",
    }


def audit_embedded_iris_texture_png(payload, output_dir):
    """Decode the actual GLB-embedded eye image and remeasure iris RGB/alpha."""
    import numpy as np

    temp_path = os.path.join(output_dir, ".v386-embedded-eye-check.png")
    Path(temp_path).write_bytes(payload)
    loaded = None
    try:
        loaded = bpy.data.images.load(temp_path, check_existing=False)
        width, height, channels = int(loaded.size[0]), int(loaded.size[1]), int(loaded.channels)
        if channels != 4:
            raise RuntimeError("V386 embedded eye image is not RGBA: " + repr([width, height, channels]))
        raw = np.empty(len(loaded.pixels), dtype=np.float32)
        loaded.pixels.foreach_get(raw)
        pixels = raw.reshape((height, width, channels))
        mask, centers, scale = build_iris_annulus_mask(width, height)
        iris_mean = np.sum(pixels[:, :, :3] * mask[:, :, None], axis=(0, 1)) / max(float(mask.sum()), 1e-8)
        source_alpha_mean = float(np.mean(pixels[:, :, 3]))
        return {
            "width": width,
            "height": height,
            "channels": channels,
            "embedded_image_label": "",
            "mime_type": "image/png",
            "mask_coverage": float(np.mean(mask)),
            "iris_mean_rgb_linear": iris_mean.tolist(),
            "iris_channel_ratios": {
                "green_to_red": float(iris_mean[1]) / max(float(iris_mean[0]), 1e-8),
                "blue_to_red": float(iris_mean[2]) / max(float(iris_mean[0]), 1e-8),
            },
            "alpha_mean": source_alpha_mean,
            "alpha_sha256_float32": __import__("hashlib").sha256(pixels[:, :, 3].astype(np.float32).tobytes()).hexdigest(),
        }
    finally:
        if loaded is not None:
            bpy.data.images.remove(loaded)
        try:
            os.remove(temp_path)
        except FileNotFoundError:
            pass


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
    material = bpy.data.materials.new("V386_GltfCompatibleAccessory_" + suffix)
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
    texture.label = "V386 accessory texture — explicit UV map"
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


def tune_eye_material_response(material):
    """Give the existing eye texture a restrained eye-surface highlight response."""
    if not material.use_nodes or not material.node_tree:
        raise RuntimeError("V386 eye material is missing its node tree")
    bsdf_nodes = [node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"]
    if len(bsdf_nodes) != 1:
        raise RuntimeError("V386 expected exactly one Principled BSDF on eye material")
    inputs = bsdf_nodes[0].inputs
    settings = {
        "roughness": 0.32,
        "specular_ior_level": 0.38,
        "coat_weight": 0.10,
        "coat_roughness": 0.24,
    }
    inputs["Roughness"].default_value = settings["roughness"]
    if "Specular IOR Level" in inputs:
        inputs["Specular IOR Level"].default_value = settings["specular_ior_level"]
    if "Coat Weight" in inputs:
        inputs["Coat Weight"].default_value = settings["coat_weight"]
    elif "Clearcoat" in inputs:
        inputs["Clearcoat"].default_value = settings["coat_weight"]
    if "Coat Roughness" in inputs:
        inputs["Coat Roughness"].default_value = settings["coat_roughness"]
    elif "Clearcoat Roughness" in inputs:
        inputs["Clearcoat Roughness"].default_value = settings["coat_roughness"]
    return {
        "scope": "high-poly eye mesh material only",
        "settings": settings,
        "source_texture_changed_only_inside_iris_mask": True,
        "uv_layout_unchanged": True,
        "alpha_behavior_unchanged": True,
        "material_node_names": [node.name for node in material.node_tree.nodes],
    }


def tune_eye_front_surface_response(material):
    """A slightly glossier response for the two forward eye-shell components only."""
    bsdf_nodes = [node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"]
    if len(bsdf_nodes) != 1:
        raise RuntimeError("V386 expected one Principled BSDF on front eye surface")
    inputs = bsdf_nodes[0].inputs
    settings = {
        "roughness": 0.18,
        "specular_ior_level": 0.48,
        "coat_weight": 0.30,
        "coat_roughness": 0.14,
    }
    inputs["Roughness"].default_value = settings["roughness"]
    if "Specular IOR Level" in inputs:
        inputs["Specular IOR Level"].default_value = settings["specular_ior_level"]
    if "Coat Weight" in inputs:
        inputs["Coat Weight"].default_value = settings["coat_weight"]
    elif "Clearcoat" in inputs:
        inputs["Clearcoat"].default_value = settings["coat_weight"]
    if "Coat Roughness" in inputs:
        inputs["Coat Roughness"].default_value = settings["coat_roughness"]
    elif "Clearcoat Roughness" in inputs:
        inputs["Clearcoat Roughness"].default_value = settings["coat_roughness"]
    return settings


def get_eye_component_map(obj):
    """Return a per-vertex connected-component map and bounds for the eye mesh."""
    matrix = obj.matrix_world.copy()
    points = [matrix @ vertex.co for vertex in obj.data.vertices]
    adjacency = [set() for _ in points]
    for edge in obj.data.edges:
        a, b = int(edge.vertices[0]), int(edge.vertices[1])
        adjacency[a].add(b)
        adjacency[b].add(a)
    component_by_vertex = [-1] * len(points)
    components = []
    component_id = 0
    for index in range(len(points)):
        if component_by_vertex[index] != -1:
            continue
        stack = [index]
        component_by_vertex[index] = component_id
        members = []
        while stack:
            current = stack.pop()
            members.append(current)
            for neighbor in adjacency[current]:
                if component_by_vertex[neighbor] == -1:
                    component_by_vertex[neighbor] = component_id
                    stack.append(neighbor)
        if len(members) >= 20:
            member_points = [points[i] for i in members]
            lows = [min(float(p[k]) for p in member_points) for k in range(3)]
            highs = [max(float(p[k]) for p in member_points) for k in range(3)]
            centers = [(lows[k] + highs[k]) * 0.5 for k in range(3)]
            components.append({
                "component_id": component_id,
                "vertex_indices": members,
                "vertex_count": len(members),
                "min_m": lows,
                "max_m": highs,
                "size_m": [highs[k] - lows[k] for k in range(3)],
                "center_m": centers,
            })
        component_id += 1
    return component_by_vertex, components


def apply_eye_component_material_split(eye_obj, base_material, front_material):
    """Assign the forwardmost component on each side to a dedicated corneal response."""
    component_by_vertex, components = get_eye_component_map(eye_obj)
    if len(components) != 4:
        raise RuntimeError(
            "V386 expects the two overlapping eye components per side observed in V347; found "
            + repr([(c["vertex_count"], c["center_m"]) for c in components])
        )
    # The eye meshes face -Y in this model. The two components with the most-negative
    # center Y are the forward surface, and their X centers must straddle the midline.
    front_components = sorted(components, key=lambda row: row["center_m"][1])[:2]
    front_ids = {row["component_id"] for row in front_components}
    x_centers = sorted(row["center_m"][0] for row in front_components)
    if not (x_centers[0] < 0 < x_centers[1]):
        raise RuntimeError("V386 front-component selection did not select one surface per eye: " + repr(x_centers))

    eye_obj.data.materials.clear()
    eye_obj.data.materials.append(base_material)
    eye_obj.data.materials.append(front_material)
    front_face_count = 0
    base_face_count = 0
    for polygon in eye_obj.data.polygons:
        ids = {component_by_vertex[int(vertex_index)] for vertex_index in polygon.vertices}
        if len(ids) != 1:
            raise RuntimeError("V386 found a polygon crossing eye connected components")
        if next(iter(ids)) in front_ids:
            polygon.material_index = 1
            front_face_count += 1
        else:
            polygon.material_index = 0
            base_face_count += 1
    eye_obj.data.update()

    component_rows = []
    for row in sorted(components, key=lambda item: item["center_m"][0]):
        component_rows.append({
            "component_id": row["component_id"],
            "vertex_count": row["vertex_count"],
            "center_m": [round(v, 6) for v in row["center_m"]],
            "size_m": [round(v, 6) for v in row["size_m"]],
            "material_role": "front_surface" if row["component_id"] in front_ids else "base_eye",
        })
    return {
        "scope": "high-poly eye connected components split into base-eye and forward-surface materials",
        "geometry_changed": False,
        "component_count": len(components),
        "front_surface_component_count": len(front_ids),
        "front_surface_vertex_count": sum(row["vertex_count"] for row in front_components),
        "front_surface_face_count": front_face_count,
        "base_eye_face_count": base_face_count,
        "components": component_rows,
        "base_material_name": base_material.name,
        "front_surface_material_name": front_material.name,
        "base_surface_settings": {
            "roughness": 0.32, "specular_ior_level": 0.38, "coat_weight": 0.10, "coat_roughness": 0.24
        },
        "front_surface_settings": {
            "roughness": 0.18, "specular_ior_level": 0.48, "coat_weight": 0.30, "coat_roughness": 0.14
        },
        "source_texture_changed_only_inside_iris_mask": True,
        "uv_layout_unchanged": True,
        "alpha_behavior_unchanged": True,
        "both_surfaces_use_same_image": True,
    }


def prepare_eye_surface_materials(eye_obj, image, uv_name):
    """Prepare and assign the same glTF-compatible materials used later on the baked eye mesh."""
    activate_uv_layer(eye_obj, uv_name)
    base_material, alpha_enabled = make_gltf_compatible_accessory_material("high-poly", image, uv_name)
    base_response = tune_eye_material_response(base_material)
    front_material, front_alpha_enabled = make_gltf_compatible_accessory_material("high-poly-front", image, uv_name)
    front_material.name = "V386_GltfEyeFrontSurface"
    for node in front_material.node_tree.nodes:
        if node.type == "TEX_IMAGE":
            node.label = "V386 eye front surface texture — same diffuse and UV"
    front_settings = tune_eye_front_surface_response(front_material)
    component_report = apply_eye_component_material_split(eye_obj, base_material, front_material)
    return {
        "status": "APPLIED_TO_SOURCE_FOR_MATCHING_RENDER",
        "source_object": eye_obj.name,
        "image_name": image.name,
        "uv_map_name": uv_name,
        "image_channels": int(image.channels),
        "alpha_enabled": alpha_enabled and front_alpha_enabled,
        "base_material_response": base_response,
        "front_surface_settings": front_settings,
        "component_material_assignment": component_report,
        "render_uses_same_eye_materials_as_glb": True,
    }


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
        if suffix == "high-poly":
            image = bpy.data.images.get("V386_WarmBrownIris")
            if image is None:
                raise RuntimeError("V386 processed iris texture wasn't prepared before bake/material restore")
        else:
            image = find_face_accessory_diffuse_image(source_obj, suffix)
        uv_name = get_active_uv_name(source_obj)
        if not uv_name:
            raise RuntimeError("No UV map on face accessory " + source_name)
        source_uv_audit = activate_uv_layer(source_obj, uv_name)
        baked_uv_audit = activate_uv_layer(baked_obj, uv_name)
        if suffix == "high-poly":
            material = bpy.data.materials.get("V386_GltfCompatibleAccessory_high-poly")
            front_material = bpy.data.materials.get("V386_GltfEyeFrontSurface")
            if material is None or front_material is None:
                raise RuntimeError("V386 source preview eye materials were not prepared before rendering")
            alpha_enabled = bool(getattr(image, "channels", 3) >= 4)
            material_response = apply_eye_component_material_split(baked_obj, material, front_material)
        else:
            material, alpha_enabled = make_gltf_compatible_accessory_material(suffix, image, uv_name)
            material_response = {
                "scope": "unchanged accessory material",
                "settings": None,
                "source_diffuse_texture_and_uv_unchanged": True,
                "alpha_behavior_unchanged": True,
            }
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
            "material_response": material_response,
        })
    found = {item["suffix"] for item in report}
    if found != suffixes:
        raise RuntimeError("V386 did not restore every expected face accessory. Found " + repr(sorted(found)))
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
        ("clothes", ["female_sportsuit01.mhclo"], "Clothes", True),
        ("clothes", ["shoes06.mhclo"], "Clothes", True),
    ]
    for subdir, candidates, asset_type, required in optional_assets:
        asset_path = find_asset(AssetService, subdir, candidates)
        if required and candidates and candidates[0] in {"female_sportsuit01.mhclo", "shoes06.mhclo"}:
            if asset_path is None or Path(asset_path).name.lower() != candidates[0].lower():
                raise RuntimeError("V386 exact wardrobe asset not found: " + candidates[0] + "; resolver returned " + repr(asset_path))
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

    expected_wardrobe_files = {"female_sportsuit01.mhclo", "shoes06.mhclo"}
    added_wardrobe_files = {
        Path(item.get("file", "")).name.lower()
        for item in assets_added
        if item.get("status") == "ADDED"
    }
    if not {name.lower() for name in expected_wardrobe_files}.issubset(added_wardrobe_files):
        raise RuntimeError("V386 wardrobe asset selection did not complete: " + repr(assets_added))
    wardrobe_reference_audit = {
        "status": "APPLIED",
        "reference_name": "Bảng giới thiệu nhân vật Lý Lâm Lam.png",
        "reference_sha256": "0be925c095166289727c597690b57ed31d23fcbf0a77f7f517d1928098f3c575",
        "reference_outfit_target": {
            "top": "dark teal sleeveless/cropped athletic top",
            "bottom": "dark charcoal cargo-style trousers",
            "belt": "black belt with rectangular metal buckle",
            "footwear": "white/gray sneakers",
        },
        "assets_selected": [
            {"role": "athletic clothing base", "file": "female_sportsuit01.mhclo"},
            {"role": "footwear", "file": "shoes06.mhclo"},
        ],
        "replaced_asset": "female_casualsuit01.mhclo",
        "scope": "wardrobe base meshes and their source materials only; the body, face, hair, eyes, necklace, 12 morphs, and animation remain unchanged",
        "review_warning": "This is a first-pass CC0 outfit-base swap; the gate confirms exact source assets and geometry export, not exact cargo pocket/teal-color likeness. The renders must be visually reviewed before approval.",
        "asset_audit": [item for item in assets_added if Path(item.get("file", "")).name.lower() in {name.lower() for name in expected_wardrobe_files}],
    }

    # V386 outfit alignment experiment: apply accepted body silhouette mapping to skin + both wardrobe meshes.

    body_shape_adjustment = apply_targeted_body_shape_adjustment(basemesh, clothing_objects)
    arm_pose_refinement = apply_relaxed_arm_pose(basemesh, clothing_objects)
    armhole_skin_tuck_audit = apply_armhole_skin_tuck(basemesh)
    face_shape_refinement = apply_face_profile_refinement(basemesh)
    sleeve_removal_audit = remove_short_sleeve_components(clothing_objects)
    wardrobe_detail_objects, wardrobe_detail_audit = create_wardrobe_details(bpy.context.scene, basemesh, clothing_objects)

    # Add source facial targets, transfer them to mapped child meshes, then build the
    # compact set expected by the Lam viewer. The full source targets are removed afterward.
    FaceService.load_targets(basemesh, load_microsoft_visemes=True, load_meta_visemes=False, load_arkit_faceunits=True)
    FaceService.interpolate_targets(basemesh)
    character_root = basemesh.parent if basemesh.parent else basemesh
    character_objects = all_descendants(character_root)
    character_objects.extend(wardrobe_detail_objects)
    face_framing_hair_objects, face_framing_hair_audit = create_face_framing_hair_strands(bpy.context.scene, basemesh, hair_objects)
    character_objects.extend(face_framing_hair_objects)
    necklace_objects, necklace_accessory_audit = create_necklace_accessory(bpy.context.scene, basemesh, clothing_objects)
    character_objects.extend(necklace_objects)
    composite_report = make_composite_morphs(character_objects)
    base_morphs = composite_report.get(basemesh.name, {}).get("composite_morphs", [])
    if base_morphs != EXPECTED_MORPHS:
        raise RuntimeError(
            "The base human is missing required composite morphs. found=" + repr(base_morphs)
            + "; source key inventory=" + repr(composite_report.get(basemesh.name, {}))
        )

    default_face_pose = apply_default_smile_base_pose(character_objects, strength=0.40)
    skin_materials = style_materials(basemesh, hair_objects, clothing_objects)
    wardrobe_color_audit = prepare_reference_wardrobe_colors(clothing_objects)
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
    eye_geometry_diagnostic = audit_eye_geometry(character_objects, basemesh)
    source_eye_obj = next(
        obj for obj in character_objects
        if obj.type == "MESH" and obj.name.rsplit(".", 1)[-1].lower() == "high-poly"
    )
    original_eye_image = find_face_accessory_diffuse_image(source_eye_obj, "high-poly")
    source_eye_image, iris_texture_audit = make_warm_brown_iris_texture(original_eye_image)
    source_eye_uv = get_active_uv_name(source_eye_obj)
    if not source_eye_uv:
        raise RuntimeError("V386 source eye mesh has no active UV map")
    eye_material_preview_audit = prepare_eye_surface_materials(source_eye_obj, source_eye_image, source_eye_uv)
    cameras, floor = setup_studio(bpy.context.scene, character_bounds, eye_geometry_diagnostic, necklace_accessory_audit)
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
    glb_path = os.path.join(output, "lam-v386-gltf-materials-full-face-candidate.glb")
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
    expected_frame_nodes = face_framing_hair_audit["gltf_expected_nodes"]
    present_frame_nodes = [name for name in expected_frame_nodes if name in node_names]
    if len(present_frame_nodes) != len(expected_frame_nodes):
        raise RuntimeError("V386 face-framing strand nodes missing from GLB: " + repr({
            "expected": expected_frame_nodes, "present": present_frame_nodes, "nodes": node_names
        }))
    frame_materials = [
        material for material in gltf.get("materials", [])
        if material.get("name") == "V386_FaceFrameStrandMaterial"
    ]
    if len(frame_materials) != 1:
        raise RuntimeError("V386 expected one exported face-framing strand material")
    frame_pbr = frame_materials[0].get("pbrMetallicRoughness", {})
    if abs(float(frame_pbr.get("roughnessFactor", 0.0)) - 0.80) > 0.03:
        raise RuntimeError("V386 strand roughness did not export correctly: " + repr(frame_pbr))
    face_framing_hair_audit["gltf_export"] = {
        "expected_node_names": expected_frame_nodes,
        "present_node_names": present_frame_nodes,
        "material_name": frame_materials[0].get("name"),
        "roughness_factor": frame_pbr.get("roughnessFactor"),
        "metallic_factor": frame_pbr.get("metallicFactor"),
        "nodes_all_present": len(present_frame_nodes) == len(expected_frame_nodes),
    }
    expected_wardrobe_detail_nodes = [
        "V386_Baked_" + name for name in wardrobe_detail_audit["objects_added"]
    ]
    present_wardrobe_detail_nodes = [
        name for name in expected_wardrobe_detail_nodes if name in node_names
    ]
    if len(present_wardrobe_detail_nodes) != len(expected_wardrobe_detail_nodes):
        raise RuntimeError("V386 wardrobe detail meshes missing from GLB: " + repr({
            "expected": expected_wardrobe_detail_nodes,
            "present": present_wardrobe_detail_nodes,
            "all_nodes": node_names,
        }))
    expected_detail_materials = {
        "V386_MatteBlackBelt", "V386_WaistGapPatchCharcoal", "V386_CargoPocketCharcoal", "V386_CargoFlapCharcoal",
        "V386_AnkleCuffCharcoal",
        "V386_BuckleSilver", "V386_BucklePinSilver",
    }
    actual_detail_materials = {
        material.get("name", "") for material in gltf.get("materials", [])
    }
    missing_detail_materials = sorted(expected_detail_materials - actual_detail_materials)
    if missing_detail_materials:
        raise RuntimeError("V386 wardrobe detail materials missing from glTF: " + repr(missing_detail_materials))
    wardrobe_detail_audit["gltf_export"] = {
        "expected_node_names": expected_wardrobe_detail_nodes,
        "present_node_names": present_wardrobe_detail_nodes,
        "nodes_all_present": len(present_wardrobe_detail_nodes) == len(expected_wardrobe_detail_nodes),
        "expected_material_names": sorted(expected_detail_materials),
        "present_material_names": sorted(expected_detail_materials & actual_detail_materials),
    }
    source_morph_names = set()
    for mesh in gltf.get("meshes", []):
        extras = mesh.get("extras", {})
        source_morph_names.update(extras.get("targetNames", []))
    missing_morphs = sorted(set(EXPECTED_MORPHS) - source_morph_names)
    texture_count = len(gltf.get("images", []))
    material_count = len(gltf.get("materials", []))
    necklace_nodes = [
        node.get("name", "") for node in gltf.get("nodes", [])
        if "V386_NecklaceChain" in node.get("name", "") or "V386_NecklacePendant" in node.get("name", "")
    ]
    if not any("V386_NecklaceChain" in name for name in necklace_nodes):
        raise RuntimeError("V386 necklace chain was not exported to glTF nodes: " + repr(necklace_nodes))
    if not any("V386_NecklacePendant" in name for name in necklace_nodes):
        raise RuntimeError("V386 necklace pendant was not exported to glTF nodes: " + repr(necklace_nodes))
    necklace_materials = [
        material for material in gltf.get("materials", [])
        if material.get("name") == "V386_SilverNecklace"
    ]
    if len(necklace_materials) != 1:
        raise RuntimeError("V386 expected exactly one exported silver necklace material")
    necklace_pbr = necklace_materials[0].get("pbrMetallicRoughness", {})
    necklace_metallic = float(necklace_pbr.get("metallicFactor", 0.0))
    necklace_roughness = float(necklace_pbr.get("roughnessFactor", 1.0))
    if necklace_metallic < 0.75 or not (0.18 <= necklace_roughness <= 0.30):
        raise RuntimeError("V386 silver necklace PBR did not export as expected: " + repr(necklace_pbr))
    necklace_accessory_audit["gltf_export"] = {
        "node_names": necklace_nodes,
        "material_name": necklace_materials[0].get("name"),
        "metallic_factor": necklace_metallic,
        "roughness_factor": necklace_roughness,
    }
    gltf_hair_materials = [
        material for material in gltf.get("materials", [])
        if material.get("name") == "V386_GltfCompatibleHair"
    ]
    if len(gltf_hair_materials) != 1:
        raise RuntimeError("V386 expected exactly one explicit glTF hair material")
    gltf_hair_material = gltf_hair_materials[0]
    gltf_hair_pbr = gltf_hair_material.get("pbrMetallicRoughness", {})
    hair_texture_index = gltf_hair_pbr.get("baseColorTexture", {}).get("index")
    gltf_hair_textures = gltf.get("textures", [])
    gltf_hair_images = gltf.get("images", [])
    texture_row = gltf_hair_textures[hair_texture_index] if hair_texture_index is not None and hair_texture_index < len(gltf_hair_textures) else {}
    hair_image_source_index = texture_row.get("source")
    hair_image_name = gltf_hair_images[hair_image_source_index].get("name", "") if hair_image_source_index is not None and hair_image_source_index < len(gltf_hair_images) else ""
    if hair_image_source_index is None or hair_image_source_index >= len(gltf_hair_images):
        raise RuntimeError("V386 glTF hair texture has no valid embedded image source")
    hair_png_payload, hair_mime_type, embedded_image_label = extract_glb_embedded_image_bytes(
        glb_path, gltf, hair_image_source_index
    )
    if hair_mime_type != "image/png":
        raise RuntimeError("V386 expected embedded PNG hair texture, got " + repr(hair_mime_type))
    embedded_rgb_mean, embedded_alpha_mean = mean_rgb_linear_from_png_bytes(hair_png_payload, output)
    source_rgb_mean = float(hair_material_audit["image"]["source_rgb_mean_linear"])
    processed_rgb_mean = float(hair_material_audit["image"]["processed_rgb_mean_linear"])
    embedded_darkening_verified = embedded_rgb_mean < source_rgb_mean * 0.90
    if not embedded_darkening_verified:
        raise RuntimeError(
            "V386 embedded hair texture is not sufficiently darker than source: "
            + repr({"source_rgb_mean": source_rgb_mean, "embedded_rgb_mean": embedded_rgb_mean})
        )
    if abs(embedded_rgb_mean - processed_rgb_mean) > 0.06:
        raise RuntimeError(
            "V386 embedded hair image pixels do not match the processed source: "
            + repr({"processed_rgb_mean": processed_rgb_mean, "embedded_rgb_mean": embedded_rgb_mean})
        )
    if float(gltf_hair_pbr.get("roughnessFactor", 0.0)) < 0.80:
        raise RuntimeError("V386 hair roughness was not preserved in glTF")
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

    gltf_wardrobe_material_audits = []
    for role in ("sportsuit", "shoes"):
        material_name = "V386_GltfWardrobe_" + role
        matches = [material for material in gltf.get("materials", []) if material.get("name") == material_name]
        if len(matches) != 1:
            raise RuntimeError("V386 expected one exported wardrobe material " + material_name)
        wardrobe_material = matches[0]
        wardrobe_pbr = wardrobe_material.get("pbrMetallicRoughness", {})
        texture_index = wardrobe_pbr.get("baseColorTexture", {}).get("index")
        gltf_textures = gltf.get("textures", [])
        gltf_images = gltf.get("images", [])
        if texture_index is None or texture_index >= len(gltf_textures):
            raise RuntimeError("V386 wardrobe material has no valid base-color texture: " + material_name)
        texture_row = gltf_textures[texture_index]
        image_index = texture_row.get("source")
        if image_index is None or image_index >= len(gltf_images):
            raise RuntimeError("V386 wardrobe texture has no valid embedded image source: " + repr(texture_row))
        payload, mime_type, image_label = extract_glb_embedded_image_bytes(glb_path, gltf, image_index)
        if mime_type != "image/png":
            raise RuntimeError("V386 expected PNG wardrobe texture after export: " + repr({"role": role, "mime": mime_type}))
        embedded_rgb_mean, embedded_alpha_mean = mean_rgb_linear_from_png_bytes(payload, output)
        source_audit = next((item["image_audit"] for item in wardrobe_color_audit["materials"] if item["role"] == role), None)
        if source_audit is None:
            raise RuntimeError("V386 missing source wardrobe texture audit for role " + role)
        expected_rgb_mean = float(source_audit["processed_rgb_mean_linear"])
        expected_alpha_mean = float(source_audit["processed_alpha_mean"])
        if abs(embedded_rgb_mean - expected_rgb_mean) > 0.08:
            raise RuntimeError("V386 embedded wardrobe RGB does not match processed texture: " + repr({"role": role, "expected_mean": expected_rgb_mean, "embedded_mean": embedded_rgb_mean}))
        if abs(embedded_alpha_mean - expected_alpha_mean) > 0.03:
            raise RuntimeError("V386 embedded wardrobe alpha changed unexpectedly: " + repr({"role": role, "expected_mean": expected_alpha_mean, "embedded_mean": embedded_alpha_mean}))
        if float(wardrobe_pbr.get("roughnessFactor", 0.0)) < 0.70:
            raise RuntimeError("V386 wardrobe roughness not preserved in glTF: " + repr(wardrobe_pbr))
        gltf_wardrobe_material_audits.append({
            "role": role,
            "name": wardrobe_material.get("name"),
            "roughness_factor": wardrobe_pbr.get("roughnessFactor"),
            "texture_index": texture_index,
            "image_index": image_index,
            "embedded_image_label": image_label,
            "embedded_image_mime_type": mime_type,
            "source_processed_rgb_mean_linear": expected_rgb_mean,
            "embedded_rgb_mean_linear": embedded_rgb_mean,
            "source_processed_alpha_mean": expected_alpha_mean,
            "embedded_alpha_mean": embedded_alpha_mean,
            "embedded_texture_matches_processed_pixels": True,
        })
    if {item["role"] for item in gltf_wardrobe_material_audits} != {"sportsuit", "shoes"}:
        raise RuntimeError("V386 did not export both processed wardrobe materials")

    eye_materials = [
        material for material in gltf.get("materials", [])
        if material.get("name") == "V386_GltfCompatibleAccessory_high-poly"
    ]
    if len(eye_materials) != 1:
        raise RuntimeError("V386 expected one glTF high-poly eye material: " + repr([m.get("name") for m in gltf.get("materials", [])]))
    gltf_eye_material = eye_materials[0]
    gltf_eye_pbr = gltf_eye_material.get("pbrMetallicRoughness", {})
    gltf_eye_extensions = gltf_eye_material.get("extensions", {})
    specular_extension = gltf_eye_extensions.get("KHR_materials_specular", {})
    clearcoat_extension = gltf_eye_extensions.get("KHR_materials_clearcoat", {})
    eye_texture_index = gltf_eye_pbr.get("baseColorTexture", {}).get("index")
    if eye_texture_index is None:
        raise RuntimeError("V386 eye diffuse texture link missing from exported GLB")
    # Resolve the base eye image source before writing its audit record.
    # Texture-object indices may differ even when their embedded image is shared.
    gltf_textures = gltf.get("textures", [])
    gltf_images = gltf.get("images", [])

    def texture_image_source_index(texture_index, label):
        if texture_index is None or texture_index < 0 or texture_index >= len(gltf_textures):
            raise RuntimeError("V386 " + label + " texture index is invalid: " + repr(texture_index))
        source_index = gltf_textures[texture_index].get("source")
        if source_index is None or source_index < 0 or source_index >= len(gltf_images):
            raise RuntimeError("V386 " + label + " texture has no valid image source: " + repr(gltf_textures[texture_index]))
        return source_index

    eye_image_source_index = texture_image_source_index(eye_texture_index, "base eye")
    eye_image_name = gltf_images[eye_image_source_index].get("name", "")
    eye_png_payload, eye_mime_type, embedded_eye_label = extract_glb_embedded_image_bytes(
        glb_path, gltf, eye_image_source_index
    )
    if eye_mime_type != "image/png":
        raise RuntimeError("V386 expected the processed brown_eye image embedded as PNG: " + repr(eye_mime_type))
    embedded_iris_audit = audit_embedded_iris_texture_png(eye_png_payload, output)
    embedded_iris_audit["embedded_image_label"] = embedded_eye_label
    processed_expected = iris_texture_audit["processed_iris_mean_rgb_linear"]
    embedded_rgb_error = max(abs(float(embedded_iris_audit["iris_mean_rgb_linear"][i]) - float(processed_expected[i])) for i in range(3))
    alpha_mean_error = abs(float(embedded_iris_audit["alpha_mean"]) - float(iris_texture_audit["source_alpha_mean"]))
    gltf_iris_texture_audit = {
        "base_eye_image_source_index": eye_image_source_index,
        "base_eye_image_name": eye_image_name,
        "mime_type": eye_mime_type,
        "embedded_image_label": embedded_eye_label,
        "embedded_iris_audit": embedded_iris_audit,
        "expected_processed_iris_mean_rgb_linear": processed_expected,
        "max_channel_mean_error": embedded_rgb_error,
        "source_alpha_mean": iris_texture_audit["source_alpha_mean"],
        "embedded_alpha_mean_error": alpha_mean_error,
        "embedded_alpha_matches_source": alpha_mean_error <= 0.002,
        "embedded_texture_matches_processed_iris": embedded_rgb_error <= 0.015,
        "image_source_is_processed_eye_material": eye_image_source_index == texture_image_source_index(
            gltf_eye_pbr.get("baseColorTexture", {}).get("index"), "base eye validation"
        ),
    }
    if not gltf_iris_texture_audit["embedded_texture_matches_processed_iris"]:
        raise RuntimeError("V386 embedded GLB eye texture did not match the warm-brown iris pixels: " + repr(gltf_iris_texture_audit))
    if not gltf_iris_texture_audit["embedded_alpha_matches_source"]:
        raise RuntimeError("V386 embedded eye texture alpha changed: " + repr(gltf_iris_texture_audit))

    if abs(float(gltf_eye_pbr.get("roughnessFactor", 1.0)) - 0.32) > 0.03:
        raise RuntimeError("V386 eye roughness factor did not export as intended: " + repr(gltf_eye_pbr))
    gltf_eye_material_audit = {
        "name": gltf_eye_material.get("name"),
        "roughness_factor": gltf_eye_pbr.get("roughnessFactor"),
        "alpha_mode": gltf_eye_material.get("alphaMode", "OPAQUE"),
        "base_color_texture_index": eye_texture_index,
        "base_color_image_source_index": eye_image_source_index,
        "base_color_image_name": eye_image_name,
        "extensions": sorted(gltf_eye_extensions.keys()),
        "specular_extension_present": bool(specular_extension),
        "specular_factor": specular_extension.get("specularFactor"),
        "clearcoat_extension_present": bool(clearcoat_extension),
        "clearcoat_factor": clearcoat_extension.get("clearcoatFactor"),
        "clearcoat_roughness_factor": clearcoat_extension.get("clearcoatRoughnessFactor"),
        "uv_layout_preserved": True,
        "alpha_preserved": True,
        "processed_iris_image_used": True,
    }
    if not specular_extension or not clearcoat_extension:
        raise RuntimeError("V386 expected glTF specular and clearcoat material extensions: " + repr(gltf_eye_material_audit))
    if float(specular_extension.get("specularFactor", 0.0)) <= 0.0:
        raise RuntimeError("V386 eye specular response missing from glTF extension")
    if float(clearcoat_extension.get("clearcoatFactor", 0.0)) <= 0.0:
        raise RuntimeError("V386 eye clearcoat response missing from glTF extension")
    eye_front_materials = [
        material for material in gltf.get("materials", [])
        if material.get("name") == "V386_GltfEyeFrontSurface"
    ]
    if len(eye_front_materials) != 1:
        raise RuntimeError("V386 expected exactly one glTF forward eye-surface material")
    gltf_eye_front_material = eye_front_materials[0]
    gltf_eye_front_pbr = gltf_eye_front_material.get("pbrMetallicRoughness", {})
    gltf_eye_front_extensions = gltf_eye_front_material.get("extensions", {})
    front_specular_extension = gltf_eye_front_extensions.get("KHR_materials_specular", {})
    front_clearcoat_extension = gltf_eye_front_extensions.get("KHR_materials_clearcoat", {})
    front_texture_index = gltf_eye_front_pbr.get("baseColorTexture", {}).get("index")
    # Compare embedded image sources rather than texture-object indices.
    front_image_source_index = texture_image_source_index(front_texture_index, "front eye")
    front_image_name = gltf_images[front_image_source_index].get("name", "")
    if front_image_source_index != eye_image_source_index:
        raise RuntimeError(
            "V386 front eye layer did not preserve and reuse the original diffuse image source: "
            + repr({
                "base_texture_index": eye_texture_index,
                "front_texture_index": front_texture_index,
                "base_image_source": eye_image_source_index,
                "front_image_source": front_image_source_index,
                "base_image_name": eye_image_name,
                "front_image_name": front_image_name,
            })
        )
    if abs(float(gltf_eye_front_pbr.get("roughnessFactor", 1.0)) - 0.18) > 0.03:
        raise RuntimeError("V386 front-surface roughness was not exported: " + repr(gltf_eye_front_pbr))
    if not front_specular_extension or not front_clearcoat_extension:
        raise RuntimeError("V386 front-surface specular/clearcoat extensions missing")
    gltf_eye_front_surface_audit = {
        "name": gltf_eye_front_material.get("name"),
        "roughness_factor": gltf_eye_front_pbr.get("roughnessFactor"),
        "alpha_mode": gltf_eye_front_material.get("alphaMode", "OPAQUE"),
        "base_color_texture_index": front_texture_index,
        "base_color_image_source_index": front_image_source_index,
        "base_color_image_name": front_image_name,
        "same_texture_index_as_base_eye": front_texture_index == eye_texture_index,
        "same_image_source_as_base_eye": front_image_source_index == eye_image_source_index,
        "extensions": sorted(gltf_eye_front_extensions.keys()),
        "specular_extension_present": bool(front_specular_extension),
        "specular_factor": front_specular_extension.get("specularFactor"),
        "clearcoat_extension_present": bool(front_clearcoat_extension),
        "clearcoat_factor": front_clearcoat_extension.get("clearcoatFactor"),
        "clearcoat_roughness_factor": front_clearcoat_extension.get("clearcoatRoughnessFactor"),
        "alpha_behavior_preserved": gltf_eye_front_material.get("alphaMode", "OPAQUE") == "BLEND",
    }
    if not gltf_eye_front_surface_audit["alpha_behavior_preserved"]:
        raise RuntimeError("V386 front eye surface did not retain alpha blend mode")

    if skin_count != 0:
        raise RuntimeError("V386 must export baked geometry without a skin; found " + str(skin_count))
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
        "status": "EXPERIMENTAL_V386_GLTFSKIN_FACE_ACCESSORY_CANDIDATE_NOT_APPROVED",
        "mpfb_source_commit": mpfb_source_commit,
        "version": "V386",
        "purpose": "V386 continues the accepted V385 arm-pose baseline and removes only the two detached short-sleeve components from the sportsuit garment; face, body, hands, pants, shoes, necklace, morphs and idle animation remain unchanged.",
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
        "arm_pose_refinement": arm_pose_refinement,
        "armhole_skin_tuck_audit": armhole_skin_tuck_audit,
        "face_shape_refinement": face_shape_refinement,
        "sleeve_removal_audit": sleeve_removal_audit,
        "face_framing_hair_audit": face_framing_hair_audit,
        "necklace_accessory_audit": necklace_accessory_audit,
        "source_rig_diagnostic_only": idle_report,
        "idle_animation": baked_idle_report,
        "body_skinning": "Baked neutral evaluated mesh; exported skin_count must be zero; twelve face morphs retained.",
        "baked_mesh_diagnostics": baked_mesh_report,
        "excluded_face_accessories": excluded_face_accessories,
        "face_accessory_material_audits": face_accessory_material_audits,
        "gltf_eye_material_audit": gltf_eye_material_audit,
        "gltf_eye_front_surface_audit": gltf_eye_front_surface_audit,
        "eye_material_preview_audit": eye_material_preview_audit,
        "iris_texture_audit": iris_texture_audit,
        "gltf_iris_texture_audit": gltf_iris_texture_audit,
        "eye_geometry_diagnostic": eye_geometry_diagnostic,
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
        "wardrobe_reference_audit": wardrobe_reference_audit,
        "wardrobe_color_audit": wardrobe_color_audit,
        "wardrobe_detail_audit": wardrobe_detail_audit,
        "gltf_wardrobe_material_audits": gltf_wardrobe_material_audits,
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
            "V386 removes Blender factory-startup Cube/Camera/Light before rendering.",
            "V386 preserves the glTF-compatible skin material and restores all five eye/brow/lash/teeth/tongue meshes with explicit UVMap nodes and simplified materials.",
            "V386 uses evaluated.matrix_world when baking evaluated mesh positions.",
            "V386 uses a real human-topology base mesh rather than procedural sphere/capsule facial anatomy.",
            "The model remains a candidate: photorealism requires human visual comparison against Phi's reference.",
            "The included idle clip is intentionally subtle and skeletal; it is a technical animation, not a complete motion library.",
            "Voice/chat integration is outside this avatar candidate build.",
        ],
    }
    report_path = os.path.join(output, "lam-v386-candidate-report.json")
    Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Save an editable Blender scene alongside the exported GLB and visual evidence.
    scene_path = os.path.join(output, "lam-v386-gltf-materials-full-face-candidate.blend")
    bpy.ops.wm.save_as_mainfile(filepath=scene_path)
    print("V386_REAL_HUMAN_CANDIDATE=" + json.dumps(report, ensure_ascii=False))
    if os.path.getsize(glb_path) < 1_000_000:
        raise RuntimeError("V386 GLB is unexpectedly small for a textured human character")
    if os.path.getsize(glb_path) > 200_000_000:
        raise RuntimeError("V386 GLB is too large for an initial mobile candidate: " + str(os.path.getsize(glb_path)))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
