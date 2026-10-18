# Lý Lâm Lam — V2 Build Kickoff

Status: ACTIVE WORK ORDER / EXPERIMENTAL ONLY
Branch: `avatar/reference-reconstruction-v1`
Production file `lam-default.glb`: protected; do not overwrite.

## Canonical references
Use the exact persistent source files in the user's Library folder `/LÝ LÂM LAM/references/originals/`:
- `lam-frontal-face.jpeg`: mandatory frontal face.
- `lam-identity-outfit.jpeg`: identity and outfit.
- `lam-body-turnaround.jpeg`: body proportions and view continuity.

Do not substitute generated images. The source images are the authority, not examples from search.

## V2 build order
1. Ingest the exact three source files into the build workspace and record file hashes in the build report.
2. Create an isolated candidate build output directory and do not touch the production GLB.
3. Rebuild face topology and proportions first; a primitive oval with attached features is not acceptable.
4. Build long black layered hair with a natural hairline and volume; a cap with thin tube strokes is not acceptable.
5. Refine neck, shoulders, torso and limbs to the proportion sheet; keep the established teal/charcoal/white outfit.
6. Add materials, rig and facial morphs only after silhouette and likeness work.
7. Export a candidate GLB and render front, three-quarter, profile and rear.
8. Compare actual candidate renders side-by-side against the exact original images. Preserve these comparisons as artifacts.
9. Test web-viewer loading and iPhone presentation.
10. Leave all visual acceptance flags false until real evidence has been inspected and the user explicitly approves.

## Stop conditions
- Missing original source image in the build environment: stop and report; do not silently replace.
- No credible sculpted face/head or layered hair: candidate remains rejected.
- Export/CI success is not visual acceptance.
- Never replace `lam-default.glb` before user approval.

## Current state
This file records the kickoff order. It is not evidence that a new GLB has already been built. Record actual build outputs and hashes in a subsequent report only after they exist.
