# Reference image below Notes

The existing reference-image box now spans the full ticket width below Notes,
320px tall on desktop and 240px on small screens, replacing the 188px-wide
side box. Materials use the reclaimed width. Images keep their proportions and
remain fully visible. Existing image markup IDs and all JavaScript blocks are
unchanged. Upload/change/remove/drop, saved image URLs and restoration continue
through their existing paths.

Source commit [`83ab625a5f3ae66bb6dd189657000f4770841954`](https://github.com/krf1786/jobticket/commit/83ab625a5f3ae66bb6dd189657000f4770841954)
passed **57 frontend scenarios** and **12 local layout/image checks**, including
1200px, 390px and 320px widths, scratch FileReader upload and saved-image
restoration/edit/reload. Source hashes, script syntax, bootstrap safety and
preview API rejection passed. Screen and mobile screenshots were inspected.
Rasterized Letter PDFs show a short ticket on one page; a 65-line notes fixture
retains every line across three pages, with the image intact on its final page.

The template was published atomically at **2026-10-22 22:12:10 UTC**. SHA-256:

`a7f65bd7dfe0c12eec7bf177ae37a2ebaa52d69c6590cda10c0ecc0286b7e7c8`

Public scratch and designated saved responses match the new source. All **15
live checks** passed, covering placement, responsive sizing, scratch-only upload
and removal, Letter output, unchanged SB0000 header identity, saved layout and
reload. SB0000 had no reference image, so live saved-image payload restoration
was not exercised; that path passed the synthetic local checks. The live-page
Letter PDF was generated locally and visually inspected. No API write was
allowed or attempted. The final server audit at **22:13:18 UTC** confirmed all
16 ticket rows unchanged, unchanged backend hashes, the same service process
and healthy service. There were no JavaScript errors or unapproved requests.

Only `ticket.html` changed at runtime. The previous template and consistent,
integrity-checked SQLite backup are in:

`/root/jobticket/release-backups/reference-image-20261022T221210Z/`

Prepared rollback (not invoked):

```sh
python3 /root/jobticket/release-backups/reference-image-20261022T221210Z/rollback.py
```

It guards against later template changes and restores only the prior template,
without a database restore or restart. Recheck scratch and saved rendering after
rollback. This follow-up uses a new branch after PR #1 was merged and is not
automatically merged. Teams/PDF production delivery remains disabled and
unverified. See [sanitized release evidence](release-evidence.json).
