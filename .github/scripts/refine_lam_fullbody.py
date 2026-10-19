#!/usr/bin/env python3
"""Improve the TripoSR full-body candidate: fix glTF axes, project the clean front reference, pad the UV atlas."""
import os, math, json
import numpy as np
import cv2
from PIL import Image
from scipy.ndimage import distance_transform_edt
import trimesh

RAW_OBJ = "output/triposr-fullbody/0/mesh.obj"
RAW_TEX = "output/triposr-fullbody/0/texture.png"
REF = "output/lam-fullbody-front-reference.png"
SHEET = "references/lam-reference.png.png"
SIDE_REF_OUT = "output/lam-fullbody-side-reference.png"
SIDE_MASK_OUT = "output/lam-fullbody-side-mask.png"
BACK_REF_OUT = "output/lam-fullbody-back-reference.png"
BACK_MASK_OUT = "output/lam-fullbody-back-mask.png"
OUT = "output/lam-triposr-fullbody-candidate.glb"
ATLAS_OUT = "output/lam-fullbody-corrected-atlas.png"
MASK_OUT = "output/lam-fullbody-front-mask.png"
COVER_OUT = "output/lam-fullbody-uv-coverage.png"
README_OUT = "output/README-lam-fullbody-refined.txt"

# TripoSR mesh is Z-up and its front faces +X. Turn it toward -X without
# flipping top/bottom, then convert the old Z-up axis to standard glTF Y-up.
rz = trimesh.transformations.rotation_matrix(math.pi, [0, 0, 1])
rx = trimesh.transformations.rotation_matrix(-math.pi / 2, [1, 0, 0])
orientation = rx @ rz
front_dot = 0.35
y_min, y_max = -0.474197, 0.478296
z_min, z_max = -0.128215, 0.126135
src_x0, src_x1 = 36.0, 470.0
src_y0, src_y1 = 8.0, 1525.0
blend = 0.97

for p in (RAW_OBJ, RAW_TEX, REF, SHEET):
    if not os.path.exists(p):
        raise SystemExit("Required source file missing: " + p)

mesh = trimesh.load(RAW_OBJ, force="mesh", process=False)
uv = np.asarray(mesh.visual.uv, dtype=np.float32).copy()
if uv.shape != (len(mesh.vertices), 2):
    raise SystemExit("Missing or mismatched UV coordinates.")
orig = np.asarray(Image.open(RAW_TEX).convert("RGB"), dtype=np.uint8).copy()
h, w = orig.shape[:2]
source = np.asarray(Image.open(REF).convert("RGB"), dtype=np.uint8)
sh, sw = source.shape[:2]
print("RAW_VERTICES=", len(mesh.vertices), "RAW_FACES=", len(mesh.faces), "ATLAS=", (w, h), "SOURCE=", (sw, sh), flush=True)

mesh.apply_transform(orientation)
mesh.fix_normals(multibody=True)
verts = np.asarray(mesh.vertices, dtype=np.float32)
faces = np.asarray(mesh.faces, dtype=np.int32)
normals = np.asarray(mesh.face_normals, dtype=np.float32)
bounds = mesh.bounds
extents = bounds[1] - bounds[0]
if int(np.argmax(extents)) != 1:
    raise SystemExit("Orientation transform failed: Y must be the longest (up) axis; extents=" + str(extents.tolist()))
print("GLTF_Y_UP_BOUNDS=", bounds.tolist(), flush=True)

# Segmentation: constrained silhouette envelope + GrabCut. This excludes
# the reference sheet's branding and the changing gray background near feet.
bg = np.median(source[:, max(0, sw - 24):sw, :].reshape(-1, 3), axis=0)
dist = np.linalg.norm(source.astype(np.float32) - bg[None, None, :], axis=2)
envelope = np.array([
 [244,12],[270,24],[293,60],[316,112],[339,174],[364,229],[395,263],[418,282],
 [435,323],[446,400],[454,510],[458,635],[455,750],[446,851],[430,952],[406,1045],
 [380,1145],[358,1240],[344,1330],[338,1430],[327,1494],[312,1520],[292,1522],
 [276,1485],[266,1425],[250,1353],[240,1308],[229,1360],[217,1430],[202,1492],
 [184,1521],[168,1510],[163,1466],[170,1380],[179,1293],[176,1203],[158,1112],
 [137,1030],[112,966],[85,905],[65,852],[50,784],[45,700],[46,600],[48,498],
 [54,400],[63,333],[79,296],[103,278],[136,259],[164,220],[188,164],[207,106],[226,48]
], dtype=np.int32)
env = np.zeros((sh, sw), dtype=np.uint8)
cv2.fillPoly(env, [envelope], 255)
gc = np.full((sh, sw), cv2.GC_PR_BGD, dtype=np.uint8)
gc[env == 0] = cv2.GC_BGD
inside = env > 0
gc[inside & (dist > 22)] = cv2.GC_PR_FGD
gc[inside & (dist > 62)] = cv2.GC_FGD
gc[inside & (dist < 13)] = cv2.GC_PR_BGD
bg_model = np.zeros((1, 65), np.float64)
fg_model = np.zeros((1, 65), np.float64)
cv2.grabCut(source, gc, None, bg_model, fg_model, 5, cv2.GC_INIT_WITH_MASK)
mask = np.where((gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
mask = cv2.bitwise_and(mask, env)
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)), iterations=1)
mask = cv2.GaussianBlur(mask, (0, 0), sigmaX=1.5, sigmaY=1.5)
Image.fromarray(mask).save(MASK_OUT)
print("BACKGROUND_RGB=", bg.tolist(), "FOREGROUND_PIXELS=", int((mask > 100).sum()), flush=True)

# Paint the clean front reference onto the front half-shell in the existing UV atlas.
# Use object-space projection, so the subject photo aligns to the whole-body mesh.
tex = orig.copy()
uvpix = uv.copy()
uvpix[:, 0] *= (w - 1)
uvpix[:, 1] = (1.0 - uvpix[:, 1]) * (h - 1)
painted = 0
selected = 0
for tri in faces:
    p3 = verts[tri]
    center = p3.mean(axis=0)
    if center[0] > -0.025:
        continue
    if center[1] < y_min - 0.015 or center[1] > y_max + 0.015 or center[2] < z_min - 0.015 or center[2] > z_max + 0.015:
        continue
    selected += 1
    p2 = uvpix[tri]
    x0, y0 = np.floor(p2.min(axis=0)).astype(int)
    x1, y1 = np.ceil(p2.max(axis=0)).astype(int)
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(w - 1, x1), min(h - 1, y1)
    if x1 < x0 or y1 < y0:
        continue
    bw, bh = x1 - x0 + 1, y1 - y0 + 1
    if bw * bh > 200000:
        continue
    gx, gy = np.meshgrid(np.arange(x0, x1 + 1, dtype=np.float32) + 0.5,
                         np.arange(y0, y1 + 1, dtype=np.float32) + 0.5)
    a, b, c = p2
    den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
    if abs(float(den)) < 1e-6:
        continue
    wa = ((b[1] - c[1]) * (gx - c[0]) + (c[0] - b[0]) * (gy - c[1])) / den
    wb = ((c[1] - a[1]) * (gx - c[0]) + (a[0] - c[0]) * (gy - c[1])) / den
    wc = 1.0 - wa - wb
    valid = (wa >= -0.005) & (wb >= -0.005) & (wc >= -0.005) & (wa <= 1.005) & (wb <= 1.005) & (wc <= 1.005)
    if not valid.any():
        continue
    py = wa * p3[0, 1] + wb * p3[1, 1] + wc * p3[2, 1]
    pz = wa * p3[0, 2] + wb * p3[1, 2] + wc * p3[2, 2]
    px = wa * p3[0, 0] + wb * p3[1, 0] + wc * p3[2, 0]
    valid &= (py >= y_min) & (py <= y_max) & (pz >= z_min) & (pz <= z_max) & (px <= 0.025)
    if not valid.any():
        continue
    sx = src_x0 + ((pz - z_min) / (z_max - z_min)) * (src_x1 - src_x0)
    sy = src_y0 + ((y_max - py) / (y_max - y_min)) * (src_y1 - src_y0)
    sx = np.clip(sx, 0, sw - 1.001).astype(np.float32)
    sy = np.clip(sy, 0, sh - 1.001).astype(np.float32)
    sample = cv2.remap(source, sx, sy, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    alpha = cv2.remap(mask, sx, sy, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0).astype(np.float32) / 255.0
    valid &= alpha > 0.12
    if not valid.any():
        continue
    al = (blend * np.clip(alpha, 0, 1))[valid][..., None]
    dest = tex[y0:y1 + 1, x0:x1 + 1]
    dest[valid] = np.clip(sample[valid].astype(np.float32) * al + dest[valid].astype(np.float32) * (1 - al), 0, 255).astype(np.uint8)
    painted += int(valid.sum())
if painted < 10000:
    raise SystemExit("Front projection covered too few atlas texels: " + str(painted))
print("FRONT_SHELL_TRIANGLES=", selected, "PROJECTED_TEXELS=", painted, flush=True)

# Use the dedicated side and back views already present in the locked reference sheet.
# The panels are low resolution, but they greatly reduce texture hallucination on the silhouette.
sheet = Image.open(SHEET).convert("RGB")
side_im = sheet.crop((773, 85, 884, 431))
back_im = sheet.crop((887, 85, 1000, 431))
side = np.asarray(side_im, dtype=np.uint8)
back = np.asarray(back_im, dtype=np.uint8)

def panel_foreground(image, polygon, out_path):
    ih, iw = image.shape[:2]
    envelope = np.zeros((ih, iw), dtype=np.uint8)
    cv2.fillPoly(envelope, [np.asarray(polygon, dtype=np.int32)], 255)
    edge = np.concatenate([image[:8].reshape(-1, 3), image[-8:].reshape(-1, 3),
                           image[:, :8].reshape(-1, 3), image[:, -8:].reshape(-1, 3)], axis=0)
    bg = np.median(edge, axis=0)
    d = np.linalg.norm(image.astype(np.float32) - bg[None, None, :], axis=2)
    gc = np.full((ih, iw), cv2.GC_PR_BGD, dtype=np.uint8)
    gc[envelope == 0] = cv2.GC_BGD
    inside = envelope > 0
    gc[inside] = cv2.GC_PR_FGD
    gc[inside & (d > 28)] = cv2.GC_FGD
    gc[inside & (d > 13) & (d <= 28)] = cv2.GC_PR_FGD
    # Keep central hair/torso as sure foreground to prevent cutout of dark hair.
    core = np.zeros((ih, iw), dtype=np.uint8)
    cv2.fillPoly(core, [np.asarray(polygon, dtype=np.int32)], 255)
    eroded = cv2.erode(core, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)), iterations=1)
    gc[eroded > 0] = cv2.GC_FGD
    bgm = np.zeros((1, 65), np.float64)
    fgm = np.zeros((1, 65), np.float64)
    cv2.grabCut(image, gc, None, bgm, fgm, 3, cv2.GC_INIT_WITH_MASK)
    mask = np.where((gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    mask = cv2.bitwise_and(mask, envelope)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)), iterations=1)
    mask = cv2.GaussianBlur(mask, (0, 0), sigmaX=0.9, sigmaY=0.9)
    Image.fromarray(image).save(out_path.replace("-mask.png", "-reference.png"))
    Image.fromarray(mask).save(out_path)
    return mask

side_poly = [(44,3),(56,3),(65,15),(70,36),(74,62),(77,90),(76,117),
             (72,144),(73,170),(78,195),(77,222),(72,250),(68,279),(64,309),
             (59,339),(43,339),(39,318),(38,290),(34,263),(30,235),(27,206),
             (24,176),(21,146),(19,116),(20,87),(23,59),(29,34),(36,15)]
back_poly = [(31,3),(68,3),(78,18),(81,44),(80,75),(79,109),(80,141),
             (82,171),(80,200),(78,229),(73,258),(69,285),(64,314),(58,339),
             (39,339),(34,314),(31,286),(29,258),(27,229),(26,199),(26,168),
             (26,137),(25,107),(25,78),(26,50),(27,23)]
side_mask = panel_foreground(side, side_poly, SIDE_MASK_OUT)
back_mask = panel_foreground(back, back_poly, BACK_MASK_OUT)
Image.fromarray(side).save(SIDE_REF_OUT)
Image.fromarray(back).save(BACK_REF_OUT)

x_min, x_max = float(bounds[0, 0]), float(bounds[1, 0])
y_lo, y_hi = float(bounds[0, 1]), float(bounds[1, 1])
z_lo, z_hi = float(bounds[0, 2]), float(bounds[1, 2])
uvpix = uv.copy()
uvpix[:, 0] *= (w - 1)
uvpix[:, 1] = (1.0 - uvpix[:, 1]) * (h - 1)

def project_view(image, alpha_mask, mode, blend_amount, x_window=None):
    ih, iw = image.shape[:2]
    texels = 0
    triangles = 0
    if mode == "side_negative":
        image = np.fliplr(image).copy()
        alpha_mask = np.fliplr(alpha_mask).copy()
    for fi, tri in enumerate(faces):
        p3 = verts[tri]
        center = p3.mean(axis=0)
        n = normals[fi]
        if mode == "back":
            if center[0] < 0.025 or n[0] < 0.22: continue
        elif mode == "side_positive":
            if center[2] < 0.025 or n[2] < 0.22: continue
        elif mode == "side_negative":
            if center[2] > -0.025 or n[2] > -0.22: continue
        else:
            raise ValueError(mode)
        p2 = uvpix[tri]
        x0, y0 = np.floor(p2.min(axis=0)).astype(int)
        x1, y1 = np.ceil(p2.max(axis=0)).astype(int)
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(w - 1, x1), min(h - 1, y1)
        if x1 < x0 or y1 < y0: continue
        bw, bh = x1 - x0 + 1, y1 - y0 + 1
        if bw * bh > 200000: continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1, dtype=np.float32) + 0.5,
                             np.arange(y0, y1 + 1, dtype=np.float32) + 0.5)
        a, b, d = p2
        den = (b[1] - d[1]) * (a[0] - d[0]) + (d[0] - b[0]) * (a[1] - d[1])
        if abs(float(den)) < 1e-6: continue
        wa = ((b[1] - d[1]) * (gx - d[0]) + (d[0] - b[0]) * (gy - d[1])) / den
        wb = ((d[1] - a[1]) * (gx - d[0]) + (a[0] - d[0]) * (gy - d[1])) / den
        wc = 1.0 - wa - wb
        valid = (wa >= -0.005) & (wb >= -0.005) & (wc >= -0.005) & (wa <= 1.005) & (wb <= 1.005) & (wc <= 1.005)
        if not valid.any(): continue
        px = wa * p3[0, 0] + wb * p3[1, 0] + wc * p3[2, 0]
        py = wa * p3[0, 1] + wb * p3[1, 1] + wc * p3[2, 1]
        pz = wa * p3[0, 2] + wb * p3[1, 2] + wc * p3[2, 2]
        sy = np.clip((y_hi - py) / (y_hi - y_lo) * (ih - 1), 0, ih - 1.001).astype(np.float32)
        if mode == "back":
            # The side/back thumbnails have panel margins. Map only the person-bearing
            # horizontal span to the full body width, rather than stretching gray margins.
            back_sx0, back_sx1 = 18.0, 88.0
            sx = back_sx0 + (z_hi - pz) / (z_hi - z_lo) * (back_sx1 - back_sx0)
            sx = np.clip(sx, 0, iw - 1.001).astype(np.float32)
            valid &= (pz >= z_lo - 0.005) & (pz <= z_hi + 0.005)
        else:
            sx0, sx1 = x_window
            sx = sx0 + np.clip((px - x_min) / (x_max - x_min), 0, 1) * (sx1 - sx0)
            sx = np.clip(sx, 0, iw - 1.001).astype(np.float32)
            valid &= (px >= x_min - 0.005) & (px <= x_max + 0.005)
        sample = cv2.remap(image, sx, sy, interpolation=cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_REPLICATE)
        a_mask = cv2.remap(alpha_mask, sx, sy, interpolation=cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_CONSTANT, borderValue=0).astype(np.float32) / 255.0
        valid &= a_mask > 0.10
        if not valid.any(): continue
        al = (blend_amount * np.clip(a_mask, 0, 1))[valid][..., None]
        dest = tex[y0:y1 + 1, x0:x1 + 1]
        dest[valid] = np.clip(sample[valid].astype(np.float32) * al +
                              dest[valid].astype(np.float32) * (1 - al), 0, 255).astype(np.uint8)
        texels += int(valid.sum())
        triangles += 1
    print("PROJECT_VIEW=", mode, "TRIANGLES=", triangles, "PROJECTED_TEXELS=", texels, flush=True)
    return texels

# Source-side front is on the left of the profile photograph; map it to negative X.
side_pos_texels = project_view(side, side_mask, "side_positive", 0.82, x_window=(13, 86))
# Mirror the one profile for the opposite side so front remains oriented correctly.
side_neg_texels = project_view(side, side_mask, "side_negative", 0.82, x_window=(13, 86))
back_texels = project_view(back, back_mask, "back", 0.85)
print("MULTIVIEW_PROJECTION_TOTALS=", json.dumps({
    "front": int(painted), "side_positive": int(side_pos_texels),
    "side_negative": int(side_neg_texels), "back": int(back_texels)
}), flush=True)

# Pad UV islands by nearest valid colors to prevent black unused atlas gutters bleeding at runtime.
coverage = np.zeros((h, w), dtype=np.uint8)
for tri in faces:
    cv2.fillPoly(coverage, [np.rint(uvpix[tri]).astype(np.int32)], 255)
Image.fromarray(coverage).save(COVER_OUT)
island = coverage > 0
distance, nearest = distance_transform_edt(~island, return_indices=True)
pad = (~island) & (distance > 0) & (distance <= 8.0)
tex[pad] = tex[nearest[0][pad], nearest[1][pad]]
print("UV_COVERAGE_PIXELS=", int(island.sum()), "ATLAS_PADDING_PIXELS=", int(pad.sum()), flush=True)
Image.fromarray(tex).save(ATLAS_OUT)

# Smooth gently while preserving UVs and the embedded atlas.
uv_keep = uv.copy()
try:
    trimesh.smoothing.filter_taubin(mesh, lamb=0.28, nu=0.31, iterations=2)
    smoothing = "taubin_2_iterations"
except Exception as exc:
    print("SMOOTHING_SKIPPED=", repr(exc))
    smoothing = "none"
mesh.fix_normals(multibody=True)
material = trimesh.visual.material.PBRMaterial(
    name="Lam full-body front-reference projection",
    baseColorTexture=Image.fromarray(tex),
    metallicFactor=0.0,
    roughnessFactor=0.82,
    alphaMode="OPAQUE",
)
mesh.visual = trimesh.visual.texture.TextureVisuals(uv=uv_keep, material=material)
os.makedirs("output", exist_ok=True)
trimesh.Scene(mesh).export(OUT)
check = trimesh.load(OUT, force="scene", process=False)
out_meshes = [g for g in check.geometry.values() if isinstance(g, trimesh.Trimesh)]
if len(out_meshes) != 1:
    raise SystemExit("Exported GLB must contain exactly one mesh.")
g = out_meshes[0]
embedded = getattr(getattr(g.visual, "material", None), "baseColorTexture", None)
extents = np.asarray(check.bounds[1]) - np.asarray(check.bounds[0])
if embedded is None or embedded.size != (w, h):
    raise SystemExit("Embedded 2048x2048 texture validation failed.")
if int(np.argmax(extents)) != 1:
    raise SystemExit("GLB orientation validation failed: Y must be up.")
if len(g.vertices) < 10000 or len(g.faces) < 10000 or os.path.getsize(OUT) < 1024:
    raise SystemExit("Mesh/file validation failed.")
summary = {
    "status": "experimental_candidate_validated",
    "vertices": len(g.vertices),
    "faces": len(g.faces),
    "bounds": check.bounds.tolist(),
    "up_axis": "Y",
    "embedded_texture": list(embedded.size),
    "geometry_smoothing": smoothing,
    "front_projection_texels": painted,
    "side_positive_projection_texels": int(side_pos_texels),
    "side_negative_projection_texels": int(side_neg_texels),
    "back_projection_texels": int(back_texels),
    "uv_padding_texels": int(pad.sum()),
    "production_modified": False,
    "note": "Not production-ready; inspect side/back texture and face likeness before use.",
}
with open(README_OUT, "w", encoding="utf-8") as f:
    f.write("LY LAM LAM — FRONT-PROJECTED FULL-BODY EXPERIMENT\n\n")
    f.write(json.dumps(summary, ensure_ascii=False, indent=2))
    f.write("\n\nSource branch: experiment/github-auto-avatar. Production/main and lam-default.glb were not modified.\n")
print("FULLBODY_GLB_VALID=1")
print("GLB_BYTES=", os.path.getsize(OUT))
print("VERTICES=", len(g.vertices))
print("FACES=", len(g.faces))
print("BOUNDS=", json.dumps(check.bounds.tolist()))
print("EMBEDDED_TEXTURE=", embedded.size)
print("UP_AXIS=Y")
print("SMOOTHING=", smoothing)
print("FRONT_PROJECTION_TEXELS=", painted)
