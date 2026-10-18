# Lý Lâm Lam — Original Reference Asset Manifest

Status: source files identified in the active work environment; repository binary persistence is not yet complete.
Branch: `avatar/reference-reconstruction-v1`

These are the two original JPEGs attached by the user in the project conversation. Use their exact content as the sole visual acceptance source; do not replace them with generated examples. SHA-256 values below identify the files used for this work session.

| Role | Source filename in work environment | Dimensions | SHA-256 |
|---|---|---:|---|
| Primary identity and everyday outfit | `862598D2-4DFD-4C36-8486-CDE0864087E5(1).jpeg` | 1214 × 1295 | `0f77371ba2f3eb27cbd39c21850f95df0a3ffa36c00019a412809b728c3dd96a` |
| Supporting body-proportion sheet | `0DD8CC41-865C-4ADC-8DF3-4F3BC64D6EE9(1).jpeg` | 1024 × 1536 | `612bf20bc237cd359bbb5cec90798164bd14c69f869e553192e7fefda6e25bb4` |

## Use rules
- The primary identity/outfit sheet defines face, hair, expression style and everyday clothes.
- The supporting sheet is for body proportion and multi-view continuity only.
- Keep these roles distinct; do not let a generated image supersede either source.
- Compare candidate renders against these exact sources at front, three-quarter and profile views.
- Keep `tools/avatar-visual-acceptance.json` blocked until the candidate passes visual review and the user approves.
- Do not replace `lam-default.glb` before approval.

## Persistence caveat
This manifest records identity and integrity of the exact source files found in the active work environment. It does not claim that the binary JPEGs themselves have been committed to the Git repository yet. The binary asset commit remains a separate task.
