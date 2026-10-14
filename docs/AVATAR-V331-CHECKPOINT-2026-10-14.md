# Lý Lâm Lam Avatar — V331 checkpoint (2026-10-14)

## Goal
Build a separate realistic-human-topology candidate for the Lý Lâm Lam avatar. The existing production GLB and main branch are not modified. Candidate is only accepted after visual inspection and browser/mobile validation.

## Candidate source
- Builder: \`tools/blender_v331_photorealistic_candidate.py\`
- Workflow: \`.github/workflows/v331-mpfb-human-candidate.yml\`
- Work branch: \`avatar/v313-repair-candidate-20261014\`
- Source: MakeHuman Community MPFB 2, MakeHuman system asset pack (CC0), Faceunits 01 (CC0), Visemes 01.
- Target body proportions: 1.60 m, feminine, fit/healthy, moderate bust.
- Planned deliverables: editable Blender scene, textured GLB, front/three-quarter/side/face renders, 12 runtime facial morphs, subtle skeletal idle action, SHA-256 report, Windows preview ZIP.

## What has passed
- Asset download step has completed successfully in multiple runs.
- System assets archive SHA-256 is pinned to \`b542127a8e25547c7c29c19f2d1d2adb9a664c80396ecd694095dbc8028a0107\`.
- Faceunits 01 archive SHA-256 is pinned to \`d113107bd7eb59f3af4df6fc0ec29bfcc593f496d0b336aec14f086a80ce7146\`.
- Blender 4.5.3 LTS launches in headless mode.
- MPFB source revision used by the run before fixes was \`3af0cd5a2ffba072e93a34e5f6f494fdc4813ddf\`.

## Failures found and fixes
1. Importing MPFB as plain \`mpfb\` fails because Blender extension APIs require the canonical namespace.
2. Manually loading under \`bl_ext.user_default.mpfb\` without add-on preference registration fails during MPFB service initialization.
3. Copying the extension package to \`extensions/.user/user_default/mpfb\` makes Blender unable to import it as an extension. That path is the extension's *user-data* path returned by \`bpy.utils.extension_path_user\`, not the package install root.
4. The workflow now installs MPFB source to \`~/.config/blender/4.5/extensions/user_default/mpfb\`, and the builder enables it through Blender's add-on manager. MPFB data assets are extracted separately by MPFB into its own user-data path.
5. A cache-save step now persists fully downloaded asset packs even when later model-building or validation steps fail.

## Current gate
- Candidate build has not passed yet. There is no V331 screenshot or GLB that should be represented as a completed avatar.
- A new workflow run was triggered after correcting the extension install root; it must pass the MPFB enable/build step first.
- Next gates: MPFB module loads; human mesh + CC0 skin/hair/clothing load; facial targets are present; rig and idle action export; all 12 morphs exist in GLB; renders and GLB generated; mobile-sized Three.js browser test passes; packaged ZIP integrity and SHA-256 verified.
- No candidate replaces the production GLB until the renders are visually reviewed against the approved face reference.

## Production safety
V331 is experimental. Do not copy its output into the main branch or mark production approved simply because an automated build passes. Keep V330 and the last tested production GLB available as rollback candidates.


## Latest execution update
- Run \`38548182116\` was stopped while still downloading the large asset archive; no model output was produced and the archive was changing during attempted cache save, so no cache was retained.
- The current workflow is \`38549291083\` and contains the corrected \`extensions/user_default/mpfb\` package installation path, an MPFB namespace preflight, a guarded cache-save step (only after archive verification), curl low-speed failover to the second official mirror, and cancellation of stale candidate runs.
- Current checkpoint: asset download/verification is still in progress; do not treat V331 as built or passed until reports and renders are present.
