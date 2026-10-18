# Lý Lâm Lam — Mandatory Frontal Face Reference

Status: REQUIRED / DO NOT SUBSTITUTE
Repository branch: `avatar/reference-reconstruction-v1`
Source: exact user-uploaded JPEG in the project conversation

- Role: **mandatory frontal face standard**
- Dimensions: 216 × 366 px
- SHA-256: `8e20a7198e118e3f9ee199796ec7bcdb90cf0ccd9120e55227f6870d8ed7cd78`
- File size: 26,077 bytes

## What it governs
Use this exact portrait to compare the frontal face: center part and hairline, forehead, face silhouette, eye shape and spacing, eyelids, eyebrows, nose bridge and tip, lips, jaw/chin, and natural expression. Jewelry is secondary and cannot substitute for face likeness.

## Reference hierarchy
1. This image: mandatory frontal face identity and proportions.
2. The previously selected dark-teal top / charcoal cargo pants / white sneakers sheet: everyday identity styling and outfit.
3. The previously selected full-body turnaround sheet: body proportion and front/side/back continuity.

No generated or unrelated portrait may replace these references. Render the actual candidate GLB from the front and compare against this exact portrait; also review three-quarter and profile views against the established sheets.

## Acceptance and production safety
Keep all visual acceptance flags false until the real rendered model is reviewed and the user approves. Do not replace `lam-default.glb` before approval.

## Binary persistence caveat
This manifest identifies the exact uploaded image by dimensions and SHA-256. It does not claim that the JPEG binary itself has been committed into the Git repository; the image asset must be uploaded as a binary Git object before claiming repository persistence.
