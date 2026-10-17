#!/usr/bin/env python3
"""Structural acceptance checks for the experimental V387 skinned GLB.

This validator intentionally rejects the V386 baked/unskinned candidate. It checks
GLB/glTF structure, not visual deformation; Blender pose renders and browser tests
remain separate required gates.
"""
from __future__ import annotations
import argparse, json, struct
from pathlib import Path

EXPECTED_MORPHS = {
    "blink_left", "blink_right", "brow_raise", "cheek_raise", "jaw_hinge",
    "jaw_open", "lip_fv", "lip_press", "lip_round", "mouth_open", "smile", "tongue_tip",
}

def read_glb(path: Path) -> dict:
    data = path.read_bytes()
    if len(data) < 20: raise ValueError(f"GLB is too small: {len(data)} bytes")
    magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF": raise ValueError("Not a GLB file (missing glTF magic)")
    if version != 2: raise ValueError(f"Expected glTF 2.0, got version {version}")
    if declared_length != len(data): raise ValueError(f"GLB length mismatch: header={declared_length}, actual={len(data)}")
    offset = 12
    while offset + 8 <= len(data):
        chunk_length, chunk_type = struct.unpack_from("<I4s", data, offset)
        offset += 8
        chunk = data[offset:offset + chunk_length]
        if len(chunk) != chunk_length: raise ValueError("Truncated GLB chunk")
        offset += chunk_length
        if chunk_type == b"JSON":
            return json.loads(chunk.decode("utf-8").rstrip(" \\t\\r\\n\\0"))
    raise ValueError("GLB has no JSON chunk")

def validate(gltf: dict) -> list[str]:
    errors = []
    nodes, meshes = gltf.get("nodes", []), gltf.get("meshes", [])
    skins, animations = gltf.get("skins", []), gltf.get("animations", [])
    accessors = gltf.get("accessors", [])
    if not skins: errors.append("No glTF skins found; candidate is baked/unskinned")
    skinned_nodes = [n for n in nodes if "skin" in n and "mesh" in n]
    if skins and not skinned_nodes: errors.append("No node references both a mesh and a skin")
    for si, skin in enumerate(skins):
        joints = skin.get("joints", [])
        if not joints: errors.append(f"Skin {si} has no joints")
        if len(joints) != len(set(joints)): errors.append(f"Skin {si} contains duplicate joint node indices")
        invalid = [j for j in joints if not isinstance(j, int) or j < 0 or j >= len(nodes)]
        if invalid: errors.append(f"Skin {si} references invalid joint node indices: {invalid}")
        ibm = skin.get("inverseBindMatrices")
        if ibm is None: errors.append(f"Skin {si} has no inverseBindMatrices accessor")
        elif not isinstance(ibm, int) or ibm < 0 or ibm >= len(accessors):
            errors.append(f"Skin {si} has invalid inverseBindMatrices accessor {ibm}")
        elif accessors[ibm].get("count") is not None and accessors[ibm]["count"] != len(joints):
            errors.append(f"Skin {si} inverse bind matrix count {accessors[ibm]['count']} != joint count {len(joints)}")
    all_joints = {j for skin in skins for j in skin.get("joints", []) if isinstance(j, int)}
    for ni, node in enumerate(nodes):
        if "skin" not in node: continue
        if not isinstance(node["skin"], int) or node["skin"] < 0 or node["skin"] >= len(skins):
            errors.append(f"Node {ni} references invalid skin index {node['skin']}")
        if "mesh" not in node: errors.append(f"Node {ni} has a skin but no mesh")
        elif isinstance(node.get("mesh"), int) and 0 <= node["mesh"] < len(meshes):
            for pi, primitive in enumerate(meshes[node["mesh"]].get("primitives", [])):
                attrs = primitive.get("attributes", {})
                if "JOINTS_0" not in attrs or "WEIGHTS_0" not in attrs:
                    errors.append(f"Skinned node {ni} primitive {pi} lacks JOINTS_0/WEIGHTS_0")
                pos_i, joints_i, weights_i = attrs.get("POSITION"), attrs.get("JOINTS_0"), attrs.get("WEIGHTS_0")
                if not all(isinstance(i, int) and 0 <= i < len(accessors) for i in (pos_i, joints_i, weights_i)):
                    errors.append(f"Skinned node {ni} primitive {pi} has an invalid POSITION/JOINTS_0/WEIGHTS_0 accessor")
                    continue
                pa, ja, wa = accessors[pos_i], accessors[joints_i], accessors[weights_i]
                if ja.get("type") != "VEC4" or ja.get("componentType") not in (5121, 5123):
                    errors.append(f"Skinned node {ni} primitive {pi} JOINTS_0 must be VEC4 unsigned byte/short")
                if wa.get("type") != "VEC4" or wa.get("componentType") not in (5121, 5123, 5126):
                    errors.append(f"Skinned node {ni} primitive {pi} WEIGHTS_0 must be VEC4 unsigned byte/short/float")
                if ja.get("count") != pa.get("count") or wa.get("count") != pa.get("count"):
                    errors.append(f"Skinned node {ni} primitive {pi} skin attribute counts must match POSITION")
                if ja.get("normalized", False):
                    errors.append(f"Skinned node {ni} primitive {pi} JOINTS_0 must not be normalized")
                if wa.get("componentType") == 5126 and wa.get("normalized", False):
                    errors.append(f"Skinned node {ni} primitive {pi} float WEIGHTS_0 must not be normalized")
    joint_targets, channel_count = set(), 0
    for animation in animations:
        for channel in animation.get("channels", []):
            channel_count += 1
            target = channel.get("target", {})
            if target.get("path") in ("translation", "rotation", "scale") and isinstance(target.get("node"), int):
                joint_targets.add(target["node"])
    if not animations: errors.append("No animation clips found")
    elif not joint_targets.intersection(all_joints): errors.append("No animation channel targets a joint in any exported skin")
    if channel_count == 0: errors.append("Animations contain no channels")
    if not meshes: errors.append("No glTF meshes found")
    found_morphs, morph_target_count = set(), 0
    for mesh in meshes:
        morph_target_count += max((len(p.get("targets", [])) for p in mesh.get("primitives", [])), default=0)
        found_morphs.update(mesh.get("extras", {}).get("targetNames", []))
    if morph_target_count == 0: errors.append("No morph targets found on any mesh")
    missing = sorted(EXPECTED_MORPHS - found_morphs)
    if missing: errors.append("Missing expected morph target names in mesh extras: " + ", ".join(missing))
    return errors

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("glb", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    gltf = read_glb(args.glb)
    errors = validate(gltf)
    report = {"file": str(args.glb), "nodes": len(gltf.get("nodes", [])),
              "meshes": len(gltf.get("meshes", [])), "skins": len(gltf.get("skins", [])),
              "animations": [a.get("name", "") for a in gltf.get("animations", [])],
              "errors": errors, "passed": not errors}
    serialized = json.dumps(report, indent=2, ensure_ascii=False)
    print(serialized)
    if args.report: args.report.write_text(serialized + "\n", encoding="utf-8")
    return 0 if not errors else 1

if __name__ == "__main__":
    raise SystemExit(main())
