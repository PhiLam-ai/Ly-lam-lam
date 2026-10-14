# Lý Lâm Lam avatar candidate checkpoint — V348–V349 (2026-10-14)

## Release decision

**No candidate here is approved as the production avatar.** Production `v312-work/lam-default.glb` is not to be replaced by this experimental eye-material branch. All work remains on `avatar/v313-repair-candidate-20261014`.

## V348 — front eye surface response experiment

- Workflow: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38592942741 — **FAILED at a validation assertion after GLB export and render generation**.
- Script: `tools/blender_v348_eye_front_surface_response.py`.
- Artifact: [V348 diagnostic artifact](https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38592942741/artifacts/11908337440), ID `11908337440`; workflow artifact digest `sha256:0168c8b872475bce2cdb1d25eb1238364c74f718ec4c2dcb10a7833e8bb78272`.
- The visual evidence includes `v348-eye-closeup.png`. It shows brown iris texture and eyelash detail; the front eye-shell component is assigned a restrained glTF-compatible response (roughness 0.18, specular IOR level 0.50, clearcoat 0.30, clearcoat roughness 0.14), while the base eye material and image are preserved.
- Root cause of the failing gate: it compared `pbrMetallicRoughness.baseColorTexture.index` between the base eye and front eye materials. In glTF this is a **texture-object index**, not an image identifier. The exported GLB legitimately has two texture entries that both point to the same embedded `brown_eye` image: base texture index `5` → image source `5`, front texture index `6` → image source `5`. Thus the check rejected a valid shared-image mapping.
- The fix must compare `gltf.textures[textureIndex].source` values, validate each source index, and record both texture and image-source indices. The evidence indicates a faulty assertion, not proof that the wrong diffuse image was used.

## V349 — validate shared eye image by glTF source index (rerun in progress)
- First workflow attempt: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38599437117 — **FAILED** in the audit/report code after successful GLB export and eye-closeup render. The GLB had the expected source-image mapping (base texture index 5 → image source 5; front texture index 6 → image source 5), but the new report tried to read `eye_image_source_index` before it had been initialized.
- Fix commit: `9a9f0306a6be5b68bf22882baa55e4c7ef9aa75c` moves base-image source resolution before building the base-eye report. It changes no geometry or material values.
- Current validation rerun: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38600138150.
- Script: `tools/blender_v349_eye_front_surface_texture_source_fix.py`.
- V349 carries forward the V348 front-eye material experiment, V340 body silhouette, V341 darkened hair material, and a closed-mouth gentle default smile from the later smile branch. It changes only validation/reporting of the eye's shared diffuse image; it does not increase eye size or move eye geometry.
- New report fields include `base_color_image_source_index`, `base_color_image_name`, and `same_image_source_as_base_eye` for the two eye materials. The workflow gate verifies source-index equality, both material extensions, roughness values, transparency mode, 12 expected morphs, idle animation, mobile WebGL load, no browser/console/failed-request errors, ZIP integrity and SHA-256 sidecar.
- Visual review is pending until the rerun produces its report, GLB, eye close-up and browser capture. A technical PASS would validate the export and test path; it would not by itself approve the full avatar likeness.
## V350 — front-eye specular extension export fix (run in progress)
- Workflow: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38600818409.
- Script: `tools/blender_v350_eye_front_surface_specular_export.py`.
- V349's next failure was real: the front material exported `KHR_materials_clearcoat` but omitted `KHR_materials_specular`. The front Principled BSDF had `Specular IOR Level = 0.50`, exactly Blender's default, so the glTF exporter omitted the extension; the base eye did export it because its value was `0.38`.
- V350 sets only the front-eye `Specular IOR Level` from `0.50` to `0.48`, which should result in a non-default glTF `specularFactor` near `0.96`. The workflow now explicitly requires that factor and the existing clearcoat factor (~`0.30`) to appear in the GLB. Roughness (`0.18`), clearcoat roughness (`0.14`), image-source mapping, alpha, UV, geometry and all other assets remain unchanged.
- V350 continues to verify that the base and front eye texture entries both map to the same embedded `brown_eye` image source. The expected run must also pass 12 morphs, `Lam_Idle_GentleSway`, 390×844 browser load, no browser/console/request errors, ZIP integrity and SHA-256 sidecar.
- Visual decision is pending. Do not promote based on material JSON alone; review the generated eye close-up and browser capture for restrained catchlights, no plastic glare, and no face change.
## Separate smile-strength experiments

The repo has parallel experimental tracks that reused some V34x version numbers. Use the workflow run ID and exact script path as the unique identifier rather than the version label alone. The successful closed-lip smile track reached V345 at strength 0.40; the V346 eye-material diagnostic is a separate run from the later “V346 stronger smile with lip closure” candidate. Keep these checkpoints distinct when comparing assets.

## Safety and rollback

- Do not copy a candidate GLB into production `v312-work/lam-default.glb` or promote it through the stable registry.
- Record file checksums only after recomputing actual downloaded bytes and matching the sidecar.
- Preserve the stable avatar and previous successful candidate artifacts; visual review remains mandatory after every material/geometry change.
