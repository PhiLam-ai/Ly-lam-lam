# Lý Lâm Lam avatar candidate checkpoint — 2026-10-14

## Release decision

**No candidate in this checkpoint is approved for production replacement.** The production `lam-default.glb` is unchanged. Work is isolated on branch `avatar/v313-repair-candidate-20261014`.

## Verified outcomes

### V332 — baked human morph candidate
- GitHub Actions run: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38553205785
- Result: workflow completed successfully; GLB is structurally valid, contains 0 glTF skins, 9 embedded images, 8 materials, the 12 expected composite morph names, and animation `Lam_Idle_GentleSway`.
- Model: `lam-v332-baked-human-candidate.glb`, 20,168,800 bytes.
- GLB SHA-256: `6ae293a9f975f7ccbedfad5f001291a400a0c5cae1b0bb0c96c4cfa06168e38d`.
- Browser smoke: passed at 390×844, WebGL ready, no browser console/page errors, projected model bounds within view, animation time advanced.
- Windows ZIP: `ly-lam-lam-v332-experimental-windows.zip`, 21,345,994 bytes. ZIP integrity passed, 81 entries. SHA-256 in package sidecar matched the actual file: `94bcd1616e51f5ded25b55caa581e4f807b525340092ecc909fbf24682394036`.
- Visual review: **NOT APPROVED**. Blender evidence images showed a factory-startup cube occluding the lower body; browser screenshot showed red/black facial patches around eyes and mouth.

### V333 — render cleanup and evaluated world transform
- GitHub Actions run: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38561847422
- Result: workflow completed successfully; factory-startup `Cube`, `Camera`, and `Light` were removed before render; evaluated mesh world transforms were used during bake.
- Model: `lam-v333-render-fix-candidate.glb`, 20,168,800 bytes.
- GLB SHA-256: `ff48fb0df3f3d02612896c84b1379b16de24dd3094f826a5d3f77109c29dcaa9`.
- Structural/browser gates: 0 glTF skins, 9 embedded images, 8 materials, 12 morph names, `Lam_Idle_GentleSway`; browser smoke passed at 390×844 with no browser page/console errors and framing heuristic passed.
- Windows ZIP: `ly-lam-lam-v333-experimental-windows.zip`, 21,345,991 bytes. ZIP integrity passed, 81 entries. SHA-256 sidecar matched: `a46902d34f4672dcd2b93d579482bce7f99b81a4deea62418f42c8dd6813dee8`.
- Visual review: **NOT APPROVED**. Removing the default cube fixed Blender render occlusion, but the same red/black face patches persisted in the browser. Passing a WebGL/load test is not sufficient evidence of face quality.

## V334 — face accessory isolation diagnostic (in progress at checkpoint time)
- Workflow: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38562895451
- Script: `tools/blender_v334_face_accessory_isolation.py`
- Hypothesis under test: separate `eyebrow001`, `eyelashes01`, `high-poly`, `teeth_base`, and `tongue01` meshes are contributing the browser facial artifacts, while the base skin texture already contains eyes and lips.
- The candidate-only GLB intentionally excludes those five face accessory meshes so the image can isolate their contribution. The editable Blender source and original reference renders remain available in the Actions artifact.
- Required gates: 0 skins, at least 12 face morph names, `Lam_Idle_GentleSway`, browser GLB load, WebGL readiness, clean console/page errors, appropriate projected bounds, actual canvas visibility, ZIP integrity and matching SHA-256 sidecar.
- Do not approve this texture-only facial test as the final avatar without manual visual review; a clean test may justify rebuilding proper 3D eye/brow/lash/teeth meshes/materials in a subsequent iteration.

## Safety and rollback
- Do not copy any candidate GLB into the production `v312-work/lam-default.glb` or promote it through the stable registry at this stage.
- Keep all test builds, images, reports, and ZIPs in versioned candidate artifacts. Record SHA-256 only after verifying the actual bytes and sidecar.
- A technical PASS means the test gates succeeded; it is not equivalent to an approved realistic avatar.
