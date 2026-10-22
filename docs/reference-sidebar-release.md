# Reference image beside job fields and Materials

The supplied annotated layout supersedes the image-below-Notes arrangement.
Job Information has a full-width heading. Date, Qty, Due Date and Time sit in
one row above Materials in a left column, with a large reference image on the
right. Production Steps and Notes remain full width below both columns. Pink
reference annotations are layout guides and are not added as UI styling.

The overview stacks at 760px and below, keeping native date/time controls usable.
Fields use two columns at 600px and below. The image starts at 240px tall and
stretches with the left column on screen, preserving its full proportions.
Print caps its height at 240px so long material lists cannot stretch the image
across pages. All existing IDs and JavaScript blocks remain unchanged.

Source commit [`5cbf34497197daa5785fd74a6fcc8637ecf2bfcb`](https://github.com/krf1786/jobticket/commit/5cbf34497197daa5785fd74a6fcc8637ecf2bfcb)
passed **57 frontend scenarios** and **45 focused layout/image checks** across
ten widths from 1200px to 320px. Checks cover field order, compact material rows,
portrait/landscape containment and saved-image edit/reload. Source hashes,
JavaScript syntax, bootstrap safety and preview API rejection passed. Desktop
and mobile screenshots were compared with the supplied layout. A five-row
synthetic ticket prints on one Letter page. A 45-row fixture prints on two
pages, with every detail retained and the image intact on page one.

The template was published atomically at **2026-10-22 23:38:46 UTC**. SHA-256:

`da5de083514982975c8bd8572749f83f710ee605345ae649f3bc59a7e172936e`

Public scratch and saved responses match this source. All **30 live checks**
passed, covering desktop/tablet/mobile arrangement, field order, full-width
Production/Notes, scratch upload/removal, local Letter output and saved layout
reload/header identity. SB0000 inspection was read-only; it had no stored image,
so saved-image payload restoration remains local synthetic evidence. No API
write was allowed or attempted. The final audit at **23:39:36 UTC** confirmed
all 16 ticket rows unchanged, unchanged backend hashes, the same service process
and healthy service. There were no page errors or unapproved requests.

Only `ticket.html` changed at runtime. Previous-template and integrity-checked
SQLite backups are in:

`/root/jobticket/release-backups/reference-sidebar-20261022T233846Z/`

Prepared rollback (not invoked):

```sh
python3 /root/jobticket/release-backups/reference-sidebar-20261022T233846Z/rollback.py
```

It guards against later template changes and restores only the previous
image-below-Notes template. It does not restore the database or restart the
service. Recheck scratch and saved rendering after rollback. PR #2 is updated
and remains unmerged. Production PDF/Teams delivery remains disabled and
unverified. See [sanitized evidence](release-evidence.json).
