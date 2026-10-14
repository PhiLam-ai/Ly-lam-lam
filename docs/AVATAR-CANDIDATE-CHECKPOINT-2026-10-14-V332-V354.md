# Lý Lâm Lam avatar candidate checkpoint — V332–V354 (2026-10-14)

## Release decision

**No current candidate is approved as the production avatar.** Production `main/v312-work/lam-default.glb` and the production viewer remain separate from the experimental branch `avatar/v313-repair-candidate-20261014`. A technical PASS does not substitute for Phi's visual approval of the complete Lam likeness.

## Accepted experimental building blocks

- **V340 body silhouette:** central-x falloff keeps the fuller hips and thighs while preserving the arm width. Visual shape experiment accepted for further candidate work; not a full-avatar approval.
- **V341 hair:** luminance-compressed darkened hair diffuse, alpha/UV preserved, glTF material verified from embedded image pixels. Visible pale crown rim substantially reduced.
- **V345 smile baseline:** the later closed-lip gentle-smile experiment at strength 0.40 is the adopted smile baseline for the eye-material work. This is distinct from V342's earlier 0.12 smile, which was technically successful but too subtle to read reliably in the full-body mobile view.
- **V350 eye front-surface material:** the existing high-poly eye mesh's four connected components are kept in place and two front components per side receive a restrained glTF-compatible specular/clearcoat response. No eye geometry is changed.
- **V352 fill lighting:** an isolated browser-only lighting change (no GLB change) brightens the eye/nose/mouth area and softens hard shadows. The A/B was judged a provisional viewer-lighting improvement; the face still does not match the chosen Lam likeness.
- **V353 Windows preview:** successful 81-entry package `ly-lam-lam-v353-experimental-windows.zip`; SHA-256 `23fce310d69e73cd78389ddb2f50c4557985a59e84c6d6f31f578a3563ed4b81` verified against the sidecar and downloaded bytes. It contains the exact V350 model GLB (20,484,436 bytes; SHA-256 `9e36f37c6e12dfbded9c47dcbf0cfbbfd7e339112aa5a32bcc4d11d9bc0f05ee`) plus the V352 viewer-only fill-lighting change. The V353 package is preview-only and is not a production promotion.

Detailed previous checkpoint evidence:
- [V332–V342 build, geometry, hair and early smile work](https://github.com/PhiLam-ai/Ly-lam-lam/blob/avatar/v313-repair-candidate-20261014/docs/AVATAR-CANDIDATE-CHECKPOINT-2026-10-14-V332-V342.md)
- [V348–V353 eye, browser lighting and preview package review](https://github.com/PhiLam-ai/Ly-lam-lam/blob/avatar/v313-repair-candidate-20261014/docs/AVATAR-CANDIDATE-CHECKPOINT-2026-10-14-V348-V349.md)

## V343 parallel smile experiment — duplicate, not adopted

A separate V343 run was created from the earlier V342 conversation checkpoint after the branch had already progressed through V344–V353. The run `38607779884` is a duplicate experiment and must not replace the later closed-lip smile baseline or be treated as the latest avatar candidate. Compare by workflow/run ID and source script, not version label alone; some experiment tracks reused V343 labels.

## V354 — necklace accessory candidate (run in progress)

- Workflow: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38608109632
- Builder: `tools/blender_v354_necklace_accessory.py`
- Workflow: `.github/workflows/v354-necklace-accessory.yml`
- Adds two separate meshes only: a thin gold chain and a small oval pendant. Chain points are positioned using sampled front-surface locations from the existing shirt/skin geometry; build fails closed if it cannot sample the needed positions. The material uses a restrained gold color, metallic 0.55 and roughness 0.28.
- Carries the V340 body silhouette, V341 darkened hair, V345 closed-lip smile and V350 front-eye material response. It should not alter the body, clothing, face, hair, eye geometry/material response, morph targets or idle animation logic.
- Gates verify the chain and pendant are actual meshes, each has nonzero geometry, seven chain samples and one pendant sample are recorded, both objects export as glTF nodes, gold material PBR values survive export, all 12 morphs remain, the eye and hair material audits still pass, mobile WebGL renders without browser errors, and the preview ZIP passes integrity and SHA-256 checks.
- Visual decision is pending. Inspect front, face-closeup and eye-closeup outputs for chain/skin separation, pendant placement and whether the necklace is visible in the browser. This is a small accessory test; it does not approve the full avatar likeness.

## Safety and rollback

- Do not copy any experimental GLB into production `v312-work/lam-default.glb` or promote it through the stable registry.
- Always inspect the actual V354 images and browser capture, not only the green workflow status.
- Record SHA-256 only after recomputing the downloaded file's bytes and matching the package sidecar.
- Preserve the previous successful preview and stable production files.