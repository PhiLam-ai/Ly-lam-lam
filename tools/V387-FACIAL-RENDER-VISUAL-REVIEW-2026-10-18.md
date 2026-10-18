# V387 Facial Render Visual Review — 2026-10-18

## Decision

**NOT APPROVED — visual quality and facial integration fail the current acceptance gate.**

Workflow run: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/39100921478  
Commit under test: `f1b01a2062b951d3348496faa3a33806a97d8025`  
Artifact: `blender36-avatar-validation` (artifact ID `12126910333`)

## What was checked

Opened the generated PNGs from the workflow artifact, including all four directional probes and the isolated `smile` expression render. The `y_plus` view is the useful frontal view for the current model; the other views are diagnostic directions. The render job produced one neutral render and 12 isolated expression renders.

## Visual findings

1. **The head is a low-poly blockout, not a finished or photorealistic face.** Large flat polygon faces are clearly visible across the forehead, cheeks, and jaw.
2. **Facial components read as separate primitives.** The eyes are protruding spherical forms; the nose and mouth/lip shapes are separate pieces rather than integrated facial anatomy.
3. **The jaw/chin and mouth are visually disconnected or layered as separate objects.** The smile render changes the mouth region, but this is not evidence of a natural smile deformation.
4. **The head, neck, and shoulder region show obvious gaps/discontinuities.** The lower face ends above a detached neck segment; small detached geometry is visible near the shoulders in the close-up.
5. **Expression renders are diagnostic only.** The pipeline confirms that shape keys can be rendered, not that the expressions are anatomically correct, smooth, or production-ready.
6. The artifact does not establish realistic skin/hair materials, natural eyelids, a coherent mouth cavity, or mobile/web quality.

## Required next steps

- Keep the camera at the verified `Y+` frontal direction for the next facial diagnostic pass.
- Fix the underlying face/head/neck geometry and component integration before spending time tuning expressions.
- Replace or remodel the primitive eye/nose/mouth forms; ensure the jaw and mouth move as a coherent system.
- Render neutral, smile, both blinks, mouth-open, brow-raise, jaw-open, and phoneme shapes from identical camera/light settings.
- Review front, three-quarter, and profile views, then test the actual GLB in the web viewer and on mobile.
- Keep the candidate and PR unmerged until all visual, deformation, browser, and mobile gates are explicitly approved.

## Scope and production safety

This review documents a visual rejection of the current facial render. It does not alter production assets. The production avatar remains unchanged. CI success is not visual approval.
