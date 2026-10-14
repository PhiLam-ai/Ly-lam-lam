# Lý Lâm Lam avatar candidate checkpoint — 2026-10-14

## Release decision

**No candidate in this checkpoint is approved for production replacement.** The production `lam-default.glb` is unchanged. Work is isolated on branch `avatar/v313-repair-candidate-20261014`.

## Verified outcomes

### V332 — baked human morph candidate
- GitHub Actions run: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38553205785
- Result: workflow completed successfully; GLB contains 0 glTF skins, 9 embedded images, 8 materials, 12 expected composite morph names, and animation `Lam_Idle_GentleSway`.
- Model: `lam-v332-baked-human-candidate.glb`, 20,168,800 bytes. SHA-256: `6ae293a9f975f7ccbedfad5f001291a400a0c5cae1b0bb0c96c4cfa06168e38d`.
- Browser smoke: passed at 390×844, WebGL ready, no browser console/page errors, projected model bounds within view, animation time advanced.
- Windows ZIP: `ly-lam-lam-v332-experimental-windows.zip`, 21,345,994 bytes, ZIP integrity passed with 81 entries. SHA-256 sidecar matched: `94bcd1616e51f5ded25b55caa581e4f807b525340092ecc909fbf24682394036`.
- Visual review: **NOT APPROVED**. Blender evidence showed a factory-startup cube occluding the lower body; browser screenshot showed red/black facial patches around eyes and mouth.

### V333 — render cleanup and evaluated world transform
- GitHub Actions run: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38561847422
- Result: workflow completed successfully; factory-startup `Cube`, `Camera`, and `Light` were removed before render; evaluated mesh world transforms were used during bake.
- Model: `lam-v333-render-fix-candidate.glb`, 20,168,800 bytes. SHA-256: `ff48fb0df3f3d02612896c84b1379b16de24dd3094f826a5d3f77109c29dcaa9`.
- Structural/browser gates: 0 glTF skins, 9 embedded images, 8 materials, 12 morph names, `Lam_Idle_GentleSway`; browser smoke passed at 390×844 with no page/console errors and framing heuristic passed.
- Windows ZIP: `ly-lam-lam-v333-experimental-windows.zip`, 21,345,991 bytes, ZIP integrity passed with 81 entries. SHA-256 sidecar matched: `a46902d34f4672dcd2b93d579482bce7f99b81a4deea62418f42c8dd6813dee8`.
- Visual review: **NOT APPROVED**. Removing the default cube fixed the Blender render, but the same facial patches persisted in the browser.

### V334 — face accessory isolation diagnostic
- GitHub Actions run: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38562895451
- Result: workflow completed successfully. The web GLB excluded `eyebrow001`, `eyelashes01`, `high-poly`, `teeth_base`, and `tongue01`; the body retained all 12 morph names and `Lam_Idle_GentleSway`.
- Model: `lam-v334-accessory-isolated-candidate.glb`, 16,565,776 bytes. SHA-256: `0dc87a937ac2dd32172938a55c4de8a73e49b47261368633bb8538d000c7a7a7`. GLB contains 0 skins, 4 textures, and 3 materials.
- Browser smoke: passed at 390×844; WebGL ready, projected model bounds within view, animation running, and no page/console errors.
- Windows ZIP: `ly-lam-lam-v334-experimental-windows.zip`, 17,932,639 bytes, ZIP integrity passed with 81 entries. SHA-256 sidecar matched: `8a5491e1b4e89c57a8d3b397c49f283f3c9f033c91f8b011028856ef3b2aac2b`.
- Visual review: **NOT APPROVED**. The facial red/black patches remained even after those five accessory meshes and their textures were excluded. This narrows the remaining cause to the base skin mesh UV/material/export path rather than those accessory meshes.

## V335 — skin material / UV diagnostic (running)
- Workflow: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38563847327
- Builder: `tools/blender_v335_skin_material_uv_candidate.py`.
- V335 audits the skin image texture and UV-layer selection, activates an explicit selected UV map, and assigns an export-only material whose node path is `UVMap → Image Texture → Principled BSDF → Material Output`. V334's five accessory exclusions remain for isolation.
- Required gates: 0 skins, at least 12 facial morph names, `Lam_Idle_GentleSway`, clean browser page/console errors, model framing/visible canvas, ZIP integrity, and a matching SHA-256 sidecar.
- This remains a diagnostic candidate. A technical PASS is not an approved realistic avatar; inspect the browser image before deciding the next step.

## Safety and rollback
- Do not copy any candidate GLB into production `v312-work/lam-default.glb` or promote it through the stable registry at this stage.
- Keep test builds, images, reports, and ZIPs in versioned candidate artifacts. Record SHA-256 only after verifying actual bytes and sidecar.
- A technical PASS means the test gates succeeded; it is not equivalent to an approved realistic avatar.
