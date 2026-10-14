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
## V350 — front-eye specular extension export fix (validation rerun)
- Earlier workflow attempts: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38600818409 (first had a duplicated comma in the summary) and its rerun https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38601219481 (second had two missing commas in the embedded report dictionary). Both reached GLB export; neither ran the mobile/browser gates.
- The GLB from the initial attempt (`lam-v350-gltf-materials-full-face-candidate.glb`, 20,484,436 bytes, SHA-256 `9e36f37c6e12dfbded9c47dcbf0cfbbfd7e339112aa5a32bcc4d11d9bc0f05ee`) was independently inspected. It contains `V350_GltfEyeFrontSurface` with `KHR_materials_specular.specularFactor ≈ 0.96`, clearcoat `0.30`, roughness `0.18`, and `alphaMode=BLEND`. Both the base and front eye texture entries map to image source index `5` (`brown_eye`).
- Latest validation run after fixing both summary syntax issues: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38601681760.
- Script: `tools/blender_v350_eye_front_surface_specular_export.py`; workflow: `.github/workflows/v350-eye-front-surface-specular-export.yml`.
- New front-eye specular setting is `0.48` in Blender so glTF exports a non-default factor near `0.96`; the base material is unchanged (`0.38` / `0.76`). Clearcoat remains `0.30`, coat roughness `0.14`, front roughness `0.18`. Eye size/position, `brown_eye` image/UV/alpha, V340 body shape, V341 hair, the 0.40 closed-mouth smile and the 12 morphs are unchanged.
- Visual decision pending. The image from the pre-summary-failure artifact shows the same eye/face shape; the successful final run must still pass browser/WebGL, no page/console/request errors, ZIP integrity and SHA-256 sidecar. Whole avatar remains not approved for production.
## Separate smile-strength experiments

The repo has parallel experimental tracks that reused some V34x version numbers. Use the workflow run ID and exact script path as the unique identifier rather than the version label alone. The successful closed-lip smile track reached V345 at strength 0.40; the V346 eye-material diagnostic is a separate run from the later “V346 stronger smile with lip closure” candidate. Keep these checkpoints distinct when comparing assets.

## Safety and rollback

- Do not copy a candidate GLB into production `v312-work/lam-default.glb` or promote it through the stable registry.
- Record file checksums only after recomputing actual downloaded bytes and matching the sidecar.
- Preserve the stable avatar and previous successful candidate artifacts; visual review remains mandatory after every material/geometry change.
