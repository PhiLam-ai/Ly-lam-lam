#!/usr/bin/env python3
"""Convert a TripoSR OBJ+texture pair into a standard Y-up textured GLB candidate."""
import os, math, argparse, json
import numpy as np
import cv2
from PIL import Image
from scipy.ndimage import distance_transform_edt
import trimesh

parser = argparse.ArgumentParser()
parser.add_argument("--mesh-dir", required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--label", default="Lam TripoSR candidate")
parser.add_argument("--minimum-vertices", type=int, default=10000)
parser.add_argument("--minimum-faces", type=int, default=10000)
parser.add_argument("--padding-pixels", type=float, default=8.0)
parser.add_argument("--atlas-output", default="")
args = parser.parse_args()

obj_path = os.path.join(args.mesh_dir, "mesh.obj")
texture_path = os.path.join(args.mesh_dir, "texture.png")
if not os.path.isfile(obj_path) or not os.path.isfile(texture_path):
    raise SystemExit(f"Expected both {obj_path} and {texture_path}")
mesh = trimesh.load(obj_path, force="mesh", process=False)
uv = getattr(mesh.visual, "uv", None)
if uv is None or np.asarray(uv).shape != (len(mesh.vertices), 2):
    raise SystemExit("TripoSR OBJ has missing or mismatched UV coordinates.")
uv = np.asarray(uv, dtype=np.float32).copy()
texture = Image.open(texture_path).convert("RGB")
atlas = np.asarray(texture, dtype=np.uint8).copy()
h, w = atlas.shape[:2]

# TripoSR output is Z-up, with the input-facing surface generally along +X.
# Rotate in the floor plane to point the front toward -X, then convert Z-up to glTF Y-up.
rz = trimesh.transformations.rotation_matrix(math.pi, [0, 0, 1])
rx = trimesh.transformations.rotation_matrix(-math.pi / 2, [1, 0, 0])
mesh.apply_transform(rx @ rz)

# Expand island pixels into unused atlas gutters to reduce black bleeding under linear filtering.
uvpix = uv.copy()
uvpix[:, 0] *= (w - 1)
uvpix[:, 1] = (1.0 - uvpix[:, 1]) * (h - 1)
coverage = np.zeros((h, w), dtype=np.uint8)
for tri in mesh.faces:
    cv2.fillPoly(coverage, [np.rint(uvpix[tri]).astype(np.int32)], 255)
island = coverage > 0
distance, nearest = distance_transform_edt(~island, return_indices=True)
pad = (~island) & (distance > 0) & (distance <= args.padding_pixels)
atlas[pad] = atlas[nearest[0][pad], nearest[1][pad]]
if args.atlas_output:
    Image.fromarray(atlas).save(args.atlas_output)

mesh.fix_normals(multibody=True)
material = trimesh.visual.material.PBRMaterial(
    name=args.label,
    baseColorTexture=Image.fromarray(atlas),
    metallicFactor=0.0,
    roughnessFactor=0.82,
    alphaMode="OPAQUE",
)
mesh.visual = trimesh.visual.texture.TextureVisuals(uv=uv, material=material)
os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
trimesh.Scene(mesh).export(args.output)

check = trimesh.load(args.output, force="scene", process=False)
meshes = [g for g in check.geometry.values() if isinstance(g, trimesh.Trimesh)]
if len(meshes) != 1:
    raise SystemExit("Exported GLB must contain exactly one mesh.")
g = meshes[0]
embedded = getattr(getattr(g.visual, "material", None), "baseColorTexture", None)
extents = np.asarray(check.bounds[1]) - np.asarray(check.bounds[0])
if embedded is None or embedded.size[0] < 512 or embedded.size[1] < 512:
    raise SystemExit("GLB embedded texture validation failed.")
if int(np.argmax(extents)) != 1:
    raise SystemExit("Orientation validation failed: glTF Y must be the longest/up axis; extents=" + str(extents.tolist()))
if len(g.vertices) < args.minimum_vertices or len(g.faces) < args.minimum_faces:
    raise SystemExit("Mesh is below minimum geometry thresholds.")
if os.path.getsize(args.output) < 1024:
    raise SystemExit("GLB output is too small.")
print("GLB_VALID=1")
print("GLB_BYTES=" + str(os.path.getsize(args.output)))
print("VERTICES=" + str(len(g.vertices)))
print("FACES=" + str(len(g.faces)))
print("BOUNDS=" + json.dumps(check.bounds.tolist()))
print("EMBEDDED_TEXTURE_SIZE=" + json.dumps(list(embedded.size)))
print("GLTF_UP_AXIS=Y")
print("ORIENTATION_FIX=Rz180_then_Rx_minus90")
print("UV_ISLAND_PADDING_PIXELS=" + str(args.padding_pixels))
print("PADDED_TEXELS=" + str(int(pad.sum())))
