# Full-size reference image preview

Clicking a displayed reference image opens a native modal viewer. Images start
fitted to the viewport; **Actual size** shows original dimensions with scrolling,
and **Fit to screen** restores the fitted view. Close, Escape or a backdrop click
dismisses the viewer and returns focus to its trigger. Enter/Space open the
viewer; the labeled scrolling region is keyboard-focusable. Touch devices keep
Change/Remove controls visible. The empty box still opens the upload picker.

Viewing does not change image URLs or ticket state and sends no save, upload or
Teams requests. Removal and Reset clear the viewer source. Print closes/hides
the viewer and retains the existing sidebar reference image without a focus
outline. No dependencies or backend changes were introduced.

## Verification

The final source passed **57 existing frontend scenarios** and **35 new viewer
checks**, including saved-image restoration, portrait/landscape containment,
1200/760/390/320px widths, keyboard activation/panning, focus restoration,
replacement/removal, original dimensions, print and absence of API requests.
Source hashes, three inline JavaScript syntax checks, safe bootstrap embedding
and loopback preview API rejection passed. Desktop/mobile screenshots and a
rasterized one-page Letter PDF were inspected. An independent source review
identified the keyboard-scroll accessibility improvement before publication.
Browser evidence uses Chromium; Safari was not run. Saved-image payload checks
used local synthetic bootstrap data.

## Publication and rollback

Code commit `fbce9f3635b99ab3d0c2d221b7a1279d4514a733` was published atomically at
**2026-10-23 00:57:42 UTC** (October 22 locally). Template SHA-256:

`69578352c0bd3cf64f41fb99ba72a69c1b72fed5ade270b04fc3d6be3441f53a`

Public scratch and the existing synthetic saved template responses match source.
**17 live checks** passed using an unsaved synthetic scratch image with all API
writes blocked. The final read-only audit at **00:58:06 UTC** confirmed all 16
ticket rows unchanged, unchanged backend hashes, the same service process and
healthy service. Production Teams/PDF delivery remains disabled and unverified.
PR #2 remains open and unmerged; a Git push does not deploy this service.

The previous template, integrity-checked consistent SQLite backup and guarded
rollback are in `/root/jobticket/release-backups/image-preview-20261023T005742Z/`.
Prepared rollback (not invoked):

```sh
python3 /root/jobticket/release-backups/image-preview-20261023T005742Z/rollback.py
```

It refuses to overwrite a later template and restores only the previous template
(SHA-256 `97724720c29af92ad17de6ea2bb5b33f7358bc6eea721b93a66c608af752dee8`).
It does not restore the database or restart the service. Verify scratch and saved
rendering after rollback. See [sanitized release evidence](release-evidence.json).
