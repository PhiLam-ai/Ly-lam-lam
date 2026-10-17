#!/usr/bin/env python3
"""Structural acceptance checks for the experimental V387 skinned GLB.

This validator deliberately fails on the current V386 baked/unskinned candidate.
It checks glTF structure only; it does not replace Blender deformation renders or
browser-side animation/morph tests.
"""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path


def read_glb(path: Path) -> dict:
    data = path.read_bytes()
    if len(data) < 20:
        raise ValueError(f"GLB is too small: {len(data)} bytes")
    magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF":
        raise ValueError("Not a GLB file (missing glTF magic)")
    if version != 2:
        raise ValueError(f"Expected glTF 2.0, got version {version}")
    if declared_length != len(data):
        raise ValueError(f"GLB length mismatch: header={declared_length}, actual={len(data)}")
    offset = 12
    while offset + 8 <= len(data):
        chunk_length, chunk_type = struct.unpack_from("<I4s", data, offset)
        offset += 8
        chunk = data[offset:offset + chunk_length]
        if len(chunk) != chunk_length:
            raise ValueError("Truncated GLB chunk")
        offset += chunk_length
        if chunk_type == b"JSON":
            return json.loads(chunk.decode("utf-8").rstrip(" \\t\\r\\n\\0"))
    raise ValueError("GLB has no JSON chunk")


def validate(gltf: dict) -> list[str]:
    errors: list[str] = []
    nodes = gltf.get("nodes", [])
    meshes = gltf.get("meshes", [])
    skins = gltf.get("skins", [])
    animations = gltf.get("animations", [])
    if not skins:
        errors.append("No glTF skins found; candidate is baked/unskinned")
    node_names = [n.get("name", "") for n in nodes]
    valid_joint_indices = set(range(len(nodes)))
    skinned_nodes = [n for n in nodes if "skin" in n and "mesh" in n]
    if skins and not skinned_nodes:
        errors.append("No node references both a mesh and a skin")
    for si, skin in enumerate(skins):
        joints = skin.get("joints", [])
        if not joints:
            errors.append(f"Skin {si} has no joints")
        invalid = [j for j in joints if j not in valid_joint_indices]
        if invalid:
            errors.append(f"Skin {si} references invalid joint node indices: {invalid}")
        if "inverseBindMatrices" not in skin:
            errors.append(f"Skin {si} has no inverseBindMatrices accessor")
    for ni, node in enumerate(nodes):
        if "skin" in node:
            if node["skin"] < 0 or node["skin"] >= len(skins):
                errors.append(f"Node {ni} references invalid skin index {node['skin']}")
            if "mesh" not in node:
                errors.append(f"Node {ni} has a skin but no mesh")
    joint_targets = set()
    animation_channels = 0
    for ai, animation in enumerate(animations):
        for channel in animation.get("channels", []):
            animation_channels += 1
            target = channel.get("target", {})
            if target.get("path") in ("translation", "rotation", "scale") and isinstance(target.get("node"), int):
                joint_targets.add(target["node"])
    all_joints = {j for skin in skins for j in skin.get("joints", [])}
    if not animations:
        errors.append("No skeletal animation clips found")
    elif not joint_targets.intersection(all_joints):
        errors.append("No animation channel targets a joint in any exported skin")
    if animation_channels == 0:
        errors.append("Animations contain no channels")
    if not meshes:
        errors.append("No glTF meshes found")
    # Keep facial controls available while the skinning pipeline is reworked.
    expected_morphs = {
        "blink_left", "blink_right", "brow_raise", "cheek_raise", "jaw_hinge",
        "jaw_open", "lip_fv", "lip_press", "lip_round", "mouth_open", "smile",
        "tongue_tip",
    }
    found_morphs = set()
    for mesh in meshes:
        for primitive in mesh.get("primitives", []):
            for target in primitive.get("targets", []):
                # glTF morph target names are stored in mesh.extras.targetNames.
                pass
        extras = mesh.get("extras", {})
        found_morphs.update(extras.get("targetNames", []))
    missing_morphs = sorted(expected_morphs - found_morphs)
    if missing_morphs:
        errors.append("Missing expected morph target names in mesh extras: " + ", ".join(missing_morphs))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("glb", type=Path, help="Path to experimental candidate GLB")
    parser.add_argument("--report", type=Path, help="Optional JSON report output path")
    args = parser.parse_args()
    gltf = read_glb(args.glb)
    errors = validate(gltf)
    report = {
        "file": str(args.glb),
        "nodes": len(gltf.get("nodes", [])),
        "meshes": len(gltf.get("meshes", [])),
        "skins": len(gltf.get("skins", [])),
        "animations": [a.get("name", "") for a in gltf.get("animations", [])],
        "errors": errors,
        "passed": not errors,
    }
    serialized = json.dumps(report, indent=2, ensure_ascii=False)
    print(serialized)
    if args.report:
        args.report.write_text(serialized + "\\n", encoding="utf-8")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
