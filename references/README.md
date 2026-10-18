# Lý Lâm Lam — Canonical Reference Library

This folder is the canonical reference-documentation index for the experimental reconstruction branch. The exact user-selected source images are authoritative; generated images must never replace them.

## Required references

1. **Mandatory frontal face portrait** — [rules and integrity fingerprint](LY-LAM-MANDATORY-FRONTAL-FACE.md)
   - SHA-256: `8e20a7198e118e3f9ee199796ec7bcdb90cf0ccd9120e55227f6870d8ed7cd78`
   - 216 × 366 JPEG, 26,077 bytes.
2. **Primary identity and everyday outfit sheet** — [source manifest](LY-LAM-ORIGINAL-REFERENCE-ASSETS.md)
   - SHA-256: `0f77371ba2f3eb27cbd39c21850f95df0a3ffa36c00019a412809b728c3dd96a`
3. **Supporting full-body proportion sheet** — [source manifest](LY-LAM-ORIGINAL-REFERENCE-ASSETS.md)
   - SHA-256: `612bf20bc237cd359bbb5cec90798164bd14c69f869e553192e7fefda6e25bb4`

## Required use
- Use the frontal portrait for frontal face likeness and proportions.
- Use the primary sheet for the selected everyday identity and outfit.
- Use the supporting sheet for body proportion and multi-view continuity.
- Compare actual renders from the candidate GLB against the exact images; never use generated stand-ins.
- Keep visual acceptance blocked until all views are reviewed and the user approves.
- Keep production `lam-default.glb` unchanged until approval.

## Important storage status
The manifests fingerprint the exact uploaded source files currently available in the work environment. As of this revision, the binary JPEG files themselves have **not** been verified as committed into Git. Do not describe the images as stored in this repository until the actual binary objects are present at stable paths, for example `references/originals/lam-frontal-face.jpeg`, `references/originals/lam-identity-outfit.jpeg`, and `references/originals/lam-body-turnaround.jpeg`.
